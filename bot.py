#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,io,logging,warnings
from PIL import Image; from fpdf import FPDF; import fitz
import qrcode; from pyzbar import pyzbar
from telegram import Update,ReplyKeyboardMarkup,ReplyKeyboardRemove,InputFile
from telegram.ext import Application,CommandHandler,MessageHandler,ConversationHandler,ContextTypes,filters
from telegram.constants import ParseMode; from telegram.warnings import PTBUserWarning
warnings.filterwarnings("ignore",category=PTBUserWarning)
BOT_TOKEN=os.environ.get("BOT_TOKEN","")
if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN មិនទាន់កំណត់!")
logging.basicConfig(format="%(asctime)s|%(levelname)s|%(message)s",level=logging.INFO)
logger=logging.getLogger(__name__)
S_MAIN,S_DOC,S_STYLE,S_PDF,S_PDF2IMG,S_QR,S_QR_CREATE,S_QR_SCAN=range(8); H=ParseMode.HTML; END=ConversationHandler.END

# ── keyboards ─────────────────────────────────────────────────────────────────
def _rk(*rows): return ReplyKeyboardMarkup(list(rows),resize_keyboard=True)
KB_MAIN   = _rk(["✍️ រចនាប័ទ្មអក្សរ","🗂️ បំប្លែង PDF"],["📷 QR Code"])
KB_DOC    = _rk(["🖼️ រូបភាព → PDF"],["🖼️ PDF → PNG","📷 PDF → JPG"],["🏠 ម៉ឺនុយមេ"])
KB_QR     = _rk(["🔳 បង្កើត QR","🔍 Scan QR"],["🏠 ម៉ឺនុយមេ"])
KB_QR_CREATE_DONE = _rk(["🔳 QR ថ្មី","🔍 Scan QR"],["🏠 ម៉ឺនុយមេ"])
KB_QR_SCAN_DONE   = _rk(["🔍 Scan ថ្មី","🔳 បង្កើត QR"],["🏠 ម៉ឺនុយមេ"])
KB_CANCEL = _rk(["❌ បោះបង់"])
KB_STYLE  = _rk(["✍️ ដំណើរការថ្មី","🏠 ម៉ឺនុយមេ"])
KB_PDF_DONE = _rk(["🖼️ PDF ថ្មី","🏠 ម៉ឺនុយមេ"])
REM = ReplyKeyboardRemove()
def kb_pdf(n): return _rk([f"✅ បង្កើត PDF ({n} រូប)","❌ បោះបង់"])
def kb_img_done(fmt): return _rk([f"🔄 {'PNG' if fmt=='PNG' else 'JPG'} ថ្មី","🏠 ម៉ឺនុយមេ"])

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
    ("𝗕𝗼𝗹𝗱",           lambda t:_t(t,BM)),
    ("𝘐𝘵𝘢𝘭𝘪𝘤",         lambda t:_t(t,IM)),
    ("𝑩𝒐𝒍𝒅 𝑰𝒕𝒂𝒍𝒊𝒄",   lambda t:_t(t,BIM)),
    ("𝒮𝒸𝓇𝒾𝓅𝓉",         lambda t:_t(t,SM)),
    ("𝓑𝓸𝓵𝓭 𝓢𝓬𝓻𝓲𝓹𝓽",  lambda t:_t(t,BSM)),
    ("𝔻𝕠𝕦𝕓𝕝𝕖",         lambda t:_t(t,DM)),
    ("𝔊𝔬𝔱𝔥𝔦𝔠",         lambda t:_t(t,FM)),
    ("𝖲𝖺𝗇𝗌",            lambda t:_t(t,SFM)),
    ("𝙼𝚘𝚗𝚘",            lambda t:_t(t,MOM)),
    ("Ｆｕｌｌｗｉｄｔｈ",  lambda t:_t(t,FW)),
    ("ˢᵘᵖᵉʳˢᶜʳⁱᵖᵗ",     lambda t:_t(t,SUPM)),
    ("Sᴍᴀʟʟ Cᴀᴘꜱ",      lambda t:_t(t.lower(),SC)),
    ("Ⓑⓤⓑⓑⓛⓔ",        lambda t:_t(t,BB)),
    ("uʍop ǝpᴉsdn",      lambda t:_t(t,UD)[::-1]),
    ("S\u0336t\u0336r\u0336i\u0336k\u0336e\u0336", lambda t:"".join(c+"\u0336" for c in t)),
    ("U\u0332n\u0332d\u0332e\u0332r\u0332",         lambda t:"".join(c+"\u0332" for c in t)),
]

