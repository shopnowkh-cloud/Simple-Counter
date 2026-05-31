# Khmer Multi-Tool Telegram Bot

A Telegram bot offering a wide range of utilities in the Khmer language — QR code generation/scanning, text styling, unit conversion, security tools, and financial calculators.

## Run & Operate

- Run the bot: `python3 bot.py`
- Required secret: `BOT_TOKEN` — your Telegram Bot API token (from @BotFather)

## Stack

- Python 3.12
- python-telegram-bot >= 22.7
- Libraries: qrcode, opencv-python, pyzbar, pillow, fpdf2, numpy, python-dateutil
- System deps (via Nix): zbar (for QR scanning)

## Where things live

- `bot.py` — all bot logic, command handlers, and utility functions
- `main.py` — simple entry point (unused; bot runs via bot.py)
- `pyproject.toml` — Python project config and dependencies
- `replit.nix` — system-level Nix dependencies

## Architecture decisions

- Single-file bot architecture; all handlers in `bot.py`
- Uses ConversationHandler pattern to manage multi-step tool states
- All UI strings are in Khmer
- BOT_TOKEN read from environment variable at startup; raises RuntimeError if missing

## Product

Users interact with the bot on Telegram to access tools for:
- QR Tools: Create and Scan QR codes
- Text & Document: Text styling, Image to PDF, Morse code, character count
- Math & Convert: Calculator, Temperature, Base conversion, Unit conversion, BMI, Loan calculator
- Security: Password strength check, password generation, Base64 encode/decode, hashing (MD5/SHA256)
- Fun & Utility: Random picker, Dice/coin, World clock, Age calculator

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- `zbar` system library must be present (handled by replit.nix) for pyzbar/QR scanning to work
- `BOT_TOKEN` must be set as a Replit secret before the bot will start
