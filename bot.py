import os
import logging
import secrets
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7965349922

logging.basicConfig(level=logging.INFO)

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect("videos.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            code TEXT PRIMARY KEY,
            file_id TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_video(code, file_id):
    conn = sqlite3.connect("videos.db")
    conn.execute("INSERT OR REPLACE INTO videos (code, file_id) VALUES (?, ?)", (code, file_id))
    conn.commit()
    conn.close()

def get_video(code):
    conn = sqlite3.connect("videos.db")
    row = conn.execute("SELECT file_id FROM videos WHERE code = ?", (code,)).fetchone()
    conn.close()
    return row[0] if row else None

def delete_video(code):
    conn = sqlite3.connect("videos.db")
    conn.execute("DELETE FROM videos WHERE code = ?", (code,))
    conn.commit()
    conn.close()

def get_all_codes():
    conn = sqlite3.connect("videos.db")
    rows = conn.execute("SELECT code FROM videos").fetchall()
    conn.close()
    return [row[0] for row in rows]

# ==================== КОМАНДЫ ====================
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
    file_id = get_video(code)
    if file_id:
        await update.message.reply_text("✅ Код принят! Отправляю видео...")
        await update.message.reply_video(
            video=file_id,
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
    file_id = update.message.video.file_id
    save_video(code, file_id)
    context.user_data["waiting_video_for"] = None
    await update.message.reply_text(
        f"🎉 Видео сохранено навсегда!\n\n"
        f"Код: {code}\n\n"
        f"Публикуй этот код в канале!"
    )

async def list_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    codes = get_all_codes()
    if not codes:
        await update.message.reply_text("📭 Нет видео.")
        return
    text = "📋 Все коды:\n\n"
    for code in codes:
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
    if get_video(code):
        delete_video(code)
        await update.message.reply_text(f"🗑 Код {code} удалён.")
    else:
        await update.message.reply_text(f"❌ Код {code} не найден.")

# ==================== ЗАПУСК ====================
def main():
    init_db()
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
