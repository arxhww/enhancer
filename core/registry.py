import winreg
from typing import Dict, Tuple, Optional, Union

REG_TYPES: Dict[str, int] = {
    "DWORD": winreg.REG_DWORD,
    "QWORD": winreg.REG_QWORD,
    "SZ": winreg.REG_SZ,
    "EXPAND_SZ": winreg.REG_EXPAND_SZ,
    "BINARY": winreg.REG_BINARY,
}

HIVES: Dict[str, int] = {
    "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
    "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
    "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
    "HKEY_USERS": winreg.HKEY_USERS,
    "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG,
}


def parse_registry_path(full_path: str) -> Tuple[int, str]:
    """
    Parse full registry path into hive and subkey components.
    
    Args:
        full_path: Full registry path (e.g., "HKEY_LOCAL_MACHINE\\Software\\Test").
    
    Returns:
        Tuple of (hive_handle, subkey_path).
    
    Raises:
        ValueError: If hive name is not recognized.
    
    Example:
        >>> hive, subkey = parse_registry_path("HKEY_CURRENT_USER\\Software\\Test")
        >>> # hive = winreg.HKEY_CURRENT_USER, subkey = "Software\\Test"
    """
    parts = full_path.split("\\", 1)
    hive_name = parts[0]
    subkey = parts[1] if len(parts) > 1 else ""
    
    if hive_name not in HIVES:
        raise ValueError(
            f"Invalid hive: {hive_name}. "
            f"Valid hives: {', '.join(HIVES.keys())}"
        )
    
    return HIVES[hive_name], subkey


def subkey_exists(path: str) -> bool:
    hive, subkey = parse_registry_path(path)
    
    try:
        reg_key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ)
        winreg.CloseKey(reg_key)
        return True
    except (FileNotFoundError, OSError):
        return False


def set_value(
    path: str,
    key: str,
    value: Union[int, str, bytes],
    reg_type: Union[str, int],
    force: bool = False
) -> None:
    hive, subkey = parse_registry_path(path)
    
    if isinstance(reg_type, str):
        if reg_type not in REG_TYPES:
            valid_types = ", ".join(REG_TYPES.keys())
            raise ValueError(
                f"Invalid registry type: '{reg_type}'. "
                f"Valid types: {valid_types}"
            )
        reg_type = REG_TYPES[reg_type]
    
    reg_key: Optional[winreg.HKEYType] = None
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
                        "The tweak requires this key to exist previously or "
                        "use force_create=true in definition."
                    )
        
        winreg.SetValueEx(reg_key, key, 0, reg_type, value)
        
    finally:
        if reg_key:
            winreg.CloseKey(reg_key)


def get_value(path: str, key: str) -> Tuple[Optional[Union[int, str, bytes]], Optional[int]]:
    hive, subkey = parse_registry_path(path)
    
    try:
        reg_key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ)
        value, reg_type = winreg.QueryValueEx(reg_key, key)
        winreg.CloseKey(reg_key)
        return value, reg_type
    except (FileNotFoundError, OSError):
        return None, None


def delete_value(path: str, key: str) -> bool:
    hive, subkey = parse_registry_path(path)
    
    try:
        reg_key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_WRITE)
        winreg.DeleteValue(reg_key, key)
        winreg.CloseKey(reg_key)
        return True
    except (FileNotFoundError, OSError):
        return False


def delete_subkey(path: str) -> bool:
    hive, subkey = parse_registry_path(path)
    
    try:
        winreg.DeleteKey(hive, subkey)
        return True
    except (FileNotFoundError, OSError):
        return False