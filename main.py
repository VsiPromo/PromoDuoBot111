
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
import sqlite3
import os

# === Налаштування ===
TOKEN = os.getenv("BOT_TOKEN")
CHANNELS = ['@Vsi_PROMO', '@uaclub_casinoman']
REWARD_PER_REF = 4
WITHDRAW_LIMIT = 100

# === База даних ===
conn = sqlite3.connect('promo_duo.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    invited_by INTEGER,
    balance INTEGER DEFAULT 0
)
""")
conn.commit()

# === Перевірка підписки ===
async def check_subscriptions(user_id, context):
    for channel in CHANNELS:
        member = await context.bot.get_chat_member(channel, user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            return False
    return True

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    args = context.args

    if not await check_subscriptions(user_id, context):
        buttons = [[InlineKeyboardButton("Підписатись на канал", url=f"https://t.me/{ch.lstrip('@')}")] for ch in CHANNELS]
        await update.message.reply_text("Підпишись на всі канали, щоб користуватись ботом:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if args:
        inviter_id = int(args[0])
        if inviter_id != user_id:
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO users (user_id, invited_by, balance) VALUES (?, ?, 0)", (user_id, inviter_id))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (REWARD_PER_REF, inviter_id))
                conn.commit()
    else:
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))

    await context.bot.send_message(chat_id=user_id, text=f"Привіт, {user.first_name}! Запрошуй друзів та отримуй по 4 грн за кожного!")
Твоє посилання: https://t.me/PromoDuoBot?start={user_id}")

# === /balance ===
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    bal = row[0] if row else 0
    msg = f"👛 Твій баланс: {bal} грн\n"
    if bal >= WITHDRAW_LIMIT:
        msg += "✅ Ти можеш вивести кошти. Надішли /withdraw"
    else:
        msg += f"🔒 Виведення доступне при {WITHDRAW_LIMIT} грн"
    await update.message.reply_text(msg)

# === /withdraw ===
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    bal = row[0] if row else 0
    if bal < WITHDRAW_LIMIT:
        await update.message.reply_text("🔒 Виведення доступне при 100 грн")
        return
    await update.message.reply_text("💳 Введи номер картки або платіжної системи для виплати")

# === Отримання реквізитів ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0] >= WITHDRAW_LIMIT:
        admin_id = 7262164512
        await context.bot.send_message(admin_id, f"🔔 Запит на виведення
👤 @{update.effective_user.username}
ID: {user_id}
💰 Сума: {row[0]} грн
📤 Реквізити: {text}")
        await update.message.reply_text("✅ Заявка на виплату надіслана адміну. Очікуй підтвердження!")

# === Запуск ===
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
