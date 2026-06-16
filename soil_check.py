import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname='10.40.140.17', port=22, username='anxq', password='ams@2605', timeout=30)
script = """#!/bin/bash
DIR=/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/runs/lijt_hybrid_neimeng_20240701_20240721/case/WRFChem_autumn_Beijing_pre3/WPS_met_save_data/pre20days_12-12_2/2024/20240701
echo "=== Good file (2024-06-30_12:00:00) ==="
ncdump -h "$DIR/met_em.d01.2024-06-30_12:00:00.nc" 2>&1 | grep -E "num_metgrid|SOIL|ST[0-9]|SM[0-9]|flag_soil|num_st_levels|num_sm_levels"
echo ""
echo "=== Bad file (2024-06-30_18:00:00) ==="
ncdump -h "$DIR/met_em.d01.2024-06-30_18:00:00.nc" 2>&1 | grep -E "num_metgrid|SOIL|ST[0-9]|SM[0-9]|flag_soil|num_st_levels|num_sm_levels"
echo ""
echo "=== Good file full vars ==="
ncdump -h "$DIR/met_em.d01.2024-06-30_12:00:00.nc" 2>&1 | grep -E "float|int|char" | head -60
"""
sftp = client.open_sftp()
with sftp.open('/tmp/soil_check.sh', 'w') as f:
    f.write(script)
sftp.close()
stdin, stdout, stderr = client.exec_command('bash /tmp/soil_check.sh', timeout=30)
print(stdout.read().decode())
err = stderr.read().decode()
if err: print('STDERR:', err[:500])
client.close()
