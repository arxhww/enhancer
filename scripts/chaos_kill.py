import os, time, subprocess

p = subprocess.Popen(["python", "-m", "cli.main", "apply", "tests/test_tweaks/minimal.json"])
time.sleep(0.2)
os.kill(p.pid, 9)
