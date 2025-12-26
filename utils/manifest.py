import hashlib
import json
import os
from pathlib import Path

CORE_FILES = [
    "core/__init__.py",
    "core/registry.py",
    "core/rollback.py",
    "core/tweak_manager.py",
    
    "core/recovery.py",
    "core/tweak_id.py",
    
    "core/actions/__init__.py",
    "core/actions/base.py",
    "core/actions/factory.py",
    "core/actions/registry_action.py",
    "core/actions/verify_action.py",
    
    "utils/__init__.py",
    "utils/admin.py",
    "utils/manifest.py",
    
    "main.py"
]

def calculate_hash(filepath):
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256.update(byte_block)
        return sha256.hexdigest()
    except FileNotFoundError:
        print(f"  [WARN] File not found: {filepath}")
        return None

def generate_manifest():
    manifest = {
        "version": "1.1.1",
        "engine_name": "EnhancerCore",
        "files": {}
    }
    
    base_path = Path(__file__).parent.parent 
    
    for file_rel in CORE_FILES:
        file_path = base_path / file_rel
        if file_path.exists():
            h = calculate_hash(file_path)
            manifest["files"][file_rel] = h
            print(f"[HASH] {file_rel}: {h[:16]}...")
        else:
            print(f"[WARN] Missing file: {file_rel}")
            
    return manifest

def verify_manifest(manifest_path="enhancer_manifest.json"):
    base_path = Path(__file__).parent.parent
    manifest_location = base_path / manifest_path
    
    if not manifest_location.exists():
        print(f"[SECURITY] No manifest found at {manifest_location}.")
        return False
        
    with open(manifest_location, 'r') as f:
        stored_manifest = json.load(f)
        
    print(f"[SECURITY] Verifying integrity of engine v{stored_manifest['version']}...")
    
    is_valid = True
    for file_rel, stored_hash in stored_manifest["files"].items():
        file_path = base_path / file_rel
        current_hash = calculate_hash(file_path)
        
        if current_hash is None:
             print(f"[WARN] File missing in verification: {file_rel}")
             continue
        
        if current_hash != stored_hash:
            print(f"[ALERT] FILE MODIFIED: {file_rel}")
            is_valid = False
        else:
            print(f"[OK] {file_rel}")
            
    if is_valid:
        print("[SECURITY] Integrity of engine preserved.")
    else:
        print("[SECURITY] CRITICAL: Modifications detected in the core.")

    return is_valid

if __name__ == "__main__":
    man = generate_manifest()

    dist_path = Path(__file__).parent.parent / "dist"
    dist_path.mkdir(exist_ok=True)

    manifest_file = dist_path / "enhancer_manifest.json"

    with open(manifest_file, "w") as f:
        json.dump(man, f, indent=4)

    print(f"\n[SUCCESS] Manifest generated at: {manifest_file}")