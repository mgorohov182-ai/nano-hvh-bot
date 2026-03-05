import os
import asyncio
import logging
import time
import uuid
import traceback
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile,
    CallbackQuery, ForceReply
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiocryptopay import AioCryptoPay, Networks

# ========== НАСТРОЙКИ ==========
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 1589789716            # Твой ID (для уведомлений о покупках и поддержки)
CL3WR_ID = 8490398012            # ID @cl3wr (тоже получает уведомления)
BOT_NAME = "Nano_hvh"

# Токен от Crypto Pay (приложение) – твой токен
CRYPTOBOT_API_TOKEN = os.getenv('CRYPTOPAY_TOKEN')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=storage)

# Клиент Crypto Pay (будет инициализирован ниже)
crypto = None

# Хранилище для отслеживания платежей (pending)
pending_payments = {}

# ========== КЛАВИАТУРЫ ==========

def main_menu_keyboard():
    """Главное меню (4 кнопки)"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📖 Об боте", callback_data="about"),
        InlineKeyboardButton(text="👤 Автор бота", callback_data="author"),
        InlineKeyboardButton(text="🛒 Выбор товара", callback_data="choose_category"),
        InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")
    )
    builder.adjust(1)
    return builder.as_markup()

def category_keyboard():
    """Выбор категории товаров"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="cl3wr #hvh", callback_data="cat_cl3wr"),
        InlineKeyboardButton(text="Nova Executor", callback_data="cat_nova"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    builder.adjust(1)
    return builder.as_markup()

def minecraft_keyboard():
    """Товары для Minecraft (категория cl3wr)"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Конфиг Apollon Client (Phoenix-Pe) - 0.90 USDT", callback_data="buy_apollon"),
        InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="choose_category")
    )
    builder.adjust(1)
    return builder.as_markup()

def roblox_keyboard():
    """Товары для Roblox (категория Nova)"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Nova Executor (v1.0)", callback_data="nova_v1"),
        InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="choose_category")
    )
    builder.adjust(1)
    return builder.as_markup()

def cancel_keyboard():
    """Кнопка отмены (для режима поддержки)"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_support"))
    return builder.as_markup()

def admin_reply_keyboard(user_id: int):
    """Кнопка ответа для админа (прикрепляется к сообщению пользователя)"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✍️ Ответить", callback_data=f"reply_to_{user_id}"))
    return builder.as_markup()

# ========== FSM для ПОДДЕРЖКИ ==========

class SupportStates(StatesGroup):
    waiting_for_message = State()      # Ожидание сообщения от пользователя
    waiting_for_admin_reply = State()  # Ожидание ответа от админа

# ========== ИНИЦИАЛИЗАЦИЯ CRYPTO PAY ==========
async def init_crypto():
    """Пытается инициализировать CryptoPay клиент"""
    global crypto
    
    # Сначала пробуем MAIN_NET
    try:
        crypto = AioCryptoPay(token=CRYPTOBOT_API_TOKEN, network=Networks.MAIN_NET)
        # Пробуем выполнить простой запрос для проверки
        await crypto.get_me()
        logger.info("✅ CryptoPay клиент инициализирован (MAIN_NET)")
        return True
    except Exception as e:
        logger.warning(f"⚠️ MAIN_NET не работает: {e}")
    
    # Если MAIN_NET не работает, пробуем TEST_NET
    try:
        crypto = AioCryptoPay(token=CRYPTOBOT_API_TOKEN, network=Networks.TEST_NET)
        await crypto.get_me()
        logger.info("✅ CryptoPay клиент инициализирован (TEST_NET)")
        return True
    except Exception as e:
        logger.error(f"❌ TEST_NET тоже не работает: {e}")
        crypto = None
        return False

