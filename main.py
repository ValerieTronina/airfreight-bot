import os
import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

import os

# Состояния
(
    MODE,
    AIRPORT,
    RAIL_CITY,
    WEIGHT,
    VOLUME,
    SHOW_RESULT,
) = range(6)

# Ставки
air_rates = {
    "pulkovo": [(45, 7.85), (100, 6.85), (300, 4.49), (500, 3.56), (1000, 2.33)],
    "svo": [(45, 7.45), (100, 6.45), (300, 4.09), (500, 3.16), (1000, 1.93)],
    "customs": 16000,
}

rail_rates = {
    "base": [(10, 220), (9999, 210)],
    "local": [(400, 225), (600, 350), (999, 350), (100000, 390)],
    "customs": 16000,
}

# Кнопки
start_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("📦 Рассчитать ставку")]], resize_keyboard=True
)

mode_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("✈️ Авиа")], [KeyboardButton("🚆 ЖД (сборный груз)")]],
    resize_keyboard=True,
)

airport_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("Пулково")], [KeyboardButton("Шереметьево")]],
    resize_keyboard=True,
)

rail_city_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("Москва")], [KeyboardButton("Санкт-Петербург")]],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу рассчитать ставку на доставку из Китая. Выберите действие:",
        reply_markup=start_keyboard,
    )
    return MODE


async def ask_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите способ доставки:", reply_markup=mode_keyboard)
    return MODE


async def handle_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = update.message.text.lower()
    context.user_data.clear()
    context.user_data["mode"] = mode

    if "авиа" in mode:
        await update.message.reply_text("Выберите аэропорт доставки:", reply_markup=airport_keyboard)
        return AIRPORT
    elif "жд" in mode:
        await update.message.reply_text("Укажите город прибытия (Москва или Санкт-Петербург):", reply_markup=rail_city_keyboard)
        return RAIL_CITY
    else:
        await update.message.reply_text("Пожалуйста, выберите корректный способ доставки.")
        return MODE


async def handle_airport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["airport"] = update.message.text.lower()
    await update.message.reply_text("Введите вес груза в килограммах:", reply_markup=ReplyKeyboardRemove())
    return WEIGHT


async def handle_rail_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["rail_city"] = update.message.text.lower()
    await update.message.reply_text("Введите вес груза в килограммах:", reply_markup=ReplyKeyboardRemove())
    return WEIGHT


async def handle_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = float(update.message.text.replace(",", "."))
        context.user_data["weight"] = weight
        await update.message.reply_text("Введите объем груза в м³:")
        return VOLUME
    except ValueError:
        await update.message.reply_text("Введите вес числом.")
        return WEIGHT


async def handle_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        volume = float(update.message.text.replace(",", "."))
        context.user_data["volume"] = volume

        mode = context.user_data["mode"]

        if "авиа" in mode:
            return await calculate_air(update, context)
        elif "жд" in mode:
            return await calculate_rail(update, context)
    except ValueError:
        await update.message.reply_text("Введите объем числом.")
        return VOLUME


async def calculate_air(update: Update, context: ContextTypes.DEFAULT_TYPE):
    airport = context.user_data["airport"]
    weight = context.user_data["weight"]
    volume = context.user_data["volume"]

    volumetric_weight = volume * 167
    chargeable_weight = max(weight, volumetric_weight)

    rate_list = air_rates["pulkovo"] if "пулково" in airport else air_rates["svo"]

    for limit, rate in rate_list:
        if chargeable_weight <= limit:
            total = chargeable_weight * rate
            break
    else:
        total = chargeable_weight * rate_list[-1][1]
        rate = rate_list[-1][1]

    result = (
    f"Авиаставка: {rate:.2f} USD/кг\n"
    f"Объемный вес: {volumetric_weight:.2f} кг\n"
    f"Облагаемый вес: {chargeable_weight:.2f} кг\n"
    f"Итого: {total:.2f} USD\n"
    f"Стоимость ДТ: 16 000 руб.\n"
    f"📩 Заказать перевозку:\n"
    f"WhatsApp: https://wa.me/79295770582\n"
    f"Email: valeriia_tronina@stforce.su"
)
context.user_data.clear()

    await update.message.reply_text(result, reply_markup=start_keyboard)
    return MODE


async def calculate_rail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = context.user_data["rail_city"]
    weight = context.user_data["weight"]
    volume = context.user_data["volume"]

    # Ставка за м3
    for limit, rate in rail_rates["base"]:
        if volume <= limit:
            freight = volume * rate
            break

    # Локальные сборы
    for w_limit, fee in rail_rates["local"]:
        if weight <= w_limit:
            local_fees = fee
            break

result = (
    f"Город прибытия: {city.title()}\n"
    f"Объем: {volume:.2f} м³\n"
    f"Вес: {weight:.2f} кг\n"
    f"Ставка: {freight:.2f} USD\n"
    f"Локальные сборы: {local_fees:.2f} USD\n"
    f"Таможенное оформление ДТ: 16 000 руб.\n"
    f"Дополнительно: локальные затраты в Китае рассчитываются отдельно\n"
    f"📩 Заказать перевозку:\n"
    f"WhatsApp: https://wa.me/79295770582\n"
    f"Email: valeriia_tronina@stforce.su"
)
context.user_data.clear()

    await update.message.reply_text(result, reply_markup=start_keyboard)
    return MODE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Расчет прерван.", reply_markup=start_keyboard)
    return ConversationHandler.END


def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("📦 Рассчитать ставку"), ask_mode),
        ],
        states={
            MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mode)],
            AIRPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_airport)],
            RAIL_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rail_city)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weight)],
            VOLUME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_volume)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()


if __name__ == "__main__":
    main()
