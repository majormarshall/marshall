"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createOrbScene, type OrbSceneApi } from "@/lib/orbScene";
import { HandTracker, type TrackerStatus } from "@/lib/handTracker";

type CameraState = "off" | "starting" | "on" | "error";
type Panel = "none" | "chat" | "files" | "apps" | "camera" | "qr" | "system";

const API = "http://localhost:8000";

const MODE_LABEL: Record<TrackerStatus["mode"], string> = {
  idle: "STANDBY",
  spin: "SPIN",
  zoom: "ZOOM",
};

export default function MarshallOrb() {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<OrbSceneApi | null>(null);
  const trackerRef = useRef<HandTracker | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const [camera, setCamera] = useState<CameraState>("off");
  const [status, setStatus] = useState<TrackerStatus>({ hands: 0, mode: "idle" });
  const [error, setError] = useState<string | null>(null);
  const [activePanel, setActivePanel] = useState<Panel>("none");

  // Chat state
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([
    { role: "marshall", text: "MARSHALL online. How can I assist you, Sir?" },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // System state
  const [sysInfo, setSysInfo] = useState<Record<string, number | string | null> | null>(null);

  // Files state
  const [filePath, setFilePath] = useState("C:\\Users\\exboi marshall");
  const [fileItems, setFileItems] = useState<{ name: string; path: string; type: string; size: number | null }[]>([]);
  const [fileSearch, setFileSearch] = useState("");

  // QR state
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  const [tunnelUrl, setTunnelUrl] = useState<string | null>(null);

  // App launcher
  const quickApps = [
    { name: "Antigravity", icon: "??" },
    { name: "Chrome", icon: "??" },
    { name: "VS Code", icon: "??" },
    { name: "Explorer", icon: "??" },
    { name: "Notepad", icon: "??" },
    { name: "Settings", icon: "??" },
    { name: "Calculator", icon: "??" },
    { name: "Task Manager", icon: "??" },
    { name: "Spotify", icon: "??" },
    { name: "Discord", icon: "??" },
    { name: "PowerShell", icon: "???" },
    { name: "Paint", icon: "??" },
  ];

  // -- Orb scene ------------------------------
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const scene = createOrbScene(container);
    sceneRef.current = scene;
    return () => {
      trackerRef.current?.stop();
      trackerRef.current = null;
      scene.dispose();
      sceneRef.current = null;
    };
  }, []);

  // -- WebSocket chat --------------------------
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/chat`);
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setMessages((m) => [...m, { role: "marshall", text: data.reply }]);
      setChatLoading(false);
    };
    ws.onerror = () => {
      // backend not running yet � silent
    };
    wsRef.current = ws;
    return () => ws.close();
  }, []);

  // -- Auto-scroll chat --------------------------
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // -- Fetch system info when panel opens --------------------------
  useEffect(() => {
    if (activePanel === "system") {
      fetch(`${API}/api/system/info`)
        .then((r) => r.json())
        .then(setSysInfo)
        .catch(() => null);
      const interval = setInterval(() => {
        fetch(`${API}/api/system/info`)
          .then((r) => r.json())
          .then(setSysInfo)
          .catch(() => null);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [activePanel]);

  // -- Fetch files --------------------------
  useEffect(() => {
    if (activePanel === "files") fetchFiles(filePath);
  }, [activePanel]);

  // -- Fetch tunnel/QR --------------------------
  useEffect(() => {
    if (activePanel === "qr") {
      fetch(`${API}/api/tunnel/url`).then((r) => r.json()).then((d) => setTunnelUrl(d.url)).catch(() => null);
      setQrUrl(`${API}/api/tunnel/qr`);
    }
  }, [activePanel]);

  const fetchFiles = (path: string) => {
    fetch(`${API}/api/files?path=${encodeURIComponent(path)}`)
      .then((r) => r.json())
      .then((d) => { setFileItems(d.items || []); setFilePath(path); })
      .catch(() => null);
  };

  // -- Hand tracker --------------------------
  const stopGestures = useCallback(() => {
    trackerRef.current?.stop();
    trackerRef.current = null;
    setCamera("off");
    setStatus({ hands: 0, mode: "idle" });
  }, []);

  const startGestures = useCallback(async () => {
    const video = videoRef.current;
    const overlay = overlayRef.current;
    if (!video || !overlay || trackerRef.current) return;
    setCamera("starting");
    setError(null);
    const tracker = new HandTracker(video, overlay, {
      onRotate: (dt, dp) => sceneRef.current?.rotateBy(dt, dp),
      onZoom: (factor) => sceneRef.current?.zoomBy(factor),
      onStatus: setStatus,
    });
    trackerRef.current = tracker;
    try {
      await tracker.start();
      setCamera("on");
    } catch (err) {
      trackerRef.current = null;
      tracker.stop();
      setCamera("error");
      setError(err instanceof DOMException && err.name === "NotAllowedError" ? "CAMERA ACCESS DENIED" : "TRACKING INIT FAILED");
    }
  }, []);

  const toggleGestures = useCallback(() => {
    if (trackerRef.current) stopGestures();
    else void startGestures();
  }, [startGestures, stopGestures]);

  // -- Keyboard shortcuts --------------------------
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      switch (e.key) {
        case "+": case "=": sceneRef.current?.zoomIn(); break;
        case "-": case "_": sceneRef.current?.zoomOut(); break;
        case "r": case "R": sceneRef.current?.resetView(); break;
        case "g": case "G": toggleGestures(); break;
        case "Escape": setActivePanel("none"); break;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggleGestures]);

  // -- Chat send --------------------------
  const sendChat = async () => {
    if (!chatInput.trim() || chatLoading) return;
    const msg = chatInput.trim();
    setChatInput("");
    setMessages((m) => [...m, { role: "user", text: msg }]);
    setChatLoading(true);

    // Check for system commands in message
    const lower = msg.toLowerCase();
    if (lower.includes("lock") && lower.includes("pc")) {
      fetch(`${API}/api/system/lock`, { method: "POST" });
    }

    try {
      if (wsRef.current?.readyState === 1) {
        wsRef.current.send(JSON.stringify({ message: msg }));
      } else {
        const res = await fetch(`${API}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: msg }),
        });
        const data = await res.json();
        setMessages((m) => [...m, { role: "marshall", text: data.reply }]);
        setChatLoading(false);
      }
    } catch {
      setMessages((m) => [...m, { role: "marshall", text: "Connection error � backend offline." }]);
      setChatLoading(false);
    }
  };

  const sendVoice = async () => {
    if (recording) {
      mediaRecorderRef.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      audioChunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        setChatLoading(true);
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const form = new FormData();
        form.append("file", blob, "voice.webm");
        try {
          const res = await fetch(`${API}/api/voice/transcribe`, { method: "POST", body: form });
          const data = await res.json();
          if (data.transcript) setMessages((m) => [...m, { role: "user", text: "🎤 " + data.transcript }]);
          if (data.reply) {
            setMessages((m) => [...m, { role: "marshall", text: data.reply }]);
            speakText(data.reply);
          }
          if (data.error && !data.reply) setMessages((m) => [...m, { role: "marshall", text: "Voice error: " + data.error }]);
        } catch {
          setMessages((m) => [...m, { role: "marshall", text: "Voice failed — backend offline?" }]);
        }
        setChatLoading(false);
      };
      mr.start();
      mediaRecorderRef.current = mr;
      setRecording(true);
    } catch {
      setMessages((m) => [...m, { role: "marshall", text: "Microphone access denied." }]);
    }
  };

  const speakText = (text: string) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(text);
    utt.rate = 0.92;
    utt.pitch = 0.8;
    utt.volume = 1;
    // Load voices and pick a deep male voice
    const trySpeak = () => {
      const voices = window.speechSynthesis.getVoices();
      const deep = voices.find((v) =>
        /google uk english male|microsoft david|daniel|google us english/i.test(v.name)
      );
      if (deep) utt.voice = deep;
      window.speechSynthesis.speak(utt);
    };
    if (window.speechSynthesis.getVoices().length > 0) trySpeak();
    else window.speechSynthesis.addEventListener("voiceschanged", trySpeak, { once: true });
  };

  const openApp = (appName: string) => {
    fetch(`${API}/api/system/open`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ app: appName }),
    });
  };

  const lockPC = () => {
    fetch(`${API}/api/system/lock`, { method: "POST" });
  };

  const cameraOn = camera === "on";
  const panelOpen = activePanel !== "none";

  return (
    <>
      <div ref={containerRef} className="orb-root" />
      <div className="overlay-vignette" />
      <div className="overlay-grain" />
      <div className="overlay-scanlines" />

      {/* -- Title -- */}
      <div className="hud hud-title">M.A.R.S.H.A.L.L.</div>

      {/* -- Nav Dock -- */}
      <div className="marshall-dock">
        {([
          { id: "chat", icon: "??", label: "Chat" },
          { id: "system", icon: "???", label: "System" },
          { id: "files", icon: "??", label: "Files" },
          { id: "apps", icon: "??", label: "Apps" },
          { id: "camera", icon: "??", label: "Camera" },
          { id: "qr", icon: "??", label: "Phone" },
        ] as { id: Panel; icon: string; label: string }[]).map((item) => (
          <button
            key={item.id}
            className={`dock-btn${activePanel === item.id ? " active" : ""}`}
            onClick={() => setActivePanel(activePanel === item.id ? "none" : item.id)}
          >
            <span className="dock-icon">{item.icon}</span>
            <span className="dock-label">{item.label}</span>
          </button>
        ))}
        <button className="dock-btn dock-lock" onClick={lockPC} title="Lock PC">
          <span className="dock-icon">??</span>
          <span className="dock-label">Lock</span>
        </button>
      </div>

      {/* -- Panels -- */}
      {panelOpen && (
        <div className="panel-overlay">
          <div className="panel-box">
            <button className="panel-close" onClick={() => setActivePanel("none")}>?</button>

            {/* CHAT */}
            {activePanel === "chat" && (
              <div className="panel-chat">
                <div className="panel-title">?? MARSHALL AI</div>
                <div className="chat-messages">
                  {messages.map((m, i) => (
                    <div key={i} className={`chat-msg ${m.role}`}>
                      <span className="chat-role">{m.role === "marshall" ? "MARSHALL" : "YOU"}</span>
                      <span className="chat-text">{m.text}</span>
                    </div>
                  ))}
                  {chatLoading && <div className="chat-msg marshall"><span className="chat-role">MARSHALL</span><span className="chat-text chat-typing">?</span></div>}
                  <div ref={chatEndRef} />
                </div>
                <div className="chat-input-row">
                  <input
                    className="chat-input"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendChat()}
                    placeholder="Ask MARSHALL anything..."
                    autoFocus
                  />
                  <button className="hud-btn" onClick={sendChat} disabled={chatLoading || recording}>SEND</button>
                  <button
                    className={`hud-btn${recording ? " mic-recording" : ""}`}
                    onClick={sendVoice}
                    title={recording ? "Click to stop recording" : "Click to speak to MARSHALL"}
                  >
                    {recording ? "🔴 STOP" : "🎤 MIC"}
                  </button>
                </div>
              </div>
            )}

            {/* SYSTEM */}
            {activePanel === "system" && (
              <div className="panel-system">
                <div className="panel-title">??? SYSTEM STATUS</div>
                {sysInfo ? (
                  <div className="sys-grid">
                    <div className="sys-card"><div className="sys-label">CPU</div><div className="sys-bar"><div className="sys-fill" style={{ width: `${sysInfo.cpu_percent}%` }} /></div><div className="sys-val">{sysInfo.cpu_percent}%</div></div>
                    <div className="sys-card"><div className="sys-label">RAM</div><div className="sys-bar"><div className="sys-fill" style={{ width: `${sysInfo.ram_percent}%` }} /></div><div className="sys-val">{sysInfo.ram_used_gb}GB / {sysInfo.ram_total_gb}GB</div></div>
                    <div className="sys-card"><div className="sys-label">DISK C:</div><div className="sys-bar"><div className="sys-fill" style={{ width: `${sysInfo.disk_percent}%` }} /></div><div className="sys-val">{sysInfo.disk_free_gb}GB free</div></div>
                    {sysInfo.battery_percent !== null && <div className="sys-card"><div className="sys-label">BATTERY</div><div className="sys-bar"><div className="sys-fill" style={{ width: `${sysInfo.battery_percent}%` }} /></div><div className="sys-val">{sysInfo.battery_percent}% {sysInfo.battery_charging ? "?" : ""}</div></div>}
                    <div className="sys-card"><div className="sys-label">PROCESSES</div><div className="sys-val big">{sysInfo.processes}</div></div>
                  </div>
                ) : <div className="panel-loading">Loading system data...</div>}
                <button className="hud-btn" style={{ marginTop: 16 }} onClick={lockPC}>?? LOCK PC</button>
              </div>
            )}

            {/* FILES */}
            {activePanel === "files" && (
              <div className="panel-files">
                <div className="panel-title">?? FILE SYSTEM</div>
                <div className="file-path-row">
                  <button className="hud-btn" onClick={() => fetchFiles(filePath.split("\\").slice(0, -1).join("\\") || "C:\\")}>?</button>
                  <span className="file-path">{filePath}</span>
                  <input className="chat-input" placeholder="Search..." value={fileSearch} onChange={(e) => setFileSearch(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { fetch(`${API}/api/files/search?q=${fileSearch}&path=${encodeURIComponent(filePath)}`).then(r => r.json()).then(d => setFileItems(d.results || [])); } }} />
                </div>
                <div className="file-list">
                  {fileItems.map((item, i) => (
                    <div key={i} className="file-item" onDoubleClick={() => item.type === "directory" ? fetchFiles(item.path) : fetch(`${API}/api/system/open-file`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: item.path }) })}>
                      <span className="file-icon">{item.type === "directory" ? "??" : "??"}</span>
                      <span className="file-name">{item.name}</span>
                      {item.size !== null && <span className="file-size">{item.size > 1024 * 1024 ? `${(item.size / 1024 / 1024).toFixed(1)}MB` : item.size > 1024 ? `${(item.size / 1024).toFixed(0)}KB` : `${item.size}B`}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* APPS */}
            {activePanel === "apps" && (
              <div className="panel-apps">
                <div className="panel-title">?? APP LAUNCHER</div>
                <div className="app-grid">
                  {quickApps.map((app) => (
                    <button key={app.name} className="app-btn" onClick={() => openApp(app.name)}>
                      <span className="app-icon">{app.icon}</span>
                      <span className="app-name">{app.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* CAMERA */}
            {activePanel === "camera" && (
              <div className="panel-camera">
                <div className="panel-title">?? CAMERA FEED</div>
                <img src={`${API}/api/camera/stream`} className="cam-feed" alt="Live camera feed" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                <div className="cam-btn-row">
                  <button className="hud-btn" onClick={() => fetch(`${API}/api/camera/start`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ index: 0 }) })}>? START</button>
                  <button className="hud-btn" onClick={() => fetch(`${API}/api/camera/stop`, { method: "POST" })}>� STOP</button>
                </div>
              </div>
            )}

            {/* QR / PHONE */}
            {activePanel === "qr" && (
              <div className="panel-qr">
                <div className="panel-title">?? PHONE ACCESS</div>
                {tunnelUrl ? (
                  <>
                    <p className="qr-url">{tunnelUrl}</p>
                    <img src={qrUrl || ""} className="qr-img" alt="QR Code" />
                    <p className="qr-hint">Scan with your phone to control MARSHALL remotely from anywhere.</p>
                  </>
                ) : (
                  <div className="panel-loading">Setting up remote tunnel...<br /><small>Takes 10�30 seconds on first launch.</small></div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* -- Original gesture controls -- */}
      <div className="hud hud-hint">
        <div><span className="key">DRAG</span> spin&nbsp;&nbsp;<span className="key">SCROLL</span> zoom</div>
        {cameraOn ? (
          <div><span className="key">PINCH + MOVE</span> spin&nbsp;&nbsp;<span className="key">PINCH BOTH HANDS � SPREAD</span> zoom</div>
        ) : (
          <div><span className="key">G</span> gestures&nbsp;&nbsp;<span className="key">R</span> reset&nbsp;&nbsp;<span className="key">+/-</span> zoom&nbsp;&nbsp;<span className="key">ESC</span> close panel</div>
        )}
      </div>

      <div className="hud hud-controls">
        <div className={`camera-panel${cameraOn ? " visible" : ""}`}>
          <video ref={videoRef} muted playsInline className="camera-video" />
          <canvas ref={overlayRef} width={208} height={156} className="camera-overlay" />
          <div className="camera-status">
            {status.hands > 0 ? `${status.hands} HAND${status.hands > 1 ? "S" : ""} � ${MODE_LABEL[status.mode]}` : "SHOW HANDS"}
          </div>
        </div>
        {error && <div className="hud-error">{error}</div>}
        <div className="hud-row">
          <button type="button" className="hud-btn" aria-pressed={cameraOn} onClick={toggleGestures} disabled={camera === "starting"}>
            {camera === "starting" ? "INITIALIZING�" : cameraOn ? "GESTURES ON" : "GESTURES OFF"}
          </button>
        </div>
        <div className="hud-row">
          <button type="button" className="hud-btn" onClick={() => sceneRef.current?.zoomIn()} aria-label="Zoom in">+</button>
          <button type="button" className="hud-btn" onClick={() => sceneRef.current?.zoomOut()} aria-label="Zoom out">-</button>
          <button type="button" className="hud-btn" onClick={() => sceneRef.current?.resetView()}>RESET</button>
        </div>
      </div>
    </>
  );
}
