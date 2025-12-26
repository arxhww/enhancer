import os
import sys
import subprocess
import shutil
from pathlib import Path

APP_NAME = "EnhancerCore"
ENTRY_POINT = "main.py"  
ICON_FILE = None # "assets/icon.ico" ...
ONE_FILE = True 

def clean_build():
    dirs_to_clean = ['build', 'dist']
    for d in dirs_to_clean:
        if os.path.exists(d):
            shutil.rmtree(d)
    print(f"[CLEAN] Directories {dirs_to_clean} removed.")

def build():
    print(f"[BUILD] Initializing packaging of {APP_NAME}...")
    
    cmd = [
        sys.executable, 
        "-m",
        "PyInstaller",
        "--name", APP_NAME,
        "--clean"
    ]
    
    if ONE_FILE:
        cmd.append("--onefile")
        
    cmd.append(ENTRY_POINT)
    
    print(f"[CMD] Executing: {' '.join(cmd)}")
    
    subprocess.run(cmd, check=True)
    dist_path = Path("dist")
    tweaks_src = Path("tweaks")
    tweaks_dst = dist_path / "tweaks"

    if tweaks_dst.exists():
        shutil.rmtree(tweaks_dst)

    shutil.copytree(tweaks_src, tweaks_dst)
    print("[BUILD] tweaks/ folder copied to dist/")
    print(f"[BUILD] Completed. Check the 'dist' folder.")

if __name__ == "__main__":
    clean_build()
    build()