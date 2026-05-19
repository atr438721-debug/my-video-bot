import os
import logging
import secrets
from telegram import Update, LabeledPrice
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    PreCheckoutQueryHandler, filters, ContextTypes
)

# ==============================
# НАСТРОЙКИ — ИЗМЕНИ ЭТО
# ==============================
BOT_TOKEN = "СЮДА_ВСТАВЬ_ТОКЕН_ОТ_BOTFATHER"
ADMIN_ID = 123456789       # Твой Telegram ID (узнать: @userinfobot)
STARS_PRICE = 50           # Сколько Stars стоит одно видео (50 Stars ≈ 1 TON)

# ==============================
# База данных (в памяти)
# video_codes = { "КОД": file_id }
# paid_users  = { user_id: ["КОД1", "КОД2"] }
# ==============================
video_codes = {}
paid_users = {}

logging.basicConfig(level=logging.INFO)

# ==================== СТАРТ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Добро пожаловать!\n\n"
        "Здесь ты можешь купить доступ к эксклюзивным видео.\n\n"
        "📌 Команды:\n"
        "/catalog — список доступных видео\n"
        "/buy КОД — купить видео\n"
        "/myvideos — мои купленные видео"
    )

# ==================== КАТАЛОГ ====================
async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not video_codes:
        await update.message.reply_text("📭 Пока нет доступных видео.")
        return

    text = "🎬 Доступные видео:\n\n"
    for code in video_codes:
        text += f"🎞 {code}\n"
    text += f"\n💰 Цена: {STARS_PRICE} ⭐ за одно видео\n"
    text += "Купить: /buy КОД"
    await update.message.reply_text(text)

# ==================== ПОКУПКА ====================
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Использование: /buy КОД\n\n"
            "Сначала посмотри список: /catalog"
        )
        return

    code = context.args[0].upper()

    if code not in video_codes:
        await update.message.reply_text(f"❌ Видео с кодом {code} не найдено.\nПосмотри /catalog")
        return

    context.user_data["buying_code"] = code

    await update.message.reply_invoice(
        title=f"🎬 Видео: {code}",
        description=f"Доступ к видео по коду {code}",
        payload=f"video_{code}",
        currency="XTR",  # XTR = Telegram Stars
        prices=[LabeledPrice(label=f"Видео {code}", amount=STARS_PRICE)],
    )

# ==================== ПОДТВЕРЖДЕНИЕ ОПЛАТЫ ====================
async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

# ==================== УСПЕШНАЯ ОПЛАТА — ВЫДАЁМ ВИДЕО ====================
async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payload = update.message.successful_payment.invoice_payload
    code = payload.replace("video_", "").upper()
    user_id = update.message.from_user.id

    if user_id not in paid_users:
        paid_users[user_id] = []
    if code not in paid_users[user_id]:
        paid_users[user_id].append(code)

    await update.message.reply_text("✅ Оплата прошла! Отправляю видео...")

    if code in video_codes:
        await update.message.reply_video(
            video=video_codes[code],
            caption=f"🎬 Видео: {code}\n\nСпасибо за покупку! ⭐"
        )
    else:
        await update.message.reply_text("⚠️ Видео временно недоступно. Напиши администратору.")

# ==================== МОИ ВИДЕО ====================
async def my_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    codes = paid_users.get(user_id, [])

    if not codes:
        await update.message.reply_text("У тебя пока нет купленных видео.\nПосмотри /catalog")
        return

    await update.message.reply_text(f"🎬 Твои видео ({len(codes)} шт.):")
    for code in codes:
        if code in video_codes:
            await update.message.reply_video(
                video=video_codes[code],
                caption=f"🎞 {code}"
            )

# ==================== АДМИН: ДОБАВИТЬ ВИДЕО ====================
async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return

    if not context.args:
        code = secrets.token_hex(3).upper()
    else:
        code = context.args[0].upper()

    context.user_data["waiting_video_for"] = code
    await update.message.reply_text(
        f"📌 Код: {code}\n\n"
        f"Теперь отправь видео файлом."
    )

# ==================== ПОЛУЧАЕМ ВИДЕО ОТ АДМИНА ====================
async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    code = context.user_data.get("waiting_video_for")
    if not code:
        await update.message.reply_text("⚠️ Сначала напиши /addvideo, потом отправь видео.")
        return

    file_id = update.message.video.file_id
    video_codes[code] = file_id
    context.user_data["waiting_video_for"] = None

    await update.message.reply_text(
        f"🎉 Видео добавлено!\n"
        f"Код: {code}\n"
        f"Цена: {STARS_PRICE} ⭐\n\n"
        f"Пользователи покупают через: /buy {code}"
    )

# ==================== СПИСОК ВИДЕО (АДМИН) ====================
async def list_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return

    if not video_codes:
        await update.message.reply_text("📭 Нет видео.")
        return

    text = "📋 Все видео:\n\n"
    for code in video_codes:
        buyers = [uid for uid, codes in paid_users.items() if code in codes]
        text += f"• {code} — продано: {len(buyers)} раз\n"
    await update.message.reply_text(text)

# ==================== УДАЛИТЬ ВИДЕО (АДМИН) ====================
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
        await update.message.reply_text(f"🗑 Видео {code} удалено.")
    else:
        await update.message.reply_text(f"❌ Код {code} не найден.")

# ==================== СТАТИСТИКА (АДМИН) ====================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return

    total_sales = sum(len(codes) for codes in paid_users.values())
    earned_stars = total_sales * STARS_PRICE

    await update.message.reply_text(
        f"📊 Статистика:\n\n"
        f"🎬 Видео в каталоге: {len(video_codes)}\n"
        f"👥 Покупателей: {len(paid_users)}\n"
        f"🛒 Всего продаж: {total_sales}\n"
        f"⭐ Заработано Stars: {earned_stars}\n"
        f"💰 Примерно TON: {earned_stars / 50:.1f}\n\n"
        f"Вывод через fragment.com"
    )

# ==================== ЗАПУСК ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("catalog", catalog))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("myvideos", my_videos))

    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    app.add_handler(CommandHandler("addvideo", add_video))
    app.add_handler(CommandHandler("list", list_codes))
    app.add_handler(CommandHandler("delete", delete_code))
    app.add_handler(CommandHandler("stats", stats))

    app.add_handler(MessageHandler(filters.VIDEO, receive_video))

    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
