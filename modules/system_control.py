"""
MARSHALL - System Control Module
Handles: lock/unlock PC, launch apps, list processes, system info
"""
import os
import subprocess
import ctypes
import psutil
import winreg
import glob
from pathlib import Path
from typing import Optional


def lock_pc():
    """Lock the Windows workstation."""
    ctypes.windll.user32.LockWorkStation()
    return {"status": "locked", "message": "PC locked successfully"}


def get_system_info():
    """Get CPU, RAM, battery, disk usage."""
    battery = psutil.sensors_battery()
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "ram_percent": psutil.virtual_memory().percent,
        "ram_used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "disk_percent": psutil.disk_usage("C:\\").percent,
        "disk_free_gb": round(psutil.disk_usage("C:\\").free / (1024**3), 2),
        "battery_percent": battery.percent if battery else None,
        "battery_charging": battery.power_plugged if battery else None,
        "processes": len(psutil.pids()),
    }


def get_running_apps():
    """List currently running applications."""
    apps = []
    for proc in psutil.process_iter(["pid", "name", "status"]):
        try:
            if proc.info["status"] == "running":
                apps.append({"pid": proc.info["pid"], "name": proc.info["name"]})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return apps[:50]  # limit to 50


def open_app(app_name: str):
    """Launch an application by name or path."""
    app_name_lower = app_name.lower().strip()

    # Common app shortcuts
    shortcuts = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "explorer": "explorer.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
        "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "vs code": r"C:\Users\exboi marshall\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        "vscode": r"C:\Users\exboi marshall\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        "spotify": rf"C:\Users\exboi marshall\AppData\Roaming\Spotify\Spotify.exe",
        "discord": rf"C:\Users\exboi marshall\AppData\Local\Discord\Update.exe --processStart Discord.exe",
        "settings": "ms-settings:",
        "task manager": "taskmgr.exe",
        "control panel": "control.exe",
        "paint": "mspaint.exe",
        "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
        "excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
        "antigravity": rf"C:\Users\exboi marshall\AppData\Local\Programs\antigravity\Antigravity.exe",
    }

    # Check shortcuts first
    if app_name_lower in shortcuts:
        path = shortcuts[app_name_lower]
        try:
            if path.startswith("ms-"):
                os.startfile(path)
            else:
                subprocess.Popen(path, shell=True)
            return {"status": "launched", "app": app_name}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # Try direct execution
    try:
        subprocess.Popen(app_name, shell=True)
        return {"status": "launched", "app": app_name}
    except Exception as e:
        return {"status": "error", "message": f"Could not open {app_name}: {e}"}


def open_file(file_path: str):
    """Open a file with its default application."""
    try:
        os.startfile(file_path)
        return {"status": "opened", "file": file_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def kill_app(pid: int):
    """Kill a process by PID."""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        return {"status": "killed", "pid": pid}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def set_volume(level: int):
    """Set system volume (0-100)."""
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level / 100, None)
        return {"status": "ok", "volume": level}
    except Exception as e:
        # Fallback using nircmd if available
        subprocess.run(f"nircmd.exe setsysvolume {int(level * 655.35)}", shell=True)
        return {"status": "ok", "volume": level}


APP_ICONS = {
    "chrome": "🌐", "firefox": "🦊", "edge": "🔵", "opera": "🎭",
    "spotify": "🎵", "discord": "💬", "slack": "💼", "teams": "👥",
    "zoom": "📹", "skype": "📞", "visual studio": "💻", "code": "💻",
    "notepad": "📝", "word": "📄", "excel": "📊", "powerpoint": "📑",
    "outlook": "📧", "onenote": "📓", "steam": "🎮", "epic": "🎮",
    "vlc": "🎬", "photoshop": "🖼️", "blender": "🎨", "paint": "🎨",
    "gimp": "🖼️", "7-zip": "🗜️", "winrar": "🗜️", "calculator": "🧮",
    "settings": "⚙️", "control panel": "⚙️", "powershell": "🖥️",
    "cmd": "🖥️", "terminal": "🖥️", "python": "🐍", "node": "🟢",
    "git": "🔀", "antigravity": "🤖", "task manager": "📊",
    "remote desktop": "🖥️", "paint": "🎨", "wordpad": "📝",
    "media player": "🎬", "default": "🚀",
}


def _get_icon(name: str) -> str:
    n = name.lower()
    for key, icon in APP_ICONS.items():
        if key in n:
            return icon
    return APP_ICONS["default"]


def get_installed_apps():
    """Scan Start Menu shortcuts and return every installed app."""
    import glob
    start_menus = [
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        r"C:\Users\exboi marshall\AppData\Roaming\Microsoft\Windows\Start Menu\Programs",
    ]
    skip = ["uninstall", "help", "read me", "readme", "release notes", "license", "what's new"]
    apps = {}
    for sm in start_menus:
        for lnk in glob.glob(sm + "/**/*.lnk", recursive=True):
            name = os.path.splitext(os.path.basename(lnk))[0].strip()
            if any(k in name.lower() for k in skip):
                continue
            if name and name not in apps:
                apps[name] = {
                    "name": name,
                    "path": lnk,
                    "icon": _get_icon(name),
                }
    return sorted(apps.values(), key=lambda x: x["name"].lower())
