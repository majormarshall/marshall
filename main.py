"""
MARSHALL - Main FastAPI Backend Server
All system control, AI, camera, and file routes.
"""
import asyncio
import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import threading

load_dotenv()

from modules import system_control, ai_router, camera, file_manager, tunnel, unlock

app = FastAPI(title="MARSHALL AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------
# STARTUP - auto-start tunnel
# ---------------------------------------------
@app.on_event("startup")
async def startup():
    print("[MARSHALL] Starting up...")
    def start_tun():
        url = tunnel.start_tunnel(8000)
        if url:
            print(f"[MARSHALL] Remote access ready: {url}")
        else:
            print("[MARSHALL] Tunnel unavailable - local only")
    threading.Thread(target=start_tun, daemon=True).start()


# ---------------------------------------------
# SERVE NEXT.JS ORB UI (static export)
# ---------------------------------------------
UI_DIR = os.path.join(os.path.dirname(__file__), "..", "ultron-marshall", "out")
UI_DIR = os.path.abspath(UI_DIR)

from fastapi.responses import FileResponse

@app.get("/")
async def root():
    index = os.path.join(UI_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"status": "MARSHALL online", "version": "1.0.0"}

# Mount static assets (_next, images, etc.)
if os.path.isdir(UI_DIR):
    app.mount("/_next", StaticFiles(directory=os.path.join(UI_DIR, "_next")), name="next-static")

# ---------------------------------------------
# PHONE UNLOCK PAGE
# ---------------------------------------------
from modules.unlock_page import UNLOCK_HTML

@app.get("/unlock")
async def unlock_page():
    """Beautiful phone unlock page with PIN pad + fingerprint."""
    return HTMLResponse(content=UNLOCK_HTML)

@app.post("/api/system/unlock-with-pin")
async def unlock_with_pin(body: dict):
    """Verify PIN then unlock PC."""
    pin = body.get("pin", "")
    stored = os.getenv("MARSHALL_PC_PASSWORD", "")
    if not stored:
        return {"status": "error", "message": "No PIN configured"}
    if pin != stored:
        return {"status": "wrong", "message": "Incorrect PIN"}
    result = await asyncio.to_thread(unlock.unlock_pc)
    return {"status": "ok", "message": result.get("message", "Unlock sent")}

@app.get("/api/status")
async def status():
    return {
        "marshall": "online",
        "tunnel_url": tunnel.get_tunnel_url(),
        "camera_active": camera.camera_is_running(),
    }

# ---------------------------------------------
# AI CHAT
# ---------------------------------------------
@app.post("/api/chat")
async def chat(body: dict):
    message = body.get("message", "")
    reset = body.get("reset", False)
    if not message:
        return {"error": "No message provided"}
    reply = await asyncio.to_thread(ai_router.chat, message, reset)
    return {"reply": reply}

@app.post("/api/research")
async def research(body: dict):
    topic = body.get("topic", "")
    if not topic:
        return {"error": "No topic provided"}
    result = await asyncio.to_thread(ai_router.research, topic)
    return {"result": result}

@app.post("/api/chat/clear")
async def clear_chat():
    return ai_router.clear_history()

@app.post("/api/voice/transcribe")
async def transcribe_voice(file: UploadFile = File(...)):
    """Transcribe voice, detect commands, execute them, and get MARSHALL reply."""
    from openai import OpenAI
    import os, tempfile
    groq_client = OpenAI(
        api_key=os.getenv("GROK_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )
    audio_bytes = await file.read()
    suffix = ".webm"
    if file.filename and "." in file.filename:
        suffix = "." + file.filename.split(".")[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as af:
            result = groq_client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=af,
                response_format="text",
            )
        text = result if isinstance(result, str) else getattr(result, "text", str(result))

        # Detect and execute system commands from voice
        action_result = await _detect_and_execute(text)

        # Get AI reply (with context about what was executed)
        context = text
        if action_result:
            context = f"{text} [MARSHALL executed: {action_result}]"
        reply = await asyncio.to_thread(ai_router.chat, context)
        return {"transcript": text, "reply": reply, "action": action_result}
    except Exception as e:
        return {"error": str(e), "transcript": "", "reply": ""}
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

async def _detect_and_execute(text: str):
    """Parse voice text for system commands and execute them."""
    t = text.lower().strip()

    # Lock PC
    if any(p in t for p in ["lock pc", "lock my pc", "lock the pc", "lock computer",
                              "lock screen", "lock my computer", "lock the computer"]):
        system_control.lock_pc()
        return "locked PC"

    # Unlock PC
    if any(p in t for p in ["unlock pc", "unlock my pc", "unlock the pc", "unlock computer",
                              "unlock screen", "unlock my computer", "unlock the computer",
                              "unlock the system", "unlock my system"]):
        unlock.unlock_pc()
        return "unlock sequence sent"

    # Open app — "open X", "launch X", "start X", "run X"
    for trigger in ["open ", "launch ", "start ", "run ", "load "]:
        if t.startswith(trigger) or f" {trigger.strip()} " in t:
            # Extract app name
            idx = t.find(trigger)
            app_name = text[idx + len(trigger):].strip().split(".")[0]
            if app_name:
                result = await asyncio.to_thread(system_control.open_app, app_name)
                if result.get("status") == "launched":
                    return f"opened {app_name}"
                # Try installed apps scan
                installed = await asyncio.to_thread(system_control.get_installed_apps)
                matches = [a for a in installed if app_name.lower() in a["name"].lower()]
                if matches:
                    os.startfile(matches[0]["path"])
                    return f"opened {matches[0]['name']}"

    # Close / kill app
    if t.startswith("close ") or t.startswith("kill "):
        app_name = t.split(" ", 1)[1].strip()
        for proc in __import__("psutil").process_iter(["name", "pid"]):
            if app_name in proc.info["name"].lower():
                system_control.kill_app(proc.info["pid"])
                return f"closed {app_name}"

    # Volume control
    if "volume up" in t or "turn up" in t:
        system_control.set_volume(80)
        return "volume set to 80"
    if "volume down" in t or "turn down" in t or "lower volume" in t:
        system_control.set_volume(30)
        return "volume set to 30"
    if "mute" in t:
        system_control.set_volume(0)
        return "muted"

    # Screenshot
    if "screenshot" in t or "take a screenshot" in t:
        import subprocess
        subprocess.Popen("snippingtool.exe", shell=True)
        return "opened snipping tool"

    return None

# WebSocket for real-time chat
@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            message = payload.get("message", "")
            reply = await asyncio.to_thread(ai_router.chat, message)
            await websocket.send_text(json.dumps({"reply": reply}))
    except WebSocketDisconnect:
        pass

# ---------------------------------------------
# SYSTEM CONTROL
# ---------------------------------------------
@app.post("/api/system/lock")
async def lock():
    return system_control.lock_pc()

@app.post("/api/system/unlock")
async def unlock_pc():
    return await asyncio.to_thread(unlock.unlock_pc)

@app.post("/api/system/set-password")
async def set_password(body: dict):
    new_pw = body.get("password", "")
    if not new_pw:
        return {"status": "error", "message": "No password provided"}
    return unlock.set_pc_password(new_pw)

@app.get("/api/system/info")
async def sysinfo():
    return await asyncio.to_thread(system_control.get_system_info)

@app.get("/api/system/apps")
async def running_apps():
    return {"apps": await asyncio.to_thread(system_control.get_running_apps)}

@app.get("/api/system/installed-apps")
async def installed_apps():
    return {"apps": await asyncio.to_thread(system_control.get_installed_apps)}

@app.post("/api/system/open")
async def open_app(body: dict):
    app_name = body.get("app", "")
    lnk_path = body.get("lnk", "")
    # If a direct .lnk path is provided, use os.startfile (most reliable)
    if lnk_path and os.path.exists(lnk_path):
        try:
            os.startfile(lnk_path)
            return {"status": "launched", "app": app_name or lnk_path}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    return await asyncio.to_thread(system_control.open_app, app_name)

@app.post("/api/system/open-file")
async def open_file(body: dict):
    path = body.get("path", "")
    return await asyncio.to_thread(system_control.open_file, path)

@app.post("/api/system/kill")
async def kill_app(body: dict):
    pid = body.get("pid", 0)
    return await asyncio.to_thread(system_control.kill_app, int(pid))

# ---------------------------------------------
# FILE MANAGER
# ---------------------------------------------
@app.get("/api/files")
async def list_files(path: str = Query(default="C:\\Users\\exboi marshall")):
    return await asyncio.to_thread(file_manager.list_directory, path)

@app.get("/api/files/search")
async def search_files(q: str, path: str = Query(default="C:\\Users\\exboi marshall")):
    return await asyncio.to_thread(file_manager.search_files, q, path)

@app.get("/api/files/read")
async def read_file(path: str):
    return await asyncio.to_thread(file_manager.read_file, path)

@app.get("/api/files/drives")
async def drives():
    return {"drives": await asyncio.to_thread(file_manager.get_drives)}

@app.delete("/api/files")
async def delete_file(path: str):
    return await asyncio.to_thread(file_manager.delete_file, path)

@app.post("/api/files/move")
async def move_file(body: dict):
    return await asyncio.to_thread(file_manager.move_file, body.get("src"), body.get("dst"))

@app.post("/api/files/mkdir")
async def mkdir(body: dict):
    return await asyncio.to_thread(file_manager.create_folder, body.get("path"))

# ---------------------------------------------
# CAMERA
# ---------------------------------------------
@app.post("/api/camera/start")
async def cam_start(body: dict = {}):
    index = body.get("index", 0) if body else 0
    return await asyncio.to_thread(camera.start_camera, index)

@app.post("/api/camera/stop")
async def cam_stop():
    return await asyncio.to_thread(camera.stop_camera)

@app.get("/api/camera/stream")
async def cam_stream():
    """MJPEG stream endpoint."""
    def generate():
        while camera.camera_is_running():
            frame = camera.get_frame_jpeg()
            if frame:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace;boundary=frame")

@app.get("/api/camera/snapshot")
async def cam_snapshot():
    frame = camera.get_frame_jpeg()
    if frame is None:
        return {"error": "Camera not running"}
    return Response(content=frame, media_type="image/jpeg")

# ---------------------------------------------
# REMOTE / TUNNEL / QR
# ---------------------------------------------
@app.get("/api/tunnel/url")
async def tunnel_url():
    return {"url": tunnel.get_tunnel_url()}

@app.get("/api/tunnel/qr")
async def tunnel_qr():
    qr_bytes = tunnel.get_qr_bytes()
    if not qr_bytes:
        return Response(content=b"", status_code=503)
    return Response(content=qr_bytes, media_type="image/png")


"""Entry point - runs the FastAPI server."""
import uvicorn
if __name__ == "__main__":
    print("[MARSHALL] Server starting on http://localhost:8000")
    print("[MARSHALL] API docs at http://localhost:8000/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
