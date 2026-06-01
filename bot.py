#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,io,logging,warnings
from PIL import Image; from fpdf import FPDF; import fitz
import qrcode; from pyzbar import pyzbar
from telegram import Update,InlineKeyboardButton as IKB,InlineKeyboardMarkup as IKM,InputFile,CopyTextButton
from telegram.ext import Application,CommandHandler,MessageHandler,CallbackQueryHandler,ConversationHandler,ContextTypes,filters
from telegram.constants import ParseMode; from telegram.warnings import PTBUserWarning
warnings.filterwarnings("ignore",category=PTBUserWarning)
BOT_TOKEN=os.environ.get("BOT_TOKEN","")
if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN មិនទាន់កំណត់!")
logging.basicConfig(format="%(asctime)s|%(levelname)s|%(message)s",level=logging.INFO)
logger=logging.getLogger(__name__)
S_MAIN,S_DOC,S_STYLE,S_PDF,S_PDF2IMG,S_QR,S_QR_CREATE,S_QR_SCAN=range(8)
H=ParseMode.HTML; END=ConversationHandler.END

# ── inline keyboards ──────────────────────────────────────────────────────────
def mkb(rows): return IKM(rows)
IK_MAIN  = mkb([[IKB("✍️ រចនាប័ទ្មអក្សរ",callback_data="style"),IKB("🗂️ បំប្លែង PDF",callback_data="doc")],[IKB("📷 QR Code",callback_data="qr")]])
IK_DOC   = mkb([[IKB("🖼️ រូបភាព → PDF",callback_data="photo_pdf")],[IKB("🖼️ PDF → PNG",callback_data="pdf_png"),IKB("📷 PDF → JPG",callback_data="pdf_jpg")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="home")]])
IK_QR    = mkb([[IKB("🔳 បង្កើត QR",callback_data="qr_create"),IKB("🔍 Scan QR",callback_data="qr_scan")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="home")]])
IK_CANCEL_MAIN = mkb([[IKB("❌ បោះបង់",callback_data="cancel_main")]])
IK_CANCEL_DOC  = mkb([[IKB("❌ បោះបង់",callback_data="cancel_doc")]])
IK_CANCEL_QR   = mkb([[IKB("❌ បោះបង់",callback_data="cancel_qr")]])
IK_PDF_DONE    = mkb([[IKB("🖼️ PDF ថ្មី",callback_data="photo_pdf"),IKB("🏠 ម៉ឺនុយមេ",callback_data="home")]])
IK_QR_CR_DONE  = mkb([[IKB("🔳 QR ថ្មី",callback_data="qr_create"),IKB("🔍 Scan QR",callback_data="qr_scan")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="home")]])
IK_QR_SC_DONE  = mkb([[IKB("🔍 Scan ថ្មី",callback_data="qr_scan"),IKB("🔳 បង្កើត QR",callback_data="qr_create")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="home")]])
def ik_pdf(n): return mkb([[IKB(f"✅ បង្កើត PDF ({n} រូប)",callback_data="pdf_build"),IKB("❌ បោះបង់",callback_data="doc")]])
def ik_img_done(fmt): return mkb([[IKB(f"🔄 {'PNG' if fmt=='PNG' else 'JPG'} ថ្មី",callback_data="pdf_png" if fmt=="PNG" else "pdf_jpg"),IKB("🏠 ម៉ឺនុយមេ",callback_data="home")]])

# ── helpers ───────────────────────────────────────────────────────────────────
def _save(ctx,msg):
    ctx.user_data["cid"]=msg.chat_id; ctx.user_data["mid"]=msg.message_id

async def _send(ctx,cid,text,kb=None):
    msg=await ctx.bot.send_message(chat_id=cid,text=text,reply_markup=kb,parse_mode=H)
    _save(ctx,msg); return msg

async def _edit_or_send(ctx,cid,text,kb=None):
    mid=ctx.user_data.get("mid")
    if mid:
        try:
            await ctx.bot.edit_message_text(chat_id=cid,message_id=mid,text=text,reply_markup=kb,parse_mode=H); return
        except: pass
    await _send(ctx,cid,text,kb)

