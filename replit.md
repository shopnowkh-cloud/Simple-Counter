# Khmer Multi-Tool Telegram Bot (RADY BOT)

A Telegram bot offering utilities in the Khmer language — text styling, PDF tools, QR code generation/scanning, live gold/silver/platinum prices, and AI background removal.

## Run & Operate

- Run the bot: `npx tsx src/bot.ts`
- Required secret: `BOT_TOKEN` — your Telegram Bot API token (from @BotFather)

## Stack

- **Language:** TypeScript (Node.js 20)
- **Bot Framework:** Grammy (`grammy`)
- **Image Processing:** `sharp`
- **PDF Creation:** `pdf-lib`
- **PDF → Image:** `mupdf` (WASM bindings)
- **QR Generation:** `qrcode`
- **QR Scanning:** `jsqr` + `sharp`
- **Background Removal:** `@imgly/background-removal-node`
- **HTTP:** `axios`
- **System deps (Nix):** zbar, mupdf, freetype, libGL, libjpeg, libwebp, zlib, and others

## Where things live

- `src/bot.ts` — all bot logic, handlers, state machine, and utilities
- `src/api/webhook.ts` — webhook server (alternative to polling)
- `package.json` — Node.js dependencies
- `tsconfig.json` — TypeScript configuration

## Architecture

- Single-file bot with session-based state machine (replaces Python's ConversationHandler)
- Grammy sessions store per-user state (current menu, uploaded photos, etc.)
- All UI strings in Khmer
- BOT_TOKEN read from environment variable at startup; throws if missing
- Polling mode by default; webhook mode available via `src/api/webhook.ts`

## User preferences

- Code in TypeScript (converted from Python)
- Preserve same structure and features as original Python version
