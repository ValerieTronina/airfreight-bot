import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import os

API_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Состояния
user_state = {}
user_data = {}

# Кнопки
start_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
start_keyboard.add(KeyboardButton("📦 Рассчитать ставку"))

@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    await message.answer("Привет! Я помогу рассчитать ставку на доставку из Китая. Выберите действие:", reply_markup=start_keyboard)

@dp.message_handler(lambda message: message.text == "📦 Рассчитать ставку")
async def ask_transport_mode(message: types.Message):
    user_state[message.from_user.id] = "choose_mode"
    await message.answer("Выберите способ доставки:
✈️ Авиа
🚆 ЖД (сборный груз)")

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "choose_mode")
async def ask_airport_or_city(message: types.Message):
    mode = message.text.lower()
    user_data[message.from_user.id] = {"mode": mode}
    if "авиа" in mode:
        user_state[message.from_user.id] = "airport"
        await message.answer("Выберите аэропорт доставки:
Шереметьево или Пулково")
    elif "жд" in mode:
        user_state[message.from_user.id] = "rail_city"
        await message.answer("Укажите город прибытия (Москва или Санкт-Петербург):")
    else:
        await message.answer("Пожалуйста, выберите 'Авиа' или 'ЖД'.")

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "airport")
async def ask_air_cargo_volume(message: types.Message):
    user_data[message.from_user.id]["airport"] = message.text.strip()
    user_state[message.from_user.id] = "volume"
    await message.answer("Укажите объём груза в м³:")

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "volume")
async def ask_air_cargo_weight(message: types.Message):
    try:
        volume = float(message.text.replace(",", "."))
        user_data[message.from_user.id]["volume"] = volume
        user_state[message.from_user.id] = "weight"
        await message.answer("Укажите вес груза в кг:")
    except ValueError:
        await message.answer("Введите числовое значение объёма в формате 1.23")

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "weight")
async def calculate_air_rate(message: types.Message):
    try:
        weight = float(message.text.replace(",", "."))
        data = user_data.get(message.from_user.id, {})
        airport = data.get("airport", "").lower()
        volume = data.get("volume", 0)
        volumetric_weight = volume * 167
        chargeable_weight = max(weight, volumetric_weight)

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
        else:
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

        base_price = round(chargeable_weight * rate, 2)
        dt = 16000
        await message.answer(
            f"💰 Авиаставка: {rate} USD/кг
"
            f"🔢 Объёмный вес: {volumetric_weight:.2f} кг
"
            f"📦 Расчётный вес: {chargeable_weight:.2f} кг
"
            f"💸 Стоимость фрахта: {base_price} USD
"
            f"🧾 Таможенное оформление: {dt} руб."
        )
    except ValueError:
        await message.answer("Введите вес в формате 12.3")
    finally:
        user_state.pop(message.from_user.id, None)

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "rail_city")
async def ask_rail_volume(message: types.Message):
    user_data[message.from_user.id]["city"] = message.text.strip()
    user_state[message.from_user.id] = "rail_volume"
    await message.answer("Укажите объём груза в м³:")

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "rail_volume")
async def ask_rail_weight(message: types.Message):
    try:
        volume = float(message.text.replace(",", "."))
        user_data[message.from_user.id]["volume"] = volume
        user_state[message.from_user.id] = "rail_weight"
        await message.answer("Укажите вес груза в кг:")
    except ValueError:
        await message.answer("Введите объём числом, например 3.2")

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "rail_weight")
async def calculate_rail_rate(message: types.Message):
    try:
        weight = float(message.text.replace(",", "."))
        data = user_data.get(message.from_user.id, {})
        volume = data.get("volume", 0)

        if volume < 10:
            rate = 220
        else:
            rate = 210
        base_price = round(rate * volume, 2)

        if weight <= 400:
            fees = 225
        elif weight <= 600:
            fees = 350
        elif weight <= 1000:
            fees = 350
        else:
            fees = 390

        dt = 16000

        await message.answer(
            f"🚆 ЖД ставка: {rate} USD/м³
"
            f"📦 Объём: {volume} м³
"
            f"⚖️ Вес: {weight} кг
"
            f"💸 Стоимость доставки: {base_price} USD
"
            f"📍 Локальные сборы: {fees} USD
"
            f"🧾 Таможенное оформление: {dt} руб."
        )
    except ValueError:
        await message.answer("Введите вес числом")
    finally:
        user_state.pop(message.from_user.id, None)

if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
