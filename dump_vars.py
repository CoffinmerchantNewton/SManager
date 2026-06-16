import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname='10.40.140.17', port=22, username='anxq', password='ams@2605', timeout=30)

sftp = client.open_sftp()
with sftp.open('/tmp/dump_vars.py', 'w') as f:
    f.write('import subprocess\n')
    f.write('good = "/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/runs/lijt_hybrid_neimeng_20240701_20240721/case/WRFChem_autumn_Beijing_pre3/WPS_met_save_data/pre20days_12-12_2/2024/20240701/met_em.d01.2024-06-30_12:00:00.nc"\n')
    f.write('bad = "/g7/anxq/Zhangjt/workspace/Smanager/auto-pollen-flow/runs/lijt_hybrid_neimeng_20240701_20240721/case/WRFChem_autumn_Beijing_pre3/WPS_met_save_data/pre20days_12-12_2/2024/20240701/met_em.d01.2024-06-30_18:00:00.nc"\n')
    f.write('for label, path in [("GOOD", good), ("BAD", bad)]:\n')
    f.write('    print(f"=== {label} ===")\n')
    f.write('    r = subprocess.run(["ncdump", "-h", path], capture_output=True, text=True)\n')
    f.write('    for line in r.stdout.splitlines():\n')
    f.write('        s = line.strip()\n')
    f.write('        if s.startswith("float") or s.startswith("int") or "soil" in s.lower() or "num_metgrid" in s.lower() or "flag_soil" in s.lower():\n')
    f.write('            print(s)\n')
    f.write('    print()\n')
sftp.close()

stdin, stdout, stderr = client.exec_command('python3 /tmp/dump_vars.py', timeout=30)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err[:500])
client.close()
