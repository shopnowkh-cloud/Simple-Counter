#!/usr/bin/env python3
import asyncio, json, os, sys, threading
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update
from bot import build_app

# ── Persistent loop + app (module-level, reused across warm requests) ──────────
_loop = asyncio.new_event_loop()

def _run_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=_run_loop, args=(_loop,), daemon=True).start()

_app = build_app()
asyncio.run_coroutine_threadsafe(_app.initialize(), _loop).result(timeout=15)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            update = Update.de_json(json.loads(body), _app.bot)
            future = asyncio.run_coroutine_threadsafe(
                _app.process_update(update), _loop
            )
            future.result(timeout=25)
            code, msg = 200, b'{"ok":true}'
        except Exception as e:
            print(f"[webhook] error: {e}")
            code, msg = 500, b'{"ok":false}'
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(msg)

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"Khmer Multi-Tool Bot webhook is active"}')

    def log_message(self, *_):
        pass
