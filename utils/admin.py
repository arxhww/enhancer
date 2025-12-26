import ctypes
import sys

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def require_admin():
    if not is_admin():
        print("ERROR: Administrator privileges are required.")
        print("Execute as administrator and try again.")
        sys.exit(1)