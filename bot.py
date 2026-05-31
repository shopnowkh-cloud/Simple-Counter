#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, io, re, math, base64, random, logging, warnings, qrcode, cv2, numpy as np
from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode
from fpdf import FPDF
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters
from telegram.constants import ParseMode
from telegram.warnings import PTBUserWarning

warnings.filterwarnings("ignore", category=PTBUserWarning)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set!")

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

S_QR, S_SCAN, S_STYLE, S_PDF, S_CALC, S_PASS, S_PICK, S_MORSE, S_B64 = range(9)

def _t(text, m): return "".join(m.get(c, c) for c in text)
BM  = {**{chr(i): chr(i+0x1D400-0x41) for i in range(0x41,0x5B)}, **{chr(i): chr(i+0x1D41A-0x61) for i in range(0x61,0x7B)}, **{chr(i): chr(i+0x1D7CE-0x30) for i in range(0x30,0x3A)}}
IM  = {**{chr(i): chr(i+0x1D434-0x41) for i in range(0x41,0x5B)}, **{chr(i): chr(i+0x1D44E-0x61) for i in range(0x61,0x7B)}}
BIM = {**{chr(i): chr(i+0x1D468-0x41) for i in range(0x41,0x5B)}, **{chr(i): chr(i+0x1D482-0x61) for i in range(0x61,0x7B)}}
SM  = {**{chr(i): chr(i+0x1D49C-0x41) for i in range(0x41,0x5B)}, **{chr(i): chr(i+0x1D4B6-0x61) for i in range(0x61,0x7B)}}
DM  = {**{chr(i): chr(i+0x1D538-0x41) for i in range(0x41,0x5B)}, **{chr(i): chr(i+0x1D552-0x61) for i in range(0x61,0x7B)}, **{chr(i): chr(i+0x1D7D8-0x30) for i in range(0x30,0x3A)}}
SC  = {"a":"ᴀ","b":"ʙ","c":"ᴄ","d":"ᴅ","e":"ᴇ","f":"ꜰ","g":"ɢ","h":"ʜ","i":"ɪ","j":"ᴊ","k":"ᴋ","l":"ʟ","m":"ᴍ","n":"ɴ","o":"ᴏ","p":"ᴘ","q":"Q","r":"ʀ","s":"ꜱ","t":"ᴛ","u":"ᴜ","v":"ᴠ","w":"ᴡ","x":"x","y":"ʏ","z":"ᴢ"}
BB  = {**{chr(i): chr(i+0x24B6-0x41) for i in range(0x41,0x5B)}, **{chr(i): chr(i+0x24D0-0x61) for i in range(0x61,0x7B)}, **{"0":"⓪","1":"①","2":"②","3":"③","4":"④","5":"⑤","6":"⑥","7":"⑦","8":"⑧","9":"⑨"}}
UD  = {"a":"ɐ","b":"q","c":"ɔ","d":"p","e":"ǝ","f":"ɟ","g":"ƃ","h":"ɥ","i":"ᴉ","j":"ɾ","k":"ʞ","l":"l","m":"ɯ","n":"u","o":"o","p":"d","q":"b","r":"ɹ","s":"s","t":"ʇ","u":"n","v":"ʌ","w":"ʍ","x":"x","y":"ʎ","z":"z","A":"∀","B":"ᗺ","C":"Ɔ","D":"ᗡ","E":"Ǝ","F":"Ⅎ","G":"פ","H":"H","I":"I","J":"ſ","K":"ʞ","L":"˥","M":"W","N":"N","O":"O","P":"Ԁ","Q":"Q","R":"ɹ","S":"S","T":"┴","U":"∩","V":"Λ","W":"M","X":"X","Y":"⅄","Z":"Z","0":"0","1":"Ɩ","2":"ᄅ","3":"Ɛ","4":"ᔭ","5":"ϛ","6":"9","7":"ㄥ","8":"8","9":"6"," ":" "}
TEXT_STYLES = {
    "bold":         ("𝗕𝗼𝗹𝗱",         lambda t: _t(t, BM)),
    "italic":       ("𝘐𝘵𝘢𝘭𝘪𝘤",       lambda t: _t(t, IM)),
    "bold_italic":  ("𝑩𝒐𝒍𝒅 𝑰𝒕𝒂𝒍𝒊𝒄", lambda t: _t(t, BIM)),
    "script":       ("𝒮𝒸𝓇𝒾𝓅𝓉",       lambda t: _t(t, SM)),
    "double":       ("𝔻𝕠𝕦𝕓𝕝𝕖",       lambda t: _t(t, DM)),
    "small_caps":   ("Sᴍᴀʟʟ Cᴀᴘꜱ",   lambda t: _t(t.lower(), SC)),
    "bubble":       ("Ⓑⓤⓑⓑⓛⓔ",       lambda t: _t(t, BB)),
    "upside_down":  ("uʍop ǝpᴉsdn",  lambda t: _t(t, UD)[::-1]),
    "strikethrough":("S̶t̶r̶i̶k̶e̶",     lambda t: "".join(c+"̶" for c in t)),
    "underline":    ("U̲n̲d̲e̲r̲",        lambda t: "".join(c+"̲" for c in t)),
}

