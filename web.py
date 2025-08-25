# web.py — FastAPI backend for your chatbot (streaming + per-session memory + web controls + export)
import os
import json
from typing import Dict, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

# Load API key and model from .env
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY missing in .env")
MODEL = os.getenv("MODEL", "gpt-4o-mini")

app = FastAPI(title="AI Chatbot Backend")

# ---- In-memory session state ----
SESSIONS: Dict[str, List[Dict[str, str]]] = {}   # session_id -> messages
MAX_TURNS = 10  # keep last N user+assistant turns (≈ 2*N messages + system)

def max_messages() -> int:
    return 1 + 2 * MAX_TURNS  # 1 system + pairs of (user, assistant)

SYSTEM_MSG = {
    "role": "system",
    "content": "You are a helpful, concise assistant. Keep answers short unless asked."
}

client = OpenAI(api_key=API_KEY)

# ---- Schemas ----
class ChatIn(BaseModel):
    message: str
    session_id: str

class ClearIn(BaseModel):
    session_id: str

class MemorySizeIn(BaseModel):
    turns: int  # >= 1

# ---- UI ----
@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>AI Chatbot</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 20px; }
    #chat { border: 1px solid #ddd; padding: 12px; height: 360px; overflow:auto; }
    .u { color:#444; margin:8px 0; }
    .b { color:#111; margin:8px 0; white-space: pre-wrap; }
    #row { margin-top: 12px; display:flex; gap:8px; }
    input, button { font-size: 16px; }
    input { flex:1; padding:8px; }
    button { padding:8px 12px; }
    #controls { margin-top:12px; display:flex; gap:8px; align-items:center; flex-wrap: wrap; }
    #status { margin-top:8px; font-size:12px; color:#666; }
    label { font-size: 14px; color:#333; }
    #turns { width: 80px; }
  </style>
</head>
<body>
  <h1>AI Chatbot (Streaming + Memory Controls)</h1>
  <div id="chat"></div>

  <div id="row">
    <input id="msg" placeholder="Type a message..." />
    <button id="send">Send</button>
  </div>

  <div id="controls">
    <button id="clear">Clear Memory</button>
    <button id="export">Export JSON</button>
    <button id="exportTxt">Export TXT</button>
    <label>Memory turns: <input id="turns" type="number" min="1" value="10"/></label>
    <button id="setTurns">Set</button>
  </div>

  <div id="status">Ready</div>

<script>
"use strict";

const chat = document.getElementById("chat");
const input = document.getElementById("msg");
const send = document.getElementById("send");
const clearBtn = document.getElementById("clear");
const exportBtn = document.getElementById("export");
const exportTxtBtn = document.getElementById("exportTxt");
const turnsInput = document.getElementById("turns");
const setTurnsBtn = document.getElementById("setTurns");
const statusEl = document.getElementById("status");

const sessionId = "webdemo"; // simple per-tab session

function logStatus(txt){ statusEl.textContent = txt; }
function appendUser(text){
  const div = document.createElement("div");
  div.className = "u";
  div.textContent = "You: " + text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}
function appendBotStart(){
  const div = document.createElement("div");
  div.className = "b";
  div.textContent = "Bot: ";
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

async function sendMsg(){
  const text = input.value.trim();
  if(!text) return;
  input.value = "";
  appendUser(text);
  const botDiv = appendBotStart();

  logStatus("Sending…");
  const resp = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
    body: JSON.stringify({ message: text, session_id: sessionId })
  });

  if(!resp.ok || !resp.body){
    botDiv.textContent += " [error]";
    logStatus("HTTP " + resp.status);
    return;
  }

  logStatus("Streaming…");
  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Split SSE frames on blank line
    let frames = buffer.split("\\n\\n");
    buffer = frames.pop();

    for (const frame of frames) {
      if (!frame.startsWith("data:")) continue;
      const payload = frame.slice(5).trim().replace(/\\r$/, "");
      if (payload === "[DONE]") { buffer = ""; break; }
      try {
        const obj = JSON.parse(payload);
        if (obj && obj.delta) {
          botDiv.textContent += obj.delta;
          chat.scrollTop = chat.scrollHeight;
        }
      } catch { /* ignore non-JSON */ }
    }
  }
  logStatus("Done");
}

async function clearMemory(){
  logStatus("Clearing memory…");
  const resp = await fetch("/clear", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId })
  });
  if(resp.ok){
    logStatus("Memory cleared");
    chat.innerHTML = ""; // reset view
  } else {
    logStatus("Clear failed: " + resp.status);
  }
}

