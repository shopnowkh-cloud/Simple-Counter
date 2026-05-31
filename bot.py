#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,io,re,math,base64,random,logging,warnings,hashlib,qrcode,cv2,numpy as np
from PIL import Image; from pyzbar.pyzbar import decode as pyzbar_decode; from fpdf import FPDF
from datetime import datetime,date; from dateutil.relativedelta import relativedelta
from telegram import Update,InlineKeyboardButton as IKB,InlineKeyboardMarkup,InputFile
from telegram.ext import Application,CommandHandler,MessageHandler,CallbackQueryHandler,ConversationHandler,ContextTypes,filters
from telegram.constants import ParseMode; from telegram.warnings import PTBUserWarning
warnings.filterwarnings("ignore",category=PTBUserWarning)
BOT_TOKEN=os.environ.get("BOT_TOKEN","")
if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN មិនទាន់កំណត់!")
logging.basicConfig(format="%(asctime)s|%(levelname)s|%(message)s",level=logging.INFO)
logger=logging.getLogger(__name__)

(S_QR,S_SCAN,S_STYLE,S_PDF,S_CALC,S_PASS,S_PICK,S_MORSE,S_B64,
 S_COUNT,S_NBASE,S_TEMP,S_HASH,S_DATE)=range(14)
H=ParseMode.HTML; END=ConversationHandler.END

