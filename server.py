# -*- coding: utf-8 -*-
"""本地小后端：发网页静态文件 + /api/chat 提供 AI 英语陪练。

支持三种后端（前端在"设置"里选供应商；浏览器没填 key 时回退到本服务器）：
  - claude  : 调用本机已登录的 Claude Code (claude -p)，无需 key
  - deepseek: 调用 DeepSeek，密钥取自环境变量 DEEPSEEK_API_KEY
  - qwen    : 调用通义千问，密钥取自环境变量 DASHSCOPE_API_KEY

启动：
  python3 server.py
  # 想用 DeepSeek/千问 代理，先设环境变量再启动，例如：
  #   export DEEPSEEK_API_KEY=sk-xxx
  #   export DASHSCOPE_API_KEY=sk-xxx
"""
import json, os, subprocess, tempfile, urllib.request, urllib.error
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

DIR = os.path.dirname(os.path.abspath(__file__))
CHAT_CWD = tempfile.mkdtemp(prefix="aichat_")  # 给 claude 一个干净的空工作目录

SYSTEM = """You are a warm, friendly English conversation tutor for a Chinese ABSOLUTE BEGINNER (A1 level).
Follow these rules strictly:
- Reply ONLY in very simple English, short sentences (under 12 words).
- The student may ask or speak in Chinese — understand it and still answer in simple English.
- If they ask how to say something in English, teach them the English sentence.
- If the student's English has a mistake, add ONE short correction line starting with 💡.
- Always keep the conversation going: end with a simple question.
- After your English reply, add a Simplified Chinese translation in parentheses.
- Do NOT use any tools. Just chat. Be encouraging."""

# OpenAI 兼容供应商：base + 取密钥的环境变量名 + 默认模型
PROVIDERS = {
    "deepseek": {"base": "https://api.deepseek.com", "env": "DEEPSEEK_API_KEY", "model": "deepseek-chat"},
    "qwen":     {"base": "https://dashscope.aliyuncs.com/compatible-mode/v1", "env": "DASHSCOPE_API_KEY", "model": "qwen-turbo"},
}

def build_messages(history):
    msgs = [{"role": "system", "content": SYSTEM}]
    for m in history[-12:]:
        role = "user" if m.get("role") == "user" else "assistant"
        if len(msgs) == 1 and role == "assistant":  # 首条业务消息不能是 assistant
            continue
        msgs.append({"role": role, "content": m.get("text", "")})
    return msgs

# 本地 Claude 用 Haiku + 跳过 MCP/额外设置 来降低启动延迟（约 6s → 3.5s）
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5")

def ask_claude(history):
    lines = [SYSTEM, "", "Conversation so far:"]
    for m in history[-12:]:
        who = "Student" if m.get("role") == "user" else "Tutor"
        lines.append(f"{who}: {m.get('text','')}")
    lines.append("Tutor:")
    try:
        r = subprocess.run(
            ["claude", "-p", "--model", CLAUDE_MODEL,
             "--strict-mcp-config", "--setting-sources", "", "\n".join(lines)],
            capture_output=True, text=True, timeout=90, cwd=CHAT_CWD)
        return (r.stdout or "").strip() or "Let's try again! (我们再试一次吧！)"
    except subprocess.TimeoutExpired:
        return "Hmm, I need more time. Please ask again. (我需要点时间，请再问一次。)"
    except Exception as e:
        return f"Server error: {e}"

def ask_openai(provider, model, history):
    cfg = PROVIDERS[provider]
    key = os.environ.get(cfg["env"])
    if not key:
        return f"（本地代理未配置 {provider} 密钥：请先设置环境变量 {cfg['env']} 再启动 server.py）"
    body = json.dumps({
        "model": model or cfg["model"],
        "max_tokens": 600,
        "messages": build_messages(history),
    }).encode("utf-8")
    req = urllib.request.Request(
        cfg["base"].rstrip("/") + "/chat/completions",
        data=body, method="POST",
        headers={"content-type": "application/json", "authorization": "Bearer " + key},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            d = json.loads(resp.read().decode("utf-8"))
        return (d.get("choices", [{}])[0].get("message", {}).get("content") or "").strip() or "（空回复）"
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:
            msg = ""
        return f"{provider} 接口出错 {e.code}: {msg}（检查密钥/额度/模型名）"
    except Exception as e:
        return f"{provider} 代理出错: {e}"

def reply_for(body):
    history = body.get("history", [])
    provider = body.get("provider", "claude")
    model = body.get("model")
    if provider in PROVIDERS:
        return ask_openai(provider, model, history)
    return ask_claude(history)  # claude 或未知供应商都走本地 Claude

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DIR, **k)

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404); return
        try:
            ln = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(ln) or b"{}")
            reply = reply_for(body)
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
    avail = [p for p, c in PROVIDERS.items() if os.environ.get(c["env"])]
    print(f"英语学习 App 服务器：http://localhost:8000")
    print(f"  AI 后端：claude(本地) " + (("+ " + " + ".join(avail)) if avail else "(未配置 DeepSeek/千问 环境变量)"))
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
