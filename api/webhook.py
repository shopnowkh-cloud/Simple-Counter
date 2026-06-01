import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update
from bot import build_app


async def _process(body: bytes):
    app = build_app()
    await app.initialize()
    try:
        update = Update.de_json(json.loads(body), app.bot)
        await app.process_update(update)
    finally:
        await app.shutdown()


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        asyncio.run(_process(body))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Khmer Multi-Tool Bot is running!")

    def log_message(self, format, *args):
        pass