MORSE = {"A":".-","B":"-...","C":"-.-.","D":"-..","E":".","F":"..-.","G":"--.","H":"....","I":"..","J":".---","K":"-.-","L":".-..","M":"--","N":"-.","O":"---","P":".--.","Q":"--.-","R":".-.","S":"...","T":"-","U":"..-","V":"...-","W":".--","X":"-..-","Y":"-.--","Z":"--..","0":"-----","1":".----","2":"..---","3":"...--","4":"....-","5":".....","6":"-....","7":"--...","8":"---..","9":"----."," ":"/"}
MR = {v: k for k, v in MORSE.items()}
def text_to_morse(t): return " ".join(MORSE.get(c.upper(), "?") for c in t)
def morse_to_text(m): return "".join(MR.get(w, "?") for w in m.strip().split(" "))

IKB = InlineKeyboardButton
def mkb(*rows): return InlineKeyboardMarkup(list(rows))
def main_menu_keyboard():
    return mkb(
        [IKB("📷 បង្កើត QR Code", callback_data="menu_qr_create"), IKB("🔍 Scan QR Code", callback_data="menu_qr_scan")],
        [IKB("✍️ រចនាប័ទ្មអក្សរ", callback_data="menu_text_style"), IKB("🖼️ រូបភាព → PDF", callback_data="menu_photo_pdf")],
        [IKB("🔢 ម៉ាស៊ីនគណនា", callback_data="menu_calculator"), IKB("🔐 ពិនិត្យ Password", callback_data="menu_password")],
        [IKB("🎲 Random Picker", callback_data="menu_picker"), IKB("📡 Morse Code", callback_data="menu_morse")],
        [IKB("🔒 Base64", callback_data="menu_base64"), IKB("ℹ️ អំពី Bot", callback_data="menu_about")],
    )