# ── text style maps ───────────────────────────────────────────────────────────
def _t(t,m): return "".join(m.get(c,c) for c in t)
def _rng(u,lo,hi,base): return {chr(i):chr(i+u-base) for i in range(lo,hi)}
BM ={**_rng(0x1D400,0x41,0x5B,0x41),**_rng(0x1D41A,0x61,0x7B,0x61),**_rng(0x1D7CE,0x30,0x3A,0x30)}
IM ={**_rng(0x1D434,0x41,0x5B,0x41),**_rng(0x1D44E,0x61,0x7B,0x61)}
BIM={**_rng(0x1D468,0x41,0x5B,0x41),**_rng(0x1D482,0x61,0x7B,0x61)}
SM ={**_rng(0x1D49C,0x41,0x5B,0x41),**_rng(0x1D4B6,0x61,0x7B,0x61)}
BSM={**_rng(0x1D4D0,0x41,0x5B,0x41),**_rng(0x1D4EA,0x61,0x7B,0x61)}
DM ={**_rng(0x1D538,0x41,0x5B,0x41),**_rng(0x1D552,0x61,0x7B,0x61),**_rng(0x1D7D8,0x30,0x3A,0x30)}
FM ={**_rng(0x1D504,0x41,0x5B,0x41),**_rng(0x1D51E,0x61,0x7B,0x61),**{"C":"\u212D","H":"\u210C","I":"\u2111","R":"\u211C","Z":"\u2128"}}
SFM={**_rng(0x1D5A0,0x41,0x5B,0x41),**_rng(0x1D5BA,0x61,0x7B,0x61),**_rng(0x1D7E2,0x30,0x3A,0x30)}
MOM={**_rng(0x1D670,0x41,0x5B,0x41),**_rng(0x1D68A,0x61,0x7B,0x61),**_rng(0x1D7F6,0x30,0x3A,0x30)}
FW ={**_rng(0xFF21,0x41,0x5B,0x41),**_rng(0xFF41,0x61,0x7B,0x61),**_rng(0xFF10,0x30,0x3A,0x30)," ":"\u2003"}
SC ={"a":"ᴀ","b":"ʙ","c":"ᴄ","d":"ᴅ","e":"ᴇ","f":"ꜰ","g":"ɢ","h":"ʜ","i":"ɪ","j":"ᴊ","k":"ᴋ","l":"ʟ","m":"ᴍ","n":"ɴ","o":"ᴏ","p":"ᴘ","q":"Q","r":"ʀ","s":"ꜱ","t":"ᴛ","u":"ᴜ","v":"ᴠ","w":"ᴡ","x":"x","y":"ʏ","z":"ᴢ"}
BB ={**_rng(0x24B6,0x41,0x5B,0x41),**_rng(0x24D0,0x61,0x7B,0x61),**{"0":"\u24ea","1":"\u2460","2":"\u2461","3":"\u2462","4":"\u2463","5":"\u2464","6":"\u2465","7":"\u2466","8":"\u2467","9":"\u2468"}}
UD ={"a":"ɐ","b":"q","c":"ɔ","d":"p","e":"ǝ","f":"ɟ","g":"ƃ","h":"ɥ","i":"ᴉ","j":"ɾ","k":"ʞ","l":"l","m":"ɯ","n":"u","o":"o","p":"d","q":"b","r":"ɹ","s":"s","t":"ʇ","u":"n","v":"ʌ","w":"ʍ","x":"x","y":"ʎ","z":"z","A":"∀","B":"ᗺ","C":"Ɔ","D":"ᗡ","E":"Ǝ","F":"Ⅎ","G":"פ","H":"H","I":"I","J":"ſ","K":"ʞ","L":"˥","M":"W","N":"N","O":"O","P":"Ԁ","Q":"Q","R":"ɹ","S":"S","T":"┴","U":"∩","V":"Λ","W":"M","X":"X","Y":"⅄","Z":"Z","0":"0","1":"Ɩ","2":"ᄅ","3":"Ɛ","4":"ᔭ","5":"ϛ","6":"9","7":"ㄥ","8":"8","9":"6"," ":" "}
SUPM={"a":"ᵃ","b":"ᵇ","c":"ᶜ","d":"ᵈ","e":"ᵉ","f":"ᶠ","g":"ᵍ","h":"ʰ","i":"ⁱ","j":"ʲ","k":"ᵏ","l":"ˡ","m":"ᵐ","n":"ⁿ","o":"ᵒ","p":"ᵖ","q":"q","r":"ʳ","s":"ˢ","t":"ᵗ","u":"ᵘ","v":"ᵛ","w":"ʷ","x":"ˣ","y":"ʸ","z":"ᶻ","A":"ᴬ","B":"ᴮ","C":"ᶜ","D":"ᴰ","E":"ᴱ","F":"ᶠ","G":"ᴳ","H":"ᴴ","I":"ᴵ","J":"ᴶ","K":"ᴷ","L":"ᴸ","M":"ᴹ","N":"ᴺ","O":"ᴼ","P":"ᴾ","Q":"Q","R":"ᴿ","S":"ˢ","T":"ᵀ","U":"ᵁ","V":"\u2c7d","W":"ᵂ","X":"ˣ","Y":"ʸ","Z":"ᶻ","0":"⁰","1":"¹","2":"²","3":"³","4":"⁴","5":"⁵","6":"⁶","7":"⁷","8":"⁸","9":"⁹"}
TS=[
    ("𝗕𝗼𝗹𝗱",          lambda t:_t(t,BM)),
    ("𝘐𝘵𝘢𝘭𝘪𝘤",        lambda t:_t(t,IM)),
    ("𝑩𝒐𝒍𝒅 𝑰𝒕𝒂𝒍𝒊𝒄",  lambda t:_t(t,BIM)),
    ("𝒮𝒸𝓇𝒾𝓅𝓉",        lambda t:_t(t,SM)),
    ("𝓑𝓸𝓵𝓭 𝓢𝓬𝓻𝓲𝓹𝓽", lambda t:_t(t,BSM)),
    ("𝔻𝕠𝕦𝕓𝕝𝕖",        lambda t:_t(t,DM)),
    ("𝔊𝔬𝔱𝔥𝔦𝔠",        lambda t:_t(t,FM)),
    ("𝖲𝖺𝗇𝗌",           lambda t:_t(t,SFM)),
    ("𝙼𝚘𝚗𝚘",           lambda t:_t(t,MOM)),
    ("Ｆｕｌｌｗｉｄｔｈ", lambda t:_t(t,FW)),
    ("ˢᵘᵖᵉʳˢᶜʳⁱᵖᵗ",    lambda t:_t(t,SUPM)),
    ("Sᴍᴀʟʟ Cᴀᴘꜱ",     lambda t:_t(t.lower(),SC)),
    ("Ⓑⓤⓑⓑⓛⓔ",       lambda t:_t(t,BB)),
    ("uʍop ǝpᴉsdn",     lambda t:_t(t,UD)[::-1]),
    ("S\u0336t\u0336r\u0336i\u0336k\u0336e\u0336",lambda t:"".join(c+"\u0336" for c in t)),
    ("U\u0332n\u0332d\u0332e\u0332r\u0332",       lambda t:"".join(c+"\u0332" for c in t)),
]

