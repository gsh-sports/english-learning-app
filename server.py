# -*- coding: utf-8 -*-
"""本地小后端：既发网页静态文件，又提供 /api/chat 转发给本地 Claude Code (claude -p)。
作为 AI 英语陪练，无需 API 密钥，用本机已登录的 Claude。
启动：python3 server.py   (默认 8000 端口)
"""
import json, os, subprocess, tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

DIR = os.path.dirname(os.path.abspath(__file__))
# 给 claude 一个干净的空工作目录，避免它去翻项目文件
CHAT_CWD = tempfile.mkdtemp(prefix="aichat_")

SYSTEM = """You are a warm, friendly English conversation tutor for a Chinese ABSOLUTE BEGINNER (A1 level).
Follow these rules strictly:
- Reply ONLY in very simple English, short sentences (under 12 words).
- If the student's English has a mistake, add ONE short correction line starting with 💡.
- Always keep the conversation going: end with a simple question.
- After your English reply, add a Simplified Chinese translation in parentheses.
- Do NOT use any tools. Just chat. Be encouraging."""

def ask_claude(history):
    lines = [SYSTEM, "", "Conversation so far:"]
    for m in history[-12:]:
        who = "Student" if m.get("role") == "user" else "Tutor"
        lines.append(f"{who}: {m.get('text','')}")
    lines.append("Tutor:")
    prompt = "\n".join(lines)
    try:
        r = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=90, cwd=CHAT_CWD,
        )
        out = (r.stdout or "").strip()
        return out or "Let's try again! (我们再试一次吧！)"
    except subprocess.TimeoutExpired:
        return "Hmm, I need more time. Please ask again. (我需要点时间，请再问一次。)"
    except Exception as e:
        return f"Server error: {e}"

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DIR, **k)

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404); return
        try:
            ln = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(ln) or b"{}")
            reply = ask_claude(body.get("history", []))
        except Exception as e:
            reply = f"Bad request: {e}"
        data = json.dumps({"reply": reply}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    print(f"英语学习 App 服务器启动：http://localhost:8000  (AI陪练工作目录 {CHAT_CWD})")
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
