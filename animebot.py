import logging
import aiohttp
import asyncio
import random
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Категории SFW изображений
SFW_CATEGORIES = [
    "waifu", "neko", "shinobu", "megumin", "bully", "cuddle", "cry", 
    "hug", "awoo", "kiss", "lick", "pat", "smug", "bonk", "yeet", 
    "blush", "smile", "wave", "highfive", "handhold", "nom", "bite", 
    "glomp", "slap", "happy", "wink", "poke", "dance", "cringe"
]

# NSFW категории по API (только рабочие)

NSFW_CATEGORIES = {
    "waifupics": ["waifu", "neko", "trap", "blowjob"],
    "nekoslife": ["lewd", "pussy", "cum", "spank", "boobs", "anal", "hentai", "femdom", "classic", "feet"],
    # "nekosbest": ["neko", "kitsune", "husbando", "waifu"],
    "waifuim": ["maid", "uniform", "marin-kitagawa", "mori-calliope", "raiden-shogun", "oppai", "selfies", 
               "ass", "hentai", "milf", "oral", "paizuri", "ecchi"]
}

# NSFW_CATEGORIES = {
    # "waifupics": ["waifu", "neko", "trap", "blowjob"],
    # "nekoslife": ["lewd", "spank"],  # Оставляем только работающие категории
    # "waifuim": ["ass", "hentai", "milf", "oral", "paizuri", "ecchi"]
# }

# Проверенные рабочие API с таймаутами
API_TIMEOUT = {
    "waifupics": 10,   # Самый стабильный API
    "nekoslife": 5,    # Некоторые категории работают
    "waifuim": 7       # Может быть менее стабильным
}

