"""
Auto-start Clipboard Manager on Windows login.
Run this script once to register/unregister the app in Windows startup.

Usage:
  python install_autostart.py install     -> Add to startup
  python install_autostart.py remove      -> Remove from startup
  python install_autostart.py status      -> Check status
"""

import sys
import os
import winreg

APP_NAME = "ClipboardManager"
SCRIPT_PATH = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
PYTHONW = os.path.join(sys.prefix, "pythonw.exe")
PYTHON_SCRIPT = os.path.join(SCRIPT_DIR, "clipboard_manager.pyw")

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_command():
    # Use pythonw.exe to run without console window
    if os.path.exists(PYTHONW):
        return f'"{PYTHONW}" "{PYTHON_SCRIPT}"'
    else:
        return f'pythonw "{PYTHON_SCRIPT}"'


def install():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0,
                             winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_command())
        winreg.CloseKey(key)
        print("✅ Clipboard Manager added to startup!")
        print("   It will start automatically when you log in.")
    except Exception as e:
        print(f"❌ Error: {e}")


def remove():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0,
                             winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        print("✅ Clipboard Manager removed from startup.")
    except FileNotFoundError:
        print("ℹ️  Clipboard Manager was not in startup.")
    except Exception as e:
        print(f"❌ Error: {e}")


def status():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0,
                             winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        print(f"✅ Clipboard Manager IS in startup:")
        print(f"   {value}")
    except FileNotFoundError:
        print("ℹ️  Clipboard Manager is NOT in startup.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    action = sys.argv[1].lower()
    if action == "install":
        install()
    elif action == "remove":
        remove()
    elif action == "status":
        status()
    else:
        print(f"Unknown action: {action}")
        print("Use: install, remove, or status")
