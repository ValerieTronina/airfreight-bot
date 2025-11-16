import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler

CITY, AIRPORT, MODE, WEIGHT, VOLUME = range(5)
logging.basicConfig(level=logging.INFO)
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"👤 Пользователь {user_id} нажал /start")
    keyboard = [["✈️ Авиа", "🚆 ЖД (сборный груз)"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Привет! Выберите тип перевозки:", reply_markup=reply_markup)
    return MODE

async def mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = update.message.text
    user_data[update.effective_user.id] = {"mode": mode}
    if "Авиа" in mode:
        await update.message.reply_text("Введите аэропорт доставки (Шереметьево или Пулково):")
        return AIRPORT
    else:
        await update.message.reply_text("Введите город прибытия в России (Москва или Санкт-Петербург):")
        return CITY

async def city_or_airport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id]["location"] = update.message.text
    await update.message.reply_text("Введите вес груза в кг:")
    return WEIGHT

async def weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите числовое значение веса.")
        return WEIGHT
    user_data[update.effective_user.id]["weight"] = weight
    await update.message.reply_text("Введите объем груза в м³:")
    return VOLUME

async def volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        volume = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите числовое значение объема.")
        return VOLUME

    user_id = update.effective_user.id
    data = user_data.get(user_id, {})
    mode = data.get("mode")
    location = data.get("location")
    weight = data.get("weight")
    volumetric_weight = volume * 167
    chargeable_weight = max(weight, volumetric_weight)

    if "Авиа" in mode:
        airport = location.lower()
        if "пулково" in airport:
            if chargeable_weight <= 45:
                rate = 7.85
            elif chargeable_weight < 100:
                rate = 7.85
            elif chargeable_weight < 300:
                rate = 6.85
            elif chargeable_weight < 500:
                rate = 4.49
            elif chargeable_weight < 1000:
                rate = 3.56
            else:
                rate = 2.33
        else:  # Шереметьево
            if chargeable_weight <= 45:
                rate = 7.45
            elif chargeable_weight < 100:
                rate = 7.45
            elif chargeable_weight < 300:
                rate = 6.45
            elif chargeable_weight < 500:
                rate = 4.09
            elif chargeable_weight < 1000:
                rate = 3.16
            else:
                rate = 1.93
        cost = chargeable_weight * rate
        reply = (
            f"✈️ Авиаперевозка ({location})"
            f"📦 Вес: {weight} кг | Объем: {volume} м³"
            f"💡 Объемный вес: {volumetric_weight:.1f} кг"
            f"💰 Ставка: {rate} USD/кг"
            f"💵 Итого: {cost:.2f} USD"
            f"📄 Таможенное оформление: 16 000 руб"
        )
    else:
        # ЖД ставки
        if volume < 10:
            rate = 220
        else:
            rate = 210
        if weight <= 400:
            local = 225
        elif weight <= 600:
            local = 350
        elif weight < 1000:
            local = 350
        else:
            local = 390
        total = volume * rate + local
        reply = (
            f"🚆 ЖД перевозка ({location})"
            f"📦 Вес: {weight} кг | Объем: {volume} м³"
            f"💰 Ставка: {rate} USD/м³"
            f"🔧 Локальные сборы: {local} USD"
            f"💵 Итого: {total:.2f} USD"
            f"📄 Таможенное оформление: 16 000 руб"
        )

    await update.message.reply_text(reply)
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Этот бот рассчитывает ставку на авиа и ЖД доставку из Китая."
        "Нажмите /start чтобы начать заново."
    )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data.pop(update.effective_user.id, None)
    await update.message.reply_text("Расчёт сброшен. Введите /start чтобы начать заново.")
    return ConversationHandler.END

def main():
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, mode)],
            AIRPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, city_or_airport)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city_or_airport)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight)],
            VOLUME: [MessageHandler(filters.TEXT & ~filters.COMMAND, volume)],
        },
        fallbacks=[CommandHandler("reset", reset_command)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_command))

    print("✅ Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
