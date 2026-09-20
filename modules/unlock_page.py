"""
MARSHALL - Phone Unlock Page
Serves a beautiful PIN pad + fingerprint unlock page at /unlock
Works via Cloudflare tunnel HTTPS on any Android/iOS phone browser.
"""

UNLOCK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>MARSHALL — Unlock</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #000;
    color: #ffaa30;
    font-family: 'Courier New', monospace;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: radial-gradient(ellipse at 50% 30%, rgba(40,20,0,0.95) 0%, #000 70%);
  }
  .title {
    font-size: 13px;
    letter-spacing: 0.4em;
    color: rgba(255,170,48,0.6);
    margin-bottom: 6px;
  }
  .logo {
    font-size: 22px;
    letter-spacing: 0.3em;
    color: #ffaa30;
    text-shadow: 0 0 20px rgba(255,170,48,0.5);
    margin-bottom: 32px;
  }
  .pin-display {
    width: 200px;
    height: 52px;
    border: 1px solid rgba(255,170,48,0.4);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-bottom: 24px;
    background: rgba(255,170,48,0.05);
  }
  .pin-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 1.5px solid rgba(255,170,48,0.4);
    transition: all 0.15s;
  }
  .pin-dot.filled {
    background: #ffaa30;
    border-color: #ffaa30;
    box-shadow: 0 0 8px rgba(255,170,48,0.6);
  }
  .keypad {
    display: grid;
    grid-template-columns: repeat(3, 72px);
    gap: 10px;
    margin-bottom: 20px;
  }
  .key {
    height: 72px;
    border: 1px solid rgba(255,170,48,0.25);
    border-radius: 12px;
    background: rgba(255,170,48,0.05);
    color: #ffaa30;
    font-size: 22px;
    font-family: 'Courier New', monospace;
    cursor: pointer;
    transition: all 0.1s;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
  }
  .key:active, .key.pressed {
    background: rgba(255,170,48,0.2);
    border-color: #ffaa30;
    transform: scale(0.95);
  }
  .key.del { font-size: 16px; color: rgba(255,100,100,0.8); border-color: rgba(255,100,100,0.25); }
  .key.ok  { font-size: 14px; letter-spacing: 0.1em; background: rgba(255,170,48,0.15); border-color: rgba(255,170,48,0.6); }
  .key.ok:active { background: rgba(255,170,48,0.35); }

  .fingerprint-btn {
    width: 226px;
    height: 56px;
    border: 1px solid rgba(100,200,255,0.4);
    border-radius: 12px;
    background: rgba(0,100,180,0.1);
    color: #66ccff;
    font-size: 14px;
    letter-spacing: 0.15em;
    font-family: 'Courier New', monospace;
    cursor: pointer;
    margin-bottom: 12px;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    -webkit-tap-highlight-color: transparent;
  }
  .fingerprint-btn:active { background: rgba(0,100,180,0.3); transform: scale(0.97); }
  .fingerprint-btn:disabled { opacity: 0.4; cursor: default; }

  .status {
    font-size: 11px;
    letter-spacing: 0.1em;
    color: rgba(255,170,48,0.5);
    text-align: center;
    min-height: 20px;
    margin-top: 8px;
  }
  .status.ok  { color: #44ff88; }
  .status.err { color: #ff4444; }

  .orb-ring {
    width: 90px; height: 90px;
    border: 2px solid rgba(255,170,48,0.15);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 16px;
    position: relative;
  }
  .orb-ring::before {
    content: '';
    position: absolute;
    inset: 6px;
    border-radius: 50%;
    border: 1px solid rgba(255,170,48,0.1);
  }
  .orb-emoji { font-size: 32px; }
</style>
</head>
<body>

<div class="orb-ring"><span class="orb-emoji">🔮</span></div>
<div class="title">M.A.R.S.H.A.L.L.</div>
<div class="logo">UNLOCK</div>

<div class="pin-display" id="pinDisplay">
  <div class="pin-dot" id="d0"></div>
  <div class="pin-dot" id="d1"></div>
  <div class="pin-dot" id="d2"></div>
  <div class="pin-dot" id="d3"></div>
  <div class="pin-dot" id="d4"></div>
  <div class="pin-dot" id="d5"></div>
</div>

<div class="keypad">
  <button class="key" onclick="press('1')">1</button>
  <button class="key" onclick="press('2')">2</button>
  <button class="key" onclick="press('3')">3</button>
  <button class="key" onclick="press('4')">4</button>
  <button class="key" onclick="press('5')">5</button>
  <button class="key" onclick="press('6')">6</button>
  <button class="key" onclick="press('7')">7</button>
  <button class="key" onclick="press('8')">8</button>
  <button class="key" onclick="press('9')">9</button>
  <button class="key del" onclick="del()">⌫ DEL</button>
  <button class="key" onclick="press('0')">0</button>
  <button class="key ok" onclick="submit()">UNLOCK</button>
</div>

<button class="fingerprint-btn" id="fpBtn" onclick="fingerprintUnlock()">
  <span>👆</span> FINGERPRINT
</button>

<div class="status" id="status">Enter PIN or use fingerprint</div>

<script>
let pin = '';
const MAX = 6;

function press(d) {
  if (pin.length >= MAX) return;
  pin += d;
  updateDots();
  if (pin.length === MAX) setTimeout(submit, 300);
}

function del() {
  pin = pin.slice(0, -1);
  updateDots();
}

function updateDots() {
  for (let i = 0; i < MAX; i++) {
    document.getElementById('d' + i).classList.toggle('filled', i < pin.length);
  }
}

async function submit() {
  if (!pin) return;
  setStatus('Verifying...', '');
  try {
    const r = await fetch('/api/system/unlock-with-pin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pin })
    });
    const d = await r.json();
    if (d.status === 'ok') {
      setStatus('🔓 PC Unlocking...', 'ok');
      pin = '';
      updateDots();
    } else {
      setStatus('❌ Wrong PIN', 'err');
      shake();
      pin = '';
      updateDots();
    }
  } catch {
    setStatus('❌ Backend offline', 'err');
    pin = '';
    updateDots();
  }
}

async function fingerprintUnlock() {
  const btn = document.getElementById('fpBtn');
  btn.disabled = true;
  setStatus('👆 Touch fingerprint sensor...', '');
  try {
    // Request biometric verification via Web Authentication API
    const challenge = new Uint8Array(32);
    crypto.getRandomValues(challenge);
    await navigator.credentials.get({
      publicKey: {
        challenge,
        timeout: 60000,
        userVerification: 'required',
        rpId: window.location.hostname,
        allowCredentials: []
      }
    });
    // Fingerprint verified — send unlock
    setStatus('✅ Fingerprint verified! Unlocking...', 'ok');
    const r = await fetch('/api/system/unlock', { method: 'POST' });
    const d = await r.json();
    setStatus('🔓 ' + (d.message || 'Unlock sent!'), 'ok');
  } catch (e) {
    if (e.name === 'NotAllowedError') {
      setStatus('Fingerprint cancelled', 'err');
    } else if (e.name === 'NotSupportedError' || e.name === 'InvalidStateError') {
      // No registered credential — fall back: just do biometric check via platform
      try {
        const ok = await verifyPlatformBiometric();
        if (ok) {
          const r = await fetch('/api/system/unlock', { method: 'POST' });
          const d = await r.json();
          setStatus('🔓 ' + (d.message || 'Unlocked!'), 'ok');
        }
      } catch {
        setStatus('Set up fingerprint in phone browser first', 'err');
      }
    } else {
      setStatus('Use PIN instead: ' + e.message, 'err');
    }
  }
  btn.disabled = false;
}

async function verifyPlatformBiometric() {
  // Try using credential.create with platform authenticator as fallback
  const challenge = new Uint8Array(32);
  crypto.getRandomValues(challenge);
  const id = new Uint8Array(16);
  crypto.getRandomValues(id);
  const cred = await navigator.credentials.create({
    publicKey: {
      challenge,
      rp: { name: 'MARSHALL', id: window.location.hostname },
      user: { id, name: 'marshall', displayName: 'Marshall' },
      pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
      authenticatorSelection: { authenticatorAttachment: 'platform', userVerification: 'required' },
      timeout: 60000
    }
  });
  return !!cred;
}

function shake() {
  const d = document.getElementById('pinDisplay');
  d.style.animation = 'shake 0.3s ease';
  setTimeout(() => d.style.animation = '', 400);
}

function setStatus(msg, cls) {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = 'status ' + cls;
}

// Keyboard support
document.addEventListener('keydown', e => {
  if (e.key >= '0' && e.key <= '9') press(e.key);
  else if (e.key === 'Backspace') del();
  else if (e.key === 'Enter') submit();
});
</script>
<style>
@keyframes shake {
  0%,100%{transform:translateX(0)} 20%{transform:translateX(-8px)} 40%{transform:translateX(8px)} 60%{transform:translateX(-6px)} 80%{transform:translateX(6px)}
}
</style>
</body>
</html>
"""
