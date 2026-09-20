"""
MARSHALL - PC Unlock Module
Attempts to unlock Windows by injecting the stored password.
NOTE: Requires MARSHALL to run as Administrator for full effect.
"""
import os
import time
import ctypes
import subprocess
import threading
from dotenv import load_dotenv

load_dotenv()

PC_PASSWORD = os.getenv("MARSHALL_PC_PASSWORD", "")


def _is_locked() -> bool:
    """Check if the workstation is currently locked."""
    import ctypes
    # Check if the active session is locked via Windows API
    try:
        import win32api, win32ts, win32con
        session_id = win32api.GetCurrentProcessId()
        # Try WTS approach
        sessions = win32ts.WTSEnumerateSessions()
        for s in sessions:
            if s.get("State") == win32con.WTSActive:
                return False
        return True
    except Exception:
        # Fallback: try to get desktop handle
        desk = ctypes.windll.user32.OpenDesktopW("Default", 0, False, 0x0200)
        locked = not bool(desk)
        if desk:
            ctypes.windll.user32.CloseDesktop(desk)
        return locked


def _send_keys_to_lock_screen(password: str):
    """
    Try to wake + unlock the lock screen by simulating keystrokes.
    Works best when running as Administrator.
    """
    # Step 1: Wake screen (press a key to show login prompt)
    ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)  # ENTER down
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)  # ENTER up
    time.sleep(0.8)

    # Step 2: Type the password using keybd_event for each character
    for ch in password:
        vk = ctypes.windll.user32.VkKeyScanW(ord(ch))
        low = vk & 0xFF
        high = (vk >> 8) & 0xFF
        # Shift if needed
        if high & 1:
            ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)  # SHIFT down
        ctypes.windll.user32.keybd_event(low, 0, 0, 0)
        time.sleep(0.03)
        ctypes.windll.user32.keybd_event(low, 0, 2, 0)
        if high & 1:
            ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)  # SHIFT up
        time.sleep(0.02)

    time.sleep(0.3)

    # Step 3: Press Enter to submit
    ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)


def _show_unlock_toast(password: str):
    """Show a Windows toast notification with the PIN for quick manual entry."""
    try:
        from winotify import Notification, audio
        toast = Notification(
            app_id="MARSHALL AI",
            title="🔓 MARSHALL — Unlock Code",
            msg=f"PIN: {password}\nTap to dismiss.",
            duration="long",
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
    except Exception:
        # Fallback: message box
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"MARSHALL Unlock PIN:\n\n{password}",
                "MARSHALL — Unlock Code",
                0x40 | 0x1000  # MB_ICONINFORMATION | MB_SYSTEMMODAL
            )
        except Exception:
            pass


def unlock_pc() -> dict:
    """
    Attempt to unlock the PC using stored password.
    - Tries keystroke injection (works as Admin)
    - Also shows PIN toast notification as backup
    """
    if not PC_PASSWORD:
        return {"status": "error", "message": "No unlock password configured"}

    # Show toast so user can see PIN quickly
    threading.Thread(target=_show_unlock_toast, args=(PC_PASSWORD,), daemon=True).start()

    # Try keystroke injection in background
    def _attempt():
        time.sleep(0.2)
        _send_keys_to_lock_screen(PC_PASSWORD)

    threading.Thread(target=_attempt, daemon=True).start()

    return {
        "status": "ok",
        "message": "Unlock sequence sent. PIN notification shown on screen.",
        "method": "keystroke_injection + toast_notification"
    }


def set_pc_password(new_password: str) -> dict:
    """Update the stored unlock password."""
    global PC_PASSWORD
    PC_PASSWORD = new_password
    # Update .env file
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    try:
        lines = open(env_path, encoding="utf-8").readlines()
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("MARSHALL_PC_PASSWORD="):
                lines[i] = f"MARSHALL_PC_PASSWORD={new_password}\n"
                updated = True
                break
        if not updated:
            lines.append(f"MARSHALL_PC_PASSWORD={new_password}\n")
        open(env_path, "w", encoding="utf-8").writelines(lines)
        return {"status": "ok", "message": "Password updated"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