# Функция для получения изображения с waifu.pics
async def get_waifu_pics_image(category, nsfw=False):
    endpoint = "nsfw" if nsfw else "sfw"
    url = f"https://api.waifu.pics/{endpoint}/{category}"
    logger.info(f"Запрос к waifu.pics: {url}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=API_TIMEOUT["waifupics"]) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("url")
        except Exception as e:
            logger.error(f"Ошибка waifu.pics API: {str(e)}")
    return None

# Функция для получения изображения с nekos.life
async def get_nekos_life_image(category):
    url = f"https://nekos.life/api/v2/img/{category}"
    logger.info(f"Запрос к nekos.life: {url}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=API_TIMEOUT["nekoslife"]) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("url")
        except Exception as e:
            logger.error(f"Ошибка nekos.life API: {str(e)}")
    return None

# Функция для получения изображения с waifu.im
async def get_waifu_im_image(category, nsfw=True):
    is_nsfw = "true" if nsfw else "false"
    url = f"https://api.waifu.im/search"
    params = {"included_tags": category, "is_nsfw": is_nsfw}
    headers = {"Accept": "application/json"}
    logger.info(f"Запрос к waifu.im: {url} с параметрами {params}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, headers=headers, timeout=API_TIMEOUT["waifuim"]) as response:
                if response.status == 200:
                    data = await response.json()
                    if "images" in data and len(data["images"]) > 0:
                        return data["images"][0].get("url")
        except Exception as e:
            logger.error(f"Ошибка waifu.im API: {str(e)}")
    return None

# Универсальная функция получения изображения с повторными попытками
async def get_image(api, category, nsfw=False, max_retries=2):
    logger.info(f"Получение изображения: API={api}, категория={category}, NSFW={nsfw}")
    
    for retry in range(max_retries):
        if retry > 0:
            logger.info(f"Повторная попытка {retry}/{max_retries}")
        
        # Выбираем соответствующий API
        if api == "waifupics":
            image_url = await get_waifu_pics_image(category, nsfw)
        elif api == "nekoslife":
            image_url = await get_nekos_life_image(category)
        elif api == "waifuim":
            image_url = await get_waifu_im_image(category, nsfw)
        else:
            logger.error(f"Неизвестный API: {api}")
            return None
        
        if image_url:
            return image_url
        
        # Пауза перед повторной попыткой
        await asyncio.sleep(0.5)
    
    logger.warning(f"Не удалось получить URL изображения после {max_retries} попыток")
    return None

# Функция для получения случайного изображения
async def get_random_image(nsfw=False):
    # Выбираем API
    apis = list(NSFW_CATEGORIES.keys()) if nsfw else ["waifupics"]
    random.shuffle(apis)
    
    for api in apis:
        # Выбираем случайную категорию
        if nsfw:
            categories = NSFW_CATEGORIES[api]
        else:
            categories = SFW_CATEGORIES if api == "waifupics" else []
            
        random.shuffle(categories)
        
        for category in categories:
            image_url = await get_image(api, category, nsfw)
            if image_url:
                return image_url, api, category
    
    # Если все API не сработали, возвращаем None
    return None, None, None

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = get_main_menu_keyboard()
    await update.message.reply_text(
        "👋 Привет! Я бот для получения аниме картинок.\n\n"
        "🔞 ВНИМАНИЕ: Некоторый контент предназначен только для лиц старше 18 лет!", 
        reply_markup=reply_markup
    )

# Создание клавиатуры главного меню
def get_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌸 SFW картинки", callback_data="menu_sfw")],
        [InlineKeyboardButton("🔞 NSFW картинки", callback_data="menu_nsfw")],
        [InlineKeyboardButton("🌟 Расширенные категории", callback_data="menu_advanced")],
        [InlineKeyboardButton("🎲 Случайное изображение", callback_data="random")],
        [InlineKeyboardButton("🔥 Случайное NSFW", callback_data="random_nsfw")]
    ])

# Создание клавиатуры для SFW категорий
def get_sfw_keyboard():
    keyboard = []
    row = []
    for i, category in enumerate(SFW_CATEGORIES):
        row.append(InlineKeyboardButton(category, callback_data=f"sfw_waifupics_{category}"))
        if len(row) == 3 or i == len(SFW_CATEGORIES) - 1:
            keyboard.append(row)
            row = []
    
    # Добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton("« Назад в главное меню", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(keyboard)

# Создание клавиатуры для NSFW категорий
def get_nsfw_keyboard():
    keyboard = []
    row = []
    for i, category in enumerate(NSFW_CATEGORIES["waifupics"]):
        row.append(InlineKeyboardButton(category, callback_data=f"nsfw_waifupics_{category}"))
        if len(row) == 3 or i == len(NSFW_CATEGORIES["waifupics"]) - 1:
            keyboard.append(row)
            row = []
    
    # Добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton("« Назад в главное меню", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(keyboard)

# Создание клавиатуры для выбора API
def get_api_keyboard():
    keyboard = [
        [InlineKeyboardButton("Waifu.pics (4 категории)", callback_data="api_waifupics")],
        # [InlineKeyboardButton("Nekos.life (2 категории)", callback_data="api_nekoslife")],
        [InlineKeyboardButton("Waifu.im (13 категорий)", callback_data="api_waifuim")],
        [InlineKeyboardButton("« Назад в главное меню", callback_data="back_to_main")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

# Создание клавиатуры для категорий конкретного API
def get_categories_keyboard(api_name):
    if api_name not in NSFW_CATEGORIES:
        return InlineKeyboardMarkup([[InlineKeyboardButton("« Назад", callback_data="menu_advanced")]])
    
    keyboard = []
    row = []
    for i, category in enumerate(NSFW_CATEGORIES[api_name]):
        row.append(InlineKeyboardButton(category, callback_data=f"nsfw_{api_name}_{category}"))
        if len(row) == 3 or i == len(NSFW_CATEGORIES[api_name]) - 1:
            keyboard.append(row)
            row = []
    
    # Добавляем кнопки навигации
    keyboard.append([
        InlineKeyboardButton("« Назад к API", callback_data="menu_advanced"),
        InlineKeyboardButton("« Главное меню", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(keyboard)

# Клавиатура для изображения (следующее и назад)
def get_image_keyboard(data_type, api, category):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Следующее ⏭️", callback_data=f"next_{data_type}_{api}_{category}")],
        [InlineKeyboardButton("« Назад к категориям", callback_data=f"back_to_{api}")],
        [InlineKeyboardButton("« Главное меню", callback_data="back_to_main")]
    ])

# Показать главное меню
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if hasattr(update, 'callback_query') and update.callback_query:
        query = update.callback_query
        # Отправляем новое сообщение вместо попытки редактирования
        await query.message.reply_text("Главное меню:", reply_markup=get_main_menu_keyboard())
    else:
        await update.message.reply_text("Главное меню:", reply_markup=get_main_menu_keyboard())

# Обработка случайного изображения
async def process_random_image(update: Update, context: ContextTypes.DEFAULT_TYPE, nsfw=False):
    # Определяем, от какого типа обновления пришел запрос
    if hasattr(update, 'callback_query') and update.callback_query:
        message = update.callback_query.message
    else:
        message = update.message
    
    wait_message = await message.reply_text("⏳ Загружаю случайное изображение...")
    
    image_url, api, category = await get_random_image(nsfw=nsfw)
    
    if image_url:
        # Создаём клавиатуру с кнопками
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Следующее ⏭️", callback_data=f"random{'_nsfw' if nsfw else ''}")],
            [InlineKeyboardButton("« Главное меню", callback_data="back_to_main")]
        ])
        
        # Отправляем изображение
        await message.reply_photo(
            photo=image_url,
            caption=f"✅ Источник: {api}, категория: {category}",
            reply_markup=keyboard
        )
        await wait_message.delete()
    else:
        await wait_message.edit_text("❌ Не удалось получить изображение. Попробуйте еще раз.")

# Обработка запроса конкретного изображения
async def process_category_image(update: Update, context: ContextTypes.DEFAULT_TYPE, api, category, is_nsfw):
    if hasattr(update, 'callback_query') and update.callback_query:
        message = update.callback_query.message
    else:
        message = update.message
    
    wait_message = await message.reply_text("⏳ Загружаю изображение...")
    
    try:
        logger.info(f"Запрос изображения: API={api}, категория={category}, NSFW={is_nsfw}")
        image_url = await get_image(api, category, is_nsfw)
        
        if image_url:
            # Отправляем изображение
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Следующее ⏭️", callback_data=f"next_{is_nsfw and 'nsfw' or 'sfw'}_{api}_{category}")],
                [InlineKeyboardButton("« Назад к категориям", callback_data=f"back_to_{api}")],
                [InlineKeyboardButton("« Главное меню", callback_data="back_to_main")]
            ])
            
            await message.reply_photo(
                image_url, 
                caption=f"Категория: {category}",
                reply_markup=keyboard
            )
            
            await wait_message.delete()
        else:
            await wait_message.edit_text("⚠️ Не удалось получить изображение. Попробуйте другую категорию.")
    except Exception as e:
        error_message = f"❌ Произошла ошибка: {str(e)}"
        logger.error(error_message)
        try:
            await wait_message.edit_text(error_message)
        except Exception as edit_error:
            logger.error(f"Не удалось отредактировать сообщение: {edit_error}")