async function exportJSON(){
  logStatus("Exporting…");
  const resp = await fetch(`/export?session_id=${encodeURIComponent(sessionId)}`);
  if(!resp.ok){ logStatus("Export failed: " + resp.status); return; }
  const data = await resp.json();
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "chat_export.json";
  a.click();
  URL.revokeObjectURL(url);
  logStatus("Exported");
}

function exportTXT(){
  window.location = `/export_txt?session_id=${encodeURIComponent(sessionId)}`;
}

async function setMemoryTurns(){
  const turns = parseInt(turnsInput.value, 10);
  if(!(turns >= 1)){ alert("Enter a number >= 1"); return; }
  logStatus("Setting memory turns…");
  const resp = await fetch("/memory_size", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ turns })
  });
  if(resp.ok){
    logStatus("Memory turns set to " + turns);
  } else {
    logStatus("Set failed: " + resp.status);
  }
}

send.addEventListener("click", sendMsg);
input.addEventListener("keydown", (e)=>{ if(e.key === "Enter") sendMsg(); });
clearBtn.addEventListener("click", clearMemory);
exportBtn.addEventListener("click", exportJSON);
exportTxtBtn.addEventListener("click", exportTXT);
setTurnsBtn.addEventListener("click", setMemoryTurns);
</script>
</body>
</html>
"""

# ---- Health ----
@app.get("/health")
def health():
    return {"ok": True}

# ---- Chat (SSE streaming) ----
@app.post("/chat")
def chat(inp: ChatIn):
    """
    Accepts JSON: { "message": "...", "session_id": "..." }
    Streams back SSE:
      data: {"delta":"..."}
      ...
      data:[DONE]
    """
    msg = inp.message.strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Empty message")

    # Get or init session
    history = SESSIONS.get(inp.session_id)
    if history is None:
        history = [SYSTEM_MSG.copy()]
        SESSIONS[inp.session_id] = history

    # Append user
    history.append({"role": "user", "content": msg})

    def sse_stream():
        stream = client.chat.completions.create(
            model=MODEL,
            messages=history,
            temperature=0.2,
            stream=True
        )
        assistant_text = ""
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                assistant_text += delta
                yield f"data:{json.dumps({'delta': delta})}\n\n"

        # Save assistant
        history.append({"role": "assistant", "content": assistant_text})

        # Trim window
        if len(history) > max_messages():
            SESSIONS[inp.session_id] = [history[0]] + history[-(max_messages()-1):]

        # End marker
        yield "data:[DONE]\n\n"

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

# ---- Memory controls ----
@app.post("/clear")
def clear_memory(inp: ClearIn):
    """Clear memory for a given session_id."""
    SESSIONS[inp.session_id] = [SYSTEM_MSG.copy()]
    return {"ok": True, "session_id": inp.session_id}

@app.post("/memory_size")
def set_memory_size(body: MemorySizeIn):
    """Set global memory window (number of user+assistant turns)."""
    global MAX_TURNS
    if body.turns < 1:
        raise HTTPException(status_code=400, detail="turns must be >= 1")
    MAX_TURNS = body.turns
    return {"ok": True, "max_turns": MAX_TURNS, "max_messages": max_messages()}

# ---- Exports ----
@app.get("/export")
def export_json(session_id: str = Query(..., description="Session ID to export as JSON")):
    """Export messages for a given session_id as JSON."""
    history = SESSIONS.get(session_id, [SYSTEM_MSG.copy()])
    clean = [{"role": m.get("role",""), "content": m.get("content","")} for m in history]
    return JSONResponse(content=clean)

@app.get("/export_txt")
def export_txt(session_id: str = Query(..., description="Session ID to export as plain text")):
    """Download the conversation as a .txt file."""
    history = SESSIONS.get(session_id, [SYSTEM_MSG.copy()])
    lines = []
    for m in history:
        role = (m.get("role") or "unknown").upper()
        content = (m.get("content") or "").replace("\r", "")
        lines.append(f"{role}: {content}")
    body = "\n\n".join(lines)
    return Response(
        content=body,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="chat_export.txt"'}
    )
