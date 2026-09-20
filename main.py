"""
MARSHALL - Main FastAPI Backend Server
All system control, AI, camera, and file routes.
"""
import asyncio
import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import threading

load_dotenv()

from modules import system_control, ai_router, camera, file_manager, tunnel

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
# HEALTH
# ---------------------------------------------
@app.get("/")
async def root():
    return {"status": "MARSHALL online", "version": "1.0.0"}

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

@app.get("/api/system/info")
async def sysinfo():
    return await asyncio.to_thread(system_control.get_system_info)

@app.get("/api/system/apps")
async def running_apps():
    return {"apps": await asyncio.to_thread(system_control.get_running_apps)}

@app.post("/api/system/open")
async def open_app(body: dict):
    app_name = body.get("app", "")
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
