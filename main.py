import logging
from typing import Optional, Dict, Any

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# 🔑 ВСТАВЬ СЮДА СВОЙ ТОКЕН
API_TOKEN = "7916963483:AAGxzxapzcyHBcBJRhijJ6kuNo4XBsiN_HE"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Память последних расчётов по пользователям
last_queries: Dict[int, Dict[str, Any]] = {}


class QueryStates(StatesGroup):
    choosing_transport = State()
    choosing_destination = State()
    choosing_origin = State()
    entering_custom_origin = State()
    entering_weight = State()
    entering_volume = State()


# ---------- КЛАВИАТУРЫ ----------

def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("✈️ Авиа из Китая"), KeyboardButton("🚂 ЖД из Китая"))
    kb.add(KeyboardButton("🔁 Посчитать заново"))
    return kb


def destination_kb(transport: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    if transport == "air":
        kb.row(
            KeyboardButton("Москва (Шереметьево)"),
            KeyboardButton("Санкт-Петербург (Пулково)"),
        )
    else:
        kb.row(
            KeyboardButton("Москва (станция)"),
            KeyboardButton("Санкт-Петербург (станция)"),
        )
    kb.add(KeyboardButton("🏠 В главное меню"))
    return kb


def origin_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("Shanghai"), KeyboardButton("Shenzhen"))
    kb.row(KeyboardButton("Guangzhou"), KeyboardButton("Beijing"))
    kb.add(KeyboardButton("Ningbo"))
    kb.add(KeyboardButton("✏️ Ввести другой город"))
    kb.add(KeyboardButton("🏠 В главное меню"))
    return kb


