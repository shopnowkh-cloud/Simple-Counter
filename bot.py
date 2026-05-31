#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,io,re,logging,warnings,zoneinfo
from PIL import Image; from fpdf import FPDF
from datetime import datetime
from telegram import Update,InlineKeyboardButton as IKB,InlineKeyboardMarkup,InputFile
from telegram.ext import Application,CommandHandler,MessageHandler,CallbackQueryHandler,ConversationHandler,ContextTypes,filters
from telegram.constants import ParseMode; from telegram.warnings import PTBUserWarning
warnings.filterwarnings("ignore",category=PTBUserWarning)
BOT_TOKEN=os.environ.get("BOT_TOKEN","")
if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN មិនទាន់កំណត់!")
logging.basicConfig(format="%(asctime)s|%(levelname)s|%(message)s",level=logging.INFO)
logger=logging.getLogger(__name__)

(S_STYLE,S_PDF)=range(2)
H=ParseMode.HTML; END=ConversationHandler.END

# ── keyboards ───────────────────────────────────────────────────────────────────
def mkb(*r): return InlineKeyboardMarkup(list(r))
def bb(): return mkb([IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")])
def bc(): return mkb([IKB("❌ បោះបង់",callback_data="back_main")])
HOME=[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]
def mm():
    return mkb(
        [IKB("✍️ រចនាប័ទ្មអក្សរ",callback_data="menu_text_style"),  IKB("🖼️ រូបភាព → PDF",callback_data="menu_photo_pdf")],
        [IKB("⏰ World Clock",callback_data="menu_wclock")],
        [IKB("ℹ️  អំពី Bot",callback_data="menu_about")],
    )

# ── edit/save helpers ───────────────────────────────────────────────────────────
async def _edit(ctx,text,kb=None):
    cid=ctx.user_data.get("cid"); mid=ctx.user_data.get("mid")
    if cid and mid:
        try: await ctx.bot.edit_message_text(chat_id=cid,message_id=mid,text=text,reply_markup=kb,parse_mode=H); return
        except Exception: pass
def _save(ctx,msg): ctx.user_data["cid"]=msg.chat_id; ctx.user_data["mid"]=msg.message_id

# ── text style maps ─────────────────────────────────────────────────────────────
def _t(t,m): return "".join(m.get(c,c) for c in t)
BM={**{chr(i):chr(i+0x1D400-0x41) for i in range(0x41,0x5B)},**{chr(i):chr(i+0x1D41A-0x61) for i in range(0x61,0x7B)},**{chr(i):chr(i+0x1D7CE-0x30) for i in range(0x30,0x3A)}}
IM={**{chr(i):chr(i+0x1D434-0x41) for i in range(0x41,0x5B)},**{chr(i):chr(i+0x1D44E-0x61) for i in range(0x61,0x7B)}}
BIM={**{chr(i):chr(i+0x1D468-0x41) for i in range(0x41,0x5B)},**{chr(i):chr(i+0x1D482-0x61) for i in range(0x61,0x7B)}}
SM={**{chr(i):chr(i+0x1D49C-0x41) for i in range(0x41,0x5B)},**{chr(i):chr(i+0x1D4B6-0x61) for i in range(0x61,0x7B)}}
DM={**{chr(i):chr(i+0x1D538-0x41) for i in range(0x41,0x5B)},**{chr(i):chr(i+0x1D552-0x61) for i in range(0x61,0x7B)},**{chr(i):chr(i+0x1D7D8-0x30) for i in range(0x30,0x3A)}}
SC={"a":"ᴀ","b":"ʙ","c":"ᴄ","d":"ᴅ","e":"ᴇ","f":"ꜰ","g":"ɢ","h":"ʜ","i":"ɪ","j":"ᴊ","k":"ᴋ","l":"ʟ","m":"ᴍ","n":"ɴ","o":"ᴏ","p":"ᴘ","q":"Q","r":"ʀ","s":"ꜱ","t":"ᴛ","u":"ᴜ","v":"ᴠ","w":"ᴡ","x":"x","y":"ʏ","z":"ᴢ"}
BB={**{chr(i):chr(i+0x24B6-0x41) for i in range(0x41,0x5B)},**{chr(i):chr(i+0x24D0-0x61) for i in range(0x61,0x7B)},**{"0":"⓪","1":"①","2":"②","3":"③","4":"④","5":"⑤","6":"⑥","7":"⑦","8":"⑧","9":"⑨"}}
UD={"a":"ɐ","b":"q","c":"ɔ","d":"p","e":"ǝ","f":"ɟ","g":"ƃ","h":"ɥ","i":"ᴉ","j":"ɾ","k":"ʞ","l":"l","m":"ɯ","n":"u","o":"o","p":"d","q":"b","r":"ɹ","s":"s","t":"ʇ","u":"n","v":"ʌ","w":"ʍ","x":"x","y":"ʎ","z":"z","A":"∀","B":"ᗺ","C":"Ɔ","D":"ᗡ","E":"Ǝ","F":"Ⅎ","G":"פ","H":"H","I":"I","J":"ſ","K":"ʞ","L":"˥","M":"W","N":"N","O":"O","P":"Ԁ","Q":"Q","R":"ɹ","S":"S","T":"┴","U":"∩","V":"Λ","W":"M","X":"X","Y":"⅄","Z":"Z","0":"0","1":"Ɩ","2":"ᄅ","3":"Ɛ","4":"ᔭ","5":"ϛ","6":"9","7":"ㄥ","8":"8","9":"6"," ":" "}
TS={"bold":("𝗕𝗼𝗹𝗱",lambda t:_t(t,BM)),"italic":("𝘐𝘵𝘢𝘭𝘪𝘤",lambda t:_t(t,IM)),"bold_italic":("𝑩𝒐𝒍𝒅 𝑰𝒕𝒂𝒍𝒊𝒄",lambda t:_t(t,BIM)),"script":("𝒮𝒸𝓇𝒾𝓅𝓉",lambda t:_t(t,SM)),"double":("𝔻𝕠𝕦𝕓𝕝𝕖",lambda t:_t(t,DM)),"small_caps":("Sᴍᴀʟʟ Cᴀᴘꜱ",lambda t:_t(t.lower(),SC)),"bubble":("Ⓑⓤⓑⓑⓛⓔ",lambda t:_t(t,BB)),"upside_down":("uʍop ǝpᴉsdn",lambda t:_t(t,UD)[::-1]),"strikethrough":("S̶t̶r̶i̶k̶e̶",lambda t:"".join(c+"̶" for c in t)),"underline":("U̲n̲d̲e̲r̲",lambda t:"".join(c+"̲" for c in t))}

# ── /start ──────────────────────────────────────────────────────────────────────
async def cmd_start(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    msg=await u.message.reply_text(
        f"👋 សួស្ដី <b>{u.effective_user.first_name}</b>!\n"
        "👇 <b>ជ្រើសរើសប្រភេទ ហើយចុចប៊ូតុង</b>",
        reply_markup=mm(),parse_mode=H)
    _save(ctx,msg); return END

# ── callback router ─────────────────────────────────────────────────────────────
async def cb(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=u.callback_query; d=q.data
    if d=="noop": await q.answer(); return END
    await q.answer()
    ctx.user_data["cid"]=q.message.chat_id; ctx.user_data["mid"]=q.message.message_id

    if d=="back_main":
        await q.edit_message_text(
            "👇 <b>ជ្រើសរើសប្រភេទ ហើយចុចប៊ូតុង</b>",
            reply_markup=mm(),parse_mode=H); return END
    if d=="menu_text_style":
        await q.edit_message_text("✍️ <b>រចនាប័ទ្មអក្សរ</b>\n\n✏️ សូមវាយ <b>អក្សរឡាតាំង</b>៖\n<i>⚠️ ដំណើរការល្អជាមួយ a-z A-Z 0-9</i>",reply_markup=bc(),parse_mode=H); return S_STYLE
    if d=="menu_photo_pdf":
        ctx.user_data["pdf_photos"]=[]
        await q.edit_message_text("🖼️ <b>រូបភាព → PDF</b>\n\n📤 Upload រូបភាព (អាចច្រើន)\n✅ ចប់ → ចុច <b>បង្កើត PDF</b>",reply_markup=mkb([IKB("✅ បង្កើត PDF",callback_data="pdf_done"),IKB("❌ បោះបង់",callback_data="back_main")]),parse_mode=H); return S_PDF
    # ── World Clock ──
    if d=="menu_wclock":
        return await _show_world_clock(q)

    if d=="menu_about":
        import telegram as _tg; import sys
        ptb_ver=_tg.__version__; py_ver=sys.version.split()[0]
        await q.edit_message_text(
            f"ℹ️ <b>Khmer Multi-Tool Bot</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 <code>{datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🐍 Python: <b>{py_ver}</b>\n"
            f"📡 python-telegram-bot: <b>{ptb_ver}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>Libraries:</b>\n"
            f"   fpdf2 • Pillow • zoneinfo\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✍️ Text Style  🖼️ PDF\n"
            f"📡 Morse  ⏰ World Clock\n"
            f"📊 <b>សរុប: 4 មុខងារ</b>",
            reply_markup=bb(),parse_mode=H); return END

    if d.startswith("copy_style_"):
        sk=d[11:]; orig=ctx.user_data.get("style_original","")
        if orig and sk in TS:
            styled=TS[sk][1](orig); await q.answer(f"✅ បានចម្លង: {styled[:15]}...",show_alert=True)
            await q.message.reply_text(f"<code>{styled}</code>",parse_mode=H)
        return S_STYLE
    if d=="pdf_done": return await _pdf_build(q,ctx)
    return END

# ── World Clock helper ────────────────────────────────────────────────────────
async def _show_world_clock(q):
    cities=[("🇰🇭 ភ្នំពេញ","Asia/Phnom_Penh"),("🇺🇸 New York","America/New_York"),
            ("🇬🇧 London","Europe/London"),("🇫🇷 Paris","Europe/Paris"),
            ("🇯🇵 Tokyo","Asia/Tokyo"),("🇦🇺 Sydney","Australia/Sydney"),
            ("🇨🇳 Beijing","Asia/Shanghai"),("🇸🇬 Singapore","Asia/Singapore"),
            ("🇦🇪 Dubai","Asia/Dubai"),("🇧🇷 São Paulo","America/Sao_Paulo")]
    lines=[]
    for name,tz in cities:
        now=datetime.now(zoneinfo.ZoneInfo(tz))
        lines.append(f"{name}\n<code>{now.strftime('%H:%M:%S')}  {now.strftime('%d/%m/%Y')}</code>")
    await q.edit_message_text(
        "⏰ <b>World Clock</b>\n━━━━━━━━━━━━\n"+"\n\n".join(lines),
        reply_markup=InlineKeyboardMarkup([[IKB("🔄 Refresh",callback_data="menu_wclock")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]]),
        parse_mode=H)
    return END

# ── Text style ──────────────────────────────────────────────────────────────────
async def text_style(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip()
    if not t: await _edit(ctx,"⚠️ សូមវាយអ្វីមួយ!",bc()); return S_STYLE
    await u.message.delete(); ctx.user_data["style_original"]=t
    rows=[f"<b>{lbl}:</b>\n{fn(t)}" for _,(lbl,fn) in TS.items()]
    ks=list(TS.keys()); btns=[[IKB(f"📋 {TS[ks[i]][0]}",callback_data=f"copy_style_{ks[i]}") for i in range(j,min(j+2,len(ks)))] for j in range(0,len(ks),2)]
    btns+=[[IKB("✍️ ដំណើរការថ្មី",callback_data="menu_text_style")],HOME]
    await _edit(ctx,f"✍️ <b>Style ទាំងអស់សម្រាប់:</b> <code>{t}</code>\n━━━━━━━━━━━━\n\n"+"\n\n".join(rows)+"\n\n━━━━━━━━━━━━\n👇 ចុចប៊ូតុង ចម្លង Style:",InlineKeyboardMarkup(btns)); return S_STYLE

# ── PDF ─────────────────────────────────────────────────────────────────────────
async def pdf_photo(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    p=u.message.photo[-1] if u.message.photo else None; dc=u.message.document if u.message.document else None
    if not p and not dc: await _edit(ctx,"⚠️ សូម Upload រូបភាព!",mkb([IKB("✅ បង្កើត PDF",callback_data="pdf_done"),IKB("❌ បោះបង់",callback_data="back_main")])); return S_PDF
    f=await ctx.bot.get_file(p.file_id if p else dc.file_id); ctx.user_data.setdefault("pdf_photos",[]).append(bytes(await f.download_as_bytearray()))
    n=len(ctx.user_data["pdf_photos"])
    await _edit(ctx,f"✅ <b>រូបភាពទី {n} បានទទួល!</b>\n📤 Upload បន្ថែម ឬ ចុច <b>បង្កើត PDF</b>",mkb([IKB("✅ បង្កើត PDF",callback_data="pdf_done"),IKB("❌ បោះបង់",callback_data="back_main")])); return S_PDF

async def _pdf_build(q,ctx:ContextTypes.DEFAULT_TYPE):
    photos=ctx.user_data.get("pdf_photos",[])
    if not photos: await q.answer("⚠️ មិនទាន់មានរូបភាពទេ!",show_alert=True); return S_PDF
    await q.edit_message_text(f"⏳ <b>កំពុងបំប្លែង {len(photos)} រូប → PDF...</b>",parse_mode=H)
    pdf=FPDF()
    for raw in photos:
        img=Image.open(io.BytesIO(raw)).convert("RGB"); w,h=img.size
        if w>h: pdf.add_page("L",(297,210)); pw,ph=297,210
        else:   pdf.add_page("P",(210,297)); pw,ph=210,297
        ra=min(pw/w,ph/h); nw,nh=w*ra,h*ra; tmp=io.BytesIO(); img.save(tmp,format="JPEG",quality=90); tmp.seek(0); pdf.image(tmp,x=(pw-nw)/2,y=(ph-nh)/2,w=nw,h=nh)
    buf=io.BytesIO(bytes(pdf.output()))
    msg=await q.message.reply_document(document=InputFile(buf,filename="KhmerBot.pdf"),caption=f"✅ <b>PDF បង្កើតជោគជ័យ!</b>\n🖼️ ចំនួន {len(photos)} ទំព័រ",reply_markup=InlineKeyboardMarkup([[IKB("🖼️ PDF ថ្មី",callback_data="menu_photo_pdf")],HOME]),parse_mode=H)
    _save(ctx,msg); ctx.user_data["pdf_photos"]=[]; return END

# ── Fallback ─────────────────────────────────────────────────────────────────
async def fallback(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    try: await u.message.delete()
    except: pass
    await _edit(ctx,"🤔 <b>ខ្ញុំមិនយល់!</b>\n\n👇 សូមជ្រើសរើស ឬ វាយ /start",mm())

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    app=Application.builder().token(BOT_TOKEN).connect_timeout(10).read_timeout(30).write_timeout(30).pool_timeout(10).build()
    TXT=filters.TEXT&~filters.COMMAND; IMG=filters.PHOTO|filters.Document.IMAGE; CB_H=CallbackQueryHandler(cb)
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start",cmd_start),CB_H],
        states={
            S_STYLE: [MessageHandler(TXT,text_style), CB_H],
            S_PDF:   [MessageHandler(IMG,pdf_photo),  CB_H],
        },
        fallbacks=[CommandHandler("start",cmd_start),MessageHandler(filters.ALL,fallback)],
        per_message=False,allow_reentry=True,
    ))
    logger.info("🤖 Bot កំពុង Start..."); app.run_polling(allowed_updates=Update.ALL_TYPES,poll_interval=1.0,drop_pending_updates=True)
if __name__=="__main__": main()
