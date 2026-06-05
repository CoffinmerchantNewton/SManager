# SManager Production Deploy

## Topology

- Browser: `https://smanager.i-am-ikun.online/`
- Nginx on `86.53.110.229`: serves static frontend from `/usr/share/nginx/html/smanager`.
- Nginx `/api/` and `/health`: proxies to `http://127.0.0.1:18000`.
- frpc on the Windows jumpbox: forwards local backend `127.0.0.1:8000` to server port `18000`.

## Deploy

Run from the repository root on the Windows jumpbox:

```powershell
$env:PROD_SSH_PASSWORD = "<server password>"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/deploy_smanager_prod.ps1
```

The script builds `frontend/dist`, uploads it to the server, rewrites `/etc/nginx/conf.d/smanager.conf`, reloads nginx, writes `D:\frp_0.69.1_windows_amd64\frpc.toml`, and starts frpc.

For a static-only redeploy using the existing build:

```powershell
$env:PROD_SSH_PASSWORD = "<server password>"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/deploy_smanager_prod.ps1 -SkipBuild
```

## Checks

```powershell
curl.exe -k https://smanager.i-am-ikun.online/
curl.exe -k https://smanager.i-am-ikun.online/health
curl.exe -k https://smanager.i-am-ikun.online/api/v1/auth/me
```

Expected:

- `/` returns `200 OK` and `index.html`.
- `/health` returns `{"status":"healthy"}`.
- `/api/v1/auth/me` returns `401` when no bearer token is supplied.
