import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname='10.40.140.17', port=22, username='anxq', password='ams@2605', timeout=30)

PY = "/g7/anxq/Zhangjt/softwares/miniconda3/envs/wrfTool/bin/python"

sftp = client.open_sftp()
with sftp.open('/tmp/dump_vars3.sh', 'w') as f:
    f.write('#!/bin/bash\n')
    f.write('module load netcdf 2>/dev/null || true\n')
    f.write('which ncdump 2>/dev/null\n')
    f.write('DIR=/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/runs/lijt_hybrid_neimeng_20240701_20240721/case/WRFChem_autumn_Beijing_pre3/WPS_met_save_data/pre20days_12-12_2/2024/20240701\n')
    f.write('echo "=== GOOD 12Z ==="\n')
    f.write('ncdump -h "$DIR/met_em.d01.2024-06-30_12:00:00.nc" 2>&1 | grep -c "float" \n')
    f.write('ncdump -h "$DIR/met_em.d01.2024-06-30_12:00:00.nc" 2>&1 | grep -iE "soil|ST0|SM0|num_metgrid|flag_soil" \n')
    f.write('echo "=== BAD 18Z ==="\n')
    f.write('ncdump -h "$DIR/met_em.d01.2024-06-30_18:00:00.nc" 2>&1 | grep -c "float" \n')
    f.write('ncdump -h "$DIR/met_em.d01.2024-06-30_18:00:00.nc" 2>&1 | grep -iE "soil|ST0|SM0|num_metgrid|flag_soil" \n')
    f.write('echo "=== NML ==="\n')
    f.write('grep -E "num_metgrid|num_soil" /g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/runs/lijt_hybrid_neimeng_20240701_20240721/case/WRFChem_autumn_Beijing_pre3/WRF-pollen1/WRF-pollen_Tot_Arte_Chen/test/em_real/namelist.input 2>/dev/null\n')
sftp.close()

stdin, stdout, stderr = client.exec_command('bash -lc "/tmp/dump_vars3.sh"', timeout=30)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err[:500])
client.close()
