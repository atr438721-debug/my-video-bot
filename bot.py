import os
import logging
import secrets
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7965349922

video_codes = {}

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Привет!\n\n"
        "Введи код из канала и я пришлю тебе видео.\n\n"
        "Просто напиши код в чат 👇"
    )

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == ADMIN_ID:
        return
    code = update.message.text.strip().upper()
    if code in video_codes:
        await update.message.reply_text("✅ Код принят! Отправляю видео...")
        await update.message.reply_video(
            video=video_codes[code],
            caption=f"🎬 Видео по коду: {code}"
        )
    else:
        await update.message.reply_text(
            "❌ Код не найден.\n"
            "Проверь правильность и попробуй снова."
        )

async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    code = context.args[0].upper() if context.args else secrets.token_hex(3).upper()
    context.user_data["waiting_video_for"] = code
    await update.message.reply_text(
        f"📌 Код: {code}\n\n"
        f"Теперь отправь видео файлом.\n"
        f"Этот код публикуй в своём канале!"
    )

async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    code = context.user_data.get("waiting_video_for")
    if not code:
        await update.message.reply_text("⚠️ Сначала напиши /addvideo, потом отправь видео.")
        return
    video_codes[code] = update.message.video.file_id
    context.user_data["waiting_video_for"] = None
    await update.message.reply_text(
        f"🎉 Видео добавлено!\n\n"
        f"Код: {code}\n\n"
        f"Публикуй этот код в канале — подписчики введут его боту и получат видео!"
    )

async def list_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    if not video_codes:
        await update.message.reply_text("📭 Нет видео.")
        return
    text = "📋 Все коды:\n\n"
    for code in video_codes:
        text += f"• {code}\n"
    await update.message.reply_text(text)

async def delete_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    if not context.args:
        await update.message.reply_text("Использование: /delete КОД")
        return
    code = context.args[0].upper()
    if code in video_codes:
        del video_codes[code]
        await update.message.reply_text(f"🗑 Код {code} удалён.")
    else:
        await update.message.reply_text(f"❌ Код {code} не найден.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addvideo", add_video))
    app.add_handler(CommandHandler("list", list_codes))
    app.add_handler(CommandHandler("delete", delete_code))
    app.add_handler(MessageHandler(filters.VIDEO, receive_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
