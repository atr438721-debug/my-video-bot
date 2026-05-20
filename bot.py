import os
import logging
import sqlite3
import secrets
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7965349922

logging.basicConfig(level=logging.INFO)

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect("videos.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS content (
            code TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            video_id TEXT,
            photo1_id TEXT,
            photo2_id TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_content(code):
    conn = sqlite3.connect("videos.db")
    row = conn.execute(
        "SELECT title, description, video_id, photo1_id, photo2_id FROM content WHERE code = ?",
        (code,)
    ).fetchone()
    conn.close()
    return row

def save_field(code, field, value):
    conn = sqlite3.connect("videos.db")
    conn.execute(f"UPDATE content SET {field} = ? WHERE code = ?", (value, code))
    conn.commit()
    conn.close()

def create_entry(code, title):
    conn = sqlite3.connect("videos.db")
    conn.execute(
        "INSERT OR REPLACE INTO content (code, title) VALUES (?, ?)", (code, title)
    )
    conn.commit()
    conn.close()

def delete_content(code):
    conn = sqlite3.connect("videos.db")
    conn.execute("DELETE FROM content WHERE code = ?", (code,))
    conn.commit()
    conn.close()

def get_all_content():
    conn = sqlite3.connect("videos.db")
    rows = conn.execute("SELECT code, title FROM content").fetchall()
    conn.close()
    return rows

# ==================== ОТПРАВКА КОНТЕНТА ПОЛЬЗОВАТЕЛЮ ====================
async def send_content(update: Update, code: str):
    result = get_content(code)
    if not result:
        await update.message.reply_text("❌ Код не найден.\nПроверь правильность и попробуй снова.")
        return

    title, description, video_id, photo1_id, photo2_id = result

    # Отправляем текст с названием и описанием
    text = f"🎬 *{title}*"
    if description:
        text += f"\n\n📝 {description}"
    await update.message.reply_text(text, parse_mode="Markdown")

    # Отправляем фото только если они есть
    if photo1_id:
        await update.message.reply_photo(photo=photo1_id)
    if photo2_id:
        await update.message.reply_photo(photo=photo2_id)

    # Отправляем видео только если оно есть
    if video_id:
        await update.message.reply_video(video=video_id)

# ==================== КОМАНДЫ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Привет!\n\n"
        "Введи код из канала и я пришлю тебе контент.\n\n"
        "Просто напиши код в чат 👇"
    )

async def new_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return

    if not context.args:
        await update.message.reply_text(
            "Использование:\n"
            "/new КОД Название\n\n"
            "Пример:\n"
            "/new 0001 Фильм Аватар"
        )
        return

    code = context.args[0].upper()
    title = " ".join(context.args[1:]) if len(context.args) > 1 else "Без названия"
    create_entry(code, title)

    # Сохраняем состояние
    context.user_data["code"] = code
    context.user_data["step"] = "description"

    await update.message.reply_text(
        f"✅ Код: {code}\n"
        f"📝 Название: {title}\n\n"
        f"Напиши описание или /skip чтобы пропустить:"
    )

async def skip_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    step = context.user_data.get("step")
    code = context.user_data.get("code")

    if not step or not code:
        await update.message.reply_text("⚠️ Сначала начни с /new КОД Название")
        return

    if step == "description":
        context.user_data["step"] = "photo1"
        await update.message.reply_text("📸 Отправь первое фото или /skip")
    elif step == "photo1":
        context.user_data["step"] = "photo2"
        await update.message.reply_text("📸 Отправь второе фото или /skip")
    elif step == "photo2":
        context.user_data["step"] = "video"
        await update.message.reply_text("🎬 Отправь видео или /skip")
    elif step == "video":
        context.user_data["step"] = None
        context.user_data["code"] = None
        await update.message.reply_text(
            f"🎉 Готово! Код *{code}* сохранён!\n"
            f"Публикуй код в канале!",
            parse_mode="Markdown"
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    # Если это админ и он в процессе добавления
    if user_id == ADMIN_ID:
        step = context.user_data.get("step")
        code = context.user_data.get("code")

        if step == "description" and code:
            save_field(code, "description", update.message.text)
            context.user_data["step"] = "photo1"
            await update.message.reply_text("✅ Описание сохранено!\n\n📸 Отправь первое фото или /skip")
            return

    # Для всех остальных — проверяем код
    code = update.message.text.strip().upper()
    await send_content(update, code)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    step = context.user_data.get("step")
    code = context.user_data.get("code")

    if not step or not code:
        await update.message.reply_text("⚠️ Сначала начни с /new КОД Название")
        return

    file_id = update.message.photo[-1].file_id

    if step == "photo1":
        save_field(code, "photo1_id", file_id)
        context.user_data["step"] = "photo2"
        await update.message.reply_text("✅ Первое фото сохранено!\n\n📸 Отправь второе фото или /skip")
    elif step == "photo2":
        save_field(code, "photo2_id", file_id)
        context.user_data["step"] = "video"
        await update.message.reply_text("✅ Второе фото сохранено!\n\n🎬 Отправь видео или /skip")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    step = context.user_data.get("step")
    code = context.user_data.get("code")

    if not step or not code:
        await update.message.reply_text("⚠️ Сначала начни с /new КОД Название")
        return

    if step == "video":
        save_field(code, "video_id", update.message.video.file_id)
        context.user_data["step"] = None
        context.user_data["code"] = None
        await update.message.reply_text(
            f"🎉 Всё сохранено!\n\n"
            f"Код: *{code}*\n"
            f"Публикуй код в канале!",
            parse_mode="Markdown"
        )

async def list_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return

    rows = get_all_content()
    if not rows:
        await update.message.reply_text("📭 Нет контента.")
        return

    text = "📋 Весь контент:\n\n"
    for code, title in rows:
        text += f"• {code} — {title}\n"
    await update.message.reply_text(text)

async def delete_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return

    if not context.args:
        await update.message.reply_text("Использование: /delete КОД")
        return

    code = context.args[0].upper()
    if get_content(code):
        delete_content(code)
        await update.message.reply_text(f"🗑 Код {code} удалён.")
    else:
        await update.message.reply_text(f"❌ Код {code} не найден.")

# ==================== ЗАПУСК ====================
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new_content))
    app.add_handler(CommandHandler("skip", skip_step))
    app.add_handler(CommandHandler("list", list_content))
    app.add_handler(CommandHandler("delete", delete_code))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
