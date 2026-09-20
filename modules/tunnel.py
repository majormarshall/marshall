"""
MARSHALL - Tunnel Module
Creates a Cloudflare Tunnel for remote phone access and generates a QR code.
"""
import subprocess
import threading
import re
import os
import io
import qrcode
import requests
import time
from pathlib import Path

_tunnel_url = None
_tunnel_proc = None
_qr_image_bytes = None


def _download_cloudflared():
    """Download cloudflared if not present."""
    cf_path = Path(__file__).parent.parent / "cloudflared.exe"
    if cf_path.exists():
        return str(cf_path)
    print("[MARSHALL] Downloading cloudflared...")
    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    try:
        r = requests.get(url, timeout=60, stream=True)
        with open(cf_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        print("[MARSHALL] cloudflared downloaded.")
        return str(cf_path)
    except Exception as e:
        print(f"[MARSHALL] Failed to download cloudflared: {e}")
        return None


def start_tunnel(local_port: int = 8000):
    """Start Cloudflare tunnel and return public URL."""
    global _tunnel_url, _tunnel_proc, _qr_image_bytes

    cf_path = _download_cloudflared()
    if not cf_path:
        return None

    def run():
        global _tunnel_url, _tunnel_proc, _qr_image_bytes
        try:
            _tunnel_proc = subprocess.Popen(
                [cf_path, "tunnel", "--url", f"http://localhost:{local_port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in _tunnel_proc.stdout:
                print("[cloudflared]", line.strip())
                match = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com", line)
                if match:
                    _tunnel_url = match.group(0)
                    print(f"[MARSHALL] Tunnel URL: {_tunnel_url}")
                    _qr_image_bytes = _generate_qr(_tunnel_url)
                    break
        except Exception as e:
            print(f"[MARSHALL] Tunnel error: {e}")

    t = threading.Thread(target=run, daemon=True)
    t.start()

    # Wait up to 20s for tunnel
    for _ in range(40):
        if _tunnel_url:
            return _tunnel_url
        time.sleep(0.5)
    return None


def _generate_qr(url: str) -> bytes:
    """Generate QR code PNG bytes."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#ffaa30", back_color="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def get_tunnel_url() -> str | None:
    return _tunnel_url


def get_qr_bytes() -> bytes | None:
    return _qr_image_bytes


def stop_tunnel():
    global _tunnel_proc, _tunnel_url, _qr_image_bytes
    if _tunnel_proc:
        _tunnel_proc.terminate()
        _tunnel_proc = None
    _tunnel_url = None
    _qr_image_bytes = None
