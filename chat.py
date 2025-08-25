# chat.py — AI chatbot with streaming + memory controls + save/load + export json
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# ---------- Helpers ----------

def save_transcript(messages, filename=None):
    """Save the current conversation (including system message) to a text file."""
    if not filename or not filename.strip():
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"chat_{ts}.txt"
    if not filename.lower().endswith(".txt"):
        filename += ".txt"

    lines = []
    for m in messages:
        role = m.get("role", "unknown").upper()
        content = (m.get("content", "") or "").replace("\r", "")
        lines.append(f"{role}: {content}")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n\n".join(lines))

    return filename

def load_transcript(filename):
    """Load a TXT transcript and return a messages list suitable for the API."""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File not found: {filename}")

    messages = []
    with open(filename, "r", encoding="utf-8") as f:
        raw = f.read()

    chunks = [c.strip() for c in raw.split("\n\n") if c.strip()]
    for chunk in chunks:
        if ":" not in chunk:
            continue
        role_part, content_part = chunk.split(":", 1)
        role = role_part.strip().lower()
        content = content_part.strip()
        if role in {"system", "user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    if not messages or messages[0]["role"] != "system":
        messages = [{"role": "system", "content": "You are a helpful, concise assistant. Keep answers short unless asked."}] + messages

    return messages

def export_json(messages, filename=None):
    """Export the conversation as JSON (list of {role, content})."""
    if not filename or not filename.strip():
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"chat_{ts}.json"
    if not filename.lower().endswith(".json"):
        filename += ".json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    return filename

# ---------- Main ----------

def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  No OPENAI_API_KEY found. Add it to your .env file.")
        return

    client = OpenAI(api_key=api_key)

    messages = [
        {"role": "system", "content": "You are a helpful, concise assistant. Keep answers short unless asked."}
    ]
    MAX_MESSAGES = 1 + 20  # system + last 20 messages

    print("🧠 Memory ON. Commands: :clear, :memory <N>, :save [file], :load <file>, :export json [file]. Type 'quit' to exit.\n")
    while True:
        user = input("You: ")
        if user.strip().lower() in {"quit", "exit"}:
            print("Bot: Bye! 👋")
            break

        # ----- Commands -----
        if user.startswith(":clear"):
            messages = [messages[0]]
            print("Bot: 🧹 Memory cleared.\n")
            continue

        if user.startswith(":memory"):
            parts = user.split()
            if len(parts) == 2 and parts[1].isdigit():
                MAX_MESSAGES = 1 + int(parts[1]) * 2
                print(f"Bot: 📏 Memory limit set to {parts[1]} turns.\n")
            else:
                print("Bot: Usage → :memory <number>\n")
            continue

        if user.startswith(":save"):
            parts = user.split(maxsplit=1)
            filename = parts[1] if len(parts) == 2 else None
            try:
                saved = save_transcript(messages, filename)
                print(f"Bot: 💾 Conversation saved to '{saved}'.\n")
            except Exception as e:
                print(f"Bot: ❌ Could not save transcript: {e}\n")
            continue

        if user.startswith(":load"):
            parts = user.split(maxsplit=1)
            if len(parts) != 2:
                print("Bot: Usage → :load <filename>\n")
                continue
            filename = parts[1]
            try:
                loaded = load_transcript(filename)
                if len(loaded) > MAX_MESSAGES:
                    loaded = [loaded[0]] + loaded[-(MAX_MESSAGES-1):]
                messages = loaded
                print(f"Bot: 📂 Loaded transcript from '{filename}'.\n")
            except Exception as e:
                print(f"Bot: ❌ Could not load transcript: {e}\n")
            continue

        if user.startswith(":export json"):
            parts = user.split(maxsplit=2)  # allow optional filename
            filename = parts[2] if len(parts) == 3 else None
            try:
                saved = export_json(messages, filename)
                print(f"Bot: 📤 JSON exported to '{saved}'.\n")
            except Exception as e:
                print(f"Bot: ❌ Could not export JSON: {e}\n")
            continue

        # ----- Normal chat -----
        messages.append({"role": "user", "content": user})

        stream = client.chat.completions.create(
            model=os.getenv("MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0.2,
            stream=True
        )

        print("Bot: ", end="", flush=True)
        assistant_text = ""
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                assistant_text += delta
                print(delta, end="", flush=True)
        print("\n")

        messages.append({"role": "assistant", "content": assistant_text})

        if len(messages) > MAX_MESSAGES:
            messages = [messages[0]] + messages[-(MAX_MESSAGES-1):]

if __name__ == "__main__":
    main()
