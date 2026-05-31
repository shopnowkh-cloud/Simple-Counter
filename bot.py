#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,io,logging,warnings
from PIL import Image; from fpdf import FPDF; import fitz
from telegram import Update,InlineKeyboardButton as IKB,InlineKeyboardMarkup,InputFile,CopyTextButton
from telegram.ext import Application,CommandHandler,MessageHandler,CallbackQueryHandler,ConversationHandler,ContextTypes,filters
from telegram.constants import ParseMode; from telegram.warnings import PTBUserWarning
warnings.filterwarnings("ignore",category=PTBUserWarning)
BOT_TOKEN=os.environ.get("BOT_TOKEN","")
if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN មិនទាន់កំណត់!")
logging.basicConfig(format="%(asctime)s|%(levelname)s|%(message)s",level=logging.INFO)
logger=logging.getLogger(__name__)
S_STYLE,S_PDF,S_PDF2IMG=range(3); H=ParseMode.HTML; END=ConversationHandler.END

# keyboards
def mkb(*r): return InlineKeyboardMarkup(list(r))
def bc(): return mkb([IKB("❌ បោះបង់",callback_data="back_main")])
HOME=[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]
def mm(): return mkb([IKB("✍️ រចនាប័ទ្មអក្សរ",callback_data="menu_text_style"),IKB("🗂️ បំប្លែង PDF",callback_data="menu_doc_tools")])
def doc_tools_kb(): return mkb([IKB("🖼️ រូបភាព → PDF",callback_data="menu_photo_pdf")],[IKB("🖼️ PDF → PNG",callback_data="menu_pdf2png")],[IKB("📷 PDF → JPG",callback_data="menu_pdf2jpg")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")])

# helpers
async def _edit(ctx,text,kb=None):
    cid=ctx.user_data.get("cid"); mid=ctx.user_data.get("mid")
    if cid and mid:
        try: await ctx.bot.edit_message_text(chat_id=cid,message_id=mid,text=text,reply_markup=kb,parse_mode=H); return
        except: pass
    if cid:
        msg=await ctx.bot.send_message(chat_id=cid,text=text,reply_markup=kb,parse_mode=H)
        ctx.user_data["mid"]=msg.message_id
def _save(ctx,msg): ctx.user_data["cid"]=msg.chat_id; ctx.user_data["mid"]=msg.message_id

# text style maps
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
    ("bold",        lambda t:_t(t,BM)),
    ("italic",      lambda t:_t(t,IM)),
    ("bold_italic", lambda t:_t(t,BIM)),
    ("script",      lambda t:_t(t,SM)),
    ("bold_script", lambda t:_t(t,BSM)),
    ("double",      lambda t:_t(t,DM)),
    ("gothic",      lambda t:_t(t,FM)),
    ("sans",        lambda t:_t(t,SFM)),
    ("mono",        lambda t:_t(t,MOM)),
    ("fullwidth",   lambda t:_t(t,FW)),
    ("superscript", lambda t:_t(t,SUPM)),
    ("small_caps",  lambda t:_t(t.lower(),SC)),
    ("bubble",      lambda t:_t(t,BB)),
    ("upside_down", lambda t:_t(t,UD)[::-1]),
    ("strikethrough",lambda t:"".join(c+"\u0336" for c in t)),
    ("underline",   lambda t:"".join(c+"\u0332" for c in t)),
]

# handlers
async def cmd_start(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    msg=await u.message.reply_text(f"👋 សួស្ដី <b>{u.effective_user.first_name}</b>!\n👇 <b>ជ្រើសរើសប្រភេទ ហើយចុចប៊ូតុង</b>",reply_markup=mm(),parse_mode=H)
    _save(ctx,msg); return END

async def cb(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=u.callback_query; d=q.data
    if d=="noop": await q.answer(); return END
    await q.answer()
    ctx.user_data["cid"]=q.message.chat_id; ctx.user_data["mid"]=q.message.message_id
    if d=="back_main":
        await _edit(ctx,"👇 <b>ជ្រើសរើសប្រភេទ ហើយចុចប៊ូតុង</b>",mm()); return END
    if d=="menu_text_style":
        await _edit(ctx,"✍️ <b>រចនាប័ទ្មអក្សរ</b>\n\n✏️ សូមវាយ <b>អក្សរឡាតាំង</b>៖\n<i>⚠️ ដំណើរការល្អជាមួយ a-z A-Z 0-9</i>",bc()); return S_STYLE
    if d=="menu_doc_tools":
        await _edit(ctx,"🗂️ <b>បំប្លែង PDF</b>\n\nសូមជ្រើសរើសប្រភេទ៖",doc_tools_kb()); return END
    if d=="menu_photo_pdf":
        ctx.user_data["pdf_photos"]=[]
        await _edit(ctx,"🖼️ <b>រូបភាព → PDF</b>\n\n📤 Upload រូបភាព (អាចច្រើន)\n✅ ចប់ → ចុច <b>បង្កើត PDF</b>",mkb([IKB("✅ បង្កើត PDF",callback_data="pdf_done"),IKB("❌ បោះបង់",callback_data="menu_doc_tools")])); return S_PDF
    if d in("menu_pdf2png","menu_pdf2jpg"):
        fmt="PNG" if d=="menu_pdf2png" else "JPG"
        ctx.user_data["pdf2img_fmt"]=fmt
        await _edit(ctx,f"{'🖼️' if fmt=='PNG' else '📷'} <b>PDF → {fmt}</b>\n\n📎 សូម Upload ឯកសារ <b>PDF</b>:\n<i>Bot នឹងបំប្លែងរាល់ទំព័រ → {fmt}</i>",mkb([IKB("❌ បោះបង់",callback_data="menu_doc_tools")])); return S_PDF2IMG
    if d=="pdf_done": return await _pdf_build(q,ctx)
    return END

async def text_style(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip()
    if not t: await _edit(ctx,"⚠️ សូមវាយអ្វីមួយ!",bc()); return S_STYLE
    await u.message.delete(); ctx.user_data["style_original"]=t
    def _prev(fn,maxlen=16):
        s=fn(t); return s[:maxlen]+("…" if len(s)>maxlen else "")
    btns=[[IKB(_prev(fn),copy_text=CopyTextButton(text=fn(t))) for _,fn in TS[j:j+2]] for j in range(0,len(TS),2)]
    btns+=[[IKB("✍️ ដំណើរការថ្មី",callback_data="menu_text_style")],HOME]
    await _edit(ctx,f"✍️ <b>Style ទាំងអស់សម្រាប់:</b> <code>{t}</code>\n━━━━━━━━━━━━\n👇 ចុចប៊ូតុង Copy ម្តង!",InlineKeyboardMarkup(btns)); return S_STYLE

async def pdf_photo(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    p=u.message.photo[-1] if u.message.photo else None; dc=u.message.document if u.message.document else None
    if not p and not dc: await _edit(ctx,"⚠️ សូម Upload រូបភាព!",mkb([IKB("✅ បង្កើត PDF",callback_data="pdf_done"),IKB("❌ បោះបង់",callback_data="menu_doc_tools")])); return S_PDF
    f=await ctx.bot.get_file(p.file_id if p else dc.file_id); ctx.user_data.setdefault("pdf_photos",[]).append(bytes(await f.download_as_bytearray()))
    n=len(ctx.user_data["pdf_photos"])
    await _edit(ctx,f"✅ <b>រូបភាពទី {n} បានទទួល!</b>\n📤 Upload បន្ថែម ឬ ចុច <b>បង្កើត PDF</b>",mkb([IKB("✅ បង្កើត PDF",callback_data="pdf_done"),IKB("❌ បោះបង់",callback_data="menu_doc_tools")])); return S_PDF

async def _pdf_build(q,ctx:ContextTypes.DEFAULT_TYPE):
    photos=ctx.user_data.get("pdf_photos",[])
    if not photos: await q.answer("⚠️ មិនទាន់មានរូបភាពទេ!",show_alert=True); return S_PDF
    await q.edit_message_text(f"⏳ <b>កំពុងបំប្លែង {len(photos)} រូប → PDF...</b>",parse_mode=H)
    pdf=FPDF()
    for raw in photos:
        img=Image.open(io.BytesIO(raw)).convert("RGB"); w,h=img.size
        pw,ph=w*25.4/96,h*25.4/96
        pdf.add_page(format=(pw,ph))
        pdf.set_margins(0,0,0); pdf.set_auto_page_break(False)
        tmp=io.BytesIO(); img.save(tmp,format="JPEG",quality=95); tmp.seek(0)
        pdf.image(tmp,x=0,y=0,w=pw,h=ph)
    buf=io.BytesIO(bytes(pdf.output()))
    msg=await q.message.reply_document(document=InputFile(buf,filename="KhmerBot.pdf"),caption=f"✅ <b>PDF បង្កើតជោគជ័យ!</b>\n🖼️ ចំនួន {len(photos)} ទំព័រ",reply_markup=InlineKeyboardMarkup([[IKB("🖼️ PDF ថ្មី",callback_data="menu_photo_pdf")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]]),parse_mode=H)
    _save(ctx,msg); ctx.user_data["pdf_photos"]=[]; return END

async def pdf_to_img(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    dc=u.message.document; fmt=ctx.user_data.get("pdf2img_fmt","PNG")
    if not dc or not (dc.file_name or "").lower().endswith(".pdf"):
        await _edit(ctx,"⚠️ <b>សូម Upload ឯកសារ PDF!</b>",mkb([IKB("❌ បោះបង់",callback_data="menu_doc_tools")])); return S_PDF2IMG
    try:
        await u.message.delete(); await _edit(ctx,f"⏳ <b>កំពុងបំប្លែង PDF → {fmt}...</b>",None)
        raw=bytes(await (await ctx.bot.get_file(dc.file_id)).download_as_bytearray())
        doc=fitz.open(stream=raw,filetype="pdf"); total=len(doc)
        ext=fmt.lower(); pil_fmt="PNG" if fmt=="PNG" else "JPEG"; media=[]
        for i,page in enumerate(doc):
            pix=page.get_pixmap(matrix=fitz.Matrix(150/72,150/72),alpha=False)
            img=Image.frombytes("RGB",[pix.width,pix.height],pix.samples)
            buf=io.BytesIO(); img.save(buf,format=pil_fmt,quality=90 if fmt=="JPG" else None); buf.seek(0)
            media.append((buf,f"page_{i+1:02d}.{ext}"))
        doc.close()
        back_kb=InlineKeyboardMarkup([[IKB("🔄 PDF ថ្មី",callback_data=f"menu_pdf2{'png' if fmt=='PNG' else 'jpg'}")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]])
        for idx,(buf,name) in enumerate(media):
            last=idx==len(media)-1
            cap=f"✅ <b>{'បំប្លែងជោគជ័យ! ' if total==1 else f'ទំព័រទី {idx+1}/{total}' if not last else f'រួចរាល់! {total} ទំព័រ → {fmt}'}</b>"
            msg=await u.message.reply_document(document=InputFile(buf,filename=name),caption=cap,reply_markup=back_kb if last else None,parse_mode=H)
        _save(ctx,msg)
    except Exception as e:
        logger.error(f"pdf2img: {e}"); await _edit(ctx,"❌ <b>មានបញ្ហា! សូមព្យាយាមម្ដងទៀត</b>",mkb([IKB("❌ ត្រឡប់",callback_data="menu_doc_tools")]))
    return END

async def fallback(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    try: await u.message.delete()
    except: pass
    await _edit(ctx,"🤔 <b>ខ្ញុំមិនយល់!</b>\n\n👇 សូមជ្រើសរើស ឬ វាយ /start",mm())

def main():
    app=Application.builder().token(BOT_TOKEN).connect_timeout(10).read_timeout(30).write_timeout(30).pool_timeout(10).build()
    TXT=filters.TEXT&~filters.COMMAND; IMG=filters.PHOTO|filters.Document.IMAGE
    PDF_F=filters.Document.MimeType("application/pdf"); CB_H=CallbackQueryHandler(cb)
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start",cmd_start),CB_H],
        states={S_STYLE:[MessageHandler(TXT,text_style),CB_H],S_PDF:[MessageHandler(IMG,pdf_photo),CB_H],S_PDF2IMG:[MessageHandler(PDF_F,pdf_to_img),CB_H]},
        fallbacks=[CommandHandler("start",cmd_start),MessageHandler(filters.ALL,fallback)],
        per_message=False,allow_reentry=True,
    ))
    logger.info("🤖 Bot កំពុង Start..."); app.run_polling(allowed_updates=Update.ALL_TYPES,poll_interval=1.0,drop_pending_updates=True)
if __name__=="__main__": main()
