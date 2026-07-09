import os
import logging
import sys
sys.path.insert(0, '/home/user/workspace')
from dekont_dogrula import dekont_dogrula
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from telegram.constants import ParseMode

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("ODEME_BOT_TOKEN", "")
ADMIN_ID  = 5019918710

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba 👋\n\nÖdeme dekontu gönderebilirsin.",
        parse_mode=ParseMode.HTML
    )

async def dekont_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fotoğraf veya belge gelirse doğrula ve admin'e ilet — başka hiçbir şey yapma"""
    user = update.effective_user
    cid  = update.effective_chat.id
    msg  = update.message

    img_bytes = None
    file_id   = None

    if msg.photo:
        file_id = msg.photo[-1].file_id
    elif msg.document:
        file_id = msg.document.file_id

    if not file_id:
        return  # Metin, sticker, ses vb. → tamamen yoksay

    tg_file   = await context.bot.get_file(file_id)
    img_bytes = await tg_file.download_as_bytearray()

    # Doğrulama
    dogrulama = None
    if img_bytes:
        try:
            dogrulama = dekont_dogrula(bytes(img_bytes), cid)
        except Exception as e:
            dogrulama = {"sonuc": "HATA", "mesaj": f"⚠️ Doğrulama hatası: {e}", "skor": 0}

    # Kullanıcıya yanıt
    if dogrulama and dogrulama["sonuc"] == "SAHTE":
        await msg.reply_text(
            "❌ Bu dekont geçersiz görünüyor. Lütfen gerçek ödeme ekran görüntüsü gönderin."
        )
    else:
        await msg.reply_text("✅ Dekontu aldım, kısa sürede kontrol edip aktif ediyorum!")

    # Admin'e ilet
    user_bilgi = f"👤 {user.first_name} (@{user.username or 'yok'}) | ID: <code>{cid}</code>"
    rapor = (dogrulama["mesaj"] + "\n\n" + user_bilgi) if dogrulama else f"🧾 <b>Dekont Geldi!</b>\n{user_bilgi}"

    if msg.photo:
        await context.bot.send_photo(
            chat_id=ADMIN_ID, photo=file_id,
            caption=rapor[:1020], parse_mode=ParseMode.HTML
        )
    elif msg.document:
        await context.bot.send_document(
            chat_id=ADMIN_ID, document=file_id,
            caption=rapor[:1020], parse_mode=ParseMode.HTML
        )

async def main():
    if not BOT_TOKEN:
        logger.error("ODEME_BOT_TOKEN eksik")
        return
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    # Sadece fotoğraf ve belge — metin mesajları dahil HİÇBİR ŞEY yakalanmıyor
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, dekont_al))
    logger.info("Ödeme botu başlatıldı (sadece dekont modu)")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
