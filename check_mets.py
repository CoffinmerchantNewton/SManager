import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname='10.40.140.17', port=22, username='anxq', password='ams@2605', timeout=30)
script = """#!/bin/bash
DIR=/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/runs/lijt_hybrid_neimeng_20240701_20240721/case/WRFChem_autumn_Beijing_pre3/WPS_met_save_data/pre20days_12-12_2/2024/20240701
cd "$DIR"
for f in met_em.d01.*.nc; do
  size=$(stat -c%s "$f" 2>/dev/null)
  if ncdump -h "$f" >/dev/null 2>&1; then
    echo "OK     $f  size=$size"
  else
    echo "CORRUPT $f  size=$size"
  fi
done
echo "TOTAL_FILES: $(ls met_em.d01.*.nc 2>/dev/null | wc -l)"
"""
sftp = client.open_sftp()
with sftp.open('/tmp/check_mets.sh', 'w') as f:
    f.write(script)
sftp.close()
stdin, stdout, stderr = client.exec_command('bash /tmp/check_mets.sh', timeout=120)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('STDERR:', err[:500])
client.close()
