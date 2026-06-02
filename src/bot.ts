#!/usr/bin/env node
// -*- coding: utf-8 -*-
import { Bot, session, InputFile, type Context, type SessionFlavor } from 'grammy';
import sharp from 'sharp';
import { PDFDocument } from 'pdf-lib';
import QRCode from 'qrcode';
import jsQR from 'jsqr';
import axios from 'axios';

const BOT_TOKEN = process.env.BOT_TOKEN ?? '';
if (!BOT_TOKEN) throw new Error('BOT_TOKEN មិនទាន់កំណត់!');

const logger = {
  info:    (m: string) => console.log(`${new Date().toISOString()}|INFO|${m}`),
  warning: (m: string) => console.warn(`${new Date().toISOString()}|WARNING|${m}`),
  error:   (m: string) => console.error(`${new Date().toISOString()}|ERROR|${m}`),
};

// ── Session / State ────────────────────────────────────────────────────────────
const S_MAIN=0,S_DOC=1,S_STYLE=2,S_PDF=3,S_PDF2IMG=4,S_QR=5,S_QR_CREATE=6,S_QR_SCAN=7,S_PDF_RENAME=8,S_GOLD=9,S_RMBG=10;

interface SessionData {
  state: number;
  mid?: number;
  cid?: number;
  pdfPhotos: Buffer[];
  pdfName?: string;
  pdf2imgFmt?: 'PNG' | 'JPG';
}

type MyCtx = Context & SessionFlavor<SessionData>;

// ── Inline keyboard helpers ────────────────────────────────────────────────────
type IBtn = { text: string; callback_data?: string; url?: string; copy_text?: { text: string } };
type IKM  = { inline_keyboard: IBtn[][] };
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Markup = any;

function mkb(rows: IBtn[][]): Markup { return { inline_keyboard: rows }; }
function ikb(text: string, cb: string): IBtn { return { text, callback_data: cb }; }
function ikbUrl(text: string, url: string): IBtn { return { text, url }; }

// ── Inline keyboards ──────────────────────────────────────────────────────────
const IK_MAIN = mkb([
  [ikb('✍️ រចនាប័ទ្មអក្សរ','style'),   ikb('🗂️ បំប្លែង PDF','doc')],
  [ikb('📷 QR Code','qr'),              ikb('🥇 ហាងឆេងមាស','gold')],
  [ikb('🪄 លុប Background រូបភាព','rmbg')],
  [ikbUrl('🎙️ បង្កើតសំឡេង Ai','https://t.me/limsovannradybot?start=start')],
]);
const IK_DOC = mkb([
  [ikb('🖼️ រូបភាព → PDF','photo_pdf')],
  [ikb('🖼️ PDF → PNG','pdf_png'), ikb('📷 PDF → JPG','pdf_jpg')],
  [ikb('🏠 ម៉ឺនុយមេ','home')],
]);
const IK_QR = mkb([
  [ikb('🔳 បង្កើត QR','qr_create'), ikb('🔍 Scan QR','qr_scan')],
  [ikb('🏠 ម៉ឺនុយមេ','home')],
]);
const IK_CANCEL_MAIN = mkb([[ikb('❌ បោះបង់','cancel_main')]]);
const IK_CANCEL_RMBG = mkb([[ikb('❌ បោះបង់','cancel_main')]]);
const IK_CANCEL_DOC  = mkb([[ikb('❌ បោះបង់','cancel_doc')]]);
const IK_CANCEL_QR   = mkb([[ikb('❌ បោះបង់','cancel_qr')]]);
const IK_PDF_DONE    = mkb([[ikb('🖼️ PDF ថ្មី','photo_pdf'), ikb('🏠 ម៉ឺនុយមេ','home')]]);
const IK_QR_CR_DONE  = mkb([[ikb('🔳 QR ថ្មី','qr_create'), ikb('🔍 Scan QR','qr_scan')],[ikb('🏠 ម៉ឺនុយមេ','home')]]);
const IK_QR_SC_DONE  = mkb([[ikb('🔍 Scan ថ្មី','qr_scan'), ikb('🔳 បង្កើត QR','qr_create')],[ikb('🏠 ម៉ឺនុយមេ','home')]]);

