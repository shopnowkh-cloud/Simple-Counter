#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║          🤖 KHMER MULTI-TOOL TELEGRAM BOT                   ║
║          បង្កើតដោយ: limsovannrady                           ║
║          Version: 2.0.0                                      ║
╚══════════════════════════════════════════════════════════════╝

លក្ខណៈពិសេស (Features):
  ✅ បង្កើត QR Code
  ✅ Scan QR Code
  ✅ រចនាប័ទ្មអក្សរ (Text Styles) + ចម្លងជាប៊ូតុង
  ✅ រូបភាព → PDF
  ✅ ម៉ាស៊ីនគណនា (Calculator)
  ✅ ពិនិត្យ Password ម៉ាស
  ✅ ចំលែកពាក្យ (Random Name / Picker)
  ✅ ក្តារចុចអក្សរ Morse Code
  ✅ Base64 Encode / Decode
  ✅ ស្ថានភាព Bot (Bot Info)

Dependencies (pip install):
  pip install python-telegram-bot==20.7
  pip install qrcode[pil]==7.4.2
  pip install Pillow==10.2.0
  pip install pyzbar==0.1.9
  pip install fpdf2==2.7.9
  pip install opencv-python-headless==4.9.0.80
"""

import os
import io
import re
import math
import base64
import random
import logging
import qrcode
import cv2
import numpy as np

from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode
from fpdf import FPDF
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

# ─────────────────────────────────────────────
#  🔐 CONFIG  — ដាក់ TOKEN របស់អ្នក
# ─────────────────────────────────────────────
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"   # ← ប្តូរ Token នៅទីនេះ

# ─────────────────────────────────────────────
#  📋 LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  🔢 CONVERSATION STATES
# ─────────────────────────────────────────────
(
    STATE_QR_INPUT,       # រង់ចាំអ្នកវាយអ្វីត្រូវបង្កើត QR
    STATE_SCAN_PHOTO,     # រង់ចាំរូបភាព QR ត្រូវ Scan
    STATE_TEXT_STYLE,     # រង់ចាំអក្សរត្រូវ Style
    STATE_PDF_PHOTOS,     # រង់ចាំរូបភាពច្រើន → PDF
    STATE_CALC_INPUT,     # ម៉ាស៊ីនគណនា
    STATE_PASS_CHECK,     # ពិនិត្យ Password
    STATE_PICKER_INPUT,   # Random Picker
    STATE_MORSE_INPUT,    # Morse Code
    STATE_BASE64_INPUT,   # Base64
) = range(9)

# ─────────────────────────────────────────────
#  🎨 TEXT STYLE DEFINITIONS  (Khmer + Unicode)
# ─────────────────────────────────────────────
# គំរូ unicode text style transformer
def _transform(text: str, mapping: dict) -> str:
    return "".join(mapping.get(c, c) for c in text)

BOLD_MAP = {
    **{chr(i): chr(i + 0x1D400 - 0x41) for i in range(0x41, 0x5B)},   # A-Z
    **{chr(i): chr(i + 0x1D41A - 0x61) for i in range(0x61, 0x7B)},   # a-z
    **{chr(i): chr(i + 0x1D7CE - 0x30) for i in range(0x30, 0x3A)},   # 0-9
}
ITALIC_MAP = {
    **{chr(i): chr(i + 0x1D434 - 0x41) for i in range(0x41, 0x5B)},
    **{chr(i): chr(i + 0x1D44E - 0x61) for i in range(0x61, 0x7B)},
}
BOLD_ITALIC_MAP = {
    **{chr(i): chr(i + 0x1D468 - 0x41) for i in range(0x41, 0x5B)},
    **{chr(i): chr(i + 0x1D482 - 0x61) for i in range(0x61, 0x7B)},
}
SCRIPT_MAP = {
    **{chr(i): chr(i + 0x1D49C - 0x41) for i in range(0x41, 0x5B)},
    **{chr(i): chr(i + 0x1D4B6 - 0x61) for i in range(0x61, 0x7B)},
}
DOUBLE_STRUCK_MAP = {
    **{chr(i): chr(i + 0x1D538 - 0x41) for i in range(0x41, 0x5B)},
    **{chr(i): chr(i + 0x1D552 - 0x61) for i in range(0x61, 0x7B)},
    **{chr(i): chr(i + 0x1D7D8 - 0x30) for i in range(0x30, 0x3A)},
}
SMALL_CAPS = {
    "a":"ᴀ","b":"ʙ","c":"ᴄ","d":"ᴅ","e":"ᴇ","f":"ꜰ","g":"ɢ","h":"ʜ",
    "i":"ɪ","j":"ᴊ","k":"ᴋ","l":"ʟ","m":"ᴍ","n":"ɴ","o":"ᴏ","p":"ᴘ",
    "q":"Q","r":"ʀ","s":"ꜱ","t":"ᴛ","u":"ᴜ","v":"ᴠ","w":"ᴡ","x":"x",
    "y":"ʏ","z":"ᴢ",
}
BUBBLE_MAP = {
    **{chr(i): chr(i + 0x24B6 - 0x41) for i in range(0x41, 0x5B)},
    **{chr(i): chr(i + 0x24D0 - 0x61) for i in range(0x61, 0x7B)},
    **{"0":"⓪","1":"①","2":"②","3":"③","4":"④",
       "5":"⑤","6":"⑥","7":"⑦","8":"⑧","9":"⑨"},
}
UPSIDE_DOWN_MAP = {
    "a":"ɐ","b":"q","c":"ɔ","d":"p","e":"ǝ","f":"ɟ","g":"ƃ","h":"ɥ",
    "i":"ᴉ","j":"ɾ","k":"ʞ","l":"l","m":"ɯ","n":"u","o":"o","p":"d",
    "q":"b","r":"ɹ","s":"s","t":"ʇ","u":"n","v":"ʌ","w":"ʍ","x":"x",
    "y":"ʎ","z":"z","A":"∀","B":"ᗺ","C":"Ɔ","D":"ᗡ","E":"Ǝ","F":"Ⅎ",
    "G":"פ","H":"H","I":"I","J":"ſ","K":"ʞ","L":"˥","M":"W","N":"N",
    "O":"O","P":"Ԁ","Q":"Q","R":"ɹ","S":"S","T":"┴","U":"∩","V":"Λ",
    "W":"M","X":"X","Y":"⅄","Z":"Z",
    "0":"0","1":"Ɩ","2":"ᄅ","3":"Ɛ","4":"ᔭ","5":"ϛ","6":"9","7":"ㄥ",
    "8":"8","9":"6"," ":" ",
}
STRIKETHROUGH_MAP = lambda t: "".join(c + "̶" for c in t)
UNDERLINE_MAP     = lambda t: "".join(c + "̲" for c in t)

TEXT_STYLES = {
    "bold":         ("𝗕𝗼𝗹𝗱",          lambda t: _transform(t, BOLD_MAP)),
    "italic":       ("𝘐𝘵𝘢𝘭𝘪𝘤",        lambda t: _transform(t, ITALIC_MAP)),
    "bold_italic":  ("𝑩𝒐𝒍𝒅 𝑰𝒕𝒂𝒍𝒊𝒄",  lambda t: _transform(t, BOLD_ITALIC_MAP)),
    "script":       ("𝒮𝒸𝓇𝒾𝓅𝓉",        lambda t: _transform(t, SCRIPT_MAP)),
    "double":       ("𝔻𝕠𝕦𝕓𝕝𝕖",        lambda t: _transform(t, DOUBLE_STRUCK_MAP)),
    "small_caps":   ("Sᴍᴀʟʟ Cᴀᴘꜱ",    lambda t: _transform(t.lower(), SMALL_CAPS)),
    "bubble":       ("Ⓑⓤⓑⓑⓛⓔ",        lambda t: _transform(t, BUBBLE_MAP)),
    "upside_down":  ("uʍop ǝpᴉsdn",   lambda t: _transform(t, UPSIDE_DOWN_MAP)[::-1]),
    "strikethrough":("S̶t̶r̶i̶k̶e̶",      STRIKETHROUGH_MAP),
    "underline":    ("U̲n̲d̲e̲r̲",         UNDERLINE_MAP),
}

# ─────────────────────────────────────────────
#  🔑 MORSE CODE TABLE
# ─────────────────────────────────────────────
MORSE = {
    "A":".-","B":"-...","C":"-.-.","D":"-..","E":".","F":"..-.","G":"--.","H":"....","I":"..","J":".---",
    "K":"-.-","L":".-..","M":"--","N":"-.","O":"---","P":".--.","Q":"--.-","R":".-.","S":"...","T":"-",
    "U":"..-","V":"...-","W":".--","X":"-..-","Y":"-.--","Z":"--..",
    "0":"-----","1":".----","2":"..---","3":"...--","4":"....-","5":".....",
    "6":"-....","7":"--...","8":"---..","9":"----."," ":"/"
}
MORSE_REVERSE = {v: k for k, v in MORSE.items()}

def text_to_morse(t: str) -> str:
    return " ".join(MORSE.get(c.upper(), "?") for c in t)

def morse_to_text(m: str) -> str:
    return "".join(MORSE_REVERSE.get(w, "?") for w in m.strip().split(" "))

# ─────────────────────────────────────────────
#  🏠 MAIN MENU  (INLINE KEYBOARD)
# ─────────────────────────────────────────────
def main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("📷 បង្កើត QR Code",    callback_data="menu_qr_create"),
            InlineKeyboardButton("🔍 Scan QR Code",       callback_data="menu_qr_scan"),
        ],
        [
            InlineKeyboardButton("✍️ រចនាប័ទ្មអក្សរ",    callback_data="menu_text_style"),
            InlineKeyboardButton("🖼️ រូបភាព → PDF",      callback_data="menu_photo_pdf"),
        ],
        [
            InlineKeyboardButton("🔢 ម៉ាស៊ីនគណនា",       callback_data="menu_calculator"),
            InlineKeyboardButton("🔐 ពិនិត្យ Password",   callback_data="menu_password"),
        ],
        [
            InlineKeyboardButton("🎲 Random Picker",      callback_data="menu_picker"),
            InlineKeyboardButton("📡 Morse Code",         callback_data="menu_morse"),
        ],
        [
            InlineKeyboardButton("🔒 Base64",             callback_data="menu_base64"),
            InlineKeyboardButton("ℹ️ អំពី Bot",           callback_data="menu_about"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)

def back_button(back_to: str = "main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 ត្រឡប់មុខដំណើរការ", callback_data=f"back_{back_to}")
    ]])

def back_and_cancel(back_to: str = "main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ បោះបង់",             callback_data=f"back_{back_to}"),
        InlineKeyboardButton("🏠 ម៉ឺនុយមេ",           callback_data="back_main"),
    ]])

# ─────────────────────────────────────────────
#  /start  COMMAND
# ─────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    welcome = (
        f"👋 សួស្ដី <b>{user.first_name}</b>!\n\n"
        "🤖 ខ្ញុំជា <b>Khmer Multi-Tool Bot</b>\n"
        "ជំនួយការ Digital របស់អ្នក! 🇰🇭\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🛠 <b>លក្ខណៈពិសេស:</b>\n"
        "  📷 បង្កើត & Scan QR Code\n"
        "  ✍️ ប្ដូររចនាប័ទ្មអក្សរ\n"
        "  🖼️ បំប្លែងរូបភាពទៅ PDF\n"
        "  🔢 ម៉ាស៊ីនគណនា\n"
        "  🔐 ពិនិត្យសុវត្ថិភាព Password\n"
        "  🎲 Random Picker\n"
        "  📡 Morse Code\n"
        "  🔒 Base64 Encode/Decode\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👇 ជ្រើសរើសមុខងារ:"
    )
    await update.message.reply_text(
        welcome,
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END

# ─────────────────────────────────────────────
#  CALLBACK ROUTER
# ─────────────────────────────────────────────
async def callback_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── BACK ──────────────────────────────────
    if data == "back_main":
        await query.edit_message_text(
            "🏠 <b>ម៉ឺនុយមេ</b>\n\n👇 ជ្រើសរើសមុខងារ:",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        ctx.user_data.clear()
        return ConversationHandler.END

    # ── QR CREATE ─────────────────────────────
    if data == "menu_qr_create":
        await query.edit_message_text(
            "📷 <b>បង្កើត QR Code</b>\n\n"
            "✏️ សូមវាយអ្វីដែលអ្នកចង់បំប្លែងទៅ QR Code:\n"
            "<i>(Link, Text, លេខទូរស័ព្ទ, ឬអ្វីក៏បាន)</i>",
            reply_markup=back_and_cancel(),
            parse_mode=ParseMode.HTML,
        )
        return STATE_QR_INPUT

    # ── QR SCAN ───────────────────────────────
    if data == "menu_qr_scan":
        await query.edit_message_text(
            "🔍 <b>Scan QR Code</b>\n\n"
            "📤 សូម Upload រូបភាព QR Code:\n"
            "<i>(ត្រូវការ pyzbar + libzbar)</i>",
            reply_markup=back_and_cancel(),
            parse_mode=ParseMode.HTML,
        )
        return STATE_SCAN_PHOTO

    # ── TEXT STYLE ────────────────────────────
    if data == "menu_text_style":
        await query.edit_message_text(
            "✍️ <b>រចនាប័ទ្មអក្សរ</b>\n\n"
            "✏️ សូមវាយ <b>អក្សរ (English)</b> ដែលអ្នកចង់ Style:\n"
            "<i>⚠️ ដំណើរការល្អបំផុតជាមួយ a-z, A-Z, 0-9</i>",
            reply_markup=back_and_cancel(),
            parse_mode=ParseMode.HTML,
        )
        return STATE_TEXT_STYLE

    # ── PHOTO → PDF ───────────────────────────
    if data == "menu_photo_pdf":
        ctx.user_data["pdf_photos"] = []
        await query.edit_message_text(
            "🖼️ <b>រូបភាព → PDF</b>\n\n"
            "📤 Upload រូបភាព (អាចច្រើន):\n"
            "✅ បន្ទាប់ពី Upload ចប់ → ចុច <b>បញ្ចប់ PDF</b>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ បញ្ចប់ PDF", callback_data="pdf_done"),
                InlineKeyboardButton("❌ បោះបង់",     callback_data="back_main"),
            ]]),
            parse_mode=ParseMode.HTML,
        )
        return STATE_PDF_PHOTOS

    # ── CALCULATOR ────────────────────────────
    if data == "menu_calculator":
        ctx.user_data["calc_expr"] = ""
        await _show_calculator(query, ctx)
        return STATE_CALC_INPUT

    # ── PASSWORD CHECK ────────────────────────
    if data == "menu_password":
        await query.edit_message_text(
            "🔐 <b>ពិនិត្យ Password</b>\n\n"
            "✏️ សូមវាយ Password ដែលអ្នកចង់ពិនិត្យ:\n"
            "<i>Bot នឹងប្រាប់ពីសុវត្ថិភាព</i>",
            reply_markup=back_and_cancel(),
            parse_mode=ParseMode.HTML,
        )
        return STATE_PASS_CHECK

    # ── RANDOM PICKER ─────────────────────────
    if data == "menu_picker":
        await query.edit_message_text(
            "🎲 <b>Random Picker</b>\n\n"
            "✏️ វាយជម្រើស ដាក់ , ចន្លោះ:\n"
            "<code>ក, ខ, គ, ឃ</code>\n"
            "<i>ឬ</i>\n"
            "<code>Alice, Bob, Charlie</code>",
            reply_markup=back_and_cancel(),
            parse_mode=ParseMode.HTML,
        )
        return STATE_PICKER_INPUT

    # ── MORSE ─────────────────────────────────
    if data == "menu_morse":
        await query.edit_message_text(
            "📡 <b>Morse Code</b>\n\n"
            "ជ្រើសរើសទិសដៅ:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔤 Text → Morse", callback_data="morse_to"),
                 InlineKeyboardButton("📡 Morse → Text", callback_data="morse_from")],
                [InlineKeyboardButton("🏠 ម៉ឺនុយមេ",     callback_data="back_main")],
            ]),
            parse_mode=ParseMode.HTML,
        )
        return STATE_MORSE_INPUT

    if data == "morse_to":
        ctx.user_data["morse_dir"] = "to"
        await query.edit_message_text(
            "📡 <b>Text → Morse Code</b>\n\n✏️ វាយ Text:",
            reply_markup=back_and_cancel(),
            parse_mode=ParseMode.HTML,
        )
        return STATE_MORSE_INPUT

    if data == "morse_from":
        ctx.user_data["morse_dir"] = "from"
        await query.edit_message_text(
            "📡 <b>Morse Code → Text</b>\n\n✏️ វាយ Morse Code:\n<code>-- --- .-. ... .</code>",
            reply_markup=back_and_cancel(),
            parse_mode=ParseMode.HTML,
        )
        return STATE_MORSE_INPUT

    # ── BASE64 ────────────────────────────────
    if data == "menu_base64":
        await query.edit_message_text(
            "🔒 <b>Base64</b>\n\nជ្រើសរើស:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Encode",  callback_data="b64_encode"),
                 InlineKeyboardButton("🔓 Decode",  callback_data="b64_decode")],
                [InlineKeyboardButton("🏠 ម៉ឺនុយមេ", callback_data="back_main")],
            ]),
            parse_mode=ParseMode.HTML,
        )
        return STATE_BASE64_INPUT

    if data == "b64_encode":
        ctx.user_data["b64_dir"] = "encode"
        await query.edit_message_text(
            "🔐 <b>Base64 Encode</b>\n\n✏️ វាយ Text ត្រូវ Encode:",
            reply_markup=back_and_cancel(),
            parse_mode=ParseMode.HTML,
        )
        return STATE_BASE64_INPUT

    if data == "b64_decode":
        ctx.user_data["b64_dir"] = "decode"
        await query.edit_message_text(
            "🔓 <b>Base64 Decode</b>\n\n✏️ វាយ Base64 ត្រូវ Decode:",
            reply_markup=back_and_cancel(),
            parse_mode=ParseMode.HTML,
        )
        return STATE_BASE64_INPUT

    # ── ABOUT ─────────────────────────────────
    if data == "menu_about":
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = (
            "ℹ️ <b>អំពី Bot</b>\n\n"
            "🤖 <b>Khmer Multi-Tool Bot v2.0</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 ថ្ងៃនេះ: <code>{now}</code>\n"
            "👨‍💻 Developer: <b>limsovannrady</b>\n"
            "🐍 Python: <b>python-telegram-bot 20.x</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📦 <b>Libraries:</b>\n"
            "  • qrcode — QR Generator\n"
            "  • pyzbar — QR Scanner\n"
            "  • fpdf2  — PDF Creator\n"
            "  • Pillow — Image Tools\n"
            "  • opencv — CV Tools\n"
        )
        await query.edit_message_text(
            msg,
            reply_markup=back_button(),
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    # ── CALC BUTTONS ──────────────────────────
    if data.startswith("calc_"):
        return await _handle_calc_button(query, ctx, data)

    # ── TEXT STYLE COPY ───────────────────────
    if data.startswith("copy_style_"):
        style_key = data.replace("copy_style_", "")
        original  = ctx.user_data.get("style_original", "")
        if original and style_key in TEXT_STYLES:
            _, fn    = TEXT_STYLES[style_key]
            styled   = fn(original)
            await query.answer(f"✅ '{styled[:20]}...' — ចម្លងក្នុង Chat ខាងក្រោម!", show_alert=True)
            await query.message.reply_text(
                f"<code>{styled}</code>",
                parse_mode=ParseMode.HTML,
            )
        return STATE_TEXT_STYLE

    # ── PDF DONE ──────────────────────────────
    if data == "pdf_done":
        return await _build_pdf(query, ctx)

    return ConversationHandler.END


# ─────────────────────────────────────────────
#  📷 QR CREATE
# ─────────────────────────────────────────────
async def handle_qr_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("⚠️ សូមវាយអ្វីមួយ!")
        return STATE_QR_INPUT

    # Generate QR
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0A0A0A", back_color="#FFFFFF").convert("RGB")

    # ── ដាក់ Logo Telegram នៅកណ្ដាល ──────────
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    caption = (
        f"✅ <b>QR Code បានបង្កើតជោគជ័យ!</b>\n\n"
        f"📝 <b>ខ្លឹមសារ:</b>\n<code>{text[:200]}</code>\n\n"
        f"📐 <b>ទំហំ:</b> {img.size[0]}×{img.size[1]} px"
    )

    await update.message.reply_photo(
        photo=buf,
        caption=caption,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 QR ថ្មី",        callback_data="menu_qr_create")],
            [InlineKeyboardButton("🏠 ម៉ឺនុយមេ",       callback_data="back_main")],
        ]),
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────
#  🔍 QR SCAN
# ─────────────────────────────────────────────
async def handle_scan_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    photo = update.message.photo[-1] if update.message.photo else None
    doc   = update.message.document if update.message.document else None

    if not photo and not doc:
        await update.message.reply_text(
            "⚠️ <b>សូម Upload រូបភាព QR Code!</b>",
            parse_mode=ParseMode.HTML,
        )
        return STATE_SCAN_PHOTO

    # Download
    file = await ctx.bot.get_file(photo.file_id if photo else doc.file_id)
    raw  = await file.download_as_bytearray()
    np_arr = np.frombuffer(raw, np.uint8)
    cv_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # ── Scan with pyzbar ────────────────────
    pil_img  = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
    decoded  = pyzbar_decode(pil_img)

    if not decoded:
        await update.message.reply_text(
            "❌ <b>រក QR Code មិនឃើញ!</b>\n\n"
            "💡 <b>ព្យាយាមម្ដងទៀត:</b>\n"
            "  • ប្រើរូបភាពច្បាស់\n"
            "  • QR ត្រូវឃើញ ពេញ\n"
            "  • Lighting ល្អ",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 ថ្មីម្ដងទៀត",  callback_data="menu_qr_scan")],
                [InlineKeyboardButton("🏠 ម៉ឺនុយមេ",      callback_data="back_main")],
            ]),
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    results = []
    for i, d in enumerate(decoded, 1):
        data_str = d.data.decode("utf-8", errors="replace")
        results.append(
            f"<b>#{i}</b> [{d.type}]\n"
            f"<code>{data_str[:300]}</code>"
        )

    msg = (
        f"✅ <b>Scan ជោគជ័យ! រក QR បាន {len(decoded)} ចំនួន</b>\n\n"
        + "\n\n".join(results)
    )
    await update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Scan ថ្មី",      callback_data="menu_qr_scan")],
            [InlineKeyboardButton("📷 បង្កើត QR",      callback_data="menu_qr_create")],
            [InlineKeyboardButton("🏠 ម៉ឺនុយមេ",       callback_data="back_main")],
        ]),
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────
#  ✍️ TEXT STYLE
# ─────────────────────────────────────────────
async def handle_text_style(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("⚠️ សូមវាយអ្វីមួយ!")
        return STATE_TEXT_STYLE

    ctx.user_data["style_original"] = text

    # Build preview rows
    rows = []
    for key, (label, fn) in TEXT_STYLES.items():
        styled = fn(text)
        rows.append(f"<b>{label}:</b>\n{styled}")

    # Inline copy buttons
    btn_rows = []
    keys = list(TEXT_STYLES.keys())
    for i in range(0, len(keys), 2):
        row = []
        for k in keys[i:i+2]:
            lbl, _ = TEXT_STYLES[k]
            row.append(InlineKeyboardButton(
                f"📋 {lbl}", callback_data=f"copy_style_{k}"
            ))
        btn_rows.append(row)
    btn_rows.append([InlineKeyboardButton("✍️ Style ថ្មី",  callback_data="menu_text_style")])
    btn_rows.append([InlineKeyboardButton("🏠 ម៉ឺនុយមេ",   callback_data="back_main")])

    header = (
        f"✍️ <b>Style ទាំងអស់របស់:</b> <code>{text}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    full_msg = header + "\n\n".join(rows) + "\n\n━━━━━━━━━━━━━━━━━━━━\n👇 ចុចប៊ូតុង ចម្លង Style:"

    await update.message.reply_text(
        full_msg,
        reply_markup=InlineKeyboardMarkup(btn_rows),
        parse_mode=ParseMode.HTML,
    )
    return STATE_TEXT_STYLE


# ─────────────────────────────────────────────
#  🖼️ PHOTO → PDF
# ─────────────────────────────────────────────
async def handle_pdf_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    photo = update.message.photo[-1] if update.message.photo else None
    doc   = update.message.document  if update.message.document else None

    if not photo and not doc:
        await update.message.reply_text("⚠️ សូម Upload រូបភាព!")
        return STATE_PDF_PHOTOS

    file_obj = await ctx.bot.get_file(photo.file_id if photo else doc.file_id)
    raw = await file_obj.download_as_bytearray()
    ctx.user_data.setdefault("pdf_photos", []).append(bytes(raw))

    count = len(ctx.user_data["pdf_photos"])
    await update.message.reply_text(
        f"✅ <b>រូបភាពទី {count} បានទទួល!</b>\n"
        f"📤 Upload រូបភាពបន្ថែម ឬ ចុច <b>បញ្ចប់ PDF</b>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ បញ្ចប់ PDF", callback_data="pdf_done"),
            InlineKeyboardButton("❌ បោះបង់",     callback_data="back_main"),
        ]]),
        parse_mode=ParseMode.HTML,
    )
    return STATE_PDF_PHOTOS

async def _build_pdf(query, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    photos = ctx.user_data.get("pdf_photos", [])
    if not photos:
        await query.answer("⚠️ មិនទាន់មានរូបភាពទេ!", show_alert=True)
        return STATE_PDF_PHOTOS

    await query.edit_message_text(
        f"⏳ <b>កំពុងបំប្លែង {len(photos)} រូប → PDF...</b>",
        parse_mode=ParseMode.HTML,
    )

    pdf = FPDF()
    for raw in photos:
        img    = Image.open(io.BytesIO(raw)).convert("RGB")
        w, h   = img.size
        # A4 landscape or portrait based on ratio
        if w > h:
            pdf.add_page("L", (297, 210))
            pw, ph = 297, 210
        else:
            pdf.add_page("P", (210, 297))
            pw, ph = 210, 297

        # Scale image to fit page
        ratio   = min(pw / w, ph / h)
        nw, nh  = w * ratio, h * ratio
        x = (pw - nw) / 2
        y = (ph - nh) / 2

        tmp = io.BytesIO()
        img.save(tmp, format="JPEG", quality=90)
        tmp.seek(0)
        pdf.image(tmp, x=x, y=y, w=nw, h=nh)

    pdf_bytes = pdf.output()
    pdf_buf   = io.BytesIO(bytes(pdf_bytes))
    pdf_buf.name = "output.pdf"

    await query.message.reply_document(
        document=InputFile(pdf_buf, filename="KhmerBot_Photos.pdf"),
        caption=(
            f"✅ <b>PDF បានបង្កើតជោគជ័យ!</b>\n"
            f"🖼️ <b>រូបភាព:</b> {len(photos)} សន្លឹក\n"
            f"📄 <b>ឈ្មោះ:</b> KhmerBot_Photos.pdf"
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🖼️ PDF ថ្មី",      callback_data="menu_photo_pdf")],
            [InlineKeyboardButton("🏠 ម៉ឺនុយមេ",      callback_data="back_main")],
        ]),
        parse_mode=ParseMode.HTML,
    )
    ctx.user_data["pdf_photos"] = []
    return ConversationHandler.END


# ─────────────────────────────────────────────
#  🔢 CALCULATOR  (Inline Keyboard)
# ─────────────────────────────────────────────
CALC_BUTTONS = [
    ["C", "±", "%", "÷"],
    ["7", "8", "9", "×"],
    ["4", "5", "6", "−"],
    ["1", "2", "3", "+"],
    ["0", ".", "⌫", "="],
]

async def _show_calculator(query_or_msg, ctx: ContextTypes.DEFAULT_TYPE, answer: str = None) -> None:
    expr = ctx.user_data.get("calc_expr", "")
    display_line = expr if expr else "0"
    if answer:
        display_line = answer

    header = (
        f"🔢 <b>ម៉ាស៊ីនគណនា</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<code>  {display_line[-30:]}</code>\n"
        f"━━━━━━━━━━━━━━━━"
    )

    btn_rows = []
    for row in CALC_BUTTONS:
        btn_rows.append([
            InlineKeyboardButton(b, callback_data=f"calc_{b}")
            for b in row
        ])
    btn_rows.append([InlineKeyboardButton("🏠 ម៉ឺនុយមេ", callback_data="back_main")])

    kb = InlineKeyboardMarkup(btn_rows)
    if hasattr(query_or_msg, "edit_message_text"):
        await query_or_msg.edit_message_text(header, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await query_or_msg.reply_text(header, reply_markup=kb, parse_mode=ParseMode.HTML)

async def _handle_calc_button(query, ctx, data: str) -> int:
    btn = data.replace("calc_", "")
    expr = ctx.user_data.get("calc_expr", "")

    if btn == "C":
        ctx.user_data["calc_expr"] = ""
        await _show_calculator(query, ctx)
        return STATE_CALC_INPUT

    if btn == "⌫":
        ctx.user_data["calc_expr"] = expr[:-1]
        await _show_calculator(query, ctx)
        return STATE_CALC_INPUT

    if btn == "±":
        if expr and expr[0] == "-":
            ctx.user_data["calc_expr"] = expr[1:]
        elif expr:
            ctx.user_data["calc_expr"] = "-" + expr
        await _show_calculator(query, ctx)
        return STATE_CALC_INPUT

    if btn == "=":
        try:
            calc_str = expr.replace("÷", "/").replace("×", "*").replace("−", "-")
            calc_str = re.sub(r'(\d)%', r'(\1/100)', calc_str)
            result   = eval(calc_str, {"__builtins__": {}})
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            ctx.user_data["calc_expr"] = str(result)
            await _show_calculator(query, ctx, answer=f"{expr} = {result}")
        except Exception:
            ctx.user_data["calc_expr"] = ""
            await _show_calculator(query, ctx, answer="❌ Error!")
        return STATE_CALC_INPUT

    ctx.user_data["calc_expr"] = expr + btn
    await _show_calculator(query, ctx)
    return STATE_CALC_INPUT


# ─────────────────────────────────────────────
#  🔐 PASSWORD STRENGTH CHECK
# ─────────────────────────────────────────────
def check_password(pw: str) -> dict:
    score  = 0
    issues = []

    checks = {
        "len_8":   (len(pw) >= 8,   "✅ ≥8 តួអក្សរ",   "❌ < 8 តួអក្សរ"),
        "len_12":  (len(pw) >= 12,  "✅ ≥12 តួអក្សរ",  None),
        "upper":   (bool(re.search(r"[A-Z]", pw)),  "✅ Uppercase",   "❌ មិនមាន Uppercase"),
        "lower":   (bool(re.search(r"[a-z]", pw)),  "✅ Lowercase",   "❌ មិនមាន Lowercase"),
        "digit":   (bool(re.search(r"\d",    pw)),  "✅ លេខ",         "❌ មិនមានលេខ"),
        "special": (bool(re.search(r"[^A-Za-z0-9]", pw)), "✅ Symbol", "❌ មិនមាន Symbol"),
    }
    passed = sum(1 for k, (ok, _, _) in checks.items() if ok)
    for k, (ok, good, bad) in checks.items():
        if bad:
            issues.append(good if ok else bad)

    if passed <= 2:   level, emoji = "ខ្សោយ (Weak)",      "🔴"
    elif passed <= 4: level, emoji = "មធ្យម (Medium)",     "🟡"
    elif passed == 5: level, emoji = "ល្អ (Strong)",        "🟢"
    else:             level, emoji = "ខ្លាំងណាស់ (Very Strong)", "🟢✨"

    entropy = math.log2(len(set(pw))) * len(pw) if len(set(pw)) > 1 else 0

    return {
        "level":   level,
        "emoji":   emoji,
        "issues":  issues,
        "entropy": round(entropy, 1),
        "score":   passed,
    }

async def handle_password(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    pw = update.message.text
    res = check_password(pw)

    hidden = "•" * len(pw)
    msg = (
        f"🔐 <b>លទ្ធផលពិនិត្យ Password</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔑 Password: <tg-spoiler>{hidden}</tg-spoiler>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{res['emoji']} <b>កម្រិត:</b> {res['level']}\n"
        f"📊 <b>ពិន្ទុ:</b> {res['score']}/6\n"
        f"🎲 <b>Entropy:</b> {res['entropy']} bits\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        + "\n".join(res["issues"])
    )
    await update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 ពិនិត្យ Password ថ្មី", callback_data="menu_password")],
            [InlineKeyboardButton("🏠 ម៉ឺនុយមេ",              callback_data="back_main")],
        ]),
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────
#  🎲 RANDOM PICKER
# ─────────────────────────────────────────────
async def handle_picker(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    raw   = update.message.text.strip()
    items = [x.strip() for x in raw.split(",") if x.strip()]

    if len(items) < 2:
        await update.message.reply_text(
            "⚠️ <b>ត្រូវការ ≥2 ជម្រើស!</b>\nដាក់ , ចន្លោះ: <code>ក, ខ, គ</code>",
            parse_mode=ParseMode.HTML,
        )
        return STATE_PICKER_INPUT

    chosen = random.choice(items)
    ranked = random.sample(items, len(items))

    msg = (
        f"🎲 <b>Random Picker</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 <b>ជ្រើស:</b> <code>{chosen}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>លំដាប់ Random:</b>\n"
        + "\n".join(f"  {i}. {x}" for i, x in enumerate(ranked, 1))
    )
    await update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Random ម្ដងទៀត", callback_data="menu_picker")],
            [InlineKeyboardButton("🏠 ម៉ឺនុយមេ",       callback_data="back_main")],
        ]),
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────
#  📡 MORSE CODE
# ─────────────────────────────────────────────
async def handle_morse(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text      = update.message.text.strip()
    direction = ctx.user_data.get("morse_dir", "to")

    if direction == "to":
        result = text_to_morse(text)
        header = "Text → Morse"
        label  = "Morse"
    else:
        result = morse_to_text(text)
        header = "Morse → Text"
        label  = "Text"

    msg = (
        f"📡 <b>{header}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📥 <b>Input:</b> <code>{text[:200]}</code>\n"
        f"📤 <b>{label}:</b> <code>{result[:500]}</code>"
    )
    await update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Morse ថ្មី",    callback_data="menu_morse")],
            [InlineKeyboardButton("🏠 ម៉ឺនុយមេ",     callback_data="back_main")],
        ]),
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────
#  🔒 BASE64
# ─────────────────────────────────────────────
async def handle_base64(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text      = update.message.text.strip()
    direction = ctx.user_data.get("b64_dir", "encode")

    try:
        if direction == "encode":
            result = base64.b64encode(text.encode("utf-8")).decode("utf-8")
            header = "Encode"
        else:
            result = base64.b64decode(text.encode("utf-8")).decode("utf-8")
            header = "Decode"
        error = False
    except Exception as e:
        result = str(e)
        error  = True
        header = "Error"

    emoji = "🔐" if direction == "encode" else "🔓"
    msg = (
        f"{emoji} <b>Base64 {header}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📥 <b>Input:</b>\n<code>{text[:200]}</code>\n\n"
        f"{'❌' if error else '📤'} <b>Result:</b>\n<code>{result[:1000]}</code>"
    )
    await update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Base64 ថ្មី",  callback_data="menu_base64")],
            [InlineKeyboardButton("🏠 ម៉ឺនុយមេ",     callback_data="back_main")],
        ]),
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────
#  ❓ FALLBACK  (Unknown message)
# ─────────────────────────────────────────────
async def fallback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🤔 <b>ខ្ញុំមិនយល់ Command!</b>\n\n"
        "👇 ចុចប៊ូតុងខាងក្រោម ឬ វាយ /start:",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML,
    )


# ─────────────────────────────────────────────
#  🚀 MAIN — BUILD & RUN BOT
# ─────────────────────────────────────────────
def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    # ─── Conversation Handler ──────────────
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            CallbackQueryHandler(callback_router),
        ],
        states={
            STATE_QR_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_qr_input),
                CallbackQueryHandler(callback_router),
            ],
            STATE_SCAN_PHOTO: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_scan_photo),
                CallbackQueryHandler(callback_router),
            ],
            STATE_TEXT_STYLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_style),
                CallbackQueryHandler(callback_router),
            ],
            STATE_PDF_PHOTOS: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_pdf_photo),
                CallbackQueryHandler(callback_router),
            ],
            STATE_CALC_INPUT: [
                CallbackQueryHandler(callback_router),
            ],
            STATE_PASS_CHECK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password),
                CallbackQueryHandler(callback_router),
            ],
            STATE_PICKER_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_picker),
                CallbackQueryHandler(callback_router),
            ],
            STATE_MORSE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_morse),
                CallbackQueryHandler(callback_router),
            ],
            STATE_BASE64_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_base64),
                CallbackQueryHandler(callback_router),
            ],
        },
        fallbacks=[
            CommandHandler("start", cmd_start),
            MessageHandler(filters.ALL, fallback_handler),
        ],
        per_message=False,
        allow_reentry=True,
    )

    app.add_handler(conv_handler)

    logger.info("🤖 Bot កំពុង Start...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        poll_interval=1.0,
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()
