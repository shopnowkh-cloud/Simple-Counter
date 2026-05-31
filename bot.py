#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,io,re,math,base64,random,logging,warnings,qrcode,cv2,numpy as np
from PIL import Image; from pyzbar.pyzbar import decode as pyzbar_decode; from fpdf import FPDF; from datetime import datetime
from telegram import Update,InlineKeyboardButton as IKB,InlineKeyboardMarkup,InputFile
from telegram.ext import Application,CommandHandler,MessageHandler,CallbackQueryHandler,ConversationHandler,ContextTypes,filters
from telegram.constants import ParseMode; from telegram.warnings import PTBUserWarning
warnings.filterwarnings("ignore",category=PTBUserWarning)
BOT_TOKEN=os.environ.get("BOT_TOKEN","")
if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN not set!")
logging.basicConfig(format="%(asctime)s|%(levelname)s|%(message)s",level=logging.INFO)
logger=logging.getLogger(__name__)
S_QR,S_SCAN,S_STYLE,S_PDF,S_CALC,S_PASS,S_PICK,S_MORSE,S_B64=range(9)
H=ParseMode.HTML; END=ConversationHandler.END
def mkb(*r): return InlineKeyboardMarkup(list(r))
def bb(b="main"): return mkb([IKB("🏠 ត្រឡប់",callback_data=f"back_{b}")])
def bc(b="main"): return mkb([IKB("❌ បោះបង់",callback_data=f"back_{b}"),IKB("🏠 ម៉ឺនុយ",callback_data="back_main")])
def mm(): return mkb([IKB("📷 QR Create",callback_data="menu_qr_create"),IKB("🔍 QR Scan",callback_data="menu_qr_scan")],[IKB("✍️ Text Style",callback_data="menu_text_style"),IKB("🖼️ Photo→PDF",callback_data="menu_photo_pdf")],[IKB("🔢 Calculator",callback_data="menu_calculator"),IKB("🔐 Password",callback_data="menu_password")],[IKB("🎲 Random",callback_data="menu_picker"),IKB("📡 Morse",callback_data="menu_morse")],[IKB("🔒 Base64",callback_data="menu_base64"),IKB("ℹ️ About",callback_data="menu_about")])
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
async def cmd_start(u:Update,_:ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(f"👋 សួស្ដី <b>{u.effective_user.first_name}</b>!\n\n🤖 <b>Khmer Multi-Tool Bot</b> 🇰🇭\n\n━━━━━━━━━━━━━━━━━━━━\n📷 QR Create/Scan  ✍️ Text Style\n🖼️ Photo→PDF       🔢 Calculator\n🔐 Password        🎲 Random Picker\n📡 Morse Code      🔒 Base64\n━━━━━━━━━━━━━━━━━━━━\n👇 ជ្រើសរើសមុខងារ:",reply_markup=mm(),parse_mode=H)
    return END
async def cb(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=u.callback_query; await q.answer(); d=q.data
    if d=="back_main":
        await q.edit_message_text("🏠 <b>ម៉ឺនុយមេ</b>\n\n👇 ជ្រើសរើស:",reply_markup=mm(),parse_mode=H); ctx.user_data.clear(); return END
    if d=="menu_qr_create": await q.edit_message_text("📷 <b>QR Code</b>\n\n✏️ វាយ text/link:",reply_markup=bc(),parse_mode=H); return S_QR
    if d=="menu_qr_scan":   await q.edit_message_text("🔍 <b>Scan QR</b>\n\n📤 Upload រូបភាព:",reply_markup=bc(),parse_mode=H); return S_SCAN
    if d=="menu_text_style":await q.edit_message_text("✍️ <b>Text Style</b>\n\n✏️ វាយ English text:",reply_markup=bc(),parse_mode=H); return S_STYLE
    if d=="menu_photo_pdf":
        ctx.user_data["pdf_photos"]=[]
        await q.edit_message_text("🖼️ <b>Photo→PDF</b>\n\n📤 Upload រូបភាព:\n✅ ចប់ → ចុច <b>Done</b>",reply_markup=mkb([IKB("✅ Done",callback_data="pdf_done"),IKB("❌ Cancel",callback_data="back_main")]),parse_mode=H); return S_PDF
    if d=="menu_calculator": ctx.user_data["calc_expr"]=""; await _calc_show(q,ctx); return S_CALC
    if d=="menu_password":  await q.edit_message_text("🔐 <b>Password Check</b>\n\n✏️ វាយ password:",reply_markup=bc(),parse_mode=H); return S_PASS
    if d=="menu_picker":    await q.edit_message_text("🎲 <b>Random Picker</b>\n\n✏️ វាយជម្រើស ដាក់ , :\n<code>ក,ខ,គ</code>",reply_markup=bc(),parse_mode=H); return S_PICK
    if d=="menu_morse":     await q.edit_message_text("📡 <b>Morse</b>\n\nជ្រើស:",reply_markup=mkb([IKB("🔤→📡 Encode",callback_data="morse_to"),IKB("📡→🔤 Decode",callback_data="morse_from")],[IKB("🏠",callback_data="back_main")]),parse_mode=H); return S_MORSE
    if d=="morse_to":   ctx.user_data["morse_dir"]="to";   await q.edit_message_text("📡 <b>Text→Morse</b>\n\n✏️ វាយ text:",reply_markup=bc(),parse_mode=H); return S_MORSE
    if d=="morse_from": ctx.user_data["morse_dir"]="from"; await q.edit_message_text("📡 <b>Morse→Text</b>\n\n✏️ វាយ morse:\n<code>-- --- .-. ... .</code>",reply_markup=bc(),parse_mode=H); return S_MORSE
    if d=="menu_base64":    await q.edit_message_text("🔒 <b>Base64</b>\n\nជ្រើស:",reply_markup=mkb([IKB("🔐 Encode",callback_data="b64_encode"),IKB("🔓 Decode",callback_data="b64_decode")],[IKB("🏠",callback_data="back_main")]),parse_mode=H); return S_B64
    if d=="b64_encode": ctx.user_data["b64_dir"]="encode"; await q.edit_message_text("🔐 <b>Base64 Encode</b>\n\n✏️ វាយ text:",reply_markup=bc(),parse_mode=H); return S_B64
    if d=="b64_decode": ctx.user_data["b64_dir"]="decode"; await q.edit_message_text("🔓 <b>Base64 Decode</b>\n\n✏️ វាយ base64:",reply_markup=bc(),parse_mode=H); return S_B64
    if d=="menu_about":
        await q.edit_message_text(f"ℹ️ <b>Khmer Multi-Tool Bot v2.0</b>\n━━━━━━━━━━━━━━━━━━━━\n📅 <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n👨‍💻 Developer: <b>limsovannrady</b>\n🐍 <b>python-telegram-bot 21.x</b>\n━━━━━━━━━━━━━━━━━━━━\nqrcode • pyzbar • fpdf2 • Pillow • opencv",reply_markup=bb(),parse_mode=H); return END
    if d.startswith("calc_"): return await _calc_btn(q,ctx,d)
    if d.startswith("copy_style_"):
        sk=d[11:]; orig=ctx.user_data.get("style_original","")
        if orig and sk in TS:
            styled=TS[sk][1](orig); await q.answer(f"✅ ចម្លង: {styled[:15]}...",show_alert=True)
            await q.message.reply_text(f"<code>{styled}</code>",parse_mode=H)
        return S_STYLE
    if d=="pdf_done": return await _pdf_build(q,ctx)
    return END
async def qr_input(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip()
    if not t: await u.message.reply_text("⚠️ សូមវាយអ្វីមួយ!"); return S_QR
    qr=qrcode.QRCode(version=None,error_correction=qrcode.constants.ERROR_CORRECT_H,box_size=12,border=4)
    qr.add_data(t); qr.make(fit=True); img=qr.make_image(fill_color="#0A0A0A",back_color="#FFFFFF").convert("RGB")
    buf=io.BytesIO(); img.save(buf,format="PNG"); buf.seek(0)
    await u.message.reply_photo(photo=buf,caption=f"✅ <b>QR Code!</b>\n📝 <code>{t[:200]}</code>\n📐 {img.size[0]}×{img.size[1]}px",reply_markup=mkb([IKB("🔄 ថ្មី",callback_data="menu_qr_create")],[IKB("🏠",callback_data="back_main")]),parse_mode=H); return END
async def qr_scan(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    p=u.message.photo[-1] if u.message.photo else None; dc=u.message.document if u.message.document else None
    if not p and not dc: await u.message.reply_text("⚠️ Upload រូបភាព!",parse_mode=H); return S_SCAN
    f=await ctx.bot.get_file(p.file_id if p else dc.file_id); raw=await f.download_as_bytearray()
    cv_img=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
    dec=pyzbar_decode(Image.fromarray(cv2.cvtColor(cv_img,cv2.COLOR_BGR2RGB)))
    if not dec: await u.message.reply_text("❌ <b>រក QR មិនឃើញ!</b>",reply_markup=mkb([IKB("🔄",callback_data="menu_qr_scan")],[IKB("🏠",callback_data="back_main")]),parse_mode=H); return END
    res=[f"<b>#{i}</b>[{d.type}]\n<code>{d.data.decode('utf-8','replace')[:300]}</code>" for i,d in enumerate(dec,1)]
    await u.message.reply_text(f"✅ <b>Scan បាន {len(dec)} QR!</b>\n\n"+"\n\n".join(res),reply_markup=mkb([IKB("🔄 Scan",callback_data="menu_qr_scan"),IKB("📷 Create",callback_data="menu_qr_create")],[IKB("🏠",callback_data="back_main")]),parse_mode=H); return END
async def text_style(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip()
    if not t: await u.message.reply_text("⚠️ សូមវាយ!"); return S_STYLE
    ctx.user_data["style_original"]=t
    rows=[f"<b>{lbl}:</b>\n{fn(t)}" for _,(lbl,fn) in TS.items()]
    ks=list(TS.keys()); btns=[[IKB(f"📋 {TS[ks[i]][0]}",callback_data=f"copy_style_{ks[i]}") for i in range(j,min(j+2,len(ks)))] for j in range(0,len(ks),2)]
    btns+=[[IKB("✍️ ថ្មី",callback_data="menu_text_style")],[IKB("🏠",callback_data="back_main")]]
    await u.message.reply_text(f"✍️ <b>Styles of:</b> <code>{t}</code>\n━━━━━━━━━━━━\n\n"+"\n\n".join(rows)+"\n\n━━━━━━━━━━━━\n👇 ចុចចម្លង:",reply_markup=InlineKeyboardMarkup(btns),parse_mode=H); return S_STYLE
async def pdf_photo(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    p=u.message.photo[-1] if u.message.photo else None; dc=u.message.document if u.message.document else None
    if not p and not dc: await u.message.reply_text("⚠️ Upload រូបភាព!"); return S_PDF
    f=await ctx.bot.get_file(p.file_id if p else dc.file_id); ctx.user_data.setdefault("pdf_photos",[]).append(bytes(await f.download_as_bytearray()))
    n=len(ctx.user_data["pdf_photos"]); await u.message.reply_text(f"✅ រូបទី {n} បានទទួល!\nUpload ទៀត ឬ ចុច Done",reply_markup=mkb([IKB("✅ Done",callback_data="pdf_done"),IKB("❌",callback_data="back_main")]),parse_mode=H); return S_PDF
async def _pdf_build(q,ctx:ContextTypes.DEFAULT_TYPE):
    photos=ctx.user_data.get("pdf_photos",[])
    if not photos: await q.answer("⚠️ គ្មានរូបភាព!",show_alert=True); return S_PDF
    await q.edit_message_text(f"⏳ <b>បំប្លែង {len(photos)} រូប→PDF...</b>",parse_mode=H)
    pdf=FPDF()
    for raw in photos:
        img=Image.open(io.BytesIO(raw)).convert("RGB"); w,h=img.size
        if w>h: pdf.add_page("L",(297,210)); pw,ph=297,210
        else:   pdf.add_page("P",(210,297)); pw,ph=210,297
        ra=min(pw/w,ph/h); nw,nh=w*ra,h*ra; tmp=io.BytesIO(); img.save(tmp,format="JPEG",quality=90); tmp.seek(0); pdf.image(tmp,x=(pw-nw)/2,y=(ph-nh)/2,w=nw,h=nh)
    buf=io.BytesIO(bytes(pdf.output()))
    await q.message.reply_document(document=InputFile(buf,filename="KhmerBot.pdf"),caption=f"✅ <b>PDF!</b> 🖼️ {len(photos)} pages",reply_markup=mkb([IKB("🖼️ ថ្មី",callback_data="menu_photo_pdf")],[IKB("🏠",callback_data="back_main")]),parse_mode=H)
    ctx.user_data["pdf_photos"]=[]; return END
CB=[["C","±","%","÷"],["7","8","9","×"],["4","5","6","−"],["1","2","3","+"],[" 0",".","⌫","="]]
async def _calc_show(qm,ctx,ans=None):
    e=ctx.user_data.get("calc_expr",""); dp=ans or(e[-30:] if e else "0")
    kb=InlineKeyboardMarkup([[IKB(b,callback_data=f"calc_{b.strip()}") for b in r] for r in CB]+[[IKB("🏠",callback_data="back_main")]])
    t=f"🔢 <b>Calculator</b>\n━━━━━━━━━━━━\n<code> {dp}</code>\n━━━━━━━━━━━━"
    if hasattr(qm,"edit_message_text"): await qm.edit_message_text(t,reply_markup=kb,parse_mode=H)
    else: await qm.reply_text(t,reply_markup=kb,parse_mode=H)
async def _calc_btn(q,ctx,data):
    b=data[5:]; e=ctx.user_data.get("calc_expr","")
    if b=="C": ctx.user_data["calc_expr"]=""; await _calc_show(q,ctx); return S_CALC
    if b=="⌫": ctx.user_data["calc_expr"]=e[:-1]; await _calc_show(q,ctx); return S_CALC
    if b=="±": ctx.user_data["calc_expr"]=e[1:] if e and e[0]=="-" else("-"+e if e else e); await _calc_show(q,ctx); return S_CALC
    if b=="=":
        try:
            r=eval(re.sub(r'(\d)%',r'(\1/100)',e.replace("÷","/").replace("×","*").replace("−","-")),{"__builtins__":{}})
            r=int(r) if isinstance(r,float) and r.is_integer() else r; ctx.user_data["calc_expr"]=str(r); await _calc_show(q,ctx,ans=f"{e}={r}")
        except: ctx.user_data["calc_expr"]=""; await _calc_show(q,ctx,ans="❌ Error!")
        return S_CALC
    ctx.user_data["calc_expr"]=e+b; await _calc_show(q,ctx); return S_CALC
async def pw_check(u:Update,_:ContextTypes.DEFAULT_TYPE):
    pw=u.message.text
    ck={"len8":(len(pw)>=8,"✅ ≥8 chars","❌ <8 chars"),"len12":(len(pw)>=12,"✅ ≥12 chars",None),"up":(bool(re.search(r"[A-Z]",pw)),"✅ Uppercase","❌ No uppercase"),"lo":(bool(re.search(r"[a-z]",pw)),"✅ Lowercase","❌ No lowercase"),"dg":(bool(re.search(r"\d",pw)),"✅ Digit","❌ No digit"),"sp":(bool(re.search(r"[^A-Za-z0-9]",pw)),"✅ Symbol","❌ No symbol")}
    passed=sum(1 for _,(ok,_,_) in ck.items() if ok); issues=[g if ok else b for _,(ok,g,b) in ck.items() if b]
    lv,em=("ខ្សោយ","🔴") if passed<=2 else("មធ្យម","🟡") if passed<=4 else("ល្អ","🟢") if passed==5 else("ខ្លាំងណាស់","🟢✨")
    ent=round(math.log2(len(set(pw)))*len(pw),1) if len(set(pw))>1 else 0
    await u.message.reply_text(f"🔐 <b>Password Check</b>\n━━━━━━━━━━━━\n🔑 <tg-spoiler>{'•'*len(pw)}</tg-spoiler>\n━━━━━━━━━━━━\n{em} <b>{lv}</b> | {passed}/6 pts | {ent}b entropy\n━━━━━━━━━━━━\n"+"\n".join(issues),reply_markup=mkb([IKB("🔄",callback_data="menu_password")],[IKB("🏠",callback_data="back_main")]),parse_mode=H); return END
async def picker(u:Update,_:ContextTypes.DEFAULT_TYPE):
    items=[x.strip() for x in u.message.text.strip().split(",") if x.strip()]
    if len(items)<2: await u.message.reply_text("⚠️ ≥2 ជម្រើស! <code>ក,ខ,គ</code>",parse_mode=H); return S_PICK
    c=random.choice(items); rk=random.sample(items,len(items))
    await u.message.reply_text(f"🎲 <b>Random Picker</b>\n━━━━━━━━━━━━\n🏆 <code>{c}</code>\n━━━━━━━━━━━━\n"+"\n".join(f"{i}. {x}" for i,x in enumerate(rk,1)),reply_markup=mkb([IKB("🔄",callback_data="menu_picker")],[IKB("🏠",callback_data="back_main")]),parse_mode=H); return END
async def morse(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip(); d=ctx.user_data.get("morse_dir","to")
    r,h,lb=(t2m(t),"Text→Morse","Morse") if d=="to" else(m2t(t),"Morse→Text","Text")
    await u.message.reply_text(f"📡 <b>{h}</b>\n📥 <code>{t[:200]}</code>\n📤 <b>{lb}:</b> <code>{r[:500]}</code>",reply_markup=mkb([IKB("🔄",callback_data="menu_morse")],[IKB("🏠",callback_data="back_main")]),parse_mode=H); return END
async def b64(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text.strip(); d=ctx.user_data.get("b64_dir","encode")
    try: r=base64.b64encode(t.encode()).decode() if d=="encode" else base64.b64decode(t.encode()).decode(); h="Encode" if d=="encode" else "Decode"; err=False
    except Exception as e: r=str(e); h="Error"; err=True
    em="🔐" if d=="encode" else"🔓"
    await u.message.reply_text(f"{em} <b>Base64 {h}</b>\n📥 <code>{t[:200]}</code>\n{'❌' if err else '📤'} <code>{r[:1000]}</code>",reply_markup=mkb([IKB("🔄",callback_data="menu_base64")],[IKB("🏠",callback_data="back_main")]),parse_mode=H); return END
async def fallback(u:Update,_:ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("🤔 <b>ខ្ញុំមិនយល់!</b> វាយ /start:",reply_markup=mm(),parse_mode=H)
def main():
    app=Application.builder().token(BOT_TOKEN).connect_timeout(10).read_timeout(30).write_timeout(30).pool_timeout(10).build()
    TXT=filters.TEXT&~filters.COMMAND; IMG=filters.PHOTO|filters.Document.IMAGE; CB_H=CallbackQueryHandler(cb)
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start",cmd_start),CB_H],
        states={S_QR:[MessageHandler(TXT,qr_input),CB_H],S_SCAN:[MessageHandler(IMG,qr_scan),CB_H],S_STYLE:[MessageHandler(TXT,text_style),CB_H],S_PDF:[MessageHandler(IMG,pdf_photo),CB_H],S_CALC:[CB_H],S_PASS:[MessageHandler(TXT,pw_check),CB_H],S_PICK:[MessageHandler(TXT,picker),CB_H],S_MORSE:[MessageHandler(TXT,morse),CB_H],S_B64:[MessageHandler(TXT,b64),CB_H]},
        fallbacks=[CommandHandler("start",cmd_start),MessageHandler(filters.ALL,fallback)],
        per_message=False,allow_reentry=True,
    ))
    logger.info("🤖 Bot starting..."); app.run_polling(allowed_updates=Update.ALL_TYPES,poll_interval=1.0,drop_pending_updates=True)
if __name__=="__main__": main()
