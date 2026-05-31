#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,io,re,math,base64,random,string,logging,warnings,hashlib,qrcode,cv2,numpy as np
from PIL import Image; from pyzbar.pyzbar import decode as pyzbar_decode; from fpdf import FPDF
from datetime import datetime,date,timezone; from dateutil.relativedelta import relativedelta
import zoneinfo
from telegram import Update,InlineKeyboardButton as IKB,InlineKeyboardMarkup,InputFile
from telegram.ext import Application,CommandHandler,MessageHandler,CallbackQueryHandler,ConversationHandler,ContextTypes,filters
from telegram.constants import ParseMode,KeyboardButtonStyle as KBS; from telegram.warnings import PTBUserWarning
PRIMARY=KBS.PRIMARY; SUCCESS=KBS.SUCCESS; DANGER=KBS.DANGER
warnings.filterwarnings("ignore",category=PTBUserWarning)
BOT_TOKEN=os.environ.get("BOT_TOKEN","")
if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN មិនទាន់កំណត់!")
logging.basicConfig(format="%(asctime)s|%(levelname)s|%(message)s",level=logging.INFO)
logger=logging.getLogger(__name__)

(S_QR,S_SCAN,S_STYLE,S_PDF,S_CALC,S_PASS,S_PICK,S_MORSE,S_B64,
 S_COUNT,S_NBASE,S_TEMP,S_HASH,S_DATE,S_UNIT,S_BMI,S_LOAN,S_LUCK)=range(18)
H=ParseMode.HTML; END=ConversationHandler.END

