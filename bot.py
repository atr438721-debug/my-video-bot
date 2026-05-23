import os
import logging
import sqlite3
import secrets
from telegram import Update, BotCommand
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
            file_id TEXT NOT NULL,
            title TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def generate_unique_code():
    conn = sqlite3.connect("videos.db")
    while True:
        code = str(secrets.randbelow(900000) + 100000)  # 6-значный код
        exists = conn.execute("SELECT 1 FROM videos WHERE code = ?", (code,)).fetchone()
        if not exists:
            conn.close()
            return code

def save_video(code, file_id, title):
    conn = sqlite3.connect("videos.db")
    conn.execute("INSERT INTO videos (code, file_id, title) VALUES (?, ?, ?)", (code, file_id, title))
    conn.commit()
    conn.close()

def get_video(code):
    conn = sqlite3.connect("videos.db")
    row = conn.execute("SELECT file_id, title FROM videos WHERE code = ?", (code,)).fetchone()
    conn.close()
    return row

def delete_video(code):
    conn = sqlite3.connect("videos.db")
    conn.execute("DELETE FROM videos WHERE code = ?", (code,))
    conn.commit()
    conn.close()

def get_all_videos():
    conn = sqlite3.connect("videos.db")
    rows = conn.execute("SELECT code, title FROM videos").fetchall()
    conn.close()
    return rows

# ==================== КОМАНДЫ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Привет! Я бот для получения видео.\n\n"
        "📌 Команды:\n"
        "/start — главное меню\n"
        "/help — помощь\n\n"
        "Просто введи код из канала 👇"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "🔧 Команды админа:\n\n"
            "📤 Отправь видео — бот создаст код\n"
            "/list — список всех видео\n"
            "/delete КОД — удалить видео\n\n"
            "👤 Команды пользователя:\n"
            "/start — главное меню\n"
            "Введи код — получи видео"
        )
    else:
        await update.message.reply_text(
            "📌 Как получить видео:\n\n"
            "1️⃣ Возьми код из канала\n"
            "2️⃣ Напиши код боту\n"
            "3️⃣ Получи видео!\n\n"
            "Просто напиши код в чат 👇"
        )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Только админ может загружать видео.")
        return

    file_id = update.message.video.file_id
    title = update.message.caption if update.message.caption else "Видео"
    code = generate_unique_code()
    save_video(code, file_id, title)

    await update.message.reply_text(
        f"✅ Видео сохранено!\n\n"
        f"🔑 Код: {code}\n"
        f"📝 Название: {title}\n\n"
        f"Публикуй этот код на YouTube/TikTok!"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == ADMIN_ID:
        return

    code = update.message.text.strip()
    result = get_video(code)

    if result:
        file_id, title = result
        await update.message.reply_text(f"✅ Код принят! Отправляю видео...")
        await update.message.reply_video(
            video=file_id,
            caption=f"🎬 {title}"
        )
    else:
        await update.message.reply_text(
            "❌ Код не найден.\n"
            "Проверь правильность и попробуй снова."
        )

async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return

    rows = get_all_videos()
    if not rows:
        await update.message.reply_text("📭 Нет видео.")
        return

    text = "📋 Все видео:\n\n"
    for code, title in rows:
        text += f"🔑 {code} — {title}\n"
    await update.message.reply_text(text)

async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return

    if not context.args:
        await update.message.reply_text("Использование: /delete КОД")
        return

    code = context.args[0]
    if get_video(code):
        delete_video(code)
        await update.message.reply_text(f"🗑 Видео с кодом {code} удалено.")
    else:
        await update.message.reply_text(f"❌ Код {code} не найден.")

# ==================== ЗАПУСК ====================
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("list", list_videos))
    app.add_handler(CommandHandler("delete", delete_cmd))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
