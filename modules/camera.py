"""
MARSHALL - Camera Module
Streams webcam and IP cameras over HTTP MJPEG.
"""
import cv2
import threading
import time

# Global camera state
_cap = None
_lock = threading.Lock()
_frame = None
_running = False


def start_camera(index: int = 0):
    global _cap, _running, _frame
    with _lock:
        if _cap is not None:
            return {"status": "already_running"}
        _cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        _cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        _cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not _cap.isOpened():
            _cap = None
            return {"status": "error", "message": "Could not open camera"}
        _running = True

    def capture_loop():
        global _frame, _running, _cap
        while _running:
            if _cap and _cap.isOpened():
                ret, frame = _cap.read()
                if ret:
                    _frame = frame
            time.sleep(0.033)  # ~30fps

    t = threading.Thread(target=capture_loop, daemon=True)
    t.start()
    return {"status": "started", "camera_index": index}


def stop_camera():
    global _cap, _running, _frame
    _running = False
    time.sleep(0.1)
    with _lock:
        if _cap:
            _cap.release()
            _cap = None
    _frame = None
    return {"status": "stopped"}


def get_frame_jpeg() -> bytes | None:
    global _frame
    if _frame is None:
        return None
    ret, buf = cv2.imencode(".jpg", _frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    if ret:
        return buf.tobytes()
    return None


def camera_is_running() -> bool:
    return _running and _cap is not None
