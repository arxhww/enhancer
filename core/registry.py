import winreg

REG_TYPES = {
    "DWORD": winreg.REG_DWORD,
    "QWORD": winreg.REG_QWORD,
    "SZ": winreg.REG_SZ,
    "EXPAND_SZ": winreg.REG_EXPAND_SZ,
    "BINARY": winreg.REG_BINARY,
}

HIVES = {
    "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
    "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
    "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
    "HKEY_USERS": winreg.HKEY_USERS,
    "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG,
}

def parse_registry_path(full_path):
    parts = full_path.split("\\", 1)
    hive_name = parts[0]
    subkey = parts[1] if len(parts) > 1 else ""
    
    if hive_name not in HIVES:
        raise ValueError(f"Invalid hive: {hive_name}")
    
    return HIVES[hive_name], subkey

def subkey_exists(path):
    hive, subkey = parse_registry_path(path)
    
    try:
        reg_key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ)
        winreg.CloseKey(reg_key)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False

def set_value(path, key, value, reg_type, force=False):
    hive, subkey = parse_registry_path(path)
    
    if isinstance(reg_type, str):
        if reg_type not in REG_TYPES:
            raise ValueError(f"Invalid registry type: {reg_type}")
        reg_type = REG_TYPES[reg_type]
    
    reg_key = None
    try:
        if force:
            reg_key = winreg.CreateKeyEx(hive, subkey, 0, winreg.KEY_WRITE)
        else:
            is_policy = "\\Policies\\" in subkey

            if is_policy:
                reg_key = winreg.CreateKeyEx(hive, subkey, 0, winreg.KEY_WRITE)
            else:
                try:
                    reg_key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_WRITE)
                except FileNotFoundError:
                    raise FileNotFoundError(
                        f"Registry path not found (and not Policy): {path}. "
                        "The tweak requires this key to exist previously."
                    )
        
        winreg.SetValueEx(reg_key, key, 0, reg_type, value)
        
    finally:
        if reg_key:
            winreg.CloseKey(reg_key)

def get_value(path, key):
    hive, subkey = parse_registry_path(path)
    
    try:
        reg_key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ)
        value, reg_type = winreg.QueryValueEx(reg_key, key)
        winreg.CloseKey(reg_key)
        return value, reg_type
    except FileNotFoundError:
        return None, None
    except OSError:
        return None, None

def delete_value(path, key):
    hive, subkey = parse_registry_path(path)
    
    try:
        reg_key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_WRITE)
        winreg.DeleteValue(reg_key, key)
        winreg.CloseKey(reg_key)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False

def delete_subkey(path):
    hive, subkey = parse_registry_path(path)
    
    try:
        winreg.DeleteKey(hive, subkey)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False