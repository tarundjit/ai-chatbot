# web.py — FastAPI backend for your chatbot (streaming + per-session memory)
import os
import json
from typing import Dict, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

# Load API key and model from .env
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY missing in .env")
MODEL = os.getenv("MODEL", "gpt-4o-mini")

# FastAPI app
app = FastAPI(title="AI Chatbot Backend")

# In-memory conversation histories by session_id (resets on server restart)
SESSIONS: Dict[str, List[Dict[str, str]]] = {}

SYSTEM_MSG = {
    "role": "system",
    "content": "You are a helpful, concise assistant. Keep answers short unless asked."
}

# OpenAI client
client = OpenAI(api_key=API_KEY)

class ChatIn(BaseModel):
    message: str
    session_id: str

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/chat")
def chat(inp: ChatIn):
    """
    Accepts JSON: { "message": "...", "session_id": "..." }
    Streams back Server-Sent Events (SSE):
      data: {"delta":"..."}
      data: {"delta":"..."}
      data: [DONE]
    """
    msg = inp.message.strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Empty message")

    # Initialize session if new
    history = SESSIONS.get(inp.session_id)
    if history is None:
        history = [SYSTEM_MSG.copy()]
        SESSIONS[inp.session_id] = history

    # Append user message
    history.append({"role": "user", "content": msg})

    def sse_stream():
        # Call OpenAI with streaming
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

        # After full reply, save assistant message
        history.append({"role": "assistant", "content": assistant_text})

        # Trim memory: keep system + last 20 messages
        MAX_MESSAGES = 1 + 20
        if len(history) > MAX_MESSAGES:
            SESSIONS[inp.session_id] = [history[0]] + history[-(MAX_MESSAGES-1):]

        # End-of-stream marker
        yield "data:[DONE]\n\n"

    return StreamingResponse(sse_stream(), media_type="text/event-stream")