def nav_inline_kb(show_other_mode: Optional[str] = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    if show_other_mode == "air":
        kb.add(
            InlineKeyboardButton(
                "✈️ Посчитать авиа по этим данным", callback_data="calc_air_from_last"
            )
        )
    elif show_other_mode == "rail":
        kb.add(
            InlineKeyboardButton(
                "🚂 Посчитать ж/д по этим данным", callback_data="calc_rail_from_last"
            )
        )
    kb.add(InlineKeyboardButton("🔁 Посчитать заново", callback_data="restart"))
    kb.add(InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu"))
    return kb


# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------

def parse_float(text: str) -> Optional[float]:
    text = text.replace(",", ".").strip()
    try:
        value = float(text)
        if value <= 0:
            return None
        return value
    except ValueError:
        return None


def format_usd(amount: float) -> str:
    return f"{amount:,.2f} USD".replace(",", " ")


# ---------- РАСЧЁТ АВИА ----------

def calc_air(weight_kg: float, volume_m3: float) -> Dict[str, Any]:
    volumetric = volume_m3 * 167
    chargeable = max(weight_kg, volumetric)

    # Фрахт
    if chargeable <= 45:
        freight = 499.0
        rate = None
    else:
        if chargeable <= 100:
            rate = 8.7
        elif chargeable <= 300:
            rate = 8.04
        elif chargeable <= 500:
            rate = 7.37
        elif chargeable <= 800:
            rate = 6.85
        else:
            rate = 6.34
        freight = chargeable * rate

    # Локальные сборы
    if chargeable <= 100:
        docs_fee = 60.0
        pickup_fee = 90.0
    elif chargeable <= 300:
        docs_fee = 60.0
        pickup_fee = 115.0
    elif chargeable <= 800:
        docs_fee = 60.0
        pickup_fee = 195.0
    else:
        docs_fee = 60.0
        pickup_fee = 230.0

    local_total = docs_fee + pickup_fee
    total = freight + local_total

    return {
        "actual_weight": weight_kg,
        "volumetric_weight": volumetric,
        "chargeable_weight": chargeable,
        "freight": freight,
        "rate": rate,
        "docs_fee": docs_fee,
        "pickup_fee": pickup_fee,
        "local_total": local_total,
        "total": total,
    }


# ---------- РАСЧЁТ ЖД ----------

def calc_rail(weight_kg: float, volume_m3: float) -> Dict[str, Any]:
    freight = volume_m3 * 200.0

    # Если вдруг веса нет, берем 1 м³ = 500 кг
    used_weight = weight_kg if weight_kg > 0 else volume_m3 * 500.0

    if used_weight <= 100:
        docs_fee = 60.0
        pickup_fee = 90.0
    elif used_weight <= 300:
        docs_fee = 60.0
        pickup_fee = 115.0
    elif used_weight <= 800:
        docs_fee = 60.0
        pickup_fee = 195.0
    else:
        docs_fee = 60.0
        pickup_fee = 230.0

    local_total = docs_fee + pickup_fee
    total = freight + local_total

    return {
        "actual_weight": weight_kg,
        "used_weight": used_weight,
        "volume_m3": volume_m3,
        "freight": freight,
        "docs_fee": docs_fee,
        "pickup_fee": pickup_fee,
        "local_total": local_total,
        "total": total,
    }


# ---------- ФОРМИРОВАНИЕ СООБЩЕНИЙ ----------

def build_air_message(origin: str, dest: str, result: Dict[str, Any]) -> str:
    airlines = "China Eastern, Hainan, China Southern"
    custom_clear_rub = 16000

    actual = result["actual_weight"]
    volumetric = result["volumetric_weight"]
    chargeable = result["chargeable_weight"]
    freight = result["freight"]
    rate = result["rate"]
    docs_fee = result["docs_fee"]
    pickup_fee = result["pickup_fee"]
    local_total = result["local_total"]
    total = result["total"]

    if rate is None:
        freight_line = (
            "Фрахт:\n"
            f"фиксированная ставка до 45 кг = {format_usd(freight)}"
        )
    else:
        freight_line = (
            "Фрахт:\n"
            f"{chargeable:.0f} кг × {rate} USD = {format_usd(freight)}"
        )

    text = (
        f"✈️ <b>Авиаперевозка {origin} → {dest}</b>\n\n"
        f"Расчетный вес: <b>{chargeable:.0f} кг</b>\n"
        f"(реальный {actual:.0f} кг, объемный {volumetric:.0f} кг)\n\n"
        f"{freight_line}\n\n"
        f"Локальные сборы в Китае:\n"
        f"{docs_fee:.0f} USD (документы) + {pickup_fee:.0f} USD (забор) = {format_usd(local_total)}\n\n"
        f"<b>ИТОГО по ставке: {format_usd(total)}</b>\n\n"
        f"Дополнительно:\n"
        f"• Таможенное оформление в РФ: {custom_clear_rub} руб/ДТ\n"
        f"• Терминальные затраты в а/п прилета: по факту тарифа аэропорта\n"
        f"• Авиалинии по данному маршруту: {airlines}\n"
        f"• Ориентировочный срок доставки: 5 дней\n\n"
        f"💡 Примечание: при авиаперевозках учитывается объемный вес (м³ × 167).\n"
        f"Если объемный вес больше фактического, расчет ведется по объемному.\n\n"
        f"👉 <b>Заказать перевозку</b>\n"
        f"WhatsApp: +7 929 577 05 82\n"
        f"Email: valeriia_tronina@stforce.su"
    )
    return text


def build_rail_message(origin: str, dest: str, result: Dict[str, Any]) -> str:
    custom_clear_rub = 16000

    volume_m3 = result["volume_m3"]
    actual = result["actual_weight"]
    used_weight = result["used_weight"]
    freight = result["freight"]
    docs_fee = result["docs_fee"]
    pickup_fee = result["pickup_fee"]
    local_total = result["local_total"]
    total = result["total"]

    text = (
        f"🚂 <b>Ж/д перевозка {origin} → {dest}</b>\n\n"
        f"Объем: <b>{volume_m3:.2f} м³</b>, вес: {actual:.0f} кг "
        f"(для расчета локальных использован вес {used_weight:.0f} кг)\n\n"
        f"Фрахт:\n"
        f"{volume_m3:.2f} м³ × 200 USD = {format_usd(freight)}\n\n"
        f"Локальные сборы в Китае:\n"
        f"{pickup_fee:.0f} USD (забор) + {docs_fee:.0f} USD (документы) = {format_usd(local_total)}\n\n"
        f"<b>ИТОГО по ставке: {format_usd(total)}</b>\n\n"
        f"Дополнительно:\n"
        f"• Таможенное оформление в РФ: {custom_clear_rub} руб/ДТ\n"
        f"• Терминальные затраты на станции прибытия: включены\n"
        f"• Дополнительно: локальные затраты в Китае могут рассчитываться отдельно.\n"
        f"• Срок доставки: 35 дней\n\n"
        f"👉 <b>Заказать перевозку</b>\n"
        f"WhatsApp: +7 929 577 05 82\n"
        f"Email: valeriia_tronina@stforce.su"
    )
    return text


# ---------- ХЭНДЛЕРЫ ----------

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "Привет! Я бот для расчета ставок на доставку грузов из Китая ✈️🚂\n\n"
        "Выберите вид перевозки:",
        reply_markup=main_menu_kb(),
    )


@dp.message_handler(lambda m: m.text in ["✈️ Авиа из Китая", "🚂 ЖД из Китая"], state="*")
async def choose_transport(message: types.Message, state: FSMContext):
    await state.finish()
    transport = "air" if "Авиа" in message.text else "rail"
    await state.update_data(transport=transport)

    await QueryStates.choosing_destination.set()
    await message.answer(
        "Куда в Россию доставляем?",
        reply_markup=destination_kb(transport),
    )


@dp.message_handler(lambda m: m.text == "🏠 В главное меню", state="*")
async def go_main_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "Главное меню. Выберите вид перевозки:",
        reply_markup=main_menu_kb(),
    )


