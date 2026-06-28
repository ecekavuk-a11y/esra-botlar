import os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- AYARLAR ---
BOT_TOKEN = os.environ.get("ODEME_BOT_TOKEN", "")
ADMIN_ID = 5019918710

# Ödeme bilgileri
IBAN = "TR49 0082 9000 0949 1261 8500 57"
IBAN_AD = "İsra Soğukpınar"
PAPARA = "1261850057"

# Fiyatlar
VIP_FIYATLAR = """💎 <b>VIP Üyelik Fiyatları</b>

🥉 <b>1 Aylık</b> → <b>1.500₺</b>
🥈 <b>3 Aylık</b> → <b>3.600₺</b>
🥇 <b>Ömür Boyu</b> → <b>9.900₺</b>"""

SHOW_FIYATLAR = """🔥 <b>Özel / Sanal Şov Fiyatları</b>

⏱️ <b>5 dakika</b> → <b>500₺</b>
⏱️ <b>15 dakika</b> → <b>1.500₺</b>
⏱️ <b>30 dakika</b> → <b>3.000₺</b>

<i>Özel şov tamamen özel, birebir, canlı gerçekleşir.
Ödeme onaylandıktan sonra hemen başlıyoruz. 🎬</i>"""

ODEME_BILGI = """💳 <b>Ödeme Bilgileri</b>

🏦 <b>IBAN:</b>
<code>{iban}</code>
👤 <b>Ad:</b> {ad}

📱 <b>Papara:</b>
<code>{papara}</code>

<i>Ödeme yaptıktan sonra dekontu buradan ilet, işlemin hemen aktif edilsin. ✅</i>"""

# Anahtar kelimeler
VIP_KELIMELER = [
    "vip", "üye", "uye", "üyelik", "uyelik", "abone", "katıl", "katil",
    "fiyat", "ücret", "ucret", "kaç para", "kac para", "ne kadar",
    "kanal", "premium", "özel kanal", "ozel kanal"
]

SHOW_KELIMELER = [
    "show", "şov", "sov", "sanal", "özel show", "ozel show",
    "sanal şov", "sanal sov", "görüntülü", "goruntulu",
    "canlı", "canli", "görüşme", "gorusme", "video call",
    "özel", "ozel", "birebir", "performans"
]

def kelime_var_mi(metin: str, kelimeler: list) -> bool:
    metin_kucuk = metin.lower()
    for k in kelimeler:
        if k in metin_kucuk:
            return True
    return False

def vip_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 IBAN ile Öde", callback_data="iban_vip")],
        [InlineKeyboardButton("📱 Papara ile Öde", callback_data="papara_vip")],
        [InlineKeyboardButton("💬 Detay Sor", url="https://t.me/malatya_esra44")],
    ])

def show_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 IBAN ile Öde", callback_data="iban_show")],
        [InlineKeyboardButton("📱 Papara ile Öde", callback_data="papara_show")],
        [InlineKeyboardButton("💬 Detay Sor", url="https://t.me/malatya_esra44")],
    ])

def ana_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 VIP Üyelik", callback_data="menu_vip"),
         InlineKeyboardButton("🔥 Özel Şov", callback_data="menu_show")],
        [InlineKeyboardButton("💳 Ödeme Bilgileri", callback_data="menu_odeme")],
    ])

# --- HANDLER'LAR ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    hosgeldin = (
        f"Merhaba {user.first_name}! 👋\n\n"
        "Ben Malatya Esra'nın asistan botuyum 🍯\n\n"
        "Ne yapmak istersin?"
    )
    await update.message.reply_text(
        hosgeldin,
        reply_markup=ana_menu_kb(),
        parse_mode=ParseMode.HTML
    )

async def mesaj_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gelen her mesajı analiz et"""
    if not update.message or not update.message.text:
        return

    metin = update.message.text
    cid = update.effective_chat.id

    # VIP anahtar kelimesi var mı?
    if kelime_var_mi(metin, VIP_KELIMELER):
        await update.message.reply_text(
            VIP_FIYATLAR + "\n\n" +
            "Hemen üye olmak için ödeme yöntemini seç 👇",
            reply_markup=vip_kb(),
            parse_mode=ParseMode.HTML
        )
        # Admin'e bildir
        await context.bot.send_message(
            ADMIN_ID,
            f"💎 VIP ilgisi!\n"
            f"Kullanıcı: {update.effective_user.first_name} (@{update.effective_user.username or 'yok'})\n"
            f"ID: {cid}\n"
            f"Mesaj: {metin[:100]}"
        )
        return

    # Şov anahtar kelimesi var mı?
    if kelime_var_mi(metin, SHOW_KELIMELER):
        await update.message.reply_text(
            SHOW_FIYATLAR + "\n\n" +
            "Rezervasyon için ödeme yöntemini seç 👇",
            reply_markup=show_kb(),
            parse_mode=ParseMode.HTML
        )
        # Admin'e bildir
        await context.bot.send_message(
            ADMIN_ID,
            f"🔥 Şov ilgisi!\n"
            f"Kullanıcı: {update.effective_user.first_name} (@{update.effective_user.username or 'yok'})\n"
            f"ID: {cid}\n"
            f"Mesaj: {metin[:100]}"
        )
        return

async def callback_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline buton basımları"""
    q = update.callback_query
    await q.answer()
    data = q.data
    cid = q.message.chat.id

    odeme_metni = ODEME_BILGI.format(iban=IBAN, ad=IBAN_AD, papara=PAPARA)

    if data == "menu_vip":
        await q.message.reply_text(
            VIP_FIYATLAR + "\n\n" + "Ödeme yöntemini seç 👇",
            reply_markup=vip_kb(),
            parse_mode=ParseMode.HTML
        )

    elif data == "menu_show":
        await q.message.reply_text(
            SHOW_FIYATLAR + "\n\n" + "Ödeme yöntemini seç 👇",
            reply_markup=show_kb(),
            parse_mode=ParseMode.HTML
        )

    elif data == "menu_odeme":
        await q.message.reply_text(
            odeme_metni,
            parse_mode=ParseMode.HTML
        )

    elif data in ("iban_vip", "papara_vip"):
        ekstra = (
            "\n\n💎 <b>VIP üyelik için ödeme tutarını</b> ve "
            "\"VIP\" yazısını açıklama kısmına ekle.\n"
            "Ardından dekontu buraya ilet → işlemin hemen aktif edilsin ✅"
        )
        await q.message.reply_text(
            odeme_metni + ekstra,
            parse_mode=ParseMode.HTML
        )

    elif data in ("iban_show", "papara_show"):
        ekstra = (
            "\n\n🔥 <b>Şov rezervasyonu için ödeme tutarını</b> ve "
            "\"Şov\" yazısını açıklama kısmına ekle.\n"
            "Ödeme onaylandıktan hemen sonra başlıyoruz 🎬"
        )
        await q.message.reply_text(
            odeme_metni + ekstra,
            parse_mode=ParseMode.HTML
        )

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_al))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_al))

    logger.info("✅ Ödeme Botu başladı — polling aktif")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
