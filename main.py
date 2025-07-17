
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler

CITY, AIRPORT, WEIGHT, LENGTH, WIDTH, HEIGHT = range(6)
logging.basicConfig(level=logging.INFO)
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"👤 Пользователь {user_id} нажал /start")
    await update.message.reply_text("👋 Привет! Я помогу рассчитать стоимость авиаперевозки из Китая в РФ.\n\nВведите город отправки:")
    return CITY

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📘 /help от {update.effective_user.id}")
    await update.message.reply_text(
        "✈️ Этот бот рассчитывает стоимость авиадоставки груза из Китая в Россию.\n"
        "Введите вес, габариты и выберите аэропорт — я всё посчитаю.\n"
        "Если хотите начать заново, используйте /reset"
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"ℹ️ /info от {update.effective_user.id}")
    await update.message.reply_text(
        "📦 В расчёте учитываются:\n"
        "- Реальный и объёмный вес\n"
        "- Тариф по весовому диапазону\n"
        "- Авиалинии\n"
        "- Локальные затраты\n"
        "- Таможенное оформление"
    )

async def contacts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📲 /contacts от {update.effective_user.id}")
    await update.message.reply_text(
        "📲 Связаться со специалистом:\n"
        "• WhatsApp: https://wa.me/79295770582\n"
        "• Email: valeriia_tronina@stforce.su"
    )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"🔁 /reset от {update.effective_user.id}")
    user_data.pop(update.effective_user.id, None)
    await update.message.reply_text("🔄 Расчёт сброшен. Введите /start чтобы начать заново.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"🚫 /cancel от {update.effective_user.id}")
    await update.message.reply_text("Расчёт прерван. Введите /start чтобы начать заново.")
    return ConversationHandler.END

def main():
    
    print("✅ Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()