@dp.message_handler(lambda m: m.text == "🔁 Посчитать заново", state="*")
async def restart_calc(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "Начнем заново. Выберите вид перевозки:",
        reply_markup=main_menu_kb(),
    )


@dp.message_handler(state=QueryStates.choosing_destination)
async def process_destination(message: types.Message, state: FSMContext):
    dest_text = message.text.strip()
    data = await state.get_data()
    transport = data.get("transport")

    if transport == "air":
        if "Москва" in dest_text or "SVO" in dest_text or "Шереметьево" in dest_text:
            dest = "Москва (Шереметьево, SVO)"
        elif (
            "Санкт" in dest_text
            or "Петербург" in dest_text
            or "LED" in dest_text
            or "Пулково" in dest_text
        ):
            dest = "Санкт-Петербург (Пулково, LED)"
        else:
            await message.answer(
                "Пожалуйста, выберите город доставки из кнопок ниже.",
                reply_markup=destination_kb(transport),
            )
            return
    else:
        if "Москва" in dest_text:
            dest = "Москва (станция)"
        elif "Санкт" in dest_text or "Петербург" in dest_text:
            dest = "Санкт-Петербург (станция)"
        else:
            await message.answer(
                "Пожалуйста, выберите город доставки из кнопок ниже.",
                reply_markup=destination_kb(transport),
            )
            return

    await state.update_data(destination=dest)
    await QueryStates.choosing_origin.set()
    await message.answer("Из какого города в Китае отправляем?", reply_markup=origin_kb())


@dp.message_handler(state=QueryStates.choosing_origin)
async def process_origin(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "✏️ Ввести другой город":
        await QueryStates.entering_custom_origin.set()
        kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("🏠 В главное меню")
        )
        await message.answer(
            "Введите город отправки в Китае (на русском или английском):",
            reply_markup=kb,
        )
        return

    origin = text
    await state.update_data(origin=origin)
    await QueryStates.entering_weight.set()

    kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("🏠 В главное меню")
    )
    await message.answer(
        "Введите вес груза (кг). Можно округлить до целого:",
        reply_markup=kb,
    )


@dp.message_handler(state=QueryStates.entering_custom_origin)
async def process_custom_origin(message: types.Message, state: FSMContext):
    origin = message.text.strip()
    await state.update_data(origin=origin)
    await QueryStates.entering_weight.set()

    kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("🏠 В главное меню")
    )
    await message.answer(
        "Введите вес груза (кг). Можно округлить до целого:",
        reply_markup=kb,
    )


@dp.message_handler(state=QueryStates.entering_weight)
async def process_weight(message: types.Message, state: FSMContext):
    value = parse_float(message.text)
    if value is None:
        await message.answer(
            "Не удалось распознать вес. Введите число в кг, больше нуля.\n"
            "Пример: 120 или 85.5"
        )
        return

    await state.update_data(weight=value)
    await QueryStates.entering_volume.set()

    kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("🏠 В главное меню")
    )
    await message.answer(
        "Введите объем груза (м³). Можно округлить до целого:",
        reply_markup=kb,
    )