function ikPdf(n: number, name?: string): IKM {
  const lbl = `✅ បង្កើត PDF (${n} រូប)` + (name ? ` 📄 "${name}"` : '');
  return mkb([[ikb(lbl,'pdf_build'), ikb('✏️ ប្តូរឈ្មោះ','pdf_rename')],[ikb('❌ បោះបង់','doc')]]);
}
function ikImgDone(fmt: string): IKM {
  return mkb([[ikb(`🔄 ${fmt === 'PNG' ? 'PNG' : 'JPG'} ថ្មី`, fmt==='PNG' ? 'pdf_png' : 'pdf_jpg'), ikb('🏠 ម៉ឺនុយមេ','home')]]);
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function saveMsg(session: SessionData, chatId: number, messageId: number) {
  session.cid = chatId; session.mid = messageId;
}

async function sendMsg(ctx: MyCtx, chatId: number, text: string, kb?: Markup): Promise<{ chat: { id: number }; message_id: number }> {
  const msg = await ctx.api.sendMessage(chatId, text, { reply_markup: kb, parse_mode: 'HTML' });
  saveMsg(ctx.session, chatId, msg.message_id);
  return msg;
}

async function editOrSend(ctx: MyCtx, chatId: number, text: string, kb?: Markup | null) {
  const mid = ctx.session.mid;
  if (mid) {
    try {
      await ctx.api.editMessageText(chatId, mid, text, { reply_markup: kb ?? undefined, parse_mode: 'HTML' });
      return;
    } catch {}
  }
  await sendMsg(ctx, chatId, text, kb ?? undefined);
}

async function downloadFile(ctx: MyCtx, fileId: string): Promise<Buffer> {
  const file = await ctx.api.getFile(fileId);
  const url  = `https://api.telegram.org/file/bot${BOT_TOKEN}/${file.file_path}`;
  const resp = await axios.get<ArrayBuffer>(url, { responseType: 'arraybuffer' });
  return Buffer.from(resp.data);
}

// ── Text style maps ───────────────────────────────────────────────────────────
function rng(u: number, lo: number, hi: number, base: number): Record<string,string> {
  const r: Record<string,string> = {};
  for (let i = lo; i < hi; i++) r[String.fromCodePoint(i)] = String.fromCodePoint(i + u - base);
  return r;
}
function applyMap(t: string, m: Record<string,string>): string {
  return [...t].map(c => m[c] ?? c).join('');
}

const BM  = { ...rng(0x1D400,0x41,0x5B,0x41), ...rng(0x1D41A,0x61,0x7B,0x61), ...rng(0x1D7CE,0x30,0x3A,0x30) };
const IM  = { ...rng(0x1D434,0x41,0x5B,0x41), ...rng(0x1D44E,0x61,0x7B,0x61) };
const BIM = { ...rng(0x1D468,0x41,0x5B,0x41), ...rng(0x1D482,0x61,0x7B,0x61) };
const SM  = { ...rng(0x1D49C,0x41,0x5B,0x41), ...rng(0x1D4B6,0x61,0x7B,0x61) };
const BSM = { ...rng(0x1D4D0,0x41,0x5B,0x41), ...rng(0x1D4EA,0x61,0x7B,0x61) };
const DM  = { ...rng(0x1D538,0x41,0x5B,0x41), ...rng(0x1D552,0x61,0x7B,0x61), ...rng(0x1D7D8,0x30,0x3A,0x30) };
const FM  = { ...rng(0x1D504,0x41,0x5B,0x41), ...rng(0x1D51E,0x61,0x7B,0x61), C:'\u212D', H:'\u210C', I:'\u2111', R:'\u211C', Z:'\u2128' };
const SFM = { ...rng(0x1D5A0,0x41,0x5B,0x41), ...rng(0x1D5BA,0x61,0x7B,0x61), ...rng(0x1D7E2,0x30,0x3A,0x30) };
const MOM = { ...rng(0x1D670,0x41,0x5B,0x41), ...rng(0x1D68A,0x61,0x7B,0x61), ...rng(0x1D7F6,0x30,0x3A,0x30) };
const FW  = { ...rng(0xFF21,0x41,0x5B,0x41),  ...rng(0xFF41,0x61,0x7B,0x61),  ...rng(0xFF10,0x30,0x3A,0x30), ' ':'\u2003' };
const SC: Record<string,string> = {a:'ᴀ',b:'ʙ',c:'ᴄ',d:'ᴅ',e:'ᴇ',f:'ꜰ',g:'ɢ',h:'ʜ',i:'ɪ',j:'ᴊ',k:'ᴋ',l:'ʟ',m:'ᴍ',n:'ɴ',o:'ᴏ',p:'ᴘ',q:'Q',r:'ʀ',s:'ꜱ',t:'ᴛ',u:'ᴜ',v:'ᴠ',w:'ᴡ',x:'x',y:'ʏ',z:'ᴢ'};
const BB: Record<string,string> = { ...rng(0x24B6,0x41,0x5B,0x41), ...rng(0x24D0,0x61,0x7B,0x61), '0':'\u24ea','1':'\u2460','2':'\u2461','3':'\u2462','4':'\u2463','5':'\u2464','6':'\u2465','7':'\u2466','8':'\u2467','9':'\u2468' };
const UD: Record<string,string> = {a:'ɐ',b:'q',c:'ɔ',d:'p',e:'ǝ',f:'ɟ',g:'ƃ',h:'ɥ',i:'ᴉ',j:'ɾ',k:'ʞ',l:'l',m:'ɯ',n:'u',o:'o',p:'d',q:'b',r:'ɹ',s:'s',t:'ʇ',u:'n',v:'ʌ',w:'ʍ',x:'x',y:'ʎ',z:'z',A:'∀',B:'ᗺ',C:'Ɔ',D:'ᗡ',E:'Ǝ',F:'Ⅎ',G:'פ',H:'H',I:'I',J:'ſ',K:'ʞ',L:'˥',M:'W',N:'N',O:'O',P:'Ԁ',Q:'Q',R:'ɹ',S:'S',T:'┴',U:'∩',V:'Λ',W:'M',X:'X',Y:'⅄',Z:'Z','0':'0','1':'Ɩ','2':'ᄅ','3':'Ɛ','4':'ᔭ','5':'ϛ','6':'9','7':'ㄥ','8':'8','9':'6',' ':' '};
const SUPM: Record<string,string> = {a:'ᵃ',b:'ᵇ',c:'ᶜ',d:'ᵈ',e:'ᵉ',f:'ᶠ',g:'ᵍ',h:'ʰ',i:'ⁱ',j:'ʲ',k:'ᵏ',l:'ˡ',m:'ᵐ',n:'ⁿ',o:'ᵒ',p:'ᵖ',q:'q',r:'ʳ',s:'ˢ',t:'ᵗ',u:'ᵘ',v:'ᵛ',w:'ʷ',x:'ˣ',y:'ʸ',z:'ᶻ',A:'ᴬ',B:'ᴮ',C:'ᶜ',D:'ᴰ',E:'ᴱ',F:'ᶠ',G:'ᴳ',H:'ᴴ',I:'ᴵ',J:'ᴶ',K:'ᴷ',L:'ᴸ',M:'ᴹ',N:'ᴺ',O:'ᴼ',P:'ᴾ',Q:'Q',R:'ᴿ',S:'ˢ',T:'ᵀ',U:'ᵁ',V:'\u2c7d',W:'ᵂ',X:'ˣ',Y:'ʸ',Z:'ᶻ','0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹'};
const SBM = { ...rng(0x1D5D4,0x41,0x5B,0x41), ...rng(0x1D5EE,0x61,0x7B,0x61), ...rng(0x1D7EC,0x30,0x3A,0x30) };
const SIM = { ...rng(0x1D608,0x41,0x5B,0x41), ...rng(0x1D622,0x61,0x7B,0x61) };
const SBIM= { ...rng(0x1D63C,0x41,0x5B,0x41), ...rng(0x1D656,0x61,0x7B,0x61) };
const BFM = { ...rng(0x1D56C,0x41,0x5B,0x41), ...rng(0x1D586,0x61,0x7B,0x61) };
const RI: Record<string,string> = { ...Object.fromEntries(Array.from({length:26},(_,i)=>[String.fromCodePoint(0x41+i),String.fromCodePoint(0x1F1E6+i)])), ...Object.fromEntries(Array.from({length:26},(_,i)=>[String.fromCodePoint(0x61+i),String.fromCodePoint(0x1F1E6+i)])) };
const SQM: Record<string,string> = { ...Object.fromEntries(Array.from({length:26},(_,i)=>[String.fromCodePoint(0x41+i),String.fromCodePoint(0x1F130+i)])), ...Object.fromEntries(Array.from({length:26},(_,i)=>[String.fromCodePoint(0x61+i),String.fromCodePoint(0x1F130+i)])) };
const PAR: Record<string,string> = { ...Object.fromEntries(Array.from({length:26},(_,i)=>[String.fromCodePoint(0x61+i),String.fromCodePoint(0x249C+i)])), ...Object.fromEntries(Array.from({length:26},(_,i)=>[String.fromCodePoint(0x41+i),String.fromCodePoint(0x249C+i)])) };
const SUBM: Record<string,string> = {a:'ₐ',e:'ₑ',h:'ₕ',i:'ᵢ',j:'ⱼ',k:'ₖ',l:'ₗ',m:'ₘ',n:'ₙ',o:'ₒ',p:'ₚ',r:'ᵣ',s:'ₛ',t:'ₜ',u:'ᵤ',v:'ᵥ',x:'ₓ','0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉'};

type StyleEntry = [string, (t: string) => string];
const TS: StyleEntry[] = [
  ['ㅤ',                  () => 'ㅤ'],
  ['𝗕𝗼𝗹𝗱',              t => applyMap(t, BM)],
  ['𝘐𝘵𝘢𝘭𝘪𝘤',            t => applyMap(t, IM)],
  ['𝑩𝒐𝒍𝒅 𝑰𝒕𝒂𝒍𝒊𝒄',      t => applyMap(t, BIM)],
  ['𝒮𝒸𝓇𝒾𝓅𝓉',            t => applyMap(t, SM)],
  ['𝓑𝓸𝓵𝓭 𝓢𝓬𝓻𝓲𝓹𝓽',     t => applyMap(t, BSM)],
  ['𝔻𝕠𝕦𝕓𝕝𝕖',            t => applyMap(t, DM)],
  ['𝔊𝔬𝔱𝔥𝔦𝔠',            t => applyMap(t, FM)],
  ['𝕭𝖔𝖑𝖉 𝕱𝖗𝖆𝖐𝖙𝖚𝖗',    t => applyMap(t, BFM)],
  ['𝖲𝖺𝗇𝗌',               t => applyMap(t, SFM)],
  ['𝗦𝗮𝗻𝘀 𝗕𝗼𝗹𝗱',         t => applyMap(t, SBM)],
  ['𝘚𝘢𝘯𝘴 𝘐𝘵𝘢𝘭𝘪𝘤',       t => applyMap(t, SIM)],
  ['𝙎𝙖𝙣𝙨 𝘽𝙤𝙡𝙙 𝙄𝙩𝙖𝙡𝙞𝙘', t => applyMap(t, SBIM)],
  ['𝙼𝚘𝚗𝚘',               t => applyMap(t, MOM)],
  ['Ｆｕｌｌｗｉｄｔｈ',   t => applyMap(t, FW)],
  ['ˢᵘᵖᵉʳˢᶜʳⁱᵖᵗ',        t => applyMap(t, SUPM)],
  ['ₛᵤᵦₛcᵣᵢₚₜ',           t => applyMap(t, SUBM)],
  ['Sᴍᴀʟʟ Cᴀᴘꜱ',         t => applyMap(t.toLowerCase(), SC)],
  ['Ⓑⓤⓑⓑⓛⓔ',           t => applyMap(t, BB)],
  ['🄰🄱🄲 Squared',        t => applyMap(t, SQM)],
  ['⒜⒝⒞ Paren',           t => applyMap(t.toLowerCase(), PAR)],
  ['🇷🇪🇬🇮🇴🇳',             t => applyMap(t, RI)],
  ['uʍop ǝpᴉsdn',         t => [...applyMap(t, UD)].reverse().join('')],
  ['S\u0336t\u0336r\u0336i\u0336k\u0336e\u0336',   t => [...t].map(c => c+'\u0336').join('')],
  ['U\u0332n\u0332d\u0332e\u0332r\u0332',           t => [...t].map(c => c+'\u0332').join('')],
  ['D\u0333o\u0333u\u0333b\u0333l\u0333e\u0333',    t => [...t].map(c => c+'\u0333').join('')],
  ['O\u0305v\u0305e\u0305r\u0305l\u0305i\u0305n\u0305e\u0305', t => [...t].map(c => c+'\u0305').join('')],
  ['T\u0303i\u0303l\u0303d\u0303e\u0303',           t => [...t].map(c => c+'\u0303').join('')],
  ['S\u0338l\u0338a\u0338s\u0338h\u0338',           t => [...t].map(c => c+'\u0338').join('')],
  ['W\u0330a\u0330v\u0330y\u0330',                  t => [...t].map(c => c+'\u0330').join('')],
  ['D\u0307o\u0307t\u0307t\u0307e\u0307d\u0307',    t => [...t].map(c => c+'\u0307').join('')],
  ['G\u0354l\u0354i\u0354t\u0354c\u0354h\u0354',    t => [...t].map((c,i) => c+['\u0315','\u035c','\u0355'][i%3]).join('')],
];

// ── /start ────────────────────────────────────────────────────────────────────
async function cmdStart(ctx: MyCtx) {
  ctx.session = { state: S_MAIN, pdfPhotos: [] };
  const msg = await ctx.reply(
    '🌱 <b>RADY BOT</b>\n' +
    'សូមស្វាគមន៍! ជ្រើសរើសមុខងារដែលអ្នកចង់ប្រើ:\n\n' +
    '✍️  រចនាប័ទ្មអក្សរ\n' +
    '🗂️  បំប្លែង PDF\n' +
    '📷  QR Code\n' +
    '🥇  ហាងឆេងមាស\n' +
    '🪄  លុប Background រូបភាព',
    { reply_markup: IK_MAIN, parse_mode: 'HTML' },
  );
  saveMsg(ctx.session, msg.chat.id, msg.message_id);
}

const HOME_TEXT =
  '🌱 <b>RADY BOT</b>\n' +
  'សូមស្វាគមន៍! ជ្រើសរើសមុខងារដែលអ្នកចង់ប្រើ:\n\n' +
  '✍️  រចនាប័ទ្មអក្សរ\n' +
  '🗂️  បំប្លែង PDF\n' +
  '📷  QR Code\n' +
  '🥇  ហាងឆេងមាស\n' +
  '🪄  លុប Background រូបភាព';

// ── Unified callback handler ───────────────────────────────────────────────────
async function cbHandler(ctx: MyCtx) {
  const q   = ctx.callbackQuery!;
  const d   = q.data ?? '';
  const cid = q.message!.chat.id;
  await ctx.answerCallbackQuery();
  saveMsg(ctx.session, cid, q.message!.message_id);

  if (d === 'home') {
    ctx.session = { state: S_MAIN, pdfPhotos: [] };
    saveMsg(ctx.session, cid, q.message!.message_id);
    await ctx.editMessageText(HOME_TEXT, { reply_markup: IK_MAIN, parse_mode: 'HTML' });
    ctx.session.state = S_MAIN; return;
  }

  if (d === 'style' || d === 'style_new') {
    await ctx.editMessageText(
      '✍️ <b>រចនាប័ទ្មអក្សរ</b>\n\nបំប្លែងអក្សរឡាតាំងទៅជាពុម្ពអក្សរពិសេស\nBold · Italic · Script · Bubble · Upside-down និងច្រើនទៀត\n\n✏️ <b>វាយអក្សរខាងក្រោម:</b>',
      { reply_markup: IK_CANCEL_MAIN, parse_mode: 'HTML' },
    );
    ctx.session.state = S_STYLE; return;
  }

  if (d === 'cancel_main') {
    ctx.session = { state: S_MAIN, pdfPhotos: [] };
    saveMsg(ctx.session, cid, q.message!.message_id);
    await ctx.editMessageText(HOME_TEXT, { reply_markup: IK_MAIN, parse_mode: 'HTML' });
    ctx.session.state = S_MAIN; return;
  }

  if (d === 'doc' || d === 'cancel_doc') {
    ctx.session.pdfPhotos = []; delete ctx.session.pdfName;
    await ctx.editMessageText(
      '🗂️ <b>បំប្លែង PDF</b>\n\n🖼️  រូបភាព → PDF — ផ្សំរូបភាពច្រើនទៅជា PDF តែមួយ\n🖼️  PDF → PNG — បំប្លែង PDF ម្តាមទំព័រជារូបភាព PNG\n📷  PDF → JPG — បំប្លែង PDF ម្តាមទំព័រជារូបភាព JPG\n\n👇 <b>ចុចជ្រើសរើស:</b>',
      { reply_markup: IK_DOC, parse_mode: 'HTML' },
    );
    ctx.session.state = S_DOC; return;
  }

  if (d === 'cancel_qr') {
    await ctx.editMessageText(
      '📷 <b>QR Code</b>\n\n🔳  បង្កើត QR — បង្កើត QR Code HD 2048×2048\n🔍  Scan QR — Decode Link ឬ Text ចេញពី QR\n\n👇 <b>ចុចជ្រើសរើស:</b>',
      { reply_markup: IK_QR, parse_mode: 'HTML' },
    );
    ctx.session.state = S_QR; return;
  }

  if (d === 'photo_pdf') {
    ctx.session.pdfPhotos = []; delete ctx.session.mid;
    await ctx.editMessageText(
      '🖼️ <b>រូបភាព → PDF</b>\n\nUpload រូបភាពម្តាមដុំ Bot នឹងផ្សំទៅជា PDF តែមួយ\nFormat: JPG · PNG · WEBP\n\n📤 <b>ចាប់ផ្ដើម Upload រូបភាព:</b>',
      { reply_markup: IK_CANCEL_DOC, parse_mode: 'HTML' },
    );
    ctx.session.state = S_PDF; return;
  }

  if (d === 'pdf_png' || d === 'pdf_jpg') {
    ctx.session.pdf2imgFmt = d === 'pdf_png' ? 'PNG' : 'JPG';
    const lbl = d === 'pdf_png' ? 'PNG' : 'JPG';
    const ico = d === 'pdf_png' ? '🖼️' : '📷';
    await ctx.editMessageText(
      `${ico} <b>PDF → ${lbl}</b>\n\nUpload ឯកសារ PDF Bot នឹងបំប្លែងម្តាមទំព័រ\nជារូបភាព <b>${lbl}</b> គុណភាពខ្ពស់ — 150 DPI\n\n📎 <b>Upload ឯកសារ PDF:</b>`,
      { reply_markup: IK_CANCEL_DOC, parse_mode: 'HTML' },
    );
    ctx.session.state = S_PDF2IMG; return;
  }

  if (d === 'pdf_build') { await pdfBuild(ctx); return; }

  if (d === 'pdf_rename') {
    const n    = ctx.session.pdfPhotos.length;
    const name = ctx.session.pdfName;
    const cur  = name ? `\n📄 ឈ្មោះបច្ចុប្បន្ន: <b>${name}</b>` : '';
    await ctx.editMessageText(
      `✏️ <b>ប្តូរឈ្មោះ PDF</b>\n\nPDF នេះមាន ${n} រូបភាព${cur}\n<i>មិនចាំបាច់វាយ .pdf — Bot នឹងបន្ថែមឱ្យ</i>\n\n📝 <b>វាយឈ្មោះខាងក្រោម:</b>`,
      { reply_markup: mkb([[ikb('❌ បោះបង់','cancel_rename')]]), parse_mode: 'HTML' },
    );
    ctx.session.state = S_PDF_RENAME; return;
  }

  if (d === 'cancel_rename') {
    const n    = ctx.session.pdfPhotos.length;
    const name = ctx.session.pdfName;
    const txt  = `🖼️ <b>បានទទួល ${n} រូប</b>\nUpload បន្ថែម ឬ ចុច <b>បង្កើត PDF</b>`;
    await ctx.editMessageText(txt, { reply_markup: ikPdf(n, name) as Markup, parse_mode: 'HTML' });
    ctx.session.state = S_PDF; return;
  }

  if (d === 'qr') {
    await ctx.editMessageText(
      '📷 <b>QR Code</b>\n\n🔳  បង្កើត QR — បង្កើត QR Code HD 2048×2048\n🔍  Scan QR — Decode Link ឬ Text ចេញពី QR\n\n👇 <b>ចុចជ្រើសរើស:</b>',
      { reply_markup: IK_QR, parse_mode: 'HTML' },
    );
    ctx.session.state = S_QR; return;
  }

  if (d === 'qr_create') {
    await ctx.editMessageText(
      '🔳 <b>បង្កើត QR Code</b>\n\nបង្កើត QR Code HD ទំហំ <b>2048×2048</b>\nអាចប្រើជាមួយ Link · Text · ព័ត៌មានគ្រប់ប្រភេទ\n\n✏️ <b>វាយ Link ឬ Text ខាងក្រោម:</b>',
      { reply_markup: IK_CANCEL_QR, parse_mode: 'HTML' },
    );
    ctx.session.state = S_QR_CREATE; return;
  }

  if (d === 'qr_scan') {
    await ctx.editMessageText(
      '🔍 <b>Scan QR Code</b>\n\nUpload រូបភាពដែលមាន QR Code\nBot នឹង Decode យក <b>Link</b> ឬ <b>Text</b> ឱ្យអ្នក\n\n📤 <b>Upload រូបភាព QR:</b>',
      { reply_markup: IK_CANCEL_QR, parse_mode: 'HTML' },
    );
    ctx.session.state = S_QR_SCAN; return;
  }

  if (d === 'rmbg') {
    await ctx.editMessageText(
      '🪄 <b>លុប Background រូបភាព</b>\n\nUpload រូបភាព Bot នឹងលុប Background ចេញ\nលទ្ធផលជា PNG មាន Background ថ្លា\n\n📤 <b>Upload រូបភាព:</b>',
      { reply_markup: IK_CANCEL_RMBG, parse_mode: 'HTML' },
    );
    ctx.session.state = S_RMBG; return;
  }

  if (d === 'gold' || d === 'cancel_gold' || d === 'gold_live') {
    await ctx.editMessageText('⏳ <b>កំពុងទាញយកទិន្ន័យ...</b>', { parse_mode: 'HTML' });
    const spots = await fetchAllSpots();
    const IK_LIVE = mkb([[ikb('🔄 ធ្វើបន្ទាប់','gold_live')],[ikb('🏠 ម៉ឺនុយមេ','home')]]);
    const txt =
      '📊 <b>ហាងឆេងឥឡូវនេះ (ពិភពលោក)</b>\n' +
      fmtPrice(spots.gold,   'មាស',   '🥇', spots.gold_chg,   spots.gold_pct)   + '\n' +
      fmtPrice(spots.silver, 'ប្រាក់', '🥈', spots.silver_chg, spots.silver_pct) + '\n' +
      fmtPrice(spots.plat,   'ផ្លាទីន','🔩', spots.plat_chg,   spots.plat_pct)   + '\n';
    await ctx.editMessageText(txt, { reply_markup: IK_LIVE, parse_mode: 'HTML' });
    ctx.session.state = S_GOLD; return;
  }

  await ctx.editMessageText('👇 <b>ជ្រើសរើស:</b>', { reply_markup: IK_MAIN, parse_mode: 'HTML' });
  ctx.session.state = S_MAIN;
}

// ── Text style handler ────────────────────────────────────────────────────────
async function styleHandler(ctx: MyCtx) {
  const t   = ctx.message!.text!;
  const cid = ctx.message!.chat.id;
  const mid = ctx.session.mid;
  const btns: IBtn[] = TS.map(([lbl, fn]) => ({ text: lbl, copy_text: { text: fn(t) } }));
  const rows: IBtn[][] = [];
  for (let i = 0; i < btns.length; i += 2)
    rows.push(i + 1 < btns.length ? [btns[i], btns[i+1]] : [btns[i]]);
  rows.push([ikb('✍️ ដំណើរការថ្មី','style_new'), ikb('🏠 ម៉ឺនុយមេ','home')]);
  const kb  = mkb(rows);
  const txt = `✍️ <b>Style:</b> <code>${t}</code>\n👇 ចុច button ដើម្បី <b>Copy</b>`;
  try { await ctx.api.deleteMessage(cid, ctx.message!.message_id); } catch {}
  if (mid) {
    try {
      await ctx.api.editMessageText(cid, mid, txt, { reply_markup: kb, parse_mode: 'HTML' });
      ctx.session.state = S_STYLE; return;
    } catch {}
  }
  const msg = await ctx.api.sendMessage(cid, txt, { reply_markup: kb, parse_mode: 'HTML' });
  saveMsg(ctx.session, cid, msg.message_id);
  ctx.session.state = S_STYLE;
}

// ── Image → PDF ───────────────────────────────────────────────────────────────
async function pdfPhoto(ctx: MyCtx) {
  const msg = ctx.message!;
  const cid = msg.chat.id;
  const p   = msg.photo?.at(-1);
  const dc  = msg.document;
  if (!p && !dc) {
    await editOrSend(ctx, cid, '⚠️ Upload រូបភាព!', IK_CANCEL_DOC);
    ctx.session.state = S_PDF; return;
  }
  const fileId = p ? p.file_id : dc!.file_id;
  const raw    = await downloadFile(ctx, fileId);
  ctx.session.pdfPhotos.push(raw);
  const n    = ctx.session.pdfPhotos.length;
  const name = ctx.session.pdfName;
  const txt  = `🖼️ <b>បានទទួល ${n} រូប</b>\nUpload បន្ថែម ឬ ចុច <b>បង្កើត PDF</b>`;
  const mid  = ctx.session.mid;
  if (n === 1 && mid) {
    try { await ctx.api.deleteMessage(cid, mid); } catch {}
    delete ctx.session.mid;
    const m = await ctx.api.sendMessage(cid, txt, { reply_markup: ikPdf(n, name) as Markup, parse_mode: 'HTML' });
    saveMsg(ctx.session, cid, m.message_id);
    ctx.session.state = S_PDF; return;
  }
  if (mid) {
    try {
      await ctx.api.editMessageText(cid, mid, txt, { reply_markup: ikPdf(n, name) as Markup, parse_mode: 'HTML' });
      ctx.session.state = S_PDF; return;
    } catch {}
  }
  const m = await ctx.api.sendMessage(cid, txt, { reply_markup: ikPdf(n, name) as Markup, parse_mode: 'HTML' });
  saveMsg(ctx.session, cid, m.message_id);
  ctx.session.state = S_PDF;
}

async function pdfBuild(ctx: MyCtx) {
  const q      = ctx.callbackQuery!;
  const photos = ctx.session.pdfPhotos;
  const cid    = q.message!.chat.id;
  if (!photos.length) {
    await ctx.editMessageText('⚠️ មិនទាន់មានរូបភាព!', { reply_markup: IK_CANCEL_DOC, parse_mode: 'HTML' });
    ctx.session.state = S_PDF; return;
  }
  await ctx.editMessageText(`⏳ <b>កំពុងបំប្លែង ${photos.length} រូប → PDF...</b>`, { parse_mode: 'HTML' });

  const pdfDoc = await PDFDocument.create();
  for (const raw of photos) {
    const jpegBuf = await sharp(raw).jpeg({ quality: 95 }).toBuffer();
    const meta    = await sharp(raw).metadata();
    const w = meta.width!, h = meta.height!;
    const mmW = w * 25.4 / 96, mmH = h * 25.4 / 96;
    const ptW = mmW * 2.8346, ptH = mmH * 2.8346;
    const img  = await pdfDoc.embedJpg(jpegBuf);
    const page = pdfDoc.addPage([ptW, ptH]);
    page.drawImage(img, { x: 0, y: 0, width: ptW, height: ptH });
  }

  const rawName  = (ctx.session.pdfName ?? 'KhmerBot').trim().replace(/\.+$/, '').replace(/\//g, '_') || 'KhmerBot';
  const fname    = rawName + '.pdf';
  const pdfBytes = await pdfDoc.save();
  await ctx.api.sendDocument(cid, new InputFile(Buffer.from(pdfBytes), fname), {
    caption: `✅ <b>PDF បង្កើតជោគជ័យ!</b>\n📄 ${fname}  |  🖼️ ${photos.length} ទំព័រ`,
    parse_mode: 'HTML',
  });
  try { await ctx.api.deleteMessage(cid, q.message!.message_id); } catch {}
  const m = await ctx.api.sendMessage(cid, '👇 <b>ជ្រើសរើស:</b>', { reply_markup: IK_MAIN, parse_mode: 'HTML' });
  ctx.session.pdfPhotos = []; delete ctx.session.pdfName;
  saveMsg(ctx.session, cid, m.message_id);
  ctx.session.state = S_MAIN;
}

// ── PDF → Image ───────────────────────────────────────────────────────────────
async function pdf2img(ctx: MyCtx) {
  const msg = ctx.message!;
  const dc  = msg.document;
  const fmt = ctx.session.pdf2imgFmt ?? 'PNG';
  const cid = msg.chat.id;
  const isPdf = dc?.mime_type === 'application/pdf' || dc?.file_name?.toLowerCase().endsWith('.pdf');
  if (!dc || !isPdf) {
    await editOrSend(ctx, cid, '⚠️ Upload ឯកសារ <b>PDF</b>!', IK_CANCEL_DOC);
    ctx.session.state = S_PDF2IMG; return;
  }
  try {
    await editOrSend(ctx, cid, `⏳ <b>កំពុងបំប្លែង PDF → ${fmt}...</b>`);
    const raw    = await downloadFile(ctx, dc.file_id);
    const mupdfMod = await import('mupdf');
    const mupdf = (mupdfMod as any).default ?? mupdfMod;
    const doc    = mupdf.Document.openDocument(raw, 'application/pdf');
    const total  = doc.countPages();
    const scale  = 150 / 72;
    const matrix: [number,number,number,number,number,number] = [scale, 0, 0, scale, 0, 0];

    for (let i = 0; i < total; i++) {
      const page    = doc.loadPage(i);
      const pixmap  = page.toPixmap(matrix, mupdf.ColorSpace.DeviceRGB, false, true);
      const pngData: Uint8Array = pixmap.asPNG();
      let   buf: Buffer;
      const ext = fmt.toLowerCase();
      if (fmt === 'PNG') {
        buf = Buffer.from(pngData);
      } else {
        buf = await sharp(Buffer.from(pngData)).jpeg({ quality: 90 }).toBuffer();
      }
      const name = `page_${String(i+1).padStart(2,'0')}.${ext}`;
      const isLast = i === total - 1;
      const cap  = `✅ <b>${total===1 ? 'បំប្លែងជោគជ័យ! 1 ទំព័រ' : isLast ? `រួចរាល់! ${total} ទំព័រ → ${fmt}` : `ទំព័រ ${i+1}/${total}`}</b>`;
      await ctx.api.sendDocument(cid, new InputFile(buf, name), { caption: cap, parse_mode: 'HTML' });
    }
    doc.destroy?.();
    const m = await ctx.api.sendMessage(cid, '👇 <b>ជ្រើសរើស:</b>', { reply_markup: IK_MAIN, parse_mode: 'HTML' });
    saveMsg(ctx.session, cid, m.message_id);
  } catch (e) {
    logger.error(`pdf2img: ${e}`);
    await editOrSend(ctx, cid, '❌ <b>មានបញ្ហា! ព្យាយាមម្ដងទៀត</b>', IK_CANCEL_DOC);
  }
  ctx.session.state = S_MAIN;
}

// ── QR create ─────────────────────────────────────────────────────────────────
async function qrCreate(ctx: MyCtx) {
  const t   = ctx.message!.text!;
  const cid = ctx.message!.chat.id;
  const CHUNK = 2800;
  const rawBytes = Buffer.from(t, 'utf-8');
  const chunks: string[] = [];
  for (let i = 0; i < rawBytes.length; i += CHUNK)
    chunks.push(rawBytes.slice(i, i+CHUNK).toString('utf-8'));
  const total = chunks.length;
  try {
    const loadingMsg = await ctx.api.sendMessage(cid, `⏳ <b>កំពុងបង្កើត ${total} QR Code${total>1?'s':''}...</b>`, { parse_mode: 'HTML' });
    for (let idx = 0; idx < chunks.length; idx++) {
      const chunk = chunks[idx];
      let buf: Buffer | null = null;
      for (const ec of ['H','Q','M','L'] as const) {
        try {
          const raw = await QRCode.toBuffer(chunk, {
            errorCorrectionLevel: ec, width: 2048, margin: 1,
            color: { dark: '#000000', light: '#FFFFFF' },
          });
          buf = await sharp(raw).resize(2048, 2048, { kernel: 'nearest' }).png({ compressionLevel: 1 }).toBuffer();
          break;
        } catch {}
      }
      if (!buf) throw new Error(`chunk ${idx+1} failed`);
      const fname = `QRCode_HD${total>1?`_p${idx+1}`:''}.png`;
      await ctx.api.sendDocument(cid, new InputFile(buf, fname));
    }
    try { await ctx.api.deleteMessage(cid, loadingMsg.message_id); } catch {}
    const mid = ctx.session.mid;
    if (mid) { try { await ctx.api.deleteMessage(cid, mid); } catch {} delete ctx.session.mid; }
    try { await ctx.api.deleteMessage(cid, ctx.message!.message_id); } catch {}
    const m = await ctx.api.sendMessage(cid, '👇 <b>ជ្រើសរើស:</b>', { reply_markup: IK_MAIN, parse_mode: 'HTML' });
    saveMsg(ctx.session, cid, m.message_id);
  } catch (e) {
    logger.error(`qr_create: ${e}`);
    await editOrSend(ctx, cid, '❌ <b>មានបញ្ហា! ព្យាយាមម្ដងទៀត</b>', IK_CANCEL_QR);
  }
  ctx.session.state = S_MAIN;
}

// ── QR scan ───────────────────────────────────────────────────────────────────
async function qrScan(ctx: MyCtx) {
  const msg = ctx.message!;
  const p   = msg.photo?.at(-1);
  const dc  = msg.document;
  const cid = msg.chat.id;
  if (!p && !dc) {
    await editOrSend(ctx, cid, '⚠️ Upload <b>រូបភាព QR</b>!', IK_CANCEL_QR);
    ctx.session.state = S_QR_SCAN; return;
  }
  try {
    const raw     = await downloadFile(ctx, p ? p.file_id : dc!.file_id);
    const { data, info } = await sharp(raw).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
    const result  = jsQR(new Uint8ClampedArray(data), info.width, info.height);
    const results2: string[] = [];
    if (result) results2.push(result.data);
    if (!results2.length) {
      await editOrSend(ctx, cid, '❌ <b>រកមិនឃើញ QR Code!</b>\nសូម Upload រូបភាពច្បាស់ជាង', IK_CANCEL_QR);
      ctx.session.state = S_QR_SCAN; return;
    }
    const lines = results2.map((d,i) => `📌 <b>លទ្ធផលទី ${i+1}:</b>\n<code>${d}</code>`).join('\n\n');
    const mid   = ctx.session.mid;
    if (mid) { try { await ctx.api.deleteMessage(cid, mid); } catch {} delete ctx.session.mid; }
    try { await ctx.api.deleteMessage(cid, msg.message_id); } catch {}
    await ctx.api.sendMessage(cid, `✅ <b>Scan QR ជោគជ័យ!</b> (${results2.length} QR)\n━━━━━━━━━\n${lines}`, { parse_mode: 'HTML' });
    const m = await ctx.api.sendMessage(cid, '👇 <b>ជ្រើសរើស:</b>', { reply_markup: IK_MAIN, parse_mode: 'HTML' });
    saveMsg(ctx.session, cid, m.message_id);
  } catch (e) {
    logger.error(`qr_scan: ${e}`);
    await editOrSend(ctx, cid, '❌ <b>មានបញ្ហា! ព្យាយាមម្ដងទៀត</b>', IK_CANCEL_QR);
  }
  ctx.session.state = S_MAIN;
}

// ── PDF rename ────────────────────────────────────────────────────────────────
async function pdfRenameHandler(ctx: MyCtx) {
  const name = ctx.message!.text!.trim();
  ctx.session.pdfName = name;
  const n   = ctx.session.pdfPhotos.length;
  const cid = ctx.message!.chat.id;
  try { await ctx.api.deleteMessage(cid, ctx.message!.message_id); } catch {}
  const txt = `🖼️ <b>បានទទួល ${n} រូប</b>\nUpload បន្ថែម ឬ ចុច <b>បង្កើត PDF</b>`;
  const mid = ctx.session.mid;
  if (mid) {
    try {
      await ctx.api.editMessageText(cid, mid, txt, { reply_markup: ikPdf(n, name) as Markup, parse_mode: 'HTML' });
      ctx.session.state = S_PDF; return;
    } catch {}
  }
  const m = await ctx.api.sendMessage(cid, txt, { reply_markup: ikPdf(n, name) as Markup, parse_mode: 'HTML' });
  saveMsg(ctx.session, cid, m.message_id);
  ctx.session.state = S_PDF;
}

// ── Gold live prices ──────────────────────────────────────────────────────────
const CHI = 3.75, DOM = 37.5, OZ = 31.1035;

interface SpotData {
  gold: number|null; silver: number|null; plat: number|null;
  gold_chg: number|null; silver_chg: number|null; plat_chg: number|null;
  gold_pct: number|null; silver_pct: number|null; plat_pct: number|null;
}

async function fetchAllSpots(): Promise<SpotData> {
  const empty: SpotData = { gold:null, silver:null, plat:null, gold_chg:null, silver_chg:null, plat_chg:null, gold_pct:null, silver_pct:null, plat_pct:null };
  try {
    const hdrs = { 'User-Agent':'Mozilla/5.0','Content-Type':'application/json','Origin':'https://www.tradingview.com','Referer':'https://www.tradingview.com/' };
    const body = { symbols:{ tickers:['TVC:GOLD','TVC:SILVER','TVC:PLATINUM'], query:{types:[]} }, columns:['close','change_abs','change'] };
    const resp = await axios.post('https://scanner.tradingview.com/global/scan', body, { headers: hdrs, timeout: 8000 });
    const rows: Record<string,[number|null,number|null,number|null]> = {};
    for (const item of resp.data?.data ?? []) rows[item.s] = item.d;
    const v = (k: string) => rows[k] ?? [null,null,null];
    const [gd,sd,pd] = [v('TVC:GOLD'),v('TVC:SILVER'),v('TVC:PLATINUM')];
    return { gold:gd[0],silver:sd[0],plat:pd[0], gold_chg:gd[1],silver_chg:sd[1],plat_chg:pd[1], gold_pct:gd[2],silver_pct:sd[2],plat_pct:pd[2] };
  } catch (e) {
    logger.warning(`fetchAllSpots: ${e}`); return empty;
  }
}

function fmtPrice(usd: number|null, label: string, emoji: string, chg?: number|null, pct?: number|null): string {
  if (usd == null) return `${emoji} <b>ហាងឆេង${label}</b>\nដំឡឹង: N/A\nជី: N/A\nអោន: N/A`;
  const domVal = usd * (DOM/OZ), chiVal = usd * (CHI/OZ);
  const d = (v: number) => `$${v.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})}`;
  return `${emoji} <b>ហាងឆេង${label}</b>\n  ដំឡឹង : <b>${d(domVal)}</b>\n  ជី        : <b>${d(chiVal)}</b>\n  អោន    : <b>${d(usd)}</b>`;
}

// ── Remove background ─────────────────────────────────────────────────────────
async function rmbgHandler(ctx: MyCtx) {
  const msg = ctx.message!;
  const cid = msg.chat.id;
  const p   = msg.photo?.at(-1);
  const dc  = msg.document;
  try {
    await editOrSend(ctx, cid, '⏳ <b>កំពុងដំណើរការ...</b>', null);
    const raw = await downloadFile(ctx, p ? p.file_id : dc!.file_id);
    const { removeBackground } = await import('@imgly/background-removal-node');
    const blob    = await removeBackground(raw) as Blob;
    const arrBuf  = await blob.arrayBuffer();
    const outBuf  = Buffer.from(arrBuf);
    try { await ctx.api.deleteMessage(cid, msg.message_id); } catch {}
    const mid = ctx.session.mid;
    if (mid) { try { await ctx.api.deleteMessage(cid, mid); } catch {} }
    const IK_RMBG_DONE = mkb([[ikb('🪄 លុប Background ថ្មី','rmbg')],[ikb('🏠 ម៉ឺនុយមេ','home')]]);
    await ctx.api.sendDocument(cid, new InputFile(outBuf, 'no_background.png'), {
      caption: '✅ <b>លុប Background រួចហើយ!</b>\nរូបភាពជា PNG Background ថ្លា', parse_mode: 'HTML',
    });
    const m = await ctx.api.sendMessage(cid, '👇 <b>ជ្រើសរើស:</b>', { reply_markup: IK_RMBG_DONE, parse_mode: 'HTML' });
    saveMsg(ctx.session, cid, m.message_id);
  } catch (e) {
    logger.error(`rmbg error: ${e}`);
    await editOrSend(ctx, cid, '❌ <b>មានបញ្ហា! ព្យាយាមម្ដងទៀត</b>', IK_CANCEL_RMBG);
  }
  ctx.session.state = S_MAIN;
}

// ── Fallback ──────────────────────────────────────────────────────────────────
async function fallbackHandler(ctx: MyCtx) {
  ctx.session = { state: S_MAIN, pdfPhotos: [] };
  const chatId = ctx.message?.chat.id ?? ctx.chat?.id;
  if (!chatId) return;
  const m = await ctx.api.sendMessage(chatId, '👇 <b>ជ្រើសរើស:</b>', { reply_markup: IK_MAIN, parse_mode: 'HTML' });
  saveMsg(ctx.session, chatId, m.message_id);
}

// ── Build bot ─────────────────────────────────────────────────────────────────
export function buildApp() {
  const bot = new Bot<MyCtx>(BOT_TOKEN);

  bot.use(session({
    initial: (): SessionData => ({ state: S_MAIN, pdfPhotos: [] }),
  }));

  bot.command('start', cmdStart);

  bot.on('callback_query:data', cbHandler);

  bot.on('message:text', async (ctx) => {
    switch (ctx.session.state) {
      case S_STYLE:      return styleHandler(ctx);
      case S_QR_CREATE:  return qrCreate(ctx);
      case S_PDF_RENAME: return pdfRenameHandler(ctx);
      default:           return fallbackHandler(ctx);
    }
  });

  bot.on(['message:photo', 'message:document'], async (ctx) => {
    switch (ctx.session.state) {
      case S_PDF:     return pdfPhoto(ctx);
      case S_PDF2IMG: return pdf2img(ctx);
      case S_QR_SCAN: return qrScan(ctx);
      case S_RMBG:    return rmbgHandler(ctx);
      default:        return fallbackHandler(ctx);
    }
  });

  return bot;
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  const bot = buildApp();
  logger.info('🤖 Bot កំពុង Start...');
  await bot.start({ drop_pending_updates: true, allowed_updates: ['message','callback_query'] });
}

export { BOT_TOKEN };

main().catch(e => { logger.error(`Fatal: ${e}`); process.exit(1); });