# ========== ОБРАБОТЧИКИ КОМАНД ==========

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Приветствие с фото и главным меню"""
    caption = (
        f"👋 *Здравствуйте!*\n"
        f"Добро пожаловать в бот проекта *{BOT_NAME}*.\n"
        f"Этот бот создан совместно с проектом "
        f"[cl3wr #hvh](https://t.me/fuckhvh0) и "
        f"[Nova Executor](https://t.me/nova_entry).\n\n"
        f"Автор бота: @PSYHOK7T\n\n"
        f"Используйте кнопки ниже для навигации."
    )
    try:
        photo = FSInputFile("logo.jpg")
        await message.answer_photo(
            photo=photo,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
    except FileNotFoundError:
        await message.answer(
            text=caption,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

# ========== НАВИГАЦИЯ ==========

@dp.callback_query(F.data == "about")
async def about_callback(callback: CallbackQuery):
    text = (
        f"ℹ️ *О боте*\n\n"
        f"*{BOT_NAME}* — это инновационный инжектор для улучшения игрового процесса.\n"
        f"Мы предоставляем лучшие решения для Minecraft и Roblox.\n\n"
        f"Бот создан при поддержке:\n"
        f"• [cl3wr #hvh](https://t.me/fuckhvh0)\n"
        f"• [Nova Executor](https://t.me/nova_entry)\n\n"
        f"По всем вопросам обращайтесь в поддержку (кнопка «Поддержка»)."
    )
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "author")
async def author_callback(callback: CallbackQuery):
    text = "👤 Автор бота: @PSYHOK7T"
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "choose_category")
async def choose_category_callback(callback: CallbackQuery):
    text = "⬇️ Выберите категорию товара:"
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=category_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "cat_cl3wr")
async def cat_cl3wr_callback(callback: CallbackQuery):
    text = "🟢 *cl3wr #hvh*\nВыберите товар:"
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=minecraft_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "cat_nova")
async def cat_nova_callback(callback: CallbackQuery):
    text = "🔵 *Nova Executor*\nВыберите товар:"
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=roblox_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "nova_v1")
async def nova_v1_callback(callback: CallbackQuery):
    text = "🚧 Nova Executor (v1.0) находится в разработке. Скоро будет доступен!"
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    try:
        await callback.message.edit_caption(
            caption="Главное меню:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
    except Exception:
        await callback.message.delete()
        try:
            photo = FSInputFile("logo.jpg")
            await callback.message.answer_photo(
                photo=photo,
                caption="👋 *Главное меню*",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        except FileNotFoundError:
            await callback.message.answer(
                "👋 *Главное меню*",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
    await callback.answer()

# ========== ТОВАРЫ И ОПЛАТА (CryptoBot) ==========

@dp.callback_query(F.data == "buy_apollon")
async def buy_apollon(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Проверяем, инициализирован ли CryptoPay клиент
    if crypto is None:
        logger.error("❌ CryptoPay клиент не инициализирован")
        await callback.message.answer("❌ Ошибка конфигурации платежной системы. Сообщите администратору.")
        await callback.answer()
        return
    
    # Генерируем уникальный ID для этой покупки
    payment_id = f"payment_{user_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    
    try:
        logger.info(f"🔄 Создание инвойса для пользователя {user_id}, payment_id: {payment_id}")
        
        # Создаём инвойс в CryptoBot через API
        invoice = await crypto.create_invoice(
            asset='USDT',
            amount=0.90,
            description="Конфиг Apollon Client (Phoenix-Pe)",
            payload=payment_id,
            expires_in=3600  # ссылка действительна 1 час
        )
        
        # Получаем URL для оплаты (в разных версиях библиотеки он может называться по-разному)
        pay_url = None
        if hasattr(invoice, 'pay_url'):
            pay_url = invoice.pay_url
        elif hasattr(invoice, 'bot_invoice_url'):
            pay_url = invoice.bot_invoice_url
        elif hasattr(invoice, 'url'):
            pay_url = invoice.url
        else:
            # Если не нашли, пробуем собрать вручную
            pay_url = f"https://t.me/CryptoBot?start={invoice.invoice_id}"
            logger.warning(f"⚠️ Не удалось найти URL в объекте, используем сгенерированный: {pay_url}")
        
        logger.info(f"✅ Инвойс создан успешно! ID: {invoice.invoice_id}, URL: {pay_url}")
        
        # Сохраняем информацию о pending платеже
        pending_payments[payment_id] = {
            'user_id': user_id,
            'status': 'pending',
            'invoice_id': invoice.invoice_id,
            'pay_url': pay_url,
            'message_id': callback.message.message_id,
            'chat_id': callback.message.chat.id
        }
        
        # Формируем сообщение с кнопкой для оплаты
        pay_text = (
            f"💎 *Оплата конфига Apollon Client*\n\n"
            f"Сумма к оплате: *0.90 USDT* (≈70₽ с учётом комиссии)\n\n"
            f"1. Нажми на кнопку ниже 👇, чтобы перейти в CryptoBot.\n"
            f"2. Подтверди перевод указанной суммы.\n"
            f"3. После оплаты бот автоматически отправит файл с конфигом.\n\n"
            f"⏳ *Ссылка действительна 1 час*"
        )
        
        pay_button = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Перейти к оплате", url=pay_url)],
                [InlineKeyboardButton(text="✅ Я оплатил (проверить)", callback_data=f"check_payment_{payment_id}")]
            ]
        )
        
        # Редактируем caption (подпись к фото), так как исходное сообщение содержит фото
        await callback.message.edit_caption(
            caption=pay_text,
            parse_mode="Markdown",
            reply_markup=pay_button
        )
        
        # Запускаем фоновую задачу для автоматической проверки
        asyncio.create_task(check_payment_status(payment_id, user_id))
        
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"❌ Ошибка при создании счета в CryptoBot: {e}\n{error_details}")
        await callback.message.answer(
            "❌ Произошла ошибка при создании платежа. Попробуйте позже."
        )
    
    await callback.answer()

# ========== ПРОВЕРКА СТАТУСА ПЛАТЕЖА ==========
async def check_payment_status(payment_id: str, user_id: int):
    """Проверяет статус платежа через API CryptoBot (раз в 30 секунд)"""
    await asyncio.sleep(30)  # Первая проверка через 30 секунд
    
    max_checks = 60  # Будем проверять 60 раз (каждые 30 сек) = 30 минут
    for i in range(max_checks):
        if payment_id not in pending_payments:
            logger.info(f"⏹️ Платёж {payment_id} уже обработан или отменён")
            return
        
        try:
            invoice_id = pending_payments[payment_id]['invoice_id']
            logger.info(f"🔄 Проверка статуса {i+1}/{max_checks} для инвойса {invoice_id}")
            
            invoices = await crypto.get_invoices(invoice_ids=[invoice_id])
            if invoices and invoices[0].status == 'paid':
                logger.info(f"✅ Инвойс {invoice_id} оплачен!")
                await send_file_and_cleanup(payment_id, user_id)
                return
            else:
                status = invoices[0].status if invoices else "unknown"
                logger.info(f"⏳ Инвойс {invoice_id} ещё не оплачен (статус: {status})")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке статуса: {e}")
        
        await asyncio.sleep(30)
    
    # Если вышли из цикла, время истекло
    if payment_id in pending_payments:
        logger.info(f"⏰ Время оплаты для {payment_id} истекло")
        del pending_payments[payment_id]
        try:
            await bot.send_message(user_id, "⏰ Время оплаты истекло. Если хотите купить, начните заново.")
        except:
            pass

@dp.callback_query(lambda c: c.data and c.data.startswith("check_payment_"))
async def check_payment_callback(callback: CallbackQuery):
    """Ручная проверка по кнопке «Я оплатил»"""
    payment_id = callback.data.replace("check_payment_", "")
    
    if payment_id not in pending_payments:
        await callback.message.edit_caption(
            caption="❌ Платеж не найден или уже обработан. Попробуйте оформить покупку заново.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        await callback.answer()
        return
    
    try:
        invoice_id = pending_payments[payment_id]['invoice_id']
        logger.info(f"🔄 Ручная проверка инвойса {invoice_id}")
        
        invoices = await crypto.get_invoices(invoice_ids=[invoice_id])
        if invoices and invoices[0].status == 'paid':
            logger.info(f"✅ Инвойс {invoice_id} оплачен (ручная проверка)")
            await send_file_and_cleanup(payment_id, callback.from_user.id, callback.message)
        else:
            status = invoices[0].status if invoices else "unknown"
            await callback.answer(f"❌ Платеж еще не поступил (статус: {status}). Попробуйте через минуту.", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Ошибка при ручной проверке: {e}")
        await callback.answer("❌ Ошибка при проверке. Попробуйте позже.", show_alert=True)

# ========== ОТПРАВКА ФАЙЛА ПОСЛЕ УСПЕШНОЙ ОПЛАТЫ ==========
async def send_file_and_cleanup(payment_id: str, user_id: int, message_to_edit=None):
    """Отправляет файл, удаляет информацию о платеже и уведомляет админов"""
    
    # Отправляем файл пользователю
    try:
        document = FSInputFile("Apollon.json")
        await bot.send_document(
            user_id,
            document=document,
            caption="✅ *Спасибо огромное за покупку!*\nЖдем вас еще!",
            parse_mode="Markdown"
        )
        logger.info(f"📄 Файл отправлен пользователю {user_id}")
    except FileNotFoundError:
        logger.error(f"❌ Файл Apollon.json не найден!")
        await bot.send_message(
            user_id,
            "✅ *Спасибо за покупку!*\nФайл временно недоступен, но администратор скоро пришлет его вручную.",
            parse_mode="Markdown"
        )
        # Уведомляем админа, что файла нет
        await bot.send_message(ADMIN_ID, f"⚠️ Пользователь {user_id} оплатил, но файл Apollon.json не найден!")
    
    # Получаем информацию о пользователе
    try:
        user_chat = await bot.get_chat(user_id)
        user_name = user_chat.full_name
        username = user_chat.username
    except:
        user_name = "Неизвестно"
        username = None
    
    user_mention = f"@{username}" if username else f"ID: {user_id}"
    
    # Текст уведомления для админов
    notification_text = (
        f"🛒 *Новая покупка в категории cl3wr #hvh!*\n\n"
        f"Покупатель: {user_name} ({user_mention})\n"
        f"Товар: Конфиг Apollon Client (Phoenix-Pe)\n"
        f"Сумма: 0.90 USDT"
    )
    
    # Отправляем уведомление @cl3wr
    try:
        await bot.send_message(CL3WR_ID, notification_text, parse_mode="Markdown")
        logger.info(f"📨 Уведомление отправлено @cl3wr (ID: {CL3WR_ID})")
    except Exception as e:
        logger.error(f"❌ Не удалось отправить уведомление @cl3wr: {e}")
    
    # Отправляем такое же уведомление тебе (админу)
    try:
        await bot.send_message(ADMIN_ID, notification_text, parse_mode="Markdown")
        logger.info(f"📨 Уведомление отправлено админу (ID: {ADMIN_ID})")
    except Exception as e:
        logger.error(f"❌ Не удалось отправить уведомление админу: {e}")
    
    # Удаляем платеж из списка ожидающих
    if payment_id in pending_payments:
        del pending_payments[payment_id]
        logger.info(f"🗑️ Платёж {payment_id} удалён из pending")
    
    # Если нужно отредактировать сообщение с кнопкой
    if message_to_edit:
        await message_to_edit.edit_caption(
            caption="✅ *Оплата прошла успешно!*\nФайл уже отправлен выше 👆",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
    
    # Возвращаем главное меню (отправляем новое сообщение)
    try:
        photo = FSInputFile("logo.jpg")
        await bot.send_photo(
            user_id,
            photo=photo,
            caption="👋 *Главное меню*",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
    except FileNotFoundError:
        await bot.send_message(
            user_id,
            "👋 *Главное меню*",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

# ========== ПОДДЕРЖКА (АНОНИМНАЯ) ==========

@dp.callback_query(F.data == "support")
async def support_callback(callback: CallbackQuery, state: FSMContext):
    text = (
        "🆘 *Поддержка*\n\n"
        "Здесь ты можешь задать вопрос или сообщить о проблеме.\n"
        "Напиши сообщение, и я передам его администратору.\n\n"
        "Ты можешь отправить текст, фото, голосовое сообщение или файл."
    )
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(SupportStates.waiting_for_message)
    await callback.answer()

@dp.callback_query(F.data == "cancel_support")
async def cancel_support_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await back_to_main(callback)

@dp.message(SupportStates.waiting_for_message)
async def handle_support_message(message: types.Message, state: FSMContext):
    """Пользователь отправил сообщение в поддержку"""
    user = message.from_user
    user_info = f"Пользователь: {user.full_name} (@{user.username})\nID: {user.id}"
    
    try:
        # Уведомление админу
        await bot.send_message(
            ADMIN_ID,
            f"📩 *Новое обращение в поддержку*\n\n{user_info}",
            parse_mode="Markdown"
        )
        
        # Пересылаем само сообщение с кнопкой ответа
        if message.text:
            await bot.send_message(
                ADMIN_ID,
                f"✉️ *Сообщение:*\n{message.text}",
                parse_mode="Markdown",
                reply_markup=admin_reply_keyboard(user.id)
            )
        elif message.photo:
            photo = message.photo[-1].file_id
            caption = message.caption or "Фото без подписи"
            await bot.send_photo(
                ADMIN_ID,
                photo,
                caption=f"📷 *Фото от пользователя*\n\n{caption}",
                parse_mode="Markdown",
                reply_markup=admin_reply_keyboard(user.id)
            )
        elif message.voice:
            await bot.send_voice(
                ADMIN_ID,
                message.voice.file_id,
                caption="🎤 *Голосовое сообщение*",
                parse_mode="Markdown",
                reply_markup=admin_reply_keyboard(user.id)
            )
        elif message.document:
            await bot.send_document(
                ADMIN_ID,
                message.document.file_id,
                caption=f"📎 *Документ*\n\n{message.caption or ''}",
                parse_mode="Markdown",
                reply_markup=admin_reply_keyboard(user.id)
            )
        else:
            await message.forward(ADMIN_ID)
        
        # Подтверждение пользователю
        await message.answer(
            "✅ Твоё сообщение отправлено администратору. Скоро получишь ответ!"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка поддержки: {e}")
        await message.answer("❌ Произошла ошибка. Попробуй позже.")
    
    await state.clear()
    # Возвращаем главное меню
    try:
        photo = FSInputFile("logo.jpg")
        await message.answer_photo(
            photo=photo,
            caption="👋 *Главное меню*",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
    except FileNotFoundError:
        await message.answer(
            "👋 *Главное меню*",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

@dp.callback_query(lambda c: c.data and c.data.startswith("reply_to_"))
async def admin_reply_callback(callback: CallbackQuery, state: FSMContext):
    """Админ нажал 'Ответить' на сообщение пользователя"""
    user_id = int(callback.data.replace("reply_to_", ""))
    await state.update_data(reply_to_user=user_id)
    await callback.message.answer(
        f"✍️ Напиши ответ пользователю (ID: {user_id}):",
        reply_markup=ForceReply(selective=True)
    )
    await state.set_state(SupportStates.waiting_for_admin_reply)
    await callback.answer()

@dp.message(SupportStates.waiting_for_admin_reply)
async def handle_admin_reply(message: types.Message, state: FSMContext):
    """Администратор отправляет ответ пользователю"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У тебя нет прав для ответа.")
        await state.clear()
        return
    
    data = await state.get_data()
    user_id = data.get("reply_to_user")
    if not user_id:
        await message.answer("❌ Ошибка: не указан получатель.")
        await state.clear()
        return
    
    try:
        await bot.send_message(
            user_id,
            f"✉️ *Ответ от поддержки:*\n\n{message.text}",
            parse_mode="Markdown"
        )
        await message.answer("✅ Ответ отправлен пользователю!")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки ответа: {e}")
        await message.answer("❌ Не удалось отправить ответ. Возможно, пользователь заблокировал бота.")
    
    await state.clear()

# ========== ЗАПУСК ==========
async def main():
    global crypto
    
    # Инициализируем CryptoPay
    logger.info("🔄 Инициализация CryptoPay...")
    crypto_initialized = await init_crypto()
    
    if crypto_initialized:
        logger.info("✅ CryptoPay успешно инициализирован")
    else:
        logger.error("❌ Не удалось инициализировать CryptoPay. Платежи работать не будут!")
    
    logger.info("🚀 Бот Nano_hvh запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())