# ── keyboards ───────────────────────────────────────────────────────────────────
def mkb(*r): return InlineKeyboardMarkup(list(r))
def bb(): return mkb([IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")])
def bc(): return mkb([IKB("❌ បោះបង់",callback_data="back_main")])
def mm():
    return mkb(
        [IKB("📷 បង្កើត QR Code",callback_data="menu_qr_create"), IKB("🔍 Scan QR Code",callback_data="menu_qr_scan")],
        [IKB("✍️ រចនាប័ទ្មអក្សរ",callback_data="menu_text_style"), IKB("🖼️ រូបភាព → PDF",callback_data="menu_photo_pdf")],
        [IKB("🔢 ម៉ាស៊ីនគណនា",callback_data="menu_calculator"),  IKB("🔐 ពិនិត្យ Password",callback_data="menu_password")],
        [IKB("🎲 Random Picker",callback_data="menu_picker"),       IKB("📡 កូដ Morse",callback_data="menu_morse")],
        [IKB("🔒 Base64",callback_data="menu_base64"),              IKB("📝 រាប់អក្សរ",callback_data="menu_count")],
        [IKB("🔢 ប្ដូរលេខ",callback_data="menu_nbase"),            IKB("🌡️ ប្ដូរសីតុណ្ហភាព",callback_data="menu_temp")],
        [IKB("#️⃣ Hash Generator",callback_data="menu_hash"),       IKB("📅 គណនាអាយុ",callback_data="menu_date")],
        [IKB("ℹ️ អំពី Bot",callback_data="menu_about")]
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
MO={"A":".-","B":"-...","C":"-.-.","D":"-..","E":".","F":"..-.","G":"--.","H":"....","I":"..","J":".---","K":"-.-","L":".-..","M":"--","N":"-.","O":"---","P":".--.","Q":"--.-","R":".-.","S":"...","T":"-","U":"..-","V":"...-","W":".--","X":"-..-","Y":"-.--","Z":"--..","0":"-----","1":".----","2":"..---","3":"...--","4":"....-","5":".....","6":"-....","7":"--...","8":"---..","9":"----."," ":"/"}
MR={v:k for k,v in MO.items()}
def t2m(t): return " ".join(MO.get(c.upper(),"?") for c in t)
def m2t(m): return "".join(MR.get(w,"?") for w in m.strip().split(" "))

KH_DAYS=["ច័ន្ទ","អង្គារ","ពុធ","ព្រហស្បតិ៍","សុក្រ","សៅរ៍","អាទិត្យ"]
KH_MONTHS=["មករា","កុម្ភៈ","មីនា","មេសា","ឧសភា","មិថុនា","កក្កដា","សីហា","កញ្ញា","តុលា","វិច្ឆិកា","ធ្នូ"]

# ── /start ──────────────────────────────────────────────────────────────────────
async def cmd_start(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    msg=await u.message.reply_text(
        f"👋 សួស្ដី <b>{u.effective_user.first_name}</b>!\n\n"
        "🤖 ខ្ញុំជា <b>Khmer Multi-Tool Bot</b> 🇰🇭\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📷 QR Code • 🔍 Scan QR • ✍️ Style អក្សរ\n"
        "🖼️ PDF • 🔢 គណនា • 🔐 Password\n"
        "🎲 Random • 📡 Morse • 🔒 Base64\n"
        "📝 រាប់អក្សរ • 🔢 ប្ដូរលេខ • 🌡️ សីតុណ្ហភាព\n"
        "#️⃣ Hash • 📅 គណនាអាយុ\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👇 សូមជ្រើសរើសមុខងារ៖",
        reply_markup=mm(),parse_mode=H)
    _save(ctx,msg); return END

# ── callback router ─────────────────────────────────────────────────────────────
async def cb(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=u.callback_query; await q.answer(); d=q.data
    ctx.user_data["cid"]=q.message.chat_id; ctx.user_data["mid"]=q.message.message_id

    if d=="back_main":
        await q.edit_message_text("🏠 <b>ម៉ឺនុយមេ</b>\n\n👇 សូមជ្រើសរើសមុខងារ៖",reply_markup=mm(),parse_mode=H); return END
    if d=="menu_qr_create":
        await q.edit_message_text("📷 <b>បង្កើត QR Code</b>\n\n✏️ សូមវាយ Text/Link ចង់បំប្លែង៖",reply_markup=bc(),parse_mode=H); return S_QR
    if d=="menu_qr_scan":
        await q.edit_message_text("🔍 <b>Scan QR Code</b>\n\n📤 សូម Upload រូបភាព QR Code៖",reply_markup=bc(),parse_mode=H); return S_SCAN
    if d=="menu_text_style":
        await q.edit_message_text("✍️ <b>រចនាប័ទ្មអក្សរ</b>\n\n✏️ សូមវាយ <b>អក្សរឡាតាំង</b>៖\n<i>⚠️ ដំណើរការល្អជាមួយ a-z A-Z 0-9</i>",reply_markup=bc(),parse_mode=H); return S_STYLE
    if d=="menu_photo_pdf":
        ctx.user_data["pdf_photos"]=[]
        await q.edit_message_text("🖼️ <b>រូបភាព → PDF</b>\n\n📤 Upload រូបភាព (អាចច្រើន)\n✅ ចប់ → ចុច <b>បង្កើត PDF</b>",reply_markup=mkb([IKB("✅ បង្កើត PDF",callback_data="pdf_done"),IKB("❌ បោះបង់",callback_data="back_main")]),parse_mode=H); return S_PDF
    if d=="menu_calculator":
        ctx.user_data["calc_expr"]=""; await _calc_show(q,ctx); return S_CALC
    if d=="menu_password":
        await q.edit_message_text("🔐 <b>ពិនិត្យ Password</b>\n\n✏️ សូមវាយ Password ចង់ពិនិត្យ៖",reply_markup=bc(),parse_mode=H); return S_PASS
    if d=="menu_picker":
        await q.edit_message_text("🎲 <b>Random Picker</b>\n\n✏️ វាយជម្រើសដោយដាក់ , ចន្លោះ៖\n<code>ក, ខ, គ, ឃ</code>",reply_markup=bc(),parse_mode=H); return S_PICK
    if d=="menu_morse":
        await q.edit_message_text("📡 <b>កូដ Morse</b>\n\nសូមជ្រើសរើសទិសដៅ៖",reply_markup=mkb([IKB("🔤 អក្សរ → Morse",callback_data="morse_to"),IKB("📡 Morse → អក្សរ",callback_data="morse_from")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]),parse_mode=H); return S_MORSE
    if d=="morse_to":   ctx.user_data["morse_dir"]="to";   await q.edit_message_text("📡 <b>អក្សរ → Morse</b>\n\n✏️ សូមវាយអក្សរ (English)៖",reply_markup=bc(),parse_mode=H); return S_MORSE
    if d=="morse_from": ctx.user_data["morse_dir"]="from"; await q.edit_message_text("📡 <b>Morse → អក្សរ</b>\n\n✏️ សូមវាយ Morse Code៖\n<code>-- --- .-. ... .</code>",reply_markup=bc(),parse_mode=H); return S_MORSE
    if d=="menu_base64":
        await q.edit_message_text("🔒 <b>Base64</b>\n\nសូមជ្រើសរើស៖",reply_markup=mkb([IKB("🔐 Encode",callback_data="b64_encode"),IKB("🔓 Decode",callback_data="b64_decode")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]),parse_mode=H); return S_B64
    if d=="b64_encode": ctx.user_data["b64_dir"]="encode"; await q.edit_message_text("🔐 <b>Base64 Encode</b>\n\n✏️ សូមវាយ Text ត្រូវ Encode៖",reply_markup=bc(),parse_mode=H); return S_B64
    if d=="b64_decode": ctx.user_data["b64_dir"]="decode"; await q.edit_message_text("🔓 <b>Base64 Decode</b>\n\n✏️ សូមវាយ Base64 ត្រូវ Decode៖",reply_markup=bc(),parse_mode=H); return S_B64
    # ── New features ──
    if d=="menu_count":
        await q.edit_message_text("📝 <b>រាប់អក្សរ</b>\n\n✏️ សូមវាយ ឬ បិទ​ភ្ជាប់ Text ណាមួយ៖",reply_markup=bc(),parse_mode=H); return S_COUNT
    if d=="menu_nbase":
        await q.edit_message_text("🔢 <b>ប្ដូរគោលលេខ</b>\n\nសូមជ្រើសរើស Input ៖",reply_markup=mkb([IKB("🔟 លេខ10",callback_data="nbase_dec"),IKB("2️⃣ លេខ2",callback_data="nbase_bin")],[IKB("8️⃣ លេខ8",callback_data="nbase_oct"),IKB("🔡 Hex",callback_data="nbase_hex")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]),parse_mode=H); return S_NBASE
    if d in("nbase_dec","nbase_bin","nbase_oct","nbase_hex"):
        nm={"nbase_dec":"លេខ១០","nbase_bin":"លេខ២","nbase_oct":"លេខ៨","nbase_hex":"Hex"}
        ctx.user_data["nbase_from"]=d.split("_")[1]
        await q.edit_message_text(f"🔢 <b>ប្ដូរពី {nm[d]}</b>\n\n✏️ សូមវាយលេខ៖",reply_markup=bc(),parse_mode=H); return S_NBASE
    if d=="menu_temp":
        await q.edit_message_text("🌡️ <b>ប្ដូរសីតុណ្ហភាព</b>\n\nសូមជ្រើស Input ៖",reply_markup=mkb([IKB("🌡 Celsius (°C)",callback_data="temp_c"),IKB("🌡 Fahrenheit (°F)",callback_data="temp_f")],[IKB("🌡 Kelvin (K)",callback_data="temp_k")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]),parse_mode=H); return S_TEMP
    if d in("temp_c","temp_f","temp_k"):
        ctx.user_data["temp_from"]=d.split("_")[1]
        lbl={"temp_c":"Celsius °C","temp_f":"Fahrenheit °F","temp_k":"Kelvin K"}
        await q.edit_message_text(f"🌡️ <b>ប្ដូរពី {lbl[d]}</b>\n\n✏️ សូមវាយតម្លៃសីតុណ្ហភាព (លេខ)៖",reply_markup=bc(),parse_mode=H); return S_TEMP
    if d=="menu_hash":
        await q.edit_message_text("#️⃣ <b>Hash Generator</b>\n\n✏️ សូមវាយ Text ចង់ Hash៖",reply_markup=bc(),parse_mode=H); return S_HASH
    if d=="menu_date":
        await q.edit_message_text("📅 <b>គណនាអាយុ / ថ្ងៃ</b>\n\n✏️ វាយថ្ងៃខែឆ្នាំកំណើត (ទ្រង់ទ្រាយ):\n<code>DD/MM/YYYY</code>\nឧទាហរណ៍: <code>15/06/1995</code>",reply_markup=bc(),parse_mode=H); return S_DATE
    if d=="menu_about":
        await q.edit_message_text(
            f"ℹ️ <b>Khmer Multi-Tool Bot v3.0</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
            "👨‍💻 អ្នកបង្កើត: <b>limsovannrady</b>\n"
            "🐍 python-telegram-bot <b>21.x</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📦 qrcode • pyzbar • fpdf2 • Pillow\n"
            "   opencv • hashlib • dateutil",
            reply_markup=bb(),parse_mode=H); return END
    if d.startswith("calc_"): return await _calc_btn(q,ctx,d)
    if d.startswith("copy_style_"):
        sk=d[11:]; orig=ctx.user_data.get("style_original","")
        if orig and sk in TS:
            styled=TS[sk][1](orig); await q.answer(f"✅ បានចម្លង: {styled[:15]}...",show_alert=True)
            await q.message.reply_text(f"<code>{styled}</code>",parse_mode=H)
        return S_STYLE
    if d=="pdf_done": return await _pdf_build(q,ctx)
    return END

# ── QR create ───────────────────────────────────────────────────────────────────
async def qr_input(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip()
    if not t: await _edit(ctx,"⚠️ សូមវាយអ្វីមួយ!",bc()); return S_QR
    await _edit(ctx,"⏳ <b>កំពុងបង្កើត QR Code...</b>"); await u.message.delete()
    qr=qrcode.QRCode(version=None,error_correction=qrcode.constants.ERROR_CORRECT_H,box_size=12,border=4)
    qr.add_data(t); qr.make(fit=True); img=qr.make_image(fill_color="#0A0A0A",back_color="#FFFFFF").convert("RGB")
    buf=io.BytesIO(); img.save(buf,format="PNG"); buf.seek(0)
    msg=await u.message.reply_photo(photo=buf,caption=f"✅ <b>QR Code បង្កើតជោគជ័យ!</b>\n📝 <code>{t[:200]}</code>\n📐 {img.size[0]}×{img.size[1]}px",reply_markup=mkb([IKB("🔄 QR Code ថ្មី",callback_data="menu_qr_create")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]),parse_mode=H)
    _save(ctx,msg); return END

# ── QR scan ─────────────────────────────────────────────────────────────────────
async def qr_scan(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    p=u.message.photo[-1] if u.message.photo else None; dc=u.message.document if u.message.document else None
    if not p and not dc: await _edit(ctx,"⚠️ <b>សូម Upload រូបភាព QR Code!</b>",bc()); return S_SCAN
    await _edit(ctx,"⏳ <b>កំពុង Scan QR Code...</b>")
    f=await ctx.bot.get_file(p.file_id if p else dc.file_id); raw=await f.download_as_bytearray()
    cv_img=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
    dec=pyzbar_decode(Image.fromarray(cv2.cvtColor(cv_img,cv2.COLOR_BGR2RGB)))
    if not dec: await _edit(ctx,"❌ <b>រក QR Code មិនឃើញ!</b>\n\n💡 ប្រើរូបភាពច្បាស់ • QR ត្រូវឃើញពេញ",mkb([IKB("🔄 ព្យាយាមម្ដងទៀត",callback_data="menu_qr_scan")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")])); return END
    res=[f"<b>#{i}</b> [{d.type}]\n<code>{d.data.decode('utf-8','replace')[:300]}</code>" for i,d in enumerate(dec,1)]
    await _edit(ctx,f"✅ <b>Scan ជោគជ័យ! រក QR បាន {len(dec)} ចំនួន</b>\n\n"+"\n\n".join(res),mkb([IKB("🔄 Scan ថ្មី",callback_data="menu_qr_scan"),IKB("📷 បង្កើត QR",callback_data="menu_qr_create")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")])); return END

# ── Text style ──────────────────────────────────────────────────────────────────
async def text_style(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip()
    if not t: await _edit(ctx,"⚠️ សូមវាយអ្វីមួយ!",bc()); return S_STYLE
    await u.message.delete(); ctx.user_data["style_original"]=t
    rows=[f"<b>{lbl}:</b>\n{fn(t)}" for _,(lbl,fn) in TS.items()]
    ks=list(TS.keys()); btns=[[IKB(f"📋 {TS[ks[i]][0]}",callback_data=f"copy_style_{ks[i]}") for i in range(j,min(j+2,len(ks)))] for j in range(0,len(ks),2)]
    btns+=[[IKB("✍️ ដំណើរការថ្មី",callback_data="menu_text_style")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]]
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
    msg=await q.message.reply_document(document=InputFile(buf,filename="KhmerBot.pdf"),caption=f"✅ <b>PDF បង្កើតជោគជ័យ!</b>\n🖼️ ចំនួន {len(photos)} ទំព័រ",reply_markup=mkb([IKB("🖼️ PDF ថ្មី",callback_data="menu_photo_pdf")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]),parse_mode=H)
    _save(ctx,msg); ctx.user_data["pdf_photos"]=[]; return END

# ── Calculator ──────────────────────────────────────────────────────────────────
CB=[["C","±","%","÷"],["7","8","9","×"],["4","5","6","−"],["1","2","3","+"],[" 0",".","⌫","="]]
async def _calc_show(qm,ctx,ans=None):
    e=ctx.user_data.get("calc_expr",""); dp=ans or(e[-30:] if e else "0")
    kb=InlineKeyboardMarkup([[IKB(b,callback_data=f"calc_{b.strip()}") for b in r] for r in CB]+[[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]])
    t=f"🔢 <b>ម៉ាស៊ីនគណនា</b>\n━━━━━━━━━━━━\n<code> {dp}</code>\n━━━━━━━━━━━━"
    if hasattr(qm,"edit_message_text"): await qm.edit_message_text(t,reply_markup=kb,parse_mode=H)

async def _calc_btn(q,ctx,data):
    b=data[5:]; e=ctx.user_data.get("calc_expr","")
    if b=="C": ctx.user_data["calc_expr"]=""; await _calc_show(q,ctx); return S_CALC
    if b=="⌫": ctx.user_data["calc_expr"]=e[:-1]; await _calc_show(q,ctx); return S_CALC
    if b=="±": ctx.user_data["calc_expr"]=e[1:] if e and e[0]=="-" else("-"+e if e else e); await _calc_show(q,ctx); return S_CALC
    if b=="=":
        try:
            r=eval(re.sub(r'(\d)%',r'(\1/100)',e.replace("÷","/").replace("×","*").replace("−","-")),{"__builtins__":{}})
            r=int(r) if isinstance(r,float) and r.is_integer() else r; ctx.user_data["calc_expr"]=str(r); await _calc_show(q,ctx,ans=f"{e}={r}")
        except: ctx.user_data["calc_expr"]=""; await _calc_show(q,ctx,ans="❌ មានបញ្ហា!")
        return S_CALC
    ctx.user_data["calc_expr"]=e+b; await _calc_show(q,ctx); return S_CALC

# ── Password ────────────────────────────────────────────────────────────────────
async def pw_check(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    pw=u.message.text; await u.message.delete()
    ck={"ល8":(len(pw)>=8,"✅ ≥8 តួអក្សរ","❌ តិចជាង 8 តួ"),"ល12":(len(pw)>=12,"✅ ≥12 តួអក្សរ",None),"ធC":(bool(re.search(r"[A-Z]",pw)),"✅ មានអក្សរធំ","❌ គ្មានអក្សរធំ"),"តc":(bool(re.search(r"[a-z]",pw)),"✅ មានអក្សរតូច","❌ គ្មានអក្សរតូច"),"លx":(bool(re.search(r"\d",pw)),"✅ មានលេខ","❌ គ្មានលេខ"),"ស#":(bool(re.search(r"[^A-Za-z0-9]",pw)),"✅ មានសញ្ញា","❌ គ្មានសញ្ញា")}
    passed=sum(1 for _,(ok,_,_) in ck.items() if ok); issues=[g if ok else b for _,(ok,g,b) in ck.items() if b]
    lv,em=("ខ្សោយ","🔴") if passed<=2 else("មធ្យម","🟡") if passed<=4 else("ល្អ","🟢") if passed==5 else("ខ្លាំងណាស់","🟢✨")
    ent=round(math.log2(len(set(pw)))*len(pw),1) if len(set(pw))>1 else 0
    await _edit(ctx,f"🔐 <b>លទ្ធផលពិនិត្យ Password</b>\n━━━━━━━━━━━━\n🔑 <tg-spoiler>{'•'*len(pw)}</tg-spoiler>\n━━━━━━━━━━━━\n{em} <b>កម្រិត:</b> {lv} | {passed}/6 ពិន្ទុ | {ent}b\n━━━━━━━━━━━━\n"+"\n".join(issues),mkb([IKB("🔄 ពិនិត្យ Password ថ្មី",callback_data="menu_password")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")])); return END

# ── Random Picker ───────────────────────────────────────────────────────────────
async def picker(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    items=[x.strip() for x in u.message.text.strip().split(",") if x.strip()]; await u.message.delete()
    if len(items)<2: await _edit(ctx,"⚠️ <b>ត្រូវការ ≥2 ជម្រើស!</b>\nដាក់ , ចន្លោះ: <code>ក, ខ, គ</code>",bc()); return S_PICK
    c=random.choice(items); rk=random.sample(items,len(items))
    await _edit(ctx,f"🎲 <b>Random Picker</b>\n━━━━━━━━━━━━\n🏆 <b>ជ្រើសបាន:</b> <code>{c}</code>\n━━━━━━━━━━━━\n📋 <b>លំដាប់ Random:</b>\n"+"\n".join(f"  {i}. {x}" for i,x in enumerate(rk,1)),mkb([IKB("🔄 Random ម្ដងទៀត",callback_data="menu_picker")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")])); return END

# ── Morse ───────────────────────────────────────────────────────────────────────
async def morse(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip(); d=ctx.user_data.get("morse_dir","to"); await u.message.delete()
    r,h,lb=(t2m(t),"អក្សរ → Morse","Morse") if d=="to" else(m2t(t),"Morse → អក្សរ","អក្សរ")
    await _edit(ctx,f"📡 <b>{h}</b>\n━━━━━━━━━━━━\n📥 Input: <code>{t[:200]}</code>\n📤 {lb}: <code>{r[:500]}</code>",mkb([IKB("🔄 ថ្មី",callback_data="menu_morse")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")])); return END

# ── Base64 ──────────────────────────────────────────────────────────────────────
async def b64(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip(); d=ctx.user_data.get("b64_dir","encode"); await u.message.delete()
    try: r=base64.b64encode(t.encode()).decode() if d=="encode" else base64.b64decode(t.encode()).decode(); h="Encode" if d=="encode" else"Decode"; err=False
    except Exception as e: r=str(e); h="Error"; err=True
    em="🔐" if d=="encode" else"🔓"
    await _edit(ctx,f"{em} <b>Base64 {h}</b>\n━━━━━━━━━━━━\n📥 Input:\n<code>{t[:200]}</code>\n\n{'❌' if err else '📤'} លទ្ធផល:\n<code>{r[:1000]}</code>",mkb([IKB("🔄 Base64 ថ្មី",callback_data="menu_base64")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")])); return END

# ── Text Counter (NEW) ──────────────────────────────────────────────────────────
async def count_text(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text; await u.message.delete()
    chars=len(t); chars_no_space=len(t.replace(" ","").replace("\n",""))
    words=len(t.split()); lines=t.count("\n")+1
    sentences=len(re.findall(r'[.!?។]+',t)) or 0
    emojis=len(re.findall(r'[\U0001F000-\U0001FFFF]|[\U00002600-\U000027FF]',t))
    khmer=len(re.findall(r'[\u1780-\u17FF]',t))
    latin=len(re.findall(r'[a-zA-Z]',t))
    digits=len(re.findall(r'\d',t))
    size_b=len(t.encode('utf-8'))
    await _edit(ctx,
        f"📝 <b>លទ្ធផលរាប់អក្សរ</b>\n━━━━━━━━━━━━\n"
        f"🔤 តួអក្សរ (សរុប): <b>{chars:,}</b>\n"
        f"🔡 តួអក្សរ (គ្មានចន្លោះ): <b>{chars_no_space:,}</b>\n"
        f"📖 ពាក្យ: <b>{words:,}</b>\n"
        f"📄 បន្ទាត់: <b>{lines:,}</b>\n"
        f"❓ ប្រយោគ: <b>{sentences}</b>\n"
        f"━━━━━━━━━━━━\n"
        f"🇰🇭 អក្សរខ្មែរ: <b>{khmer:,}</b>\n"
        f"🔤 Latin: <b>{latin:,}</b>\n"
        f"🔢 លេខ: <b>{digits:,}</b>\n"
        f"😊 Emoji: <b>{emojis}</b>\n"
        f"💾 ទំហំ: <b>{size_b:,} bytes</b>",
        mkb([IKB("🔄 រាប់អក្សរថ្មី",callback_data="menu_count")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")])); return END

# ── Number Base Converter (NEW) ─────────────────────────────────────────────────
async def nbase_convert(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip(); frm=ctx.user_data.get("nbase_from","dec"); await u.message.delete()
    try:
        base_map={"dec":10,"bin":2,"oct":8,"hex":16}; b=base_map[frm]
        n=int(t,b)
        await _edit(ctx,
            f"🔢 <b>លទ្ធផលប្ដូរគោលលេខ</b>\n━━━━━━━━━━━━\n"
            f"📥 Input ({frm.upper()}): <code>{t}</code>\n"
            f"━━━━━━━━━━━━\n"
            f"🔟 លេខ១០ (Decimal):  <code>{n}</code>\n"
            f"2️⃣ លេខ២ (Binary):   <code>{bin(n)[2:]}</code>\n"
            f"8️⃣ លេខ៨ (Octal):    <code>{oct(n)[2:]}</code>\n"
            f"🔡 Hex:              <code>{hex(n)[2:].upper()}</code>",
            mkb([IKB("🔄 ប្ដូរថ្មី",callback_data="menu_nbase")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]))
    except: await _edit(ctx,"❌ <b>លេខមិនត្រឹមត្រូវ!</b>\nសូមវាយឡើងវិញ",bc())
    return END

# ── Temperature Converter (NEW) ─────────────────────────────────────────────────
async def temp_convert(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip(); frm=ctx.user_data.get("temp_from","c"); await u.message.delete()
    try:
        v=float(t)
        if frm=="c":   c,f,k=v,v*9/5+32,v+273.15
        elif frm=="f": c,f,k=(v-32)*5/9,v,(v-32)*5/9+273.15
        else:          c,f,k=v-273.15,(v-273.15)*9/5+32,v
        await _edit(ctx,
            f"🌡️ <b>លទ្ធផលប្ដូរសីតុណ្ហភាព</b>\n━━━━━━━━━━━━\n"
            f"🌡 Celsius:    <b>{c:.2f} °C</b>\n"
            f"🌡 Fahrenheit: <b>{f:.2f} °F</b>\n"
            f"🌡 Kelvin:     <b>{k:.2f} K</b>\n"
            f"━━━━━━━━━━━━\n"
            f"{'🥶 ត្រជាក់ខ្លាំង' if c<0 else '❄️ ត្រជាក់' if c<15 else '😊 ធម្មតា' if c<28 else '☀️ ក្ដៅ' if c<38 else '🔥 ក្ដៅខ្លាំងណាស់'}",
            mkb([IKB("🔄 ប្ដូរថ្មី",callback_data="menu_temp")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]))
    except: await _edit(ctx,"❌ <b>លេខមិនត្រឹមត្រូវ!</b>\nសូមវាយឡើងវិញ",bc())
    return END

# ── Hash Generator (NEW) ────────────────────────────────────────────────────────
async def hash_gen(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip(); await u.message.delete()
    enc=t.encode()
    md5=hashlib.md5(enc).hexdigest()
    sha1=hashlib.sha1(enc).hexdigest()
    sha256=hashlib.sha256(enc).hexdigest()
    sha512=hashlib.sha512(enc).hexdigest()[:32]+"..."
    await _edit(ctx,
        f"#️⃣ <b>Hash Generator</b>\n━━━━━━━━━━━━\n"
        f"📝 Input: <code>{t[:80]}</code>\n"
        f"━━━━━━━━━━━━\n"
        f"🔵 MD5:\n<code>{md5}</code>\n\n"
        f"🟢 SHA-1:\n<code>{sha1}</code>\n\n"
        f"🟡 SHA-256:\n<code>{sha256}</code>\n\n"
        f"🔴 SHA-512 (32):\n<code>{sha512}</code>",
        mkb([IKB("🔄 Hash ថ្មី",callback_data="menu_hash")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")])); return END

# ── Date / Age Calculator (NEW) ─────────────────────────────────────────────────
async def date_calc(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip(); await u.message.delete()
    try:
        bday=datetime.strptime(t,"%d/%m/%Y").date(); today=date.today()
        if bday>today: raise ValueError
        rd=relativedelta(today,bday)
        age_y,age_m,age_d=rd.years,rd.months,rd.days
        total_days=(today-bday).days
        day_name=KH_DAYS[bday.weekday()]
        month_name=KH_MONTHS[bday.month-1]
        next_bday=bday.replace(year=today.year) if bday.replace(year=today.year)>=today else bday.replace(year=today.year+1)
        days_to_bday=(next_bday-today).days
        await _edit(ctx,
            f"📅 <b>លទ្ធផលគណនាអាយុ</b>\n━━━━━━━━━━━━\n"
            f"🎂 ថ្ងៃខែឆ្នាំ: <b>{bday.day} {month_name} {bday.year}</b>\n"
            f"📆 ថ្ងៃ: <b>{day_name}</b>\n"
            f"━━━━━━━━━━━━\n"
            f"🎉 អាយុ: <b>{age_y} ឆ្នាំ {age_m} ខែ {age_d} ថ្ងៃ</b>\n"
            f"📊 សរុបថ្ងៃ: <b>{total_days:,} ថ្ងៃ</b>\n"
            f"⏳ ខួបកំណើតទៀត: <b>{days_to_bday} ថ្ងៃ</b>",
            mkb([IKB("🔄 គណនាថ្មី",callback_data="menu_date")],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main")]))
    except: await _edit(ctx,"❌ <b>ទ្រង់ទ្រាយខុស!</b>\nសូមវាយ: <code>DD/MM/YYYY</code>\nឧ: <code>15/06/1995</code>",bc())
    return END

# ── Fallback ────────────────────────────────────────────────────────────────────
async def fallback(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    try: await u.message.delete()
    except: pass
    await _edit(ctx,"🤔 <b>ខ្ញុំមិនយល់!</b>\n\n👇 សូមជ្រើសរើស ឬ វាយ /start",mm())

# ── main ────────────────────────────────────────────────────────────────────────
def main():
    app=Application.builder().token(BOT_TOKEN).connect_timeout(10).read_timeout(30).write_timeout(30).pool_timeout(10).build()
    TXT=filters.TEXT&~filters.COMMAND; IMG=filters.PHOTO|filters.Document.IMAGE; CB_H=CallbackQueryHandler(cb)
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start",cmd_start),CB_H],
        states={
            S_QR:    [MessageHandler(TXT,qr_input),   CB_H],
            S_SCAN:  [MessageHandler(IMG,qr_scan),    CB_H],
            S_STYLE: [MessageHandler(TXT,text_style), CB_H],
            S_PDF:   [MessageHandler(IMG,pdf_photo),  CB_H],
            S_CALC:  [CB_H],
            S_PASS:  [MessageHandler(TXT,pw_check),   CB_H],
            S_PICK:  [MessageHandler(TXT,picker),     CB_H],
            S_MORSE: [MessageHandler(TXT,morse),      CB_H],
            S_B64:   [MessageHandler(TXT,b64),        CB_H],
            S_COUNT: [MessageHandler(TXT,count_text), CB_H],
            S_NBASE: [MessageHandler(TXT,nbase_convert),CB_H],
            S_TEMP:  [MessageHandler(TXT,temp_convert), CB_H],
            S_HASH:  [MessageHandler(TXT,hash_gen),   CB_H],
            S_DATE:  [MessageHandler(TXT,date_calc),  CB_H],
        },
        fallbacks=[CommandHandler("start",cmd_start),MessageHandler(filters.ALL,fallback)],
        per_message=False,allow_reentry=True,
    ))
    logger.info("🤖 Bot កំពុង Start..."); app.run_polling(allowed_updates=Update.ALL_TYPES,poll_interval=1.0,drop_pending_updates=True)
if __name__=="__main__": main()