@dp.message_handler(state=QueryStates.entering_volume)
async def process_volume(message: types.Message, state: FSMContext):
    value = parse_float(message.text)
    if value is None:
        await message.answer(
            "Не удалось распознать объем. Введите число в м³, больше нуля.\n"
            "Пример: 2.5"
        )
        return

    data = await state.get_data()
    transport = data.get("transport")
    destination = data.get("destination")
    origin = data.get("origin")
    weight = data.get("weight")
    volume = value

    user_id = message.from_user.id
    last_queries[user_id] = {
        "origin": origin,
        "destination": destination,
        "weight": weight,
        "volume": volume,
    }

    await state.finish()

    if transport == "air":
        result = calc_air(weight, volume)
        text = build_air_message(origin, destination, result)
        kb = nav_inline_kb(show_other_mode="rail")
    else:
        result = calc_rail(weight, volume)
        text = build_rail_message(origin, destination, result)
        kb = nav_inline_kb(show_other_mode="air")

    await message.answer(text, reply_markup=kb)


# ---------- CALLBACK-КНОПКИ ----------

@dp.callback_query_handler(
    lambda c: c.data in {"calc_air_from_last", "calc_rail_from_last", "restart", "main_menu"}
)
async def callbacks_handler(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if data == "restart":
        await state.finish()
        await bot.send_message(
            user_id,
            "Начнем заново. Выберите вид перевозки:",
            reply_markup=main_menu_kb(),
        )
        await callback_query.answer()
        return

    if data == "main_menu":
        await state.finish()
        await bot.send_message(
            user_id,
            "Главное меню. Выберите вид перевозки:",
            reply_markup=main_menu_kb(),
        )
        await callback_query.answer()
        return

    if user_id not in last_queries:
        await callback_query.answer(
            "Нет сохраненных параметров. Пожалуйста, начните новый расчет.",
            show_alert=True,
        )
        return

    q = last_queries[user_id]
    origin = q["origin"]
    destination = q["destination"]
    weight = q["weight"]
    volume = q["volume"]

    if data == "calc_air_from_last":
        result = calc_air(weight, volume)
        text = build_air_message(origin, destination, result)
        kb = nav_inline_kb(show_other_mode="rail")
    else:
        result = calc_rail(weight, volume)
        text = build_rail_message(origin, destination, result)
        kb = nav_inline_kb(show_other_mode="air")

    await bot.send_message(user_id, text, reply_markup=kb)
    await callback_query.answer()


# ---------- БЫСТРЫЕ КОМАНДЫ "АВИА"/"ЖД" ----------

@dp.message_handler(
    lambda m: m.text and m.text.lower().strip() in {"авиа", "✈️ авиа", "авиа из китая"},
    state="*",
)
async def quick_air_from_last(message: types.Message):
    user_id = message.from_user.id
    if user_id not in last_queries:
        await message.answer(
            "Нет сохраненных параметров. Сначала сделайте расчет, "
            "а затем можно будет пересчитывать авиа/жд по тем же данным."
        )
        return

    q = last_queries[user_id]
    result = calc_air(q["weight"], q["volume"])
    text = build_air_message(q["origin"], q["destination"], result)
    kb = nav_inline_kb(show_other_mode="rail")
    await message.answer(text, reply_markup=kb)


@dp.message_handler(
    lambda m: m.text and ("жд" in m.text.lower() or "ж/д" in m.text.lower()),
    state="*",
)
async def quick_rail_from_last(message: types.Message):
    user_id = message.from_user.id
    if user_id not in last_queries:
        await message.answer(
            "Нет сохраненных параметров. Сначала сделайте расчет, "
            "а затем можно будет пересчитывать авиа/жд по тем же данным."
        )
        return

    q = last_queries[user_id]
    result = calc_rail(q["weight"], q["volume"])
    text = build_rail_message(q["origin"], q["destination"], result)
    kb = nav_inline_kb(show_other_mode="air")
    await message.answer(text, reply_markup=kb)


# ---------- ФОЛБЭК ----------

@dp.message_handler(state="*")
async def fallback(message: types.Message):
    await message.answer(
        "Я пока умею считать ставки ✈️ и 🚂.\n"
        "Выберите действие в меню:",
        reply_markup=main_menu_kb(),
    )


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