# Главный обработчик кнопок
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logger.error(f"Ошибка при ответе на callback: {e}")
    
    data = query.data
    logger.info(f"Получен callback_data: {data}")
    
    # Переменная для проверки, содержит ли сообщение изображение
    has_photo = query.message.photo is not None and len(query.message.photo) > 0
    
    # Обработка возврата в главное меню
    if data == "back_to_main":
        await show_main_menu(update, context)
        return
    
    # Обработка пунктов главного меню
    if data.startswith("menu_"):
        menu_type = data.split("_")[1]
        
        if menu_type == "sfw":
            # Показываем SFW категории
            await query.message.reply_text("Выберите SFW категорию:", reply_markup=get_sfw_keyboard())
        elif menu_type == "nsfw":
            # Показываем NSFW категории
            await query.message.reply_text("⚠️ ВНИМАНИЕ: 18+ контент\nВыберите NSFW категорию:", 
                                          reply_markup=get_nsfw_keyboard())
        elif menu_type == "advanced":
            # Показываем выбор API
            await query.message.reply_text("⚠️ ВНИМАНИЕ: 18+ контент\nВыберите API:", 
                                          reply_markup=get_api_keyboard())
        
        return
    
    # Обработка случайных изображений
    if data == "random":
        await process_random_image(update, context, nsfw=False)
        return
    
    if data == "random_nsfw":
        await process_random_image(update, context, nsfw=True)
        return
    
    # Обработка выбора API
    if data.startswith("api_"):
        api_name = data.split("_")[1]
        logger.info(f"Выбран API: {api_name}")
        
        # Отправляем сообщение с категориями
        await query.message.reply_text(f"Выберите категорию из {api_name}:", 
                                      reply_markup=get_categories_keyboard(api_name))
        return
    
    # Обработка кнопки "Назад к категориям"
    if data.startswith("back_to_"):
        api_name = data.split("_")[2]
        
        if api_name == "waifupics":
            # Возврат к базовым категориям
            await query.message.reply_text("Выберите категорию:", 
                                          reply_markup=get_nsfw_keyboard())
        else:
            # Возврат к категориям конкретного API
            await query.message.reply_text(f"Выберите категорию из {api_name}:", 
                                          reply_markup=get_categories_keyboard(api_name))
        return
    
    # Обработка кнопки "Следующее" для той же категории
    if data.startswith("next_"):
        parts = data.split("_", 3)[1:]  # next_nsfw_waifupics_waifu -> [nsfw, waifupics, waifu]
        if len(parts) == 3:
            type_img, api, category = parts
            is_nsfw = type_img == "nsfw"
            
            await process_category_image(update, context, api, category, is_nsfw)
            return
    
    # Обработка выбора категории (sfw_api_category или nsfw_api_category)
    if data.startswith("sfw_") or data.startswith("nsfw_"):
        parts = data.split("_", 2)
        if len(parts) == 3:
            type_img, api, category = parts
            is_nsfw = type_img == "nsfw"
            
            await process_category_image(update, context, api, category, is_nsfw)
            return
    
    logger.warning(f"Неизвестный формат callback_data: {data}")

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Исключение при обработке обновления: {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text("Произошла ошибка обработки запроса. Попробуйте еще раз позже.")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения об ошибке: {e}")

def main():
    # Создание приложения
    app = Application.builder().token("7749183289:AAG-4DV9aSpyoHJ8QBfoEZDFTaAyj2Re_fM").build()
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", show_main_menu))
    app.add_handler(CallbackQueryHandler(button))
    app.add_error_handler(error_handler)
    
    # Запуск webhook для работы на хостинге
    app.run_webhook(
        listen="0.0.0.0",
        port=8443,
        webhook_url="https://botfotki-wd8u2eri.b4a.run/7749183289:AAG-4DV9aSpyoHJ8QBfoEZDFTaAyj2Re_fM"
    )

if __name__ == "__main__":
    main()

