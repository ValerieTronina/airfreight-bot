import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler

CITY, AIRPORT, WEIGHT, LENGTH, WIDTH, HEIGHT = range(6)
logging.basicConfig(level=logging.INFO)
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Я помогу рассчитать стоимость авиаперевозки из Китая в РФ.\n\nВведите город отправки:")
    return CITY

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✈️ Этот бот рассчитывает стоимость авиадоставки груза из Китая в Россию.\n"
        "Введите вес, габариты и выберите аэропорт — я всё посчитаю.\n"
        "Если хотите начать заново, используйте /reset"
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 В расчёте учитываются:\n"
        "- Реальный и объёмный вес\n"
        "- Тариф по весовому диапазону\n"
        "- Авиалинии\n"
        "- Локальные затраты\n"
        "- Таможенное оформление"
    )

async def contacts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📲 Связаться со специалистом:\n"
        "• WhatsApp: https://wa.me/79295770582\n"
        "• Email: valeriia_tronina@stforce.su"
    )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data.pop(update.effective_user.id, None)
    await update.message.reply_text("🔄 Расчёт сброшен. Введите /start чтобы начать заново.")
    return ConversationHandler.END

async def city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id] = {'city': update.message.text}
    reply_keyboard = [['Шереметьево', 'Пулково']]
    await update.message.reply_text("✈️ Выберите аэропорт доставки:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return AIRPORT

async def airport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id]['airport'] = update.message.text
    await update.message.reply_text("⚖️ Укажите вес груза (в кг):")
    return WEIGHT

async def weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_data[update.effective_user.id]['weight'] = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("❗ Пожалуйста, введите вес числом.")
        return WEIGHT
    await update.message.reply_text("📦 Укажите длину груза (в см):")
    return LENGTH

async def length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_data[update.effective_user.id]['length'] = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("❗ Пожалуйста, введите длину числом.")
        return LENGTH
    await update.message.reply_text("📦 Укажите ширину груза (в см):")
    return WIDTH

async def width(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_data[update.effective_user.id]['width'] = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("❗ Пожалуйста, введите ширину числом.")
        return WIDTH
    await update.message.reply_text("📦 Укажите высоту груза (в см):")
    return HEIGHT

async def height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        user_data[user_id]['height'] = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("❗ Пожалуйста, введите высоту числом.")
        return HEIGHT

    data = user_data[user_id]
    vol_weight = (data['length'] * data['width'] * data['height']) / 6000
    chargeable_weight = max(data['weight'], vol_weight)

    if chargeable_weight <= 45:
        cost = 450
        note = "Фиксированная ставка до 45 кг"
    elif chargeable_weight < 100:
        cost = chargeable_weight * 5.00
        note = "Ставка 5 USD/кг"
    elif chargeable_weight < 300:
        cost = chargeable_weight * 4.65
        note = "Ставка 4.65 USD/кг"
    elif chargeable_weight < 500:
        cost = chargeable_weight * 3.69
        note = "Ставка 3.69 USD/кг"
    else:
        cost = chargeable_weight * 3.09
        note = "Ставка 3.09 USD/кг"

    response = f"""
📦 Стоимость авиаперевозки: {round(cost, 2)} USD
🧾 Применено: {note}

📍 Город отправки: {data['city']}
✈️ Аэропорт доставки: {data['airport']}
⚖️ Учтённый вес: {round(chargeable_weight, 2)} кг (реальный: {data['weight']} кг, объемный: {round(vol_weight, 2)} кг)

ℹ️ Дополнительно:
• Локальные затраты: от 80 до 150 USD
• Авиалинии: China Eastern, Hainan Airlines, China Southern
• Таможенное оформление: 16 000 ₽ за ДТ

📲 Связаться с логистом:
• WhatsApp: https://wa.me/79295770582
• Email: valeriia_tronina@stforce.su
"""
    await update.message.reply_text(response)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Расчёт прерван. Введите /start чтобы начать заново.")
    return ConversationHandler.END

def main():
    TOKEN = "7916963483:AAGKLGf8h-678gyxJMBDiJ6bDLaiMQqjQsM"
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city)],
            AIRPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, airport)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight)],
            LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, length)],
            WIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, width)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, height)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("reset", reset_command)
        ],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(CommandHandler("contacts", contacts_command))
    app.add_handler(CommandHandler("reset", reset_command))
    print("✅ Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