# ── nav helpers ───────────────────────────────────────────────────────────────
async def go_main(u,ctx):
    ctx.user_data.clear()
    await u.message.reply_text("👇 <b>ជ្រើសរើស:</b>",reply_markup=KB_MAIN,parse_mode=H)
    return S_MAIN

async def go_doc(u,ctx):
    await u.message.reply_text("🗂️ <b>បំប្លែង PDF</b>\nជ្រើស:",reply_markup=KB_DOC,parse_mode=H)
    return S_DOC

async def go_qr(u,ctx):
    await u.message.reply_text("📷 <b>QR Code</b>\nជ្រើស:",reply_markup=KB_QR,parse_mode=H)
    return S_QR

# ── handlers ──────────────────────────────────────────────────────────────────
async def cmd_start(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await u.message.reply_text(f"👋 សួស្ដី <b>{u.effective_user.first_name}</b>!\n👇 <b>ជ្រើសរើស:</b>",reply_markup=KB_MAIN,parse_mode=H)
    return S_MAIN

async def main_handler(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text
    if t=="✍️ រចនាប័ទ្មអក្សរ":
        await u.message.reply_text("✍️ <b>រចនាប័ទ្មអក្សរ</b>\n\n✏️ វាយ <b>អក្សរឡាតាំង</b>:\n<i>⚠️ ដំណើរការល្អជាមួយ a-z A-Z 0-9</i>",reply_markup=KB_CANCEL,parse_mode=H)
        return S_STYLE
    if t=="🗂️ បំប្លែង PDF": return await go_doc(u,ctx)
    if t=="📷 QR Code": return await go_qr(u,ctx)
    await u.message.reply_text("👇 <b>ជ្រើសរើស:</b>",reply_markup=KB_MAIN,parse_mode=H)
    return S_MAIN

async def style_handler(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text
    if t in("❌ បោះបង់","🏠 ម៉ឺនុយមេ"): return await go_main(u,ctx)
    if t=="✍️ ដំណើរការថ្មី":
        await u.message.reply_text("✏️ វាយ <b>អក្សរឡាតាំង</b>:",reply_markup=KB_CANCEL,parse_mode=H); return S_STYLE
    lines="\n".join(f"<b>{lbl}:</b>  <code>{fn(t)}</code>" for lbl,fn in TS)
    await u.message.reply_text(
        f"✍️ <b>Style:</b> <code>{t}</code>\n━━━━━━━━━\n{lines}\n━━━━━━━━━\n👆 ចុចលើ code ដើម្បី Copy",
        reply_markup=KB_STYLE,parse_mode=H)
    return S_STYLE

async def doc_handler(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text
    if t in("❌ បោះបង់","🏠 ម៉ឺនុយមេ"): return await go_main(u,ctx)
    if t in("🖼️ រូបភាព → PDF","🖼️ PDF ថ្មី"):
        ctx.user_data["pdf_photos"]=[]; ctx.user_data.pop("pdf_mid",None)
        await u.message.reply_text("🖼️ <b>រូបភាព → PDF</b>\n📤 Upload រូបភាព:",reply_markup=KB_CANCEL,parse_mode=H); return S_PDF
    if t in("🖼️ PDF → PNG","🔄 PNG ថ្មី"):
        ctx.user_data["pdf2img_fmt"]="PNG"
        await u.message.reply_text("🖼️ <b>PDF → PNG</b>\n📎 Upload PDF:",reply_markup=KB_CANCEL,parse_mode=H); return S_PDF2IMG
    if t in("📷 PDF → JPG","🔄 JPG ថ្មី"):
        ctx.user_data["pdf2img_fmt"]="JPG"
        await u.message.reply_text("📷 <b>PDF → JPG</b>\n📎 Upload PDF:",reply_markup=KB_CANCEL,parse_mode=H); return S_PDF2IMG
    return await go_doc(u,ctx)

async def pdf_handler(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text or ""
    if t:
        if t.startswith("✅ បង្កើត PDF"): return await _pdf_build(u,ctx)
        if t in("❌ បោះបង់","🏠 ម៉ឺនុយមេ"): return await go_doc(u,ctx)
        await u.message.reply_text("📤 Upload រូបភាព!",reply_markup=KB_CANCEL,parse_mode=H); return S_PDF
    p=u.message.photo[-1] if u.message.photo else None
    dc=u.message.document if u.message.document else None
    if not p and not dc:
        await u.message.reply_text("⚠️ Upload រូបភាព!",reply_markup=KB_CANCEL,parse_mode=H); return S_PDF
    f=await ctx.bot.get_file(p.file_id if p else dc.file_id)
    ctx.user_data.setdefault("pdf_photos",[]).append(bytes(await f.download_as_bytearray()))
    n=len(ctx.user_data["pdf_photos"])
    prev_mid=ctx.user_data.get("pdf_mid")
    if prev_mid and n>1:
        try: await ctx.bot.delete_message(chat_id=u.message.chat_id,message_id=prev_mid)
        except: pass
    msg=await u.message.reply_text(f"🖼️ <b>បានទទួល {n} រូប</b>\nUpload បន្ថែម ឬ ចុច <b>បង្កើត PDF</b>",reply_markup=kb_pdf(n),parse_mode=H)
    ctx.user_data["pdf_mid"]=msg.message_id; return S_PDF

async def _pdf_build(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    photos=ctx.user_data.get("pdf_photos",[])
    if not photos:
        await u.message.reply_text("⚠️ មិនទាន់មានរូបភាព!",reply_markup=KB_CANCEL,parse_mode=H); return S_PDF
    await u.message.reply_text(f"⏳ <b>កំពុងបំប្លែង {len(photos)} រូប → PDF...</b>",reply_markup=REM,parse_mode=H)
    pdf=FPDF()
    for raw in photos:
        img=Image.open(io.BytesIO(raw)).convert("RGB"); w,h=img.size
        pw,ph=w*25.4/96,h*25.4/96
        pdf.add_page(format=(pw,ph)); pdf.set_margins(0,0,0); pdf.set_auto_page_break(False)
        tmp=io.BytesIO(); img.save(tmp,format="JPEG",quality=95); tmp.seek(0)
        pdf.image(tmp,x=0,y=0,w=pw,h=ph)
    buf=io.BytesIO(bytes(pdf.output()))
    await u.message.reply_document(document=InputFile(buf,filename="KhmerBot.pdf"),caption=f"✅ <b>PDF បង្កើតជោគជ័យ!</b>\n🖼️ {len(photos)} ទំព័រ",reply_markup=KB_PDF_DONE,parse_mode=H)
    ctx.user_data["pdf_photos"]=[]; ctx.user_data.pop("pdf_mid",None); return S_DOC

async def pdf2img_handler(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text or ""; fmt=ctx.user_data.get("pdf2img_fmt","PNG")
    if t:
        if t in("❌ បោះបង់","🏠 ម៉ឺនុយមេ"): return await go_doc(u,ctx)
        await u.message.reply_text("📎 Upload PDF!",reply_markup=KB_CANCEL,parse_mode=H); return S_PDF2IMG
    dc=u.message.document
    if not dc or not (dc.file_name or "").lower().endswith(".pdf"):
        await u.message.reply_text("⚠️ Upload ឯកសារ PDF!",reply_markup=KB_CANCEL,parse_mode=H); return S_PDF2IMG
    try:
        await u.message.reply_text(f"⏳ <b>កំពុងបំប្លែង PDF → {fmt}...</b>",reply_markup=REM,parse_mode=H)
        raw=bytes(await (await ctx.bot.get_file(dc.file_id)).download_as_bytearray())
        doc=fitz.open(stream=raw,filetype="pdf"); total=len(doc)
        ext=fmt.lower(); pil_fmt="PNG" if fmt=="PNG" else "JPEG"; media=[]
        for i,page in enumerate(doc):
            pix=page.get_pixmap(matrix=fitz.Matrix(150/72,150/72),alpha=False)
            img=Image.frombytes("RGB",[pix.width,pix.height],pix.samples)
            buf=io.BytesIO(); img.save(buf,format=pil_fmt,quality=90 if fmt=="JPG" else None); buf.seek(0)
            media.append((buf,f"page_{i+1:02d}.{ext}"))
        doc.close()
        done_kb=kb_img_done(fmt)
        for idx,(buf,name) in enumerate(media):
            last=idx==len(media)-1
            cap=f"✅ <b>{'បំប្លែងជោគជ័យ! 1 ទំព័រ' if total==1 else f'ទំព័រ {idx+1}/{total}' if not last else f'រួចរាល់! {total} ទំព័រ → {fmt}'}</b>"
            await u.message.reply_document(document=InputFile(buf,filename=name),caption=cap,reply_markup=done_kb if last else None,parse_mode=H)
    except Exception as e:
        logger.error(f"pdf2img: {e}")
        await u.message.reply_text("❌ <b>មានបញ្ហា! ព្យាយាមម្ដងទៀត</b>",reply_markup=KB_CANCEL,parse_mode=H)
    return S_DOC

async def qr_handler(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text
    if t in("❌ បោះបង់","🏠 ម៉ឺនុយមេ"): return await go_main(u,ctx)
    if t in("🔳 បង្កើត QR","🔳 QR ថ្មី"):
        await u.message.reply_text("🔳 <b>បង្កើត QR Code</b>\n\n✏️ វាយ <b>Link / Text</b> ដែលចង់បំប្លែង:",reply_markup=KB_CANCEL,parse_mode=H)
        return S_QR_CREATE
    if t in("🔍 Scan QR","🔍 Scan ថ្មី"):
        await u.message.reply_text("🔍 <b>Scan QR Code</b>\n\n📤 Upload <b>រូបភាព QR</b>:",reply_markup=KB_CANCEL,parse_mode=H)
        return S_QR_SCAN
    return await go_qr(u,ctx)

async def qr_create_handler(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text
    if t in("❌ បោះបង់","🏠 ម៉ឺនុយមេ"): return await go_main(u,ctx)
    if t in("🔍 Scan QR","🔍 Scan ថ្មី"):
        await u.message.reply_text("🔍 <b>Scan QR Code</b>\n\n📤 Upload <b>រូបភាព QR</b>:",reply_markup=KB_CANCEL,parse_mode=H)
        return S_QR_SCAN
    try:
        qr=qrcode.QRCode(version=None,error_correction=qrcode.constants.ERROR_CORRECT_H,box_size=10,border=4)
        qr.add_data(t); qr.make(fit=True)
        img=qr.make_image(fill_color="black",back_color="white").convert("RGB")
        buf=io.BytesIO(); img.save(buf,format="PNG"); buf.seek(0)
        await u.message.reply_photo(photo=buf,caption=f"✅ <b>QR Code បង្កើតជោគជ័យ!</b>\n\n📝 <code>{t}</code>",reply_markup=KB_QR_CREATE_DONE,parse_mode=H)
    except Exception as e:
        logger.error(f"qr_create: {e}")
        await u.message.reply_text("❌ <b>មានបញ្ហា! ព្យាយាមម្ដងទៀត</b>",reply_markup=KB_CANCEL,parse_mode=H)
    return S_QR

async def qr_scan_handler(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text or ""
    if t in("❌ បោះបង់","🏠 ម៉ឺនុយមេ"): return await go_main(u,ctx)
    if t in("🔳 បង្កើត QR","🔳 QR ថ្មី"):
        await u.message.reply_text("🔳 <b>បង្កើត QR Code</b>\n\n✏️ វាយ <b>Link / Text</b>:",reply_markup=KB_CANCEL,parse_mode=H)
        return S_QR_CREATE
    if t: await u.message.reply_text("📤 Upload <b>រូបភាព QR</b>!",reply_markup=KB_CANCEL,parse_mode=H); return S_QR_SCAN
    p=u.message.photo[-1] if u.message.photo else None
    dc=u.message.document if u.message.document else None
    if not p and not dc:
        await u.message.reply_text("⚠️ Upload <b>រូបភាព QR</b>!",reply_markup=KB_CANCEL,parse_mode=H); return S_QR_SCAN
    try:
        raw=bytes(await (await ctx.bot.get_file(p.file_id if p else dc.file_id)).download_as_bytearray())
        img=Image.open(io.BytesIO(raw)).convert("RGB")
        codes=pyzbar.decode(img)
        if not codes:
            await u.message.reply_text("❌ <b>រកមិនឃើញ QR Code!</b>\nសូម Upload រូបភាពច្បាស់ជាង",reply_markup=KB_CANCEL,parse_mode=H); return S_QR_SCAN
        lines="\n\n".join(f"📌 <b>លទ្ធផលទី {i+1}:</b>\n<code>{c.data.decode('utf-8','replace')}</code>" for i,c in enumerate(codes))
        await u.message.reply_text(f"✅ <b>Scan QR ជោគជ័យ!</b> ({len(codes)} QR)\n━━━━━━━━━\n{lines}",reply_markup=KB_QR_SCAN_DONE,parse_mode=H)
    except Exception as e:
        logger.error(f"qr_scan: {e}")
        await u.message.reply_text("❌ <b>មានបញ្ហា! ព្យាយាមម្ដងទៀត</b>",reply_markup=KB_CANCEL,parse_mode=H)
    return S_QR

async def _back_main(u,ctx):
    await u.message.reply_text("👇 <b>ជ្រើសរើស:</b>",reply_markup=KB_MAIN,parse_mode=H)
    return S_MAIN

async def _catch_main(u,ctx): return await _back_main(u,ctx)
async def _catch_doc(u,ctx): return await go_doc(u,ctx)
async def _catch_style(u,ctx):
    await u.message.reply_text("✏️ វាយ <b>អក្សរឡាតាំង</b>:",reply_markup=KB_CANCEL,parse_mode=H); return S_STYLE
async def _catch_pdf(u,ctx):
    n=len(ctx.user_data.get("pdf_photos",[]))
    kb=kb_pdf(n) if n>0 else KB_CANCEL
    await u.message.reply_text("📤 Upload <b>រូបភាព</b> (photo/file)!",reply_markup=kb,parse_mode=H); return S_PDF
async def _catch_pdf2img(u,ctx):
    await u.message.reply_text("📎 Upload <b>ឯកសារ PDF</b>!",reply_markup=KB_CANCEL,parse_mode=H); return S_PDF2IMG
async def _catch_qr(u,ctx): return await go_qr(u,ctx)
async def _catch_qr_create(u,ctx):
    await u.message.reply_text("✏️ វាយ <b>Link / Text</b> ដើម្បីបង្កើត QR:",reply_markup=KB_CANCEL,parse_mode=H); return S_QR_CREATE
async def _catch_qr_scan(u,ctx):
    await u.message.reply_text("📤 Upload <b>រូបភាព QR</b>!",reply_markup=KB_CANCEL,parse_mode=H); return S_QR_SCAN

def main():
    app=Application.builder().token(BOT_TOKEN).connect_timeout(10).read_timeout(30).write_timeout(30).pool_timeout(10).build()
    TXT=filters.TEXT&~filters.COMMAND
    IMG=filters.PHOTO|filters.Document.IMAGE
    PDF_F=filters.Document.MimeType("application/pdf")|filters.Document.FileExtension("pdf")
    ANY=filters.ALL
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start",cmd_start),MessageHandler(ANY,cmd_start)],
        states={
            S_MAIN:      [MessageHandler(TXT,main_handler),          MessageHandler(ANY,_catch_main)],
            S_DOC:       [MessageHandler(TXT,doc_handler),           MessageHandler(ANY,_catch_doc)],
            S_STYLE:     [MessageHandler(TXT,style_handler),         MessageHandler(ANY,_catch_style)],
            S_PDF:       [MessageHandler(TXT|IMG,pdf_handler),       MessageHandler(ANY,_catch_pdf)],
            S_PDF2IMG:   [MessageHandler(TXT|PDF_F,pdf2img_handler), MessageHandler(ANY,_catch_pdf2img)],
            S_QR:        [MessageHandler(TXT,qr_handler),            MessageHandler(ANY,_catch_qr)],
            S_QR_CREATE: [MessageHandler(TXT,qr_create_handler),     MessageHandler(ANY,_catch_qr_create)],
            S_QR_SCAN:   [MessageHandler(TXT|IMG,qr_scan_handler),   MessageHandler(ANY,_catch_qr_scan)],
        },
        fallbacks=[CommandHandler("start",cmd_start),MessageHandler(ANY,_back_main)],
        per_message=False,allow_reentry=False,
    ))
    logger.info("🤖 Bot កំពុង Start..."); app.run_polling(allowed_updates=Update.ALL_TYPES,poll_interval=1.0,drop_pending_updates=True)
if __name__=="__main__": main()
