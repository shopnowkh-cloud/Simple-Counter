#!/usr/bin/env node
// webhook.ts — equivalent of api/webhook.py
import http from 'http';
import { buildApp } from '../bot.js';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const bot: any = buildApp();

await bot.init();

const server = http.createServer(async (req, res) => {
  if (req.method === 'POST') {
    try {
      const chunks: Buffer[] = [];
      for await (const chunk of req) chunks.push(chunk as Buffer);
      const body   = Buffer.concat(chunks).toString('utf-8');
      const update = JSON.parse(body);
      await bot.handleUpdate(update);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true }));
    } catch (e) {
      console.error('[webhook] error:', e);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: false }));
    }
  } else if (req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'Khmer Multi-Tool Bot webhook is active' }));
  } else {
    res.writeHead(405);
    res.end();
  }
});

const PORT = parseInt(process.env.PORT ?? '8080', 10);
server.listen(PORT, () => {
  console.log(`[webhook] Listening on port ${PORT}`);
});
