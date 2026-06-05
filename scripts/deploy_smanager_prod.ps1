param(
  [string]$Domain = "smanager.i-am-ikun.online",
  [string]$RemoteHost = "86.53.110.229",
  [string]$RemoteUser = "root",
  [int]$RemoteSshPort = 22,
  [int]$FrpsPort = 7000,
  [int]$LocalBackendPort = 8000,
  [int]$RemoteBackendPort = 18000,
  [string]$FrpDir = "D:\frp_0.69.1_windows_amd64",
  [string]$RemoteStaticRoot = "/usr/share/nginx/html/smanager",
  [string]$RemoteNginxConf = "/etc/nginx/conf.d/smanager.conf",
  [string]$Python = "C:\ProgramData\miniconda3\envs\smanager\python.exe",
  [switch]$SkipBuild,
  [switch]$SkipFrpc
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $repoRoot "frontend"
$runtimeDir = Join-Path $repoRoot "runtime\deploy"
$zipPath = Join-Path $runtimeDir "smanager-dist.zip"
$frpcConfig = Join-Path $FrpDir "frpc.toml"

if (-not $env:PROD_SSH_PASSWORD) {
  throw "Set PROD_SSH_PASSWORD in this shell before deploying."
}
if (-not (Test-Path $Python)) {
  throw "Python was not found: $Python"
}
if (-not (Test-Path (Join-Path $FrpDir "frpc.exe"))) {
  throw "frpc.exe was not found under $FrpDir"
}

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

if (-not $SkipBuild) {
  Push-Location $frontendDir
  try {
    npm run build
  } finally {
    Pop-Location
  }
}

if (Test-Path $zipPath) {
  Remove-Item -Force $zipPath
}
& $Python -c @"
from pathlib import Path
import zipfile
root = Path(r'$frontendDir') / 'dist'
out = Path(r'$zipPath')
if not root.exists():
    raise SystemExit(f'frontend dist not found: {root}')
with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for path in root.rglob('*'):
        if path.is_file():
            zf.write(path, path.relative_to(root).as_posix())
print(out)
"@

$frpcToml = @"
serverAddr = "$RemoteHost"
serverPort = $FrpsPort

[[proxies]]
name = "smanager-backend"
type = "tcp"
localIP = "127.0.0.1"
localPort = $LocalBackendPort
remotePort = $RemoteBackendPort
"@
Set-Content -Path $frpcConfig -Value $frpcToml -Encoding ASCII

if (-not $SkipFrpc) {
  $existing = Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -like "*frpc*" -and $_.CommandLine -like "*$FrpDir*" }
  $ids = @($existing | Select-Object -ExpandProperty ProcessId)
  if ($ids.Count -gt 0) {
    Stop-Process -Id $ids -Force
    Start-Sleep -Seconds 2
  }
  Start-Process -FilePath (Join-Path $FrpDir "frpc.exe") `
    -ArgumentList @("-c", $frpcConfig) `
    -WorkingDirectory $FrpDir `
    -RedirectStandardOutput (Join-Path $repoRoot "runtime\logs\frpc.out.log") `
    -RedirectStandardError (Join-Path $repoRoot "runtime\logs\frpc.err.log") `
    -WindowStyle Hidden
  Start-Sleep -Seconds 4
}

$env:DEPLOY_DOMAIN = $Domain
$env:DEPLOY_REMOTE_HOST = $RemoteHost
$env:DEPLOY_REMOTE_USER = $RemoteUser
$env:DEPLOY_REMOTE_PORT = [string]$RemoteSshPort
$env:DEPLOY_ZIP_PATH = $zipPath
$env:DEPLOY_STATIC_ROOT = $RemoteStaticRoot
$env:DEPLOY_NGINX_CONF = $RemoteNginxConf
$env:DEPLOY_BACKEND_PORT = [string]$RemoteBackendPort

$deployPython = @'
import os
from pathlib import Path
import paramiko

domain = os.environ["DEPLOY_DOMAIN"]
host = os.environ["DEPLOY_REMOTE_HOST"]
user = os.environ["DEPLOY_REMOTE_USER"]
port = int(os.environ["DEPLOY_REMOTE_PORT"])
password = os.environ["PROD_SSH_PASSWORD"]
zip_path = Path(os.environ["DEPLOY_ZIP_PATH"])
static_root = os.environ["DEPLOY_STATIC_ROOT"]
nginx_conf = os.environ["DEPLOY_NGINX_CONF"]
backend_port = os.environ["DEPLOY_BACKEND_PORT"]
remote_zip = "/tmp/smanager-dist.zip"
remote_conf = "/tmp/smanager.conf.new"

conf = f"""map $http_upgrade $connection_upgrade {{
    default upgrade;
    ''      close;
}}

server {{
    listen 80;
    listen 443 ssl;
    http2 on;
    server_name {domain};

    ssl_certificate     /etc/v2ray-agent/tls/www.i-am-ikun.online.crt;
    ssl_certificate_key /etc/v2ray-agent/tls/www.i-am-ikun.online.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         TLS13_AES_128_GCM_SHA256:TLS13_AES_256_GCM_SHA384:TLS13_CHACHA20_POLY1305_SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers on;

    root {static_root};
    index index.html;
    client_max_body_size 100m;

    location /api/ {{
        proxy_pass http://127.0.0.1:{backend_port};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }}

    location /health {{
        proxy_pass http://127.0.0.1:{backend_port}/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    location / {{
        try_files $uri $uri/ /index.html;
    }}
}}
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=host, port=port, username=user, password=password, timeout=15)

def run(command: str, timeout: int = 120) -> str:
    _stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if code:
        raise RuntimeError(f"remote command failed {code}: {command}\nSTDOUT:\n{out}\nSTDERR:\n{err}")
    return out

sftp = client.open_sftp()
try:
    sftp.put(str(zip_path), remote_zip)
    tmp_conf = Path(os.environ.get("TEMP", ".")) / "smanager.conf.new"
    tmp_conf.write_text(conf, encoding="utf-8")
    sftp.put(str(tmp_conf), remote_conf)
finally:
    sftp.close()

run(f"""
set -e
backup={nginx_conf}.$(date +%Y%m%d%H%M%S).bak
[ -f {nginx_conf} ] && cp {nginx_conf} "$backup" || true
rm -rf {static_root}
mkdir -p {static_root}
if command -v unzip >/dev/null 2>&1; then
  unzip -q {remote_zip} -d {static_root}
else
  python3 - <<'PYZIP'
import zipfile
zipfile.ZipFile('{remote_zip}').extractall('{static_root}')
PYZIP
fi
mv {remote_conf} {nginx_conf}
nginx -t
systemctl reload nginx || nginx -s reload
""")

print(run(f"""
echo '[remote] static files:'
find {static_root} -maxdepth 2 -type f | sort | head -20
echo '[remote] health:'
curl -sS --max-time 8 http://127.0.0.1/health
echo
echo '[remote] api auth status:'
curl -sS --max-time 8 -H 'Host: {domain}' http://127.0.0.1/api/v1/auth/me -o /tmp/smanager-api.out -w '%{{http_code}}\n'
head -c 200 /tmp/smanager-api.out; echo
"""))
client.close()
'@
$deployPython | & $Python -

Write-Host "Deployment complete: https://$Domain/"
