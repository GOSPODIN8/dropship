# -*- coding: utf-8 -*-
"""
Конфигурация бота. Значения берутся из переменных окружения (.env),
чтобы не хранить токен и другие секреты прямо в коде.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота, полученный от @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН_СЮДА")

# ID администратора (ваш Telegram user_id) — для уведомлений о продажах.
# Узнать свой ID можно у бота @userinfobot
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Цена полного гайда в Telegram Stars
PRICE_STARS = int(os.getenv("PRICE_STARS", "3999"))

# Ссылка на бота для покупки звёзд (ваша реферальная ссылка)
STARS_BOT_LINK = os.getenv("STARS_BOT_LINK", "https://t.me/suastarsbot?start=user-6147195726")

# Пути к файлам
FREE_PDF_PATH = os.getenv("FREE_PDF_PATH", "files/free_vsl.pdf")
FULL_PDF_PATH = os.getenv("FULL_PDF_PATH", "files/full_guide.pdf")

# Путь к базе данных SQLite (создаётся автоматически)
DB_PATH = os.getenv("DB_PATH", "bot_database.db")