def back_btn(b="main"): return mkb([IKB("🏠 ត្រឡប់មុខដំណើរការ", callback_data=f"back_{b}")])
def back_cancel(b="main"): return mkb([IKB("❌ បោះបង់", callback_data=f"back_{b}"), IKB("🏠 ម៉ឺនុយមេ", callback_data="back_main")])

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await update.message.reply_text(
        f"👋 សួស្ដី <b>{u.first_name}</b>!\n\n🤖 ខ្ញុំជា <b>Khmer Multi-Tool Bot</b>\nជំនួយការ Digital របស់អ្នក! 🇰🇭\n\n━━━━━━━━━━━━━━━━━━━━\n🛠 <b>លក្ខណៈពិសេស:</b>\n  📷 បង្កើត & Scan QR Code\n  ✍️ ប្ដូររចនាប័ទ្មអក្សរ\n  🖼️ បំប្លែងរូបភាពទៅ PDF\n  🔢 ម៉ាស៊ីនគណនា\n  🔐 ពិនិត្យសុវត្ថិភាព Password\n  🎲 Random Picker\n  📡 Morse Code\n  🔒 Base64 Encode/Decode\n━━━━━━━━━━━━━━━━━━━━\n👇 ជ្រើសរើសមុខងារ:",
        reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END

async def callback_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    H = ParseMode.HTML

    if d == "back_main":
        await q.edit_message_text("🏠 <b>ម៉ឺនុយមេ</b>\n\n👇 ជ្រើសរើសមុខងារ:", reply_markup=main_menu_keyboard(), parse_mode=H)
        ctx.user_data.clear(); return ConversationHandler.END

    if d == "menu_qr_create":
        await q.edit_message_text("📷 <b>បង្កើត QR Code</b>\n\n✏️ សូមវាយអ្វីដែលអ្នកចង់បំប្លែងទៅ QR Code:\n<i>(Link, Text, លេខទូរស័ព្ទ, ឬអ្វីក៏បាន)</i>", reply_markup=back_cancel(), parse_mode=H)
        return S_QR
    if d == "menu_qr_scan":
        await q.edit_message_text("🔍 <b>Scan QR Code</b>\n\n📤 សូម Upload រូបភាព QR Code:", reply_markup=back_cancel(), parse_mode=H)
        return S_SCAN
    if d == "menu_text_style":
        await q.edit_message_text("✍️ <b>រចនាប័ទ្មអក្សរ</b>\n\n✏️ សូមវាយ <b>អក្សរ (English)</b> ដែលអ្នកចង់ Style:\n<i>⚠️ ដំណើរការល្អបំផុតជាមួយ a-z, A-Z, 0-9</i>", reply_markup=back_cancel(), parse_mode=H)
        return S_STYLE
    if d == "menu_photo_pdf":
        ctx.user_data["pdf_photos"] = []
        await q.edit_message_text("🖼️ <b>រូបភាព → PDF</b>\n\n📤 Upload រូបភាព (អាចច្រើន):\n✅ បន្ទាប់ពី Upload ចប់ → ចុច <b>បញ្ចប់ PDF</b>", reply_markup=mkb([IKB("✅ បញ្ចប់ PDF", callback_data="pdf_done"), IKB("❌ បោះបង់", callback_data="back_main")]), parse_mode=H)
        return S_PDF
    if d == "menu_calculator":
        ctx.user_data["calc_expr"] = ""; await _show_calc(q, ctx); return S_CALC
    if d == "menu_password":
        await q.edit_message_text("🔐 <b>ពិនិត្យ Password</b>\n\n✏️ សូមវាយ Password ដែលអ្នកចង់ពិនិត្យ:\n<i>Bot នឹងប្រាប់ពីសុវត្ថិភាព</i>", reply_markup=back_cancel(), parse_mode=H)
        return S_PASS
    if d == "menu_picker":
        await q.edit_message_text("🎲 <b>Random Picker</b>\n\n✏️ វាយជម្រើស ដាក់ , ចន្លោះ:\n<code>ក, ខ, គ, ឃ</code>\n<i>ឬ</i>\n<code>Alice, Bob, Charlie</code>", reply_markup=back_cancel(), parse_mode=H)
        return S_PICK
    if d == "menu_morse":
        await q.edit_message_text("📡 <b>Morse Code</b>\n\nជ្រើសរើសទិសដៅ:", reply_markup=mkb([IKB("🔤 Text → Morse", callback_data="morse_to"), IKB("📡 Morse → Text", callback_data="morse_from")], [IKB("🏠 ម៉ឺនុយមេ", callback_data="back_main")]), parse_mode=H)
        return S_MORSE
    if d == "morse_to":
        ctx.user_data["morse_dir"] = "to"
        await q.edit_message_text("📡 <b>Text → Morse Code</b>\n\n✏️ វាយ Text:", reply_markup=back_cancel(), parse_mode=H); return S_MORSE
    if d == "morse_from":
        ctx.user_data["morse_dir"] = "from"
        await q.edit_message_text("📡 <b>Morse Code → Text</b>\n\n✏️ វាយ Morse Code:\n<code>-- --- .-. ... .</code>", reply_markup=back_cancel(), parse_mode=H); return S_MORSE
    if d == "menu_base64":
        await q.edit_message_text("🔒 <b>Base64</b>\n\nជ្រើសរើស:", reply_markup=mkb([IKB("🔐 Encode", callback_data="b64_encode"), IKB("🔓 Decode", callback_data="b64_decode")], [IKB("🏠 ម៉ឺនុយមេ", callback_data="back_main")]), parse_mode=H)
        return S_B64
    if d == "b64_encode":
        ctx.user_data["b64_dir"] = "encode"
        await q.edit_message_text("🔐 <b>Base64 Encode</b>\n\n✏️ វាយ Text ត្រូវ Encode:", reply_markup=back_cancel(), parse_mode=H); return S_B64
    if d == "b64_decode":
        ctx.user_data["b64_dir"] = "decode"
        await q.edit_message_text("🔓 <b>Base64 Decode</b>\n\n✏️ វាយ Base64 ត្រូវ Decode:", reply_markup=back_cancel(), parse_mode=H); return S_B64
    if d == "menu_about":
        await q.edit_message_text(
            f"ℹ️ <b>អំពី Bot</b>\n\n🤖 <b>Khmer Multi-Tool Bot v2.0</b>\n━━━━━━━━━━━━━━━━━━━━\n📅 ថ្ងៃនេះ: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n👨‍💻 Developer: <b>limsovannrady</b>\n🐍 Python: <b>python-telegram-bot 21.x</b>\n━━━━━━━━━━━━━━━━━━━━\n📦 <b>Libraries:</b>\n  • qrcode — QR Generator\n  • pyzbar — QR Scanner\n  • fpdf2  — PDF Creator\n  • Pillow — Image Tools\n  • opencv — CV Tools",
            reply_markup=back_btn(), parse_mode=H)
        return ConversationHandler.END
    if d.startswith("calc_"): return await _handle_calc(q, ctx, d)
    if d.startswith("copy_style_"):
        sk = d.replace("copy_style_", ""); orig = ctx.user_data.get("style_original", "")
        if orig and sk in TEXT_STYLES:
            styled = TEXT_STYLES[sk][1](orig)
            await q.answer(f"✅ '{styled[:20]}...' — ចម្លងក្នុង Chat ខាងក្រោម!", show_alert=True)
            await q.message.reply_text(f"<code>{styled}</code>", parse_mode=H)
        return S_STYLE
    if d == "pdf_done": return await _build_pdf(q, ctx)
    return ConversationHandler.END

async def handle_qr_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text: await update.message.reply_text("⚠️ សូមវាយអ្វីមួយ!"); return S_QR
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=12, border=4)
    qr.add_data(text); qr.make(fit=True)
    img = qr.make_image(fill_color="#0A0A0A", back_color="#FFFFFF").convert("RGB")
    buf = io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    await update.message.reply_photo(photo=buf, caption=f"✅ <b>QR Code បានបង្កើតជោគជ័យ!</b>\n\n📝 <b>ខ្លឹមសារ:</b>\n<code>{text[:200]}</code>\n\n📐 <b>ទំហំ:</b> {img.size[0]}×{img.size[1]} px", reply_markup=mkb([IKB("🔄 QR ថ្មី", callback_data="menu_qr_create")], [IKB("🏠 ម៉ឺនុយមេ", callback_data="back_main")]), parse_mode=ParseMode.HTML)
    return ConversationHandler.END