# ── /start ────────────────────────────────────────────────────────────────────
async def cmd_start(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    msg=await u.message.reply_text(
        f"👋 សួស្ដី <b>{u.effective_user.first_name}</b>! ខ្ញុំជា <b>Khmer Multi-Tool Bot</b>\n\n"
        "✍️ <b>រចនាប័ទ្មអក្សរ</b> — បំប្លែងអក្សរឡាតាំងជាពុម្ពអក្សរពិសេស\n"
        "🗂️ <b>បំប្លែង PDF</b> — ផ្សំរូបភាពជា PDF ឬ PDF ជារូបភាព\n"
        "📷 <b>QR Code</b> — បង្កើត QR HD និង Scan QR Code\n\n"
        "👇 <b>ចុចជ្រើសរើសមុខងារ:</b>",
        reply_markup=IK_MAIN,parse_mode=H)
    _save(ctx,msg); return S_MAIN

# ── unified callback handler ───────────────────────────────────────────────────
async def cb(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=u.callback_query; await q.answer(); d=q.data
    cid=q.message.chat_id; _save(ctx,q.message)

    if d=="home":
        ctx.user_data.clear(); _save(ctx,q.message)
        await q.edit_message_text(
            "🏠 <b>ម៉ឺនុយមេ</b>\n\n"
            "✍️ <b>រចនាប័ទ្មអក្សរ</b> — បំប្លែងអក្សរឡាតាំងជាពុម្ពអក្សរពិសេស\n"
            "🗂️ <b>បំប្លែង PDF</b> — ផ្សំរូបភាពជា PDF ឬ PDF ជារូបភាព\n"
            "📷 <b>QR Code</b> — បង្កើត QR HD និង Scan QR Code\n\n"
            "👇 <b>ចុចជ្រើសរើសមុខងារ:</b>",
            reply_markup=IK_MAIN,parse_mode=H); return S_MAIN

    if d=="style" or d=="style_new":
        await q.edit_message_text(
            "✍️ <b>រចនាប័ទ្មអក្សរ</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "បំប្លែងអក្សរឡាតាំងធម្មតា ទៅជាពុម្ពអក្សរពិសេសជាច្រើនប្រភេទ\n"
            "ដូចជា Bold, Italic, Script, Bubble, Upside-down និងច្រើនទៀត!\n\n"
            "✏️ <b>វាយអក្សរឡាតាំងខាងក្រោម:</b>\n"
            "<i>⚠️ ដំណើរការបានល្អជាមួយ a-z  A-Z  0-9</i>",
            reply_markup=IK_CANCEL_MAIN,parse_mode=H); return S_STYLE

    if d=="cancel_main":
        ctx.user_data.clear(); _save(ctx,q.message)
        await q.edit_message_text(
            "🏠 <b>ម៉ឺនុយមេ</b>\n\n"
            "✍️ <b>រចនាប័ទ្មអក្សរ</b> — បំប្លែងអក្សរឡាតាំងជាពុម្ពអក្សរពិសេស\n"
            "🗂️ <b>បំប្លែង PDF</b> — ផ្សំរូបភាពជា PDF ឬ PDF ជារូបភាព\n"
            "📷 <b>QR Code</b> — បង្កើត QR HD និង Scan QR Code\n\n"
            "👇 <b>ចុចជ្រើសរើសមុខងារ:</b>",
            reply_markup=IK_MAIN,parse_mode=H); return S_MAIN

    if d=="doc" or d=="cancel_doc":
        ctx.user_data.pop("pdf_photos",None); ctx.user_data.pop("pdf_mid",None)
        await q.edit_message_text(
            "🗂️ <b>បំប្លែង PDF</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "🖼️ <b>រូបភាព → PDF</b> — ផ្សំរូបភាពច្រើន​ទៅជា​ PDF​ ​តែ​មួយ\n"
            "🖼️ <b>PDF → PNG</b> — បំប្លែង​ PDF ​ម្តា​ម​ទំព័រ​ជា​រូបភាព​ PNG\n"
            "📷 <b>PDF → JPG</b> — បំប្លែង​ PDF ​ម្តា​ម​ទំព័រ​ជា​រូបភាព​ JPG\n\n"
            "👇 <b>ចុចជ្រើសរើស:</b>",
            reply_markup=IK_DOC,parse_mode=H); return S_DOC

    if d=="cancel_qr":
        await q.edit_message_text(
            "📷 <b>QR Code</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "🔳 <b>បង្កើត QR</b> — វាយ Link ឬ Text ដើម្បីបង្កើត QR Code HD 2048×2048\n"
            "🔍 <b>Scan QR</b> — Upload រូបភាព QR ដើម្បី Decode យក Link ឬ Text\n\n"
            "👇 <b>ចុចជ្រើសរើស:</b>",
            reply_markup=IK_QR,parse_mode=H); return S_QR

    if d=="photo_pdf":
        ctx.user_data["pdf_photos"]=[]; ctx.user_data.pop("pdf_mid",None)
        await q.edit_message_text(
            "🖼️ <b>រូបភាព → PDF</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Upload រូបភាព​ ម្តា​ម​ដុំ ហើយ​ Bot​ នឹង​ ផ្សំ​ ទៅ​ជា​ PDF​ ​​តែ​មួយ\n"
            "អាច​ Upload​ ​បាន​ច្រើន​រូប — ​ ​ ​ Format: JPG, PNG, WEBP\n\n"
            "📤 <b>ចាប់ផ្ដើម Upload រូបភាព:</b>",
            reply_markup=IK_CANCEL_DOC,parse_mode=H); return S_PDF

    if d in("pdf_png","pdf_jpg"):
        ctx.user_data["pdf2img_fmt"]="PNG" if d=="pdf_png" else "JPG"
        lbl="PNG" if d=="pdf_png" else "JPG"; ico="🖼️" if d=="pdf_png" else "📷"
        await q.edit_message_text(
            f"{ico} <b>PDF → {lbl}</b>\n"
            "━━━━━━━━━━━━━━━\n"
            f"Upload ឯកសារ PDF ហើយ Bot នឹងបំប្លែង​ ​ម្តា​ម​ទំព័រ​​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​\n"
            f"ទៅ​ជា​រូបភាព​ <b>{lbl}</b> គុណភាពខ្ពស់ — Resolution: 150 DPI\n\n"
            "📎 <b>Upload ឯកសារ PDF:</b>",
            reply_markup=IK_CANCEL_DOC,parse_mode=H); return S_PDF2IMG

    if d=="pdf_build":
        return await _pdf_build(q,ctx)

    if d=="qr":
        await q.edit_message_text(
            "📷 <b>QR Code</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "🔳 <b>បង្កើត QR</b> — វាយ Link ឬ Text ដើម្បីបង្កើត QR Code HD 2048×2048\n"
            "🔍 <b>Scan QR</b> — Upload រូបភាព QR ដើម្បី Decode យក Link ឬ Text\n\n"
            "👇 <b>ចុចជ្រើសរើស:</b>",
            reply_markup=IK_QR,parse_mode=H); return S_QR

    if d=="qr_create":
        await q.edit_message_text(
            "🔳 <b>បង្កើត QR Code</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Bot នឹងបង្កើត QR Code ​ HD​ ​ ​​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​\n"
            "ទំហំ <b>2048×2048</b> ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ ​\n"
            "អាចប្រើជាមួយ <b>Link, Text</b> ឬ <b>ឧបករណ៍</b>\n\n"
            "✏️ <b>វាយ Link ឬ Text ខាងក្រោម:</b>",
            reply_markup=IK_CANCEL_QR,parse_mode=H); return S_QR_CREATE

    if d=="qr_scan":
        await q.edit_message_text(
            "🔍 <b>Scan QR Code</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Upload រឹបភាពតែលមាន QR Code ហើល្យ Bot\n"
            "នឹង Decode យក <b>Link</b> ឬ <b>Text</b> ចើញពី QR នោះ\n"
            "យក Scan QR Code បានយាងងាយស្រួល\n\n"
            "📤 <b>Upload រឹបភាព QR:</b>",
            reply_markup=IK_CANCEL_QR,parse_mode=H); return S_QR_SCAN
    await q.edit_message_text("👇 <b>ជ្រើសរើស:</b>",reply_markup=IK_MAIN,parse_mode=H); return S_MAIN

# ── text style ────────────────────────────────────────────────────────────────
async def style_handler(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text
    rows=[[IKB(fn(t),copy_text=CopyTextButton(fn(t)))] for lbl,fn in TS]
    rows.append([IKB("✍️ ដំណើរការថ្មី",callback_data="style_new"),IKB("🏠 ម៉ឺនុយមេ",callback_data="home")])
    kb=IKM(rows); txt=f"✍️ <b>Style:</b> <code>{t}</code>\n👇 ចុច button ដើម្បី <b>Copy</b>"
    cid=u.message.chat_id; mid=ctx.user_data.get("mid")
    try: await u.message.delete()
    except: pass
    if mid:
        try:
            await ctx.bot.edit_message_text(chat_id=cid,message_id=mid,text=txt,reply_markup=kb,parse_mode=H)
            return S_STYLE
        except: pass
    msg=await ctx.bot.send_message(chat_id=cid,text=txt,reply_markup=kb,parse_mode=H)
    _save(ctx,msg); return S_STYLE

# ── image → PDF ───────────────────────────────────────────────────────────────
async def pdf_photo(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    p=u.message.photo[-1] if u.message.photo else None
    dc=u.message.document if u.message.document else None
    if not p and not dc:
        cid=u.message.chat_id; await _edit_or_send(ctx,cid,"⚠️ Upload រូបភាព!",IK_CANCEL_DOC); return S_PDF
    f=await ctx.bot.get_file(p.file_id if p else dc.file_id)
    ctx.user_data.setdefault("pdf_photos",[]).append(bytes(await f.download_as_bytearray()))
    n=len(ctx.user_data["pdf_photos"]); cid=u.message.chat_id
    txt=f"🖼️ <b>បានទទួល {n} រូប</b>\nUpload បន្ថែម ឬ ចុច <b>បង្កើត PDF</b>"
    mid=ctx.user_data.get("mid")
    if mid and n>1:
        try:
            await ctx.bot.edit_message_text(chat_id=cid,message_id=mid,text=txt,reply_markup=ik_pdf(n),parse_mode=H)
            return S_PDF
        except: pass
    msg=await u.message.reply_text(txt,reply_markup=ik_pdf(n),parse_mode=H)
    _save(ctx,msg); return S_PDF

async def _pdf_build(q,ctx:ContextTypes.DEFAULT_TYPE):
    photos=ctx.user_data.get("pdf_photos",[])
    if not photos:
        await q.edit_message_text("⚠️ មិនទាន់មានរូបភាព!",reply_markup=IK_CANCEL_DOC,parse_mode=H); return S_PDF
    await q.edit_message_text(f"⏳ <b>កំពុងបំប្លែង {len(photos)} រូប → PDF...</b>",parse_mode=H)
    pdf=FPDF()
    for raw in photos:
        img=Image.open(io.BytesIO(raw)).convert("RGB"); w,h=img.size
        pw,ph=w*25.4/96,h*25.4/96
        pdf.add_page(format=(pw,ph)); pdf.set_margins(0,0,0); pdf.set_auto_page_break(False)
        tmp=io.BytesIO(); img.save(tmp,format="JPEG",quality=95); tmp.seek(0)
        pdf.image(tmp,x=0,y=0,w=pw,h=ph)
    buf=io.BytesIO(bytes(pdf.output()))
    await ctx.bot.send_document(chat_id=q.message.chat_id,document=InputFile(buf,filename="KhmerBot.pdf"),
        caption=f"✅ <b>PDF បង្កើតជោគជ័យ!</b>\n🖼️ {len(photos)} ទំព័រ",parse_mode=H)
    msg=await ctx.bot.send_message(chat_id=q.message.chat_id,text="👇 <b>ជ្រើសរើស:</b>",reply_markup=IK_MAIN,parse_mode=H)
    ctx.user_data["pdf_photos"]=[]; _save(ctx,msg); return S_MAIN

# ── PDF → image ───────────────────────────────────────────────────────────────
async def pdf2img(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    dc=u.message.document; fmt=ctx.user_data.get("pdf2img_fmt","PNG"); cid=u.message.chat_id
    if not dc or not (dc.mime_type=="application/pdf" or (dc.file_name or "").lower().endswith(".pdf")):
        await _edit_or_send(ctx,cid,"⚠️ Upload ឯកសារ <b>PDF</b>!",IK_CANCEL_DOC); return S_PDF2IMG
    try:
        await _edit_or_send(ctx,cid,f"⏳ <b>កំពុងបំប្លែង PDF → {fmt}...</b>")
        raw=bytes(await (await ctx.bot.get_file(dc.file_id)).download_as_bytearray())
        doc=fitz.open(stream=raw,filetype="pdf"); total=len(doc)
        ext=fmt.lower(); pil_fmt="PNG" if fmt=="PNG" else "JPEG"; media=[]
        for i,page in enumerate(doc):
            pix=page.get_pixmap(matrix=fitz.Matrix(150/72,150/72),alpha=False)
            img=Image.frombytes("RGB",[pix.width,pix.height],pix.samples)
            buf=io.BytesIO(); img.save(buf,format=pil_fmt,quality=90 if fmt=="JPG" else None); buf.seek(0)
            media.append((buf,f"page_{i+1:02d}.{ext}"))
        doc.close()
        for idx,(buf,name) in enumerate(media):
            last=idx==len(media)-1
            cap=f"✅ <b>{'បំប្លែងជោគជ័យ! 1 ទំព័រ' if total==1 else f'ទំព័រ {idx+1}/{total}' if not last else f'រួចរាល់! {total} ទំព័រ → {fmt}'}</b>"
            await u.message.reply_document(document=InputFile(buf,filename=name),caption=cap,parse_mode=H)
        msg=await u.message.reply_text("👇 <b>ជ្រើសរើស:</b>",reply_markup=IK_MAIN,parse_mode=H)
        _save(ctx,msg)
    except Exception as e:
        logger.error(f"pdf2img: {e}")
        await _edit_or_send(ctx,cid,"❌ <b>មានបញ្ហា! ព្យាយាមម្ដងទៀត</b>",IK_CANCEL_DOC)
    return S_MAIN

# ── QR create ─────────────────────────────────────────────────────────────────
async def qr_create(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text; cid=u.message.chat_id
    def _make_qr_buf(chunk):
        for ec,nm in zip([qrcode.constants.ERROR_CORRECT_H,qrcode.constants.ERROR_CORRECT_Q,qrcode.constants.ERROR_CORRECT_M,qrcode.constants.ERROR_CORRECT_L],["H","Q","M","L"]):
            try:
                qr=qrcode.QRCode(version=None,error_correction=ec,box_size=40,border=1)
                qr.add_data(chunk); qr.make(fit=True)
                img=qr.make_image(fill_color="#000000",back_color="#FFFFFF").convert("L")
                bbox=img.getbbox()
                if bbox: img=img.crop(bbox)
                pad=20; cv=Image.new("L",(img.width+pad*2,img.height+pad*2),255); cv.paste(img,(pad,pad))
                cv=cv.convert("RGB").resize((2048,2048),Image.NEAREST)
                buf=io.BytesIO(); cv.save(buf,format="PNG",optimize=False,compress_level=1); buf.seek(0)
                return buf,nm
            except Exception: pass
        return None,None
    try:
        CHUNK=2800; raw=t.encode("utf-8")
        chunks=[raw[i:i+CHUNK].decode("utf-8","ignore") for i in range(0,len(raw),CHUNK)]
        total=len(chunks)
        msg=await u.message.reply_text(f"⏳ <b>កំពុងបង្កើត {total} QR Code{'s' if total>1 else ''}...</b>",parse_mode=H)
        _save(ctx,msg)
        for idx,chunk in enumerate(chunks):
            buf,ec=_make_qr_buf(chunk)
            if buf is None: raise ValueError(f"chunk {idx+1} fail")
            fname=f"QRCode_HD{'_p'+str(idx+1) if total>1 else ''}.png"
            part_info=f" ({idx+1}/{total})" if total>1 else ""
            last=idx==total-1
            cap=f"✅ <b>QR Code HD{part_info}</b>\n📐 2048×2048  |  EC: {ec}\n\n📝 <code>{chunk[:80]}{'…' if len(chunk)>80 else ''}</code>"
            await u.message.reply_document(document=InputFile(buf,filename=fname),caption=cap,parse_mode=H)
        msg=await u.message.reply_text("👇 <b>ជ្រើសរើស:</b>",reply_markup=IK_MAIN,parse_mode=H)
        _save(ctx,msg)
    except Exception as e:
        logger.error(f"qr_create: {e}")
        await _edit_or_send(ctx,cid,"❌ <b>មានបញ្ហា! ព្យាយាមម្ដងទៀត</b>",IK_CANCEL_QR)
    return S_MAIN

# ── QR scan ───────────────────────────────────────────────────────────────────
async def qr_scan(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    p=u.message.photo[-1] if u.message.photo else None
    dc=u.message.document if u.message.document else None
    cid=u.message.chat_id
    if not p and not dc:
        await _edit_or_send(ctx,cid,"⚠️ Upload <b>រូបភាព QR</b>!",IK_CANCEL_QR); return S_QR_SCAN
    try:
        raw=bytes(await (await ctx.bot.get_file(p.file_id if p else dc.file_id)).download_as_bytearray())
        img=Image.open(io.BytesIO(raw)).convert("RGB"); codes=pyzbar.decode(img)
        if not codes:
            await _edit_or_send(ctx,cid,"❌ <b>រកមិនឃើញ QR Code!</b>\nសូម Upload រូបភាពច្បាស់ជាង",IK_CANCEL_QR); return S_QR_SCAN
        lines="\n\n".join(f"📌 <b>លទ្ធផលទី {i+1}:</b>\n<code>{c.data.decode('utf-8','replace')}</code>" for i,c in enumerate(codes))
        await u.message.reply_text(f"✅ <b>Scan QR ជោគជ័យ!</b> ({len(codes)} QR)\n━━━━━━━━━\n{lines}",parse_mode=H)
        msg=await u.message.reply_text("👇 <b>ជ្រើសរើស:</b>",reply_markup=IK_MAIN,parse_mode=H)
        _save(ctx,msg)
    except Exception as e:
        logger.error(f"qr_scan: {e}")
        await _edit_or_send(ctx,cid,"❌ <b>មានបញ្ហា! ព្យាយាមម្ដងទៀត</b>",IK_CANCEL_QR)
    return S_MAIN

# ── fallback ──────────────────────────────────────────────────────────────────
async def fallback(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    msg=await u.message.reply_text("👇 <b>ជ្រើសរើស:</b>",reply_markup=IK_MAIN,parse_mode=H)
    _save(ctx,msg); return S_MAIN

def main():
    app=Application.builder().token(BOT_TOKEN).connect_timeout(10).read_timeout(30).write_timeout(30).pool_timeout(10).build()
    TXT=filters.TEXT&~filters.COMMAND
    IMG=filters.PHOTO|filters.Document.IMAGE
    PDF_F=filters.Document.MimeType("application/pdf")|filters.Document.FileExtension("pdf")
    CBQ=CallbackQueryHandler(cb)
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start",cmd_start),MessageHandler(filters.ALL,fallback)],
        states={
            S_MAIN:      [CBQ],
            S_DOC:       [CBQ],
            S_STYLE:     [MessageHandler(TXT,style_handler),    CBQ],
            S_PDF:       [MessageHandler(IMG,pdf_photo),        CBQ],
            S_PDF2IMG:   [MessageHandler(PDF_F,pdf2img),        CBQ],
            S_QR:        [CBQ],
            S_QR_CREATE: [MessageHandler(TXT,qr_create),       CBQ],
            S_QR_SCAN:   [MessageHandler(IMG,qr_scan),         CBQ],
        },
        fallbacks=[CommandHandler("start",cmd_start),MessageHandler(filters.ALL,fallback)],
        per_message=False,allow_reentry=False,
    ))
    logger.info("🤖 Bot កំពុង Start..."); app.run_polling(allowed_updates=Update.ALL_TYPES,poll_interval=1.0,drop_pending_updates=True)
if __name__=="__main__": main()