# ── keyboards ───────────────────────────────────────────────────────────────────
def mkb(*r): return InlineKeyboardMarkup(list(r))
def bb(): return mkb([IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main",style=PRIMARY)])
def bc(): return mkb([IKB("❌ បោះបង់",callback_data="back_main",style=DANGER)])
HOME=[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main",style=PRIMARY)]
def _qr_nav(excl=None):
    b=[IKB("📷 QR Create",callback_data="menu_qr_create",style=PRIMARY),IKB("🔍 QR Scan",callback_data="menu_qr_scan",style=PRIMARY)]
    r=[x for x in b if x.callback_data!=excl]; return [r] if r else []
def _text_nav(excl=None):
    b=[IKB("✍️ Style",callback_data="menu_text_style"),IKB("🖼️ PDF",callback_data="menu_photo_pdf"),IKB("📝 Count",callback_data="menu_count"),IKB("📡 Morse",callback_data="menu_morse")]
    r=[x for x in b if x.callback_data!=excl]; return [r[i:i+2] for i in range(0,len(r),2)]
def _math_nav(excl=None):
    b=[IKB("🔢 Calc",callback_data="menu_calculator",style=SUCCESS),IKB("🌡️ Temp",callback_data="menu_temp",style=SUCCESS),IKB("🔢 Base",callback_data="menu_nbase",style=SUCCESS),IKB("📏 Unit",callback_data="menu_unit",style=SUCCESS),IKB("📐 BMI",callback_data="menu_bmi",style=SUCCESS),IKB("💰 Loan",callback_data="menu_loan",style=SUCCESS)]
    r=[x for x in b if x.callback_data!=excl]; return [r[i:i+3] for i in range(0,len(r),3)]
def _sec_nav(excl=None):
    b=[IKB("🔐 PW Check",callback_data="menu_password",style=DANGER),IKB("🔑 PW Gen",callback_data="menu_genpass",style=DANGER),IKB("🔒 Base64",callback_data="menu_base64",style=DANGER),IKB("#️⃣ Hash",callback_data="menu_hash",style=DANGER)]
    r=[x for x in b if x.callback_data!=excl]; return [r[i:i+2] for i in range(0,len(r),2)]
def _fun_nav(excl=None):
    b=[IKB("🎲 Picker",callback_data="menu_picker",style=SUCCESS),IKB("🎰 Dice",callback_data="menu_dice",style=SUCCESS),IKB("⏰ Clock",callback_data="menu_wclock",style=SUCCESS),IKB("📅 អាយុ",callback_data="menu_date",style=SUCCESS)]
    r=[x for x in b if x.callback_data!=excl]; return [r[i:i+2] for i in range(0,len(r),2)]
def mm():
    return mkb(
        # ── 🔵 QR Tools ──
        [IKB("╔═ 🔵 QR TOOLS ══════════╗",callback_data="noop",style=PRIMARY)],
        [IKB("📷 បង្កើត QR Code",callback_data="menu_qr_create",style=PRIMARY), IKB("🔍 Scan QR Code",callback_data="menu_qr_scan",style=PRIMARY)],
        # ── 🟣 Text & Document ──
        [IKB("╠═ 🟣 TEXT & DOCUMENT ════╣",callback_data="noop")],
        [IKB("✍️ រចនាប័ទ្មអក្សរ",callback_data="menu_text_style"),  IKB("🖼️ រូបភាព → PDF",callback_data="menu_photo_pdf")],
        [IKB("📝 រាប់អក្សរ",callback_data="menu_count"),             IKB("📡 កូដ Morse",callback_data="menu_morse")],
        # ── 🟢 Math & Convert ──
        [IKB("╠═ 🟢 MATH & CONVERT ═════╣",callback_data="noop",style=SUCCESS)],
        [IKB("🔢 ម៉ាស៊ីនគណនា",callback_data="menu_calculator",style=SUCCESS),  IKB("🌡️ សីតុណ្ហភាព",callback_data="menu_temp",style=SUCCESS)],
        [IKB("🔢 ប្ដូរគោលលេខ",callback_data="menu_nbase",style=SUCCESS),       IKB("📏 ប្ដូរឯកតា",callback_data="menu_unit",style=SUCCESS)],
        [IKB("📐 BMI Calculator",callback_data="menu_bmi",style=SUCCESS),        IKB("💰 គណនាការប្រាក់",callback_data="menu_loan",style=SUCCESS)],
        # ── 🔴 Security ──
        [IKB("╠═ 🔴 SECURITY ════════════╣",callback_data="noop",style=DANGER)],
        [IKB("🔐 ពិនិត្យ Password",callback_data="menu_password",style=DANGER),  IKB("🔑 បង្កើត Password",callback_data="menu_genpass",style=DANGER)],
        [IKB("🔒 Base64",callback_data="menu_base64",style=DANGER),               IKB("#️⃣ Hash Generator",callback_data="menu_hash",style=DANGER)],
        # ── 🟡 Fun & Utility ──
        [IKB("╠═ 🟡 FUN & UTILITY ══════╣",callback_data="noop",style=SUCCESS)],
        [IKB("🎲 Random Picker",callback_data="menu_picker",style=SUCCESS),       IKB("🎰 Coin & Dice",callback_data="menu_dice",style=SUCCESS)],
        [IKB("⏰ World Clock",callback_data="menu_wclock",style=SUCCESS),          IKB("📅 គណនាអាយុ",callback_data="menu_date",style=SUCCESS)],
        # ── Info ──
        [IKB("╚═ ℹ️ អំពី Bot ══════════════╝",callback_data="menu_about",style=PRIMARY)],
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
        f"👋 សួស្ដី <b>{u.effective_user.first_name}</b>!\n"
        "┌─────────────────────────┐\n"
        "│  🤖 <b>Khmer Multi-Tool Bot</b> 🇰🇭  │\n"
        "└─────────────────────────┘\n"
        "🔵 QR Code  🟣 Text & Doc\n"
        "🟢 Math & Convert  🔴 Security\n"
        "🟡 Fun & Utility\n"
        "──────────────────────────\n"
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
            "┌─────────────────────────┐\n"
            "│  🤖 <b>Khmer Multi-Tool Bot</b> 🇰🇭  │\n"
            "└─────────────────────────┘\n"
            "🔵 QR Code  🟣 Text & Doc\n"
            "🟢 Math & Convert  🔴 Security\n"
            "🟡 Fun & Utility\n"
            "──────────────────────────\n"
            "👇 <b>ជ្រើសរើសប្រភេទ ហើយចុចប៊ូតុង</b>",
            reply_markup=mm(),parse_mode=H); return END
    if d=="menu_qr_create":
        await q.edit_message_text("📷 <b>បង្កើត QR Code</b>\n\n✏️ សូមវាយ Text/Link ចង់បំប្លែង៖",reply_markup=bc(),parse_mode=H); return S_QR
    if d=="menu_qr_scan":
        await q.edit_message_text("🔍 <b>Scan QR Code</b>\n\n📤 សូម Upload រូបភាព QR Code៖",reply_markup=bc(),parse_mode=H); return S_SCAN
    if d=="menu_text_style":
        await q.edit_message_text("✍️ <b>រចនាប័ទ្មអក្សរ</b>\n\n✏️ សូមវាយ <b>អក្សរឡាតាំង</b>៖\n<i>⚠️ ដំណើរការល្អជាមួយ a-z A-Z 0-9</i>",reply_markup=bc(),parse_mode=H); return S_STYLE
    if d=="menu_photo_pdf":
        ctx.user_data["pdf_photos"]=[]
        await q.edit_message_text("🖼️ <b>រូបភាព → PDF</b>\n\n📤 Upload រូបភាព (អាចច្រើន)\n✅ ចប់ → ចុច <b>បង្កើត PDF</b>",reply_markup=mkb([IKB("✅ បង្កើត PDF",callback_data="pdf_done",style=SUCCESS),IKB("❌ បោះបង់",callback_data="back_main",style=DANGER)]),parse_mode=H); return S_PDF
    if d=="menu_calculator":
        ctx.user_data["calc_expr"]=""; await _calc_show(q,ctx); return S_CALC
    if d=="menu_password":
        await q.edit_message_text("🔐 <b>ពិនិត្យ Password</b>\n\n✏️ សូមវាយ Password ចង់ពិនិត្យ៖",reply_markup=bc(),parse_mode=H); return S_PASS
    if d=="menu_picker":
        await q.edit_message_text("🎲 <b>Random Picker</b>\n\n✏️ វាយជម្រើសដោយដាក់ , ចន្លោះ៖\n<code>ក, ខ, គ, ឃ</code>",reply_markup=bc(),parse_mode=H); return S_PICK
    if d=="menu_morse":
        await q.edit_message_text("📡 <b>កូដ Morse</b>\n\nសូមជ្រើសរើសទិសដៅ៖",reply_markup=mkb([IKB("🔤 អក្សរ → Morse",callback_data="morse_to",style=PRIMARY),IKB("📡 Morse → អក្សរ",callback_data="morse_from",style=PRIMARY)],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main",style=PRIMARY)]),parse_mode=H); return S_MORSE
    if d=="morse_to":   ctx.user_data["morse_dir"]="to";   await q.edit_message_text("📡 <b>អក្សរ → Morse</b>\n\n✏️ សូមវាយអក្សរ (English)៖",reply_markup=bc(),parse_mode=H); return S_MORSE
    if d=="morse_from": ctx.user_data["morse_dir"]="from"; await q.edit_message_text("📡 <b>Morse → អក្សរ</b>\n\n✏️ សូមវាយ Morse Code៖\n<code>-- --- .-. ... .</code>",reply_markup=bc(),parse_mode=H); return S_MORSE
    if d=="menu_base64":
        await q.edit_message_text("🔒 <b>Base64</b>\n\nសូមជ្រើសរើស៖",reply_markup=mkb([IKB("🔐 Encode",callback_data="b64_encode",style=DANGER),IKB("🔓 Decode",callback_data="b64_decode",style=DANGER)],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main",style=PRIMARY)]),parse_mode=H); return S_B64
    if d=="b64_encode": ctx.user_data["b64_dir"]="encode"; await q.edit_message_text("🔐 <b>Base64 Encode</b>\n\n✏️ សូមវាយ Text ត្រូវ Encode៖",reply_markup=bc(),parse_mode=H); return S_B64
    if d=="b64_decode": ctx.user_data["b64_dir"]="decode"; await q.edit_message_text("🔓 <b>Base64 Decode</b>\n\n✏️ សូមវាយ Base64 ត្រូវ Decode៖",reply_markup=bc(),parse_mode=H); return S_B64
    if d=="menu_count":
        await q.edit_message_text("📝 <b>រាប់អក្សរ</b>\n\n✏️ សូមវាយ ឬ បិទ​ភ្ជាប់ Text ណាមួយ៖",reply_markup=bc(),parse_mode=H); return S_COUNT
    if d=="menu_nbase":
        await q.edit_message_text("🔢 <b>ប្ដូរគោលលេខ</b>\n\nសូមជ្រើសរើស Input ៖",reply_markup=mkb([IKB("🔟 លេខ10",callback_data="nbase_dec",style=SUCCESS),IKB("2️⃣ លេខ2",callback_data="nbase_bin",style=SUCCESS)],[IKB("8️⃣ លេខ8",callback_data="nbase_oct",style=SUCCESS),IKB("🔡 Hex",callback_data="nbase_hex",style=SUCCESS)],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main",style=PRIMARY)]),parse_mode=H); return S_NBASE
    if d in("nbase_dec","nbase_bin","nbase_oct","nbase_hex"):
        nm={"nbase_dec":"លេខ១០","nbase_bin":"លេខ២","nbase_oct":"លេខ៨","nbase_hex":"Hex"}
        ctx.user_data["nbase_from"]=d.split("_")[1]
        await q.edit_message_text(f"🔢 <b>ប្ដូរពី {nm[d]}</b>\n\n✏️ សូមវាយលេខ៖",reply_markup=bc(),parse_mode=H); return S_NBASE
    if d=="menu_temp":
        await q.edit_message_text("🌡️ <b>ប្ដូរសីតុណ្ហភាព</b>\n\nសូមជ្រើស Input ៖",reply_markup=mkb([IKB("🌡 Celsius (°C)",callback_data="temp_c",style=SUCCESS),IKB("🌡 Fahrenheit (°F)",callback_data="temp_f",style=SUCCESS)],[IKB("🌡 Kelvin (K)",callback_data="temp_k",style=SUCCESS)],[IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main",style=PRIMARY)]),parse_mode=H); return S_TEMP
    if d in("temp_c","temp_f","temp_k"):
        ctx.user_data["temp_from"]=d.split("_")[1]
        lbl={"temp_c":"Celsius °C","temp_f":"Fahrenheit °F","temp_k":"Kelvin K"}
        await q.edit_message_text(f"🌡️ <b>ប្ដូរពី {lbl[d]}</b>\n\n✏️ សូមវាយតម្លៃសីតុណ្ហភាព (លេខ)៖",reply_markup=bc(),parse_mode=H); return S_TEMP
    if d=="menu_hash":
        await q.edit_message_text("#️⃣ <b>Hash Generator</b>\n\n✏️ សូមវាយ Text ចង់ Hash៖",reply_markup=bc(),parse_mode=H); return S_HASH
    if d=="menu_date":
        await q.edit_message_text("📅 <b>គណនាអាយុ / ថ្ងៃ</b>\n\n✏️ វាយថ្ងៃខែឆ្នាំកំណើត (ទ្រង់ទ្រាយ):\n<code>DD/MM/YYYY</code>\nឧទាហរណ៍: <code>15/06/1995</code>",reply_markup=bc(),parse_mode=H); return S_DATE

    # ── Password Generator ──
    if d=="menu_genpass":
        await q.edit_message_text(
            "🔑 <b>បង្កើត Password</b>\n\nជ្រើសប្រភេទ Password៖",
            reply_markup=mkb(
                [IKB("🔡 អក្សរ + លេខ",callback_data="gp_type_alnum",style=DANGER),IKB("🔐 អក្សរ + លេខ + សញ្ញា",callback_data="gp_type_full",style=DANGER)],
                [IKB("🔢 លេខ PIN",callback_data="gp_type_pin",style=DANGER),IKB("🔤 អក្សរ (ងាយចង់ចាំ)",callback_data="gp_type_words",style=DANGER)],
                [IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main",style=PRIMARY)]
            ),parse_mode=H); return END
    if d.startswith("gp_type_"):
        ctx.user_data["gp_type"]=d[8:]
        t=d[8:]
        lbl={"alnum":"អក្សរ + លេខ","full":"Full (+ សញ្ញា)","pin":"PIN","words":"ងាយចង់ចាំ"}
        await q.edit_message_text(
            f"🔑 <b>ជ្រើសប្រវែង ({lbl.get(t,t)})</b>",
            reply_markup=mkb(
                [IKB("8",callback_data=f"gp_len_8",style=DANGER),IKB("12",callback_data=f"gp_len_12",style=DANGER),IKB("16",callback_data=f"gp_len_16",style=DANGER)],
                [IKB("20",callback_data=f"gp_len_20",style=DANGER),IKB("24",callback_data=f"gp_len_24",style=DANGER),IKB("32",callback_data=f"gp_len_32",style=DANGER)],
                [IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main",style=PRIMARY)]
            ),parse_mode=H); return END
    if d.startswith("gp_len_"):
        length=int(d[7:]); ptype=ctx.user_data.get("gp_type","alnum")
        pw=_gen_password(ptype,length)
        await q.edit_message_text(
            f"🔑 <b>Password ថ្មីរបស់អ្នក</b>\n━━━━━━━━━━━━\n"
            f"<code>{pw}</code>\n━━━━━━━━━━━━\n"
            f"📏 ប្រវែង: <b>{len(pw)}</b> តួ",
            reply_markup=InlineKeyboardMarkup([
                [IKB("🔄 បង្កើតថ្មីទៀត",callback_data=f"gp_len_{length}",style=DANGER),IKB("🔑 ប្រភេទផ្សេង",callback_data="menu_genpass",style=DANGER)],
                *_sec_nav("menu_genpass"),HOME]),parse_mode=H); return END

    # ── Unit Converter ──
    if d=="menu_unit":
        await q.edit_message_text(
            "📏 <b>ប្ដូរឯកតា</b>\n\nជ្រើសប្រភេទ៖",
            reply_markup=mkb(
                [IKB("📏 ចម្ងាយ",callback_data="unit_length",style=SUCCESS),IKB("⚖️ ទម្ងន់",callback_data="unit_weight",style=SUCCESS)],
                [IKB("📐 ផ្ទៃក្រឡា",callback_data="unit_area",style=SUCCESS),IKB("🧪 បរិមាណ",callback_data="unit_volume",style=SUCCESS)],
                [IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main",style=PRIMARY)]
            ),parse_mode=H); return S_UNIT
    if d in("unit_length","unit_weight","unit_area","unit_volume"):
        ctx.user_data["unit_type"]=d.split("_")[1]
        guides={"length":"<code>ឧ: 10 km</code> ឬ <code>5 miles</code> ឬ <code>100 cm</code>\nឯកតា: km, m, cm, mm, miles, feet, inches, yard",
                "weight":"<code>ឧ: 70 kg</code> ឬ <code>150 lbs</code>\nឯកតា: kg, g, mg, lb/lbs, oz",
                "area":"<code>ឧ: 100 m2</code> ឬ <code>1 km2</code>\nឯកតា: km2, m2, cm2, hectare, acre",
                "volume":"<code>ឧ: 2 L</code> ឬ <code>500 ml</code>\nឯកតា: L, mL, gallon, cup, fl_oz"}
        lbl={"length":"ចម្ងាយ","weight":"ទម្ងន់","area":"ផ្ទៃក្រឡា","volume":"បរិមាណ"}
        t=d.split("_")[1]
        await q.edit_message_text(
            f"📏 <b>ប្ដូរ{lbl[t]}</b>\n\n✏️ វាយ <b>លេខ + ឯកតា</b>:\n{guides[t]}",
            reply_markup=bc(),parse_mode=H); return S_UNIT

    # ── BMI ──
    if d=="menu_bmi":
        await q.edit_message_text(
            "📐 <b>BMI Calculator</b>\n\n✏️ វាយ <b>ទម្ងន់ (kg) និង កម្ពស់ (cm)</b>:\n"
            "<code>ឧ: 65 170</code>\n<i>(ទម្ងន់ (kg) ចន្លោះ កម្ពស់ (cm))</i>",
            reply_markup=bc(),parse_mode=H); return S_BMI

    # ── World Clock ──
    if d=="menu_wclock":
        return await _show_world_clock(q)

    # ── Loan Calculator ──
    if d=="menu_loan":
        await q.edit_message_text(
            "💰 <b>គណនាការប្រាក់</b>\n\n✏️ វាយ <b>ប្រាក់ ▪ អត្រា% ▪ ខែ</b>:\n"
            "<code>ឧ: 10000 5 12</code>\n"
            "<i>ប្រាក់ $10,000 ▪ 5%/ឆ្នាំ ▪ 12 ខែ</i>",
            reply_markup=mkb(
                [IKB("📊 ការប្រាក់ធម្មតា",callback_data="loan_simple",style=SUCCESS),IKB("📈 ការប្រាក់ផ្សំ",callback_data="loan_compound",style=SUCCESS)],
                [IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main",style=PRIMARY)]
            ),parse_mode=H); return S_LOAN
    if d in("loan_simple","loan_compound"):
        ctx.user_data["loan_type"]=d.split("_")[1]
        lbl={"simple":"ធម្មតា (Simple)","compound":"ផ្សំ (Compound)"}
        await q.edit_message_text(
            f"💰 <b>ការប្រាក់{lbl[d.split('_')[1]]}</b>\n\n✏️ វាយ <b>ប្រាក់ ▪ អត្រា% ▪ ខែ</b>:\n"
            "<code>ឧ: 10000 5 12</code>",
            reply_markup=bc(),parse_mode=H); return S_LOAN

    # ── Coin & Dice ──
    if d=="menu_dice":
        return await _show_dice_menu(q)
    if d=="dice_coin":
        r=random.choice(["👑 HEADS (ព្រះ)","🦅 TAILS (ខ)"])
        await q.edit_message_text(
            f"🎴 <b>សសេ</b>\n━━━━━━━━━━━━\n{r}",
            reply_markup=InlineKeyboardMarkup([[IKB("🔄 សសេម្ដងទៀត",callback_data="dice_coin",style=SUCCESS),IKB("🎲 D6",callback_data="dice_roll6",style=SUCCESS),IKB("🍀 នាសី",callback_data="dice_lucky",style=SUCCESS)],*_fun_nav("menu_dice"),HOME]),parse_mode=H); return END
    if d.startswith("dice_roll"):
        sides=int(d[9:]); r=random.randint(1,sides)
        pips={1:"⚀",2:"⚁",3:"⚂",4:"⚃",5:"⚄",6:"⚅"}
        em=pips.get(r,"🎲")
        await q.edit_message_text(
            f"🎲 <b>គ្រាប់ចៃ D{sides}</b>\n━━━━━━━━━━━━\n{em} <b>{r}</b>",
            reply_markup=InlineKeyboardMarkup([[IKB("🎲 D6",callback_data="dice_roll6",style=SUCCESS),IKB("🎲 D12",callback_data="dice_roll12",style=SUCCESS),IKB("🎲 D20",callback_data="dice_roll20",style=SUCCESS)],[IKB("🔄 ម្ដងទៀត",callback_data=f"dice_roll{sides}",style=SUCCESS),IKB("🎴 សសេ",callback_data="dice_coin",style=SUCCESS),IKB("🍀 នាសី",callback_data="dice_lucky",style=SUCCESS)],*_fun_nav("menu_dice"),HOME]),parse_mode=H); return END
    if d=="dice_lucky":
        nums=random.sample(range(1,50),6); nums.sort()
        await q.edit_message_text(
            f"🍀 <b>លេខនាសី</b>\n━━━━━━━━━━━━\n"+"  ".join(f"<b>{n}</b>" for n in nums)+
            f"\n━━━━━━━━━━━━\n⭐ លេខពិសេស: <b>{random.randint(1,12)}</b>",
            reply_markup=InlineKeyboardMarkup([[IKB("🔄 ថ្មីម្ដងទៀត",callback_data="dice_lucky",style=SUCCESS),IKB("🎴 សសេ",callback_data="dice_coin",style=SUCCESS),IKB("🎲 D6",callback_data="dice_roll6",style=SUCCESS)],*_fun_nav("menu_dice"),HOME]),parse_mode=H); return END

    if d=="menu_about":
        import telegram as _tg
        ptb_ver=_tg.__version__
        import sys
        py_ver=sys.version.split()[0]
        await q.edit_message_text(
            f"ℹ️ <b>Khmer Multi-Tool Bot</b>\n"
            f"┌─────────────────────────┐\n"
            f"│  🔖 Version: <b>4.0</b>  │  🇰🇭 Khmer  │\n"
            f"└─────────────────────────┘\n"
            f"📅 <code>{datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🐍 Python: <b>{py_ver}</b>\n"
            f"📡 python-telegram-bot: <b>{ptb_ver}</b>\n"
            f"🤖 Telegram Bot API: <b>9.4 ✅</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>Libraries:</b>\n"
            f"   qrcode • pyzbar • fpdf2\n"
            f"   Pillow • opencv • numpy\n"
            f"   hashlib • dateutil • zoneinfo\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔵 QR Tools (2)  🟣 Text & Doc (4)\n"
            f"🟢 Math & Convert (6)  🔴 Security (4)\n"
            f"🟡 Fun & Utility (4)\n"
            f"📊 <b>សរុប: 20 មុខងារ</b>",
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

# ── Password Generator helper ─────────────────────────────────────────────────
def _gen_password(ptype:str,length:int)->str:
    if ptype=="alnum":
        chars=string.ascii_letters+string.digits
        pw=[random.choice(string.ascii_uppercase),random.choice(string.ascii_lowercase),random.choice(string.digits)]
    elif ptype=="full":
        special="!@#$%^&*()-_=+[]{}|;:,.<>?"
        chars=string.ascii_letters+string.digits+special
        pw=[random.choice(string.ascii_uppercase),random.choice(string.ascii_lowercase),random.choice(string.digits),random.choice(special)]
    elif ptype=="pin":
        return "".join(random.choices(string.digits,k=length))
    else:
        words=["Sky","Fire","Moon","Star","Blue","Gold","Fast","Wave","Rock","Leaf","Rain","Wind","Jade","Bolt","Sage"]
        w1=random.choice(words); w2=random.choice(words); n=random.randint(10,99)
        return f"{w1}{n}{w2}!"
    pw+=random.choices(chars,k=max(0,length-len(pw)))
    random.shuffle(pw)
    return "".join(pw)

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
        reply_markup=InlineKeyboardMarkup([[IKB("🔄 Refresh",callback_data="menu_wclock",style=SUCCESS)],*_fun_nav("menu_wclock"),HOME]),
        parse_mode=H)
    return END

# ── Dice menu helper ──────────────────────────────────────────────────────────
async def _show_dice_menu(q):
    await q.edit_message_text(
        "🎲 <b>Coin & Dice</b>\n\nជ្រើសការលេង៖",
        reply_markup=mkb(
            [IKB("🎴 សសេ (Coin Flip)",callback_data="dice_coin",style=SUCCESS)],
            [IKB("⚀ D6",callback_data="dice_roll6",style=SUCCESS),IKB("🎲 D12",callback_data="dice_roll12",style=SUCCESS),IKB("🎲 D20",callback_data="dice_roll20",style=SUCCESS)],
            [IKB("🍀 លេខនាសី",callback_data="dice_lucky",style=SUCCESS)],
            [IKB("🏠 ម៉ឺនុយមេ",callback_data="back_main",style=PRIMARY)]
        ),parse_mode=H)
    return END

# ── QR create ───────────────────────────────────────────────────────────────────
async def qr_input(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip()
    if not t: await _edit(ctx,"⚠️ សូមវាយអ្វីមួយ!",bc()); return S_QR
    await _edit(ctx,"⏳ <b>កំពុងបង្កើត QR Code...</b>"); await u.message.delete()
    qr=qrcode.QRCode(version=None,error_correction=qrcode.constants.ERROR_CORRECT_H,box_size=12,border=4)
    qr.add_data(t); qr.make(fit=True); img=qr.make_image(fill_color="#0A0A0A",back_color="#FFFFFF").convert("RGB")
    buf=io.BytesIO(); img.save(buf,format="PNG"); buf.seek(0)
    msg=await u.message.reply_photo(photo=buf,caption=f"✅ <b>QR Code បង្កើតជោគជ័យ!</b>\n📝 <code>{t[:200]}</code>\n📐 {img.size[0]}×{img.size[1]}px",reply_markup=InlineKeyboardMarkup([[IKB("🔄 QR Code ថ្មី",callback_data="menu_qr_create",style=PRIMARY)],*_qr_nav("menu_qr_create"),HOME]),parse_mode=H)
    _save(ctx,msg); return END

# ── QR scan ─────────────────────────────────────────────────────────────────────
async def qr_scan(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    p=u.message.photo[-1] if u.message.photo else None; dc=u.message.document if u.message.document else None
    if not p and not dc: await _edit(ctx,"⚠️ <b>សូម Upload រូបភាព QR Code!</b>",bc()); return S_SCAN
    await _edit(ctx,"⏳ <b>កំពុង Scan QR Code...</b>")
    f=await ctx.bot.get_file(p.file_id if p else dc.file_id); raw=await f.download_as_bytearray()
    cv_img=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
    dec=pyzbar_decode(Image.fromarray(cv2.cvtColor(cv_img,cv2.COLOR_BGR2RGB)))
    if not dec: await _edit(ctx,"❌ <b>រក QR Code មិនឃើញ!</b>\n\n💡 ប្រើរូបភាពច្បាស់ • QR ត្រូវឃើញពេញ",InlineKeyboardMarkup([[IKB("🔄 ព្យាយាមម្ដងទៀត",callback_data="menu_qr_scan",style=PRIMARY)],*_qr_nav("menu_qr_scan"),HOME])); return END
    res=[f"<b>#{i}</b> [{d.type}]\n<code>{d.data.decode('utf-8','replace')[:300]}</code>" for i,d in enumerate(dec,1)]
    await _edit(ctx,f"✅ <b>Scan ជោគជ័យ! រក QR បាន {len(dec)} ចំនួន</b>\n\n"+"\n\n".join(res),InlineKeyboardMarkup([[IKB("🔄 Scan ថ្មី",callback_data="menu_qr_scan",style=PRIMARY)],*_qr_nav("menu_qr_scan"),HOME])); return END

# ── Text style ──────────────────────────────────────────────────────────────────
async def text_style(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip()
    if not t: await _edit(ctx,"⚠️ សូមវាយអ្វីមួយ!",bc()); return S_STYLE
    await u.message.delete(); ctx.user_data["style_original"]=t
    rows=[f"<b>{lbl}:</b>\n{fn(t)}" for _,(lbl,fn) in TS.items()]
    ks=list(TS.keys()); btns=[[IKB(f"📋 {TS[ks[i]][0]}",callback_data=f"copy_style_{ks[i]}") for i in range(j,min(j+2,len(ks)))] for j in range(0,len(ks),2)]
    btns+=[[IKB("✍️ ដំណើរការថ្មី",callback_data="menu_text_style",style=PRIMARY)],*_text_nav("menu_text_style"),HOME]
    await _edit(ctx,f"✍️ <b>Style ទាំងអស់សម្រាប់:</b> <code>{t}</code>\n━━━━━━━━━━━━\n\n"+"\n\n".join(rows)+"\n\n━━━━━━━━━━━━\n👇 ចុចប៊ូតុង ចម្លង Style:",InlineKeyboardMarkup(btns)); return S_STYLE

# ── PDF ─────────────────────────────────────────────────────────────────────────
async def pdf_photo(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    p=u.message.photo[-1] if u.message.photo else None; dc=u.message.document if u.message.document else None
    if not p and not dc: await _edit(ctx,"⚠️ សូម Upload រូបភាព!",mkb([IKB("✅ បង្កើត PDF",callback_data="pdf_done",style=SUCCESS),IKB("❌ បោះបង់",callback_data="back_main",style=DANGER)])); return S_PDF
    f=await ctx.bot.get_file(p.file_id if p else dc.file_id); ctx.user_data.setdefault("pdf_photos",[]).append(bytes(await f.download_as_bytearray()))
    n=len(ctx.user_data["pdf_photos"])
    await _edit(ctx,f"✅ <b>រូបភាពទី {n} បានទទួល!</b>\n📤 Upload បន្ថែម ឬ ចុច <b>បង្កើត PDF</b>",mkb([IKB("✅ បង្កើត PDF",callback_data="pdf_done",style=SUCCESS),IKB("❌ បោះបង់",callback_data="back_main",style=DANGER)])); return S_PDF

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
    msg=await q.message.reply_document(document=InputFile(buf,filename="KhmerBot.pdf"),caption=f"✅ <b>PDF បង្កើតជោគជ័យ!</b>\n🖼️ ចំនួន {len(photos)} ទំព័រ",reply_markup=InlineKeyboardMarkup([[IKB("🖼️ PDF ថ្មី",callback_data="menu_photo_pdf",style=SUCCESS)],*_text_nav("menu_photo_pdf"),HOME]),parse_mode=H)
    _save(ctx,msg); ctx.user_data["pdf_photos"]=[]; return END

# ── Calculator ──────────────────────────────────────────────────────────────────
CB=[["C","±","%","÷"],["7","8","9","×"],["4","5","6","−"],["1","2","3","+"],[" 0",".","⌫","="]]
async def _calc_show(qm,ctx,ans=None):
    e=ctx.user_data.get("calc_expr",""); dp=ans or(e[-30:] if e else "0")
    kb=InlineKeyboardMarkup([[IKB(b,callback_data=f"calc_{b.strip()}") for b in r] for r in CB]+_math_nav("menu_calculator")+[HOME])
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

# ── Password checker ────────────────────────────────────────────────────────────
async def pw_check(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    pw=u.message.text; await u.message.delete()
    ck={"ល8":(len(pw)>=8,"✅ ≥8 តួអក្សរ","❌ តិចជាង 8 តួ"),"ល12":(len(pw)>=12,"✅ ≥12 តួអក្សរ",None),"ធC":(bool(re.search(r"[A-Z]",pw)),"✅ មានអក្សរធំ","❌ គ្មានអក្សរធំ"),"តc":(bool(re.search(r"[a-z]",pw)),"✅ មានអក្សរតូច","❌ គ្មានអក្សរតូច"),"លx":(bool(re.search(r"\d",pw)),"✅ មានលេខ","❌ គ្មានលេខ"),"ស#":(bool(re.search(r"[^A-Za-z0-9]",pw)),"✅ មានសញ្ញា","❌ គ្មានសញ្ញា")}
    passed=sum(1 for _,(ok,_,_) in ck.items() if ok); issues=[g if ok else b for _,(ok,g,b) in ck.items() if b]
    lv,em=("ខ្សោយ","🔴") if passed<=2 else("មធ្យម","🟡") if passed<=4 else("ល្អ","🟢") if passed==5 else("ខ្លាំងណាស់","🟢✨")
    ent=round(math.log2(len(set(pw)))*len(pw),1) if len(set(pw))>1 else 0
    await _edit(ctx,f"🔐 <b>លទ្ធផលពិនិត្យ Password</b>\n━━━━━━━━━━━━\n🔑 <tg-spoiler>{'•'*len(pw)}</tg-spoiler>\n━━━━━━━━━━━━\n{em} <b>កម្រិត:</b> {lv} | {passed}/6 ពិន្ទុ | {ent}b\n━━━━━━━━━━━━\n"+"\n".join(issues),InlineKeyboardMarkup([[IKB("🔄 ពិនិត្យ Password ថ្មី",callback_data="menu_password",style=DANGER)],*_sec_nav("menu_password"),HOME])); return END

# ── Random Picker ───────────────────────────────────────────────────────────────
async def picker(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    items=[x.strip() for x in u.message.text.strip().split(",") if x.strip()]; await u.message.delete()
    if len(items)<2: await _edit(ctx,"⚠️ <b>ត្រូវការ ≥2 ជម្រើស!</b>\nដាក់ , ចន្លោះ: <code>ក, ខ, គ</code>",bc()); return S_PICK
    c=random.choice(items); rk=random.sample(items,len(items))
    await _edit(ctx,f"🎲 <b>Random Picker</b>\n━━━━━━━━━━━━\n🏆 <b>ជ្រើសបាន:</b> <code>{c}</code>\n━━━━━━━━━━━━\n📋 <b>លំដាប់ Random:</b>\n"+"\n".join(f"  {i}. {x}" for i,x in enumerate(rk,1)),InlineKeyboardMarkup([[IKB("🔄 Random ម្ដងទៀត",callback_data="menu_picker",style=SUCCESS)],*_fun_nav("menu_picker"),HOME])); return END

# ── Morse ───────────────────────────────────────────────────────────────────────
async def morse(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip(); d=ctx.user_data.get("morse_dir","to"); await u.message.delete()
    r,h,lb=(t2m(t),"អក្សរ → Morse","Morse") if d=="to" else(m2t(t),"Morse → អក្សរ","អក្សរ")
    await _edit(ctx,f"📡 <b>{h}</b>\n━━━━━━━━━━━━\n📥 Input: <code>{t[:200]}</code>\n📤 {lb}: <code>{r[:500]}</code>",InlineKeyboardMarkup([[IKB("🔄 ថ្មី",callback_data="menu_morse",style=PRIMARY)],*_text_nav("menu_morse"),HOME])); return END

# ── Base64 ──────────────────────────────────────────────────────────────────────
async def b64(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip(); d=ctx.user_data.get("b64_dir","encode"); await u.message.delete()
    try: r=base64.b64encode(t.encode()).decode() if d=="encode" else base64.b64decode(t.encode()).decode(); h="Encode" if d=="encode" else"Decode"; err=False
    except Exception as e: r=str(e); h="Error"; err=True
    em="🔐" if d=="encode" else"🔓"
    await _edit(ctx,f"{em} <b>Base64 {h}</b>\n━━━━━━━━━━━━\n📥 Input:\n<code>{t[:200]}</code>\n\n{'❌' if err else '📤'} លទ្ធផល:\n<code>{r[:1000]}</code>",InlineKeyboardMarkup([[IKB("🔄 Base64 ថ្មី",callback_data="menu_base64",style=DANGER)],*_sec_nav("menu_base64"),HOME])); return END

# ── Text Counter ────────────────────────────────────────────────────────────────
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
        InlineKeyboardMarkup([[IKB("🔄 រាប់អក្សរថ្មី",callback_data="menu_count",style=PRIMARY)],*_text_nav("menu_count"),HOME])); return END

# ── Number Base Converter ────────────────────────────────────────────────────────
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
            InlineKeyboardMarkup([[IKB("🔄 ប្ដូរថ្មី",callback_data="menu_nbase",style=SUCCESS)],*_math_nav("menu_nbase"),HOME]))
    except: await _edit(ctx,"❌ <b>លេខមិនត្រឹមត្រូវ!</b>\nសូមវាយឡើងវិញ",bc())
    return END

# ── Temperature Converter ────────────────────────────────────────────────────────
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
            InlineKeyboardMarkup([[IKB("🔄 ប្ដូរថ្មី",callback_data="menu_temp",style=SUCCESS)],*_math_nav("menu_temp"),HOME]))
    except: await _edit(ctx,"❌ <b>លេខមិនត្រឹមត្រូវ!</b>\nសូមវាយឡើងវិញ",bc())
    return END

# ── Hash Generator ────────────────────────────────────────────────────────────
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
        InlineKeyboardMarkup([[IKB("🔄 Hash ថ្មី",callback_data="menu_hash",style=DANGER)],*_sec_nav("menu_hash"),HOME])); return END

# ── Date / Age Calculator ─────────────────────────────────────────────────────
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
            InlineKeyboardMarkup([[IKB("🔄 គណនាថ្មី",callback_data="menu_date",style=SUCCESS)],*_fun_nav("menu_date"),HOME]))
    except: await _edit(ctx,"❌ <b>ទ្រង់ទ្រាយខុស!</b>\nសូមវាយ: <code>DD/MM/YYYY</code>\nឧ: <code>15/06/1995</code>",bc())
    return END

# ── Unit Converter ────────────────────────────────────────────────────────────
UNIT_TABLE={
    "length":{
        "km":1000,"m":1,"cm":0.01,"mm":0.001,
        "miles":1609.344,"mile":1609.344,"feet":0.3048,"foot":0.3048,
        "ft":0.3048,"inches":0.0254,"inch":0.0254,"in":0.0254,
        "yard":0.9144,"yd":0.9144
    },
    "weight":{
        "kg":1,"g":0.001,"mg":0.000001,
        "lb":0.453592,"lbs":0.453592,"pound":0.453592,"pounds":0.453592,
        "oz":0.0283495,"ounce":0.0283495
    },
    "area":{
        "km2":1e6,"m2":1,"cm2":0.0001,"mm2":0.000001,
        "hectare":10000,"ha":10000,"acre":4046.86
    },
    "volume":{
        "l":1,"liter":1,"litre":1,"ml":0.001,"milliliter":0.001,
        "gallon":3.78541,"gal":3.78541,"cup":0.236588,
        "fl_oz":0.0295735,"floz":0.0295735
    }
}
UNIT_DISPLAY={
    "length":{"km":"km","m":"m","cm":"cm","mm":"mm","miles":"miles","feet":"feet","inches":"inches","yard":"yard"},
    "weight":{"kg":"kg","g":"g","mg":"mg","lbs":"lbs","oz":"oz"},
    "area":{"km2":"km²","m2":"m²","cm2":"cm²","hectare":"hectare","acre":"acre"},
    "volume":{"l":"L","ml":"mL","gallon":"gallon","cup":"cup","fl_oz":"fl oz"}
}

async def unit_convert(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    raw=u.message.text.strip().lower(); await u.message.delete()
    utype=ctx.user_data.get("unit_type","length")
    table=UNIT_TABLE.get(utype,{})
    disp=UNIT_DISPLAY.get(utype,{})
    parts=raw.split(None,1)
    if len(parts)!=2: await _edit(ctx,"❌ <b>ទ្រង់ទ្រាយខុស!</b>\nឧ: <code>10 km</code>",bc()); return S_UNIT
    try: val=float(parts[0])
    except: await _edit(ctx,"❌ <b>លេខមិនត្រឹមត្រូវ!</b>",bc()); return S_UNIT
    unit=parts[1].strip().lower()
    if unit not in table: await _edit(ctx,f"❌ <b>ឯកតា '{parts[1]}' មិនស្គាល់!</b>\nសូមប្រើឯកតាដែលមាន",bc()); return S_UNIT
    base_val=val*table[unit]
    lbl={"length":"ចម្ងាយ","weight":"ទម្ងន់","area":"ផ្ទៃក្រឡា","volume":"បរិមាណ"}
    rows=[]
    for k,factor in table.items():
        converted=base_val/factor
        label=disp.get(k,k)
        fmt=f"{converted:.6g}"
        rows.append(f"  {label}: <b>{fmt}</b>")
    await _edit(ctx,
        f"📏 <b>ប្ដូរ{lbl.get(utype,utype)}</b>\n━━━━━━━━━━━━\n"
        f"📥 Input: <b>{val:g} {parts[1]}</b>\n━━━━━━━━━━━━\n"
        +"\n".join(rows),
        InlineKeyboardMarkup([[IKB("🔄 ប្ដូរថ្មី",callback_data=f"unit_{utype}",style=SUCCESS),IKB("📏 ប្រភេទ",callback_data="menu_unit",style=SUCCESS)],*_math_nav("menu_unit"),HOME]))
    return END

# ── BMI Calculator ────────────────────────────────────────────────────────────
async def bmi_calc(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    raw=u.message.text.strip(); await u.message.delete()
    parts=raw.split()
    if len(parts)!=2:
        await _edit(ctx,"❌ <b>ទ្រង់ទ្រាយខុស!</b>\nវាយ: <code>ទម្ងន់(kg) កម្ពស់(cm)</code>\nឧ: <code>65 170</code>",bc()); return S_BMI
    try:
        weight=float(parts[0]); height_cm=float(parts[1])
        height_m=height_cm/100
        bmi=weight/(height_m**2)
        if bmi<18.5:   cat,em,tip="ស្តើងពេក (Underweight)","🟡","💡 ត្រូវញ៉ាំបន្ថែម ។"
        elif bmi<23:   cat,em,tip="ធម្មតា (Normal)","🟢","✅ ទម្ងន់ល្អ! បន្តរក្សា ។"
        elif bmi<25:   cat,em,tip="លើសបន្តិច (Overweight)","🟠","💡 ហាត់ប្រាណបន្ថែម ។"
        elif bmi<30:   cat,em,tip="លើស (Obese I)","🔴","⚠️ គួរពិគ្រោះវេជ្ជបណ្ឌិត ។"
        else:          cat,em,tip="លើសខ្លាំង (Obese II)","🔴","⚠️ ត្រូវការការថែទាំ ។"
        ideal_low=18.5*height_m**2; ideal_high=22.9*height_m**2
        await _edit(ctx,
            f"📐 <b>BMI Calculator</b>\n━━━━━━━━━━━━\n"
            f"⚖️ ទម្ងន់: <b>{weight} kg</b>\n"
            f"📏 កម្ពស់: <b>{height_cm} cm ({height_m:.2f} m)</b>\n"
            f"━━━━━━━━━━━━\n"
            f"📊 BMI: <b>{bmi:.1f}</b>\n"
            f"{em} ស្ថានភាព: <b>{cat}</b>\n"
            f"━━━━━━━━━━━━\n"
            f"🎯 ទម្ងន់គួរមាន: <b>{ideal_low:.1f}–{ideal_high:.1f} kg</b>\n"
            f"{tip}",
            InlineKeyboardMarkup([[IKB("🔄 គណនាថ្មី",callback_data="menu_bmi",style=SUCCESS)],*_math_nav("menu_bmi"),HOME]))
    except: await _edit(ctx,"❌ <b>លេខមិនត្រឹមត្រូវ!</b>\nឧ: <code>65 170</code>",bc())
    return END

# ── Loan / Interest Calculator ────────────────────────────────────────────────
async def loan_calc(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    raw=u.message.text.strip(); await u.message.delete()
    ltype=ctx.user_data.get("loan_type","simple")
    parts=raw.split()
    if len(parts)!=3:
        await _edit(ctx,"❌ <b>ទ្រង់ទ្រាយខុស!</b>\nវាយ: <code>ប្រាក់ អត្រា% ខែ</code>\nឧ: <code>10000 5 12</code>",bc()); return S_LOAN
    try:
        principal=float(parts[0]); annual_rate=float(parts[1]); months=int(parts[2])
        monthly_rate=annual_rate/100/12
        if ltype=="simple":
            interest=principal*(annual_rate/100)*(months/12)
            total=principal+interest
            monthly_pay=total/months
            rows=(f"💵 ប្រាក់ដើម: <b>${principal:,.2f}</b>\n"
                  f"📈 ការប្រាក់: <b>${interest:,.2f}</b>\n"
                  f"💰 សរុប: <b>${total:,.2f}</b>\n"
                  f"📅 បង់/ខែ: <b>${monthly_pay:,.2f}</b>")
        else:
            if monthly_rate>0:
                monthly_pay=principal*monthly_rate*(1+monthly_rate)**months/((1+monthly_rate)**months-1)
            else:
                monthly_pay=principal/months
            total=monthly_pay*months; interest=total-principal
            rows=(f"💵 ប្រាក់ដើម: <b>${principal:,.2f}</b>\n"
                  f"📈 ការប្រាក់: <b>${interest:,.2f}</b>\n"
                  f"💰 សរុប: <b>${total:,.2f}</b>\n"
                  f"📅 បង់/ខែ: <b>${monthly_pay:,.2f}</b>")
        lbl={"simple":"ធម្មតា","compound":"ផ្សំ"}
        await _edit(ctx,
            f"💰 <b>ការប្រាក់{lbl[ltype]}</b>\n━━━━━━━━━━━━\n"
            f"⏱ {months} ខែ  •  {annual_rate}%/ឆ្នាំ\n━━━━━━━━━━━━\n"
            +rows,
            InlineKeyboardMarkup([[IKB("🔄 គណនាថ្មី",callback_data="menu_loan",style=SUCCESS)],*_math_nav("menu_loan"),HOME]))
    except: await _edit(ctx,"❌ <b>លេខមិនត្រឹមត្រូវ!</b>\nឧ: <code>10000 5 12</code>",bc())
    return END

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
            S_TEMP:  [MessageHandler(TXT,temp_convert),CB_H],
            S_HASH:  [MessageHandler(TXT,hash_gen),   CB_H],
            S_DATE:  [MessageHandler(TXT,date_calc),  CB_H],
            S_UNIT:  [MessageHandler(TXT,unit_convert),CB_H],
            S_BMI:   [MessageHandler(TXT,bmi_calc),   CB_H],
            S_LOAN:  [MessageHandler(TXT,loan_calc),  CB_H],
            S_LUCK:  [CB_H],
        },
        fallbacks=[CommandHandler("start",cmd_start),MessageHandler(filters.ALL,fallback)],
        per_message=False,allow_reentry=True,
    ))
    logger.info("🤖 Bot កំពុង Start..."); app.run_polling(allowed_updates=Update.ALL_TYPES,poll_interval=1.0,drop_pending_updates=True)
if __name__=="__main__": main()