async def handle_scan_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1] if update.message.photo else None
    doc   = update.message.document if update.message.document else None
    if not photo and not doc:
        await update.message.reply_text("⚠️ <b>សូម Upload រូបភាព QR Code!</b>", parse_mode=ParseMode.HTML); return S_SCAN
    f = await ctx.bot.get_file(photo.file_id if photo else doc.file_id)
    raw = await f.download_as_bytearray()
    cv_img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    decoded = pyzbar_decode(Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)))
    if not decoded:
        await update.message.reply_text("❌ <b>រក QR Code មិនឃើញ!</b>\n\n💡 ប្រើរូបភាពច្បាស់ • QR ត្រូវឃើញពេញ • Lighting ល្អ", reply_markup=mkb([IKB("🔄 ថ្មីម្ដងទៀត", callback_data="menu_qr_scan")], [IKB("🏠 ម៉ឺនុយមេ", callback_data="back_main")]), parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    results = [f"<b>#{i}</b> [{d.type}]\n<code>{d.data.decode('utf-8','replace')[:300]}</code>" for i, d in enumerate(decoded, 1)]
    await update.message.reply_text(f"✅ <b>Scan ជោគជ័យ! រក QR បាន {len(decoded)} ចំនួន</b>\n\n" + "\n\n".join(results), reply_markup=mkb([IKB("🔄 Scan ថ្មី", callback_data="menu_qr_scan"), IKB("📷 បង្កើត QR", callback_data="menu_qr_create")], [IKB("🏠 ម៉ឺនុយមេ", callback_data="back_main")]), parse_mode=ParseMode.HTML)
    return ConversationHandler.END

async def handle_text_style(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text: await update.message.reply_text("⚠️ សូមវាយអ្វីមួយ!"); return S_STYLE
    ctx.user_data["style_original"] = text
    rows = [f"<b>{lbl}:</b>\n{fn(text)}" for _, (lbl, fn) in TEXT_STYLES.items()]
    keys = list(TEXT_STYLES.keys())
    btn_rows = [[IKB(f"📋 {TEXT_STYLES[keys[i]][0]}", callback_data=f"copy_style_{keys[i]}") for i in range(j, min(j+2, len(keys)))] for j in range(0, len(keys), 2)]
    btn_rows += [[IKB("✍️ Style ថ្មី", callback_data="menu_text_style")], [IKB("🏠 ម៉ឺនុយមេ", callback_data="back_main")]]
    await update.message.reply_text(f"✍️ <b>Style ទាំងអស់របស់:</b> <code>{text}</code>\n━━━━━━━━━━━━━━━━━━━━\n\n" + "\n\n".join(rows) + "\n\n━━━━━━━━━━━━━━━━━━━━\n👇 ចុចប៊ូតុង ចម្លង Style:", reply_markup=InlineKeyboardMarkup(btn_rows), parse_mode=ParseMode.HTML)
    return S_STYLE

async def handle_pdf_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1] if update.message.photo else None
    doc   = update.message.document if update.message.document else None
    if not photo and not doc: await update.message.reply_text("⚠️ សូម Upload រូបភាព!"); return S_PDF
    f = await ctx.bot.get_file(photo.file_id if photo else doc.file_id)
    ctx.user_data.setdefault("pdf_photos", []).append(bytes(await f.download_as_bytearray()))
    count = len(ctx.user_data["pdf_photos"])
    await update.message.reply_text(f"✅ <b>រូបភាពទី {count} បានទទួល!</b>\n📤 Upload រូបភាពបន្ថែម ឬ ចុច <b>បញ្ចប់ PDF</b>", reply_markup=mkb([IKB("✅ បញ្ចប់ PDF", callback_data="pdf_done"), IKB("❌ បោះបង់", callback_data="back_main")]), parse_mode=ParseMode.HTML)
    return S_PDF

async def _build_pdf(q, ctx: ContextTypes.DEFAULT_TYPE):
    photos = ctx.user_data.get("pdf_photos", [])
    if not photos: await q.answer("⚠️ មិនទាន់មានរូបភាពទេ!", show_alert=True); return S_PDF
    await q.edit_message_text(f"⏳ <b>កំពុងបំប្លែង {len(photos)} រូប → PDF...</b>", parse_mode=ParseMode.HTML)
    pdf = FPDF()
    for raw in photos:
        img = Image.open(io.BytesIO(raw)).convert("RGB"); w, h = img.size
        if w > h: pdf.add_page("L", (297, 210)); pw, ph = 297, 210
        else:      pdf.add_page("P", (210, 297)); pw, ph = 210, 297
        ratio = min(pw/w, ph/h); nw, nh = w*ratio, h*ratio
        tmp = io.BytesIO(); img.save(tmp, format="JPEG", quality=90); tmp.seek(0)
        pdf.image(tmp, x=(pw-nw)/2, y=(ph-nh)/2, w=nw, h=nh)
    buf = io.BytesIO(bytes(pdf.output()))
    await q.message.reply_document(document=InputFile(buf, filename="KhmerBot_Photos.pdf"), caption=f"✅ <b>PDF បានបង្កើតជោគជ័យ!</b>\n🖼️ <b>រូបភាព:</b> {len(photos)} សន្លឹក", reply_markup=mkb([IKB("🖼️ PDF ថ្មី", callback_data="menu_photo_pdf")], [IKB("🏠 ម៉ឺនុយមេ", callback_data="back_main")]), parse_mode=ParseMode.HTML)
    ctx.user_data["pdf_photos"] = []; return ConversationHandler.END

CALC_BTNS = [["C","±","%","÷"],["7","8","9","×"],["4","5","6","−"],["1","2","3","+"],[" 0",".",  "⌫","="]]
async def _show_calc(qm, ctx, answer=None):
    expr = ctx.user_data.get("calc_expr", ""); disp = answer or (expr[-30:] if expr else "0")
    kb = InlineKeyboardMarkup([[IKB(b, callback_data=f"calc_{b.strip()}") for b in row] for row in CALC_BTNS] + [[IKB("🏠 ម៉ឺនុយមេ", callback_data="back_main")]])
    txt = f"🔢 <b>ម៉ាស៊ីនគណនា</b>\n━━━━━━━━━━━━━━━━\n<code>  {disp}</code>\n━━━━━━━━━━━━━━━━"
    if hasattr(qm, "edit_message_text"): await qm.edit_message_text(txt, reply_markup=kb, parse_mode=ParseMode.HTML)
    else: await qm.reply_text(txt, reply_markup=kb, parse_mode=ParseMode.HTML)

async def _handle_calc(q, ctx, data):
    btn = data.replace("calc_", ""); expr = ctx.user_data.get("calc_expr", "")
    if btn == "C": ctx.user_data["calc_expr"] = ""; await _show_calc(q, ctx); return S_CALC
    if btn == "⌫": ctx.user_data["calc_expr"] = expr[:-1]; await _show_calc(q, ctx); return S_CALC
    if btn == "±":
        ctx.user_data["calc_expr"] = expr[1:] if expr and expr[0]=="-" else ("-"+expr if expr else expr)
        await _show_calc(q, ctx); return S_CALC
    if btn == "=":
        try:
            r = eval(re.sub(r'(\d)%', r'(\1/100)', expr.replace("÷","/").replace("×","*").replace("−","-")), {"__builtins__": {}})
            r = int(r) if isinstance(r, float) and r.is_integer() else r
            ctx.user_data["calc_expr"] = str(r); await _show_calc(q, ctx, answer=f"{expr} = {r}")
        except: ctx.user_data["calc_expr"] = ""; await _show_calc(q, ctx, answer="❌ Error!")
        return S_CALC
    ctx.user_data["calc_expr"] = expr + btn; await _show_calc(q, ctx); return S_CALC

async def handle_password(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    pw = update.message.text
    checks = {"len_8":(len(pw)>=8,"✅ ≥8 តួអក្សរ","❌ < 8 តួអក្សរ"),"len_12":(len(pw)>=12,"✅ ≥12 តួអក្សរ",None),"upper":(bool(re.search(r"[A-Z]",pw)),"✅ Uppercase","❌ មិនមាន Uppercase"),"lower":(bool(re.search(r"[a-z]",pw)),"✅ Lowercase","❌ មិនមាន Lowercase"),"digit":(bool(re.search(r"\d",pw)),"✅ លេខ","❌ មិនមានលេខ"),"special":(bool(re.search(r"[^A-Za-z0-9]",pw)),"✅ Symbol","❌ មិនមាន Symbol")}
    passed = sum(1 for _,(ok,_,_) in checks.items() if ok)
    issues = [good if ok else bad for _,(ok,good,bad) in checks.items() if bad]
    lvl,em = ("ខ្សោយ (Weak)","🔴") if passed<=2 else ("មធ្យម (Medium)","🟡") if passed<=4 else ("ល្អ (Strong)","🟢") if passed==5 else ("ខ្លាំងណាស់ (Very Strong)","🟢✨")
    entropy = round(math.log2(len(set(pw)))*len(pw),1) if len(set(pw))>1 else 0
    await update.message.reply_text(f"🔐 <b>លទ្ធផលពិនិត្យ Password</b>\n━━━━━━━━━━━━━━━━━━━━\n🔑 Password: <tg-spoiler>{'•'*len(pw)}</tg-spoiler>\n━━━━━━━━━━━━━━━━━━━━\n{em} <b>កម្រិត:</b> {lvl}\n📊 <b>ពិន្ទុ:</b> {passed}/6\n🎲 <b>Entropy:</b> {entropy} bits\n━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(issues), reply_markup=mkb([IKB("🔄 ពិនិត្យ Password ថ្មី", callback_data="menu_password")], [IKB("🏠 ម៉ឺនុយមេ", callback_data="back_main")]), parse_mode=ParseMode.HTML)
    return ConversationHandler.END

async def handle_picker(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    items = [x.strip() for x in update.message.text.strip().split(",") if x.strip()]
    if len(items) < 2: await update.message.reply_text("⚠️ <b>ត្រូវការ ≥2 ជម្រើស!</b>\nដាក់ , ចន្លោះ: <code>ក, ខ, គ</code>", parse_mode=ParseMode.HTML); return S_PICK
    chosen = random.choice(items); ranked = random.sample(items, len(items))
    await update.message.reply_text(f"🎲 <b>Random Picker</b>\n━━━━━━━━━━━━━━━━━━━━\n🏆 <b>ជ្រើស:</b> <code>{chosen}</code>\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>លំដាប់ Random:</b>\n" + "\n".join(f"  {i}. {x}" for i,x in enumerate(ranked,1)), reply_markup=mkb([IKB("🔄 Random ម្ដងទៀត", callback_data="menu_picker")], [IKB("🏠 ម៉ឺនុយមេ", callback_data="back_main")]), parse_mode=ParseMode.HTML)
    return ConversationHandler.END

async def handle_morse(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip(); d = ctx.user_data.get("morse_dir", "to")
    result, header, label = (text_to_morse(text),"Text → Morse","Morse") if d=="to" else (morse_to_text(text),"Morse → Text","Text")
    await update.message.reply_text(f"📡 <b>{header}</b>\n━━━━━━━━━━━━━━━━━━━━\n📥 <b>Input:</b> <code>{text[:200]}</code>\n📤 <b>{label}:</b> <code>{result[:500]}</code>", reply_markup=mkb([IKB("🔄 Morse ថ្មី", callback_data="menu_morse")], [IKB("🏠 ម៉ឺនុយមេ", callback_data="back_main")]), parse_mode=ParseMode.HTML)
    return ConversationHandler.END

async def handle_base64(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip(); d = ctx.user_data.get("b64_dir", "encode")
    try:
        result = base64.b64encode(text.encode()).decode() if d=="encode" else base64.b64decode(text.encode()).decode()
        header = "Encode" if d=="encode" else "Decode"; error = False
    except Exception as e: result = str(e); header = "Error"; error = True
    em = "🔐" if d=="encode" else "🔓"
    await update.message.reply_text(f"{em} <b>Base64 {header}</b>\n━━━━━━━━━━━━━━━━━━━━\n📥 <b>Input:</b>\n<code>{text[:200]}</code>\n\n{'❌' if error else '📤'} <b>Result:</b>\n<code>{result[:1000]}</code>", reply_markup=mkb([IKB("🔄 Base64 ថ្មី", callback_data="menu_base64")], [IKB("🏠 ម៉ឺនុយមេ", callback_data="back_main")]), parse_mode=ParseMode.HTML)
    return ConversationHandler.END

async def fallback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤔 <b>ខ្ញុំមិនយល់ Command!</b>\n\n👇 ចុចប៊ូតុងខាងក្រោម ឬ វាយ /start:", reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML)

def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(10)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(10)
        .build()
    )
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start), CallbackQueryHandler(callback_router)],
        states={
            S_QR:    [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_qr_input),    CallbackQueryHandler(callback_router)],
            S_SCAN:  [MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_scan_photo), CallbackQueryHandler(callback_router)],
            S_STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_style),  CallbackQueryHandler(callback_router)],
            S_PDF:   [MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_pdf_photo), CallbackQueryHandler(callback_router)],
            S_CALC:  [CallbackQueryHandler(callback_router)],
            S_PASS:  [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password),    CallbackQueryHandler(callback_router)],
            S_PICK:  [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_picker),      CallbackQueryHandler(callback_router)],
            S_MORSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_morse),       CallbackQueryHandler(callback_router)],
            S_B64:   [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_base64),      CallbackQueryHandler(callback_router)],
        },
        fallbacks=[CommandHandler("start", cmd_start), MessageHandler(filters.ALL, fallback_handler)],
        per_message=False, allow_reentry=True,
    )
    app.add_handler(conv)
    logger.info("🤖 Bot កំពុង Start...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, poll_interval=1.0, drop_pending_updates=True)

if __name__ == "__main__":
    main()
