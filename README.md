# AI Chatbot 🚀

A Python-based chatbot built **from scratch** using the OpenAI API.  
Features both a **CLI chatbot** and a **web-based chatbot (FastAPI + HTML/JS)** with streaming replies and memory.

---

## ✨ Features

### CLI Mode (`chat.py`)
- Real-time **streaming responses**
- Short-term **memory** (remembers conversation context)
- Memory controls:
  - `:clear` → reset memory
  - `:memory <N>` → set memory window (number of turns)
  - `:save [filename]` → save conversation as `.txt`
  - `:load <filename>` → load previous conversation
  - `:export json [filename]` → export conversation as `.json`

### Web Mode (`web.py`)
- Simple **browser chat interface** (http://127.0.0.1:8000)
- **Streaming replies** (typed out live)
- Per-session **memory** (context-aware)
- Memory controls via buttons:
  - Clear Memory
  - Set Memory Turns
- **Export conversation**
  - Download as `.json`
  - Download as `.txt`

---

## 🛠️ Setup

1. **Clone repo & enter folder**
   ```bash
   git clone https://github.com/<your-username>/ai-chatbot.git
   cd ai-chatbot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate venv**
   - Windows:
     ```powershell
     .venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   *(If you don’t have `requirements.txt`, run `pip install openai fastapi uvicorn python-dotenv` and then `pip freeze > requirements.txt`)*

5. **Add `.env` file**
   ```env
   OPENAI_API_KEY=your_api_key_here
   MODEL=gpt-4o-mini
   ```

---

## 🚀 Usage

### Run CLI chatbot
```bash
python chat.py
```
Example:
```
You: My name is Tarun.
Bot: Nice to meet you, Tarun! How can I assist you today?
You: What is my name?
Bot: Your name is Tarun.
```

### Run Web chatbot
```bash
uvicorn web:app --reload
```
- Open → [http://127.0.0.1:8000](http://127.0.0.1:8000)  
- Type in the input box → see replies **stream live**  
- Use controls:
  - **Clear Memory**
  - **Export JSON**
  - **Export TXT**
  - **Set Memory Turns**

---

## 📂 Project Structure
```
ai-chatbot/
│── chat.py        # CLI chatbot
│── web.py         # Web chatbot (FastAPI + HTML/JS)
│── .env           # API key (ignored by git)
│── .gitignore     # Ignores .env, venv, caches, exports
│── requirements.txt
└── README.md
```

---

## 📌 Roadmap
- [x] Basic CLI chatbot (echo)
- [x] Connect to OpenAI API
- [x] Streaming responses
- [x] Memory in CLI
- [x] Save/Load/Export conversations (CLI)
- [x] Web interface with FastAPI
- [x] Web memory controls + JSON/TXT export
- [ ] Upload files → Ask questions (RAG)
- [ ] Multi-session support in web UI
- [ ] Deploy online (Render, Railway, HuggingFace Spaces)

---

## ⚡ Credits
Built with ❤️ using:
- [Python](https://www.python.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
