#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, logging, warnings
from datetime import datetime
from telegram import Update, InlineKeyboardButton as IKB, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters
from telegram.constants import ParseMode, KeyboardButtonStyle as KBS
from telegram.warnings import PTBUserWarning

PRIMARY = KBS.PRIMARY
warnings.filterwarnings("ignore", category=PTBUserWarning)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN មិនទាន់កំណត់!")
logging.basicConfig(format="%(asctime)s|%(levelname)s|%(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

END = ConversationHandler.END
H = ParseMode.HTML

def mkb(*r): return InlineKeyboardMarkup(list(r))
def bb(): return mkb([IKB("🏠 ម៉ឺនុយមេ", callback_data="back_main", style=PRIMARY)])

def mm():
    return mkb(
        [IKB("ℹ️  អំពី Bot", callback_data="menu_about", style=PRIMARY)],
    )

async def _edit(ctx, text, kb=None):
    cid = ctx.user_data.get("cid"); mid = ctx.user_data.get("mid")
    if cid and mid:
        try:
            await ctx.bot.edit_message_text(chat_id=cid, message_id=mid, text=text, reply_markup=kb, parse_mode=H)
            return
        except Exception:
            pass

def _save(ctx, msg):
    ctx.user_data["cid"] = msg.chat_id
    ctx.user_data["mid"] = msg.message_id

# ── /start ──────────────────────────────────────────────────────────────────────
async def cmd_start(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    msg = await u.message.reply_text(
        f"👋 សួស្ដី <b>{u.effective_user.first_name}</b>!\n"
        "┌─────────────────────────┐\n"
        "│  🤖 <b>Khmer Multi-Tool Bot</b> 🇰🇭  │\n"
        "└─────────────────────────┘\n"
        "──────────────────────────\n"
        "👇 <b>ជ្រើសរើស ហើយចុចប៊ូតុង</b>",
        reply_markup=mm(), parse_mode=H)
    _save(ctx, msg)
    return END

# ── callback router ─────────────────────────────────────────────────────────────
async def cb(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query; d = q.data
    if d == "noop": await q.answer(); return END
    await q.answer()
    ctx.user_data["cid"] = q.message.chat_id
    ctx.user_data["mid"] = q.message.message_id

    if d == "back_main":
        await q.edit_message_text(
            "┌─────────────────────────┐\n"
            "│  🤖 <b>Khmer Multi-Tool Bot</b> 🇰🇭  │\n"
            "└─────────────────────────┘\n"
            "──────────────────────────\n"
            "👇 <b>ជ្រើសរើស ហើយចុចប៊ូតុង</b>",
            reply_markup=mm(), parse_mode=H)
        return END

    if d == "menu_about":
        import telegram as _tg
        import sys
        ptb_ver = _tg.__version__
        py_ver = sys.version.split()[0]
        await q.edit_message_text(
            f"ℹ️ <b>Khmer Multi-Tool Bot</b>\n"
            f"┌─────────────────────────┐\n"
            f"│  🔖 Version: <b>4.0</b>  │  🇰🇭 Khmer  │\n"
            f"└─────────────────────────┘\n"
            f"📅 <code>{datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🐍 Python: <b>{py_ver}</b>\n"
            f"📡 python-telegram-bot: <b>{ptb_ver}</b>\n"
            f"🤖 Telegram Bot API: <b>9.4 ✅</b>",
            reply_markup=bb(), parse_mode=H)
        return END

    return END

# ── Fallback ──────────────────────────────────────────────────────────────────
async def fallback(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try: await u.message.delete()
    except: pass
    await _edit(ctx, "🤔 <b>ខ្ញុំមិនយល់!</b>\n\n👇 សូមជ្រើសរើស ឬ វាយ /start", mm())

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).connect_timeout(10).read_timeout(30).write_timeout(30).pool_timeout(10).build()
    CB_H = CallbackQueryHandler(cb)
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start), CB_H],
        states={},
        fallbacks=[CommandHandler("start", cmd_start), MessageHandler(filters.ALL, fallback)],
        per_message=False, allow_reentry=True,
    ))
    logger.info("🤖 Bot កំពុង Start...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, poll_interval=1.0, drop_pending_updates=True)

if __name__ == "__main__":
    main()
