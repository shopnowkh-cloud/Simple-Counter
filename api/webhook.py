#!/usr/bin/env python3
import asyncio, json, os, sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update
from bot import build_app


async def _process(body: bytes) -> None:
    app = build_app()
    async with app:
        update = Update.de_json(json.loads(body), app.bot)
        await app.process_update(update)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            asyncio.run(_process(body))
            code = 200
            msg = b'{"ok":true}'
        except Exception as e:
            print(f"[webhook] error: {e}")
            code = 500
            msg = b'{"ok":false}'
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
