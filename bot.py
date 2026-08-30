# -*- coding: utf-8 -*-
"""
Telegram-бот для продажи PDF-гайда «СТАРТ.SHOPIFY» через Telegram Stars.

Логика:
1. /start -> приветствие + бесплатный VSL-урок (текст + PDF)
2. Показ оффера на покупку полного гайда за Stars
3. Кнопка "Купить" -> выставляется invoice в валюте XTR (Telegram Stars)
4. После успешной оплаты -> бот сразу присылает файл полного гайда
5. Кнопка "У меня нет звёзд" -> ссылка на бота для покупки Stars

Запуск: python bot.py
Требования: pip install -r requirements.txt
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, PreCheckoutQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, FSInputFile,
)

import config
import db
import texts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


# ---------------------------------------------------------------
# Клавиатуры
# ---------------------------------------------------------------
def kb_after_free_lesson() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💎 Купить полный гайд за {config.PRICE_STARS} ⭐",
            callback_data="buy_guide"
        )],
        [InlineKeyboardButton(
            text="❓ У меня нет звёзд — как купить?",
            callback_data="no_stars"
        )],
    ])


def kb_no_stars() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Купить Telegram Stars", url=config.STARS_BOT_LINK)],
        [InlineKeyboardButton(
            text=f"💎 Купить гайд за {config.PRICE_STARS} ⭐",
            callback_data="buy_guide"
        )],
    ])


def kb_buy_again() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💎 Купить полный гайд за {config.PRICE_STARS} ⭐",
            callback_data="buy_guide"
        )],
    ])


# ---------------------------------------------------------------
# /start — приветствие + бесплатный урок
# ---------------------------------------------------------------
@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    db.upsert_user(user.id, user.username or user.full_name)

    await message.answer(texts.WELCOME, parse_mode="HTML")
    await asyncio.sleep(1.5)

    await message.answer(texts.FREE_LESSON_INTRO, parse_mode="HTML")

    try:
        pdf_file = FSInputFile(config.FREE_PDF_PATH)
        await message.answer_document(pdf_file, caption=texts.FREE_LESSON_CAPTION)
        db.mark_free_lesson_sent(user.id)
    except FileNotFoundError:
        logger.error("Файл бесплатного урока не найден: %s", config.FREE_PDF_PATH)
        await message.answer("⚠️ Файл урока временно недоступен, но оффер уже готов ниже.")

    await asyncio.sleep(1.5)
    await message.answer(texts.OFFER_TEXT, parse_mode="HTML", reply_markup=kb_after_free_lesson())


# ---------------------------------------------------------------
# /buy — прямой вызов покупки
# ---------------------------------------------------------------
@router.message(Command("buy"))
async def cmd_buy(message: Message):
    await send_invoice(message.chat.id, message.from_user)


# ---------------------------------------------------------------
# /myguide — повторная отправка купленного файла
# ---------------------------------------------------------------
@router.message(Command("myguide"))
async def cmd_myguide(message: Message):
    if db.has_purchased(message.from_user.id):
        pdf_file = FSInputFile(config.FULL_PDF_PATH)
        await message.answer_document(pdf_file, caption="📘 Вот твой файл ещё раз.")
    else:
        await message.answer(
            "Пока не вижу покупки на твоём аккаунте 🙂",
            reply_markup=kb_buy_again()
        )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(texts.HELP_TEXT)


# ---------------------------------------------------------------
# Callback: "У меня нет звёзд"
# ---------------------------------------------------------------
@router.callback_query(F.data == "no_stars")
async def cb_no_stars(callback: CallbackQuery):
    await callback.message.answer(
        texts.NO_STARS_TEXT.format(link=config.STARS_BOT_LINK),
        parse_mode="HTML",
        reply_markup=kb_no_stars(),
        disable_web_page_preview=True,
    )
    await callback.answer()


# ---------------------------------------------------------------
# Callback: "Купить гайд" -> выставляем инвойс в Stars
# ---------------------------------------------------------------
@router.callback_query(F.data == "buy_guide")
async def cb_buy_guide(callback: CallbackQuery):
    await send_invoice(callback.message.chat.id, callback.from_user)
    await callback.answer()


async def send_invoice(chat_id: int, user):
    """Выставляет счёт на оплату в Telegram Stars (валюта XTR)."""
    prices = [LabeledPrice(label="СТАРТ.SHOPIFY — полное руководство", amount=config.PRICE_STARS)]
    await bot.send_invoice(
        chat_id=chat_id,
        title=texts.INVOICE_TITLE,
        description=texts.INVOICE_DESCRIPTION,
        payload=f"full_guide_{user.id}",
        provider_token="",  # для Stars provider_token всегда пустой
        currency="XTR",
        prices=prices,
    )


# ---------------------------------------------------------------
# Обязательный обработчик pre_checkout — должен ответить в течение 10 сек
# ---------------------------------------------------------------
@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


# ---------------------------------------------------------------
# Успешная оплата -> выдаём файл
# ---------------------------------------------------------------
@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payment = message.successful_payment
    user = message.from_user

    db.save_purchase(
        user_id=user.id,
        username=user.username or user.full_name,
        amount_stars=payment.total_amount,
        charge_id=payment.telegram_payment_charge_id,
    )

    await message.answer(texts.PAYMENT_SUCCESS, parse_mode="HTML")

    pdf_file = FSInputFile(config.FULL_PDF_PATH)
    await message.answer_document(pdf_file, caption="📘 СТАРТ.SHOPIFY — полное руководство")

    if config.ADMIN_ID:
        try:
            await bot.send_message(
                config.ADMIN_ID,
                f"💰 Новая продажа!\n"
                f"Пользователь: @{user.username or user.id} (id: {user.id})\n"
                f"Сумма: {payment.total_amount} ⭐\n"
                f"Charge ID: {payment.telegram_payment_charge_id}"
            )
        except Exception as e:
            logger.warning("Не удалось уведомить админа: %s", e)


# ---------------------------------------------------------------
# /stats — только для администратора
# ---------------------------------------------------------------
@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    s = db.stats()
    await message.answer(
        f"📊 Статистика бота\n\n"
        f"Всего пользователей: {s['total_users']}\n"
        f"Продаж: {s['total_purchases']}\n"
        f"Всего заработано: {s['total_stars']} ⭐"
    )


# ---------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------
async def main():
    db.init_db()
    logger.info("Бот запущен, ожидаю сообщения...")
    await bot.delete\_webhook drop\_pending\_updates=True\ await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
