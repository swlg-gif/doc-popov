import os
import logging
import aiohttp
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from app.database import SessionLocal
from app.models import Patient, Parent, Appointment

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL", "https://doc-popov.ru")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    # Сбрасываем состояние пользователя
    context.user_data.clear()
    
    keyboard = [
        [InlineKeyboardButton("🔐 АВТОРИЗОВАТЬСЯ", callback_data="auth")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Добро пожаловать! Для доступа к данным ребенка необходимо авторизоваться.",
        reply_markup=reply_markup
    )

async def handle_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка авторизации"""
    query = update.callback_query
    await query.answer()
    
    # Устанавливаем состояние ожидания телефона
    context.user_data['awaiting_phone'] = True
    context.user_data['awaiting_password'] = False
    
    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Введите телефонный номер, который указан у врача:"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user_message = update.message.text
    user_id = update.message.from_user.id
    
    logger.info(f"Получено сообщение от пользователя {user_id}: {user_message}")
    
    # Если пользователь в процессе авторизации - ожидаем телефон
    if context.user_data.get('awaiting_phone'):
        # Сохраняем телефон и запрашиваем пароль
        context.user_data['phone'] = user_message
        context.user_data['awaiting_phone'] = False
        context.user_data['awaiting_password'] = True
        
        logger.info(f"Пользователь {user_id} ввел телефон: {user_message}")
        await update.message.reply_text("Введите пароль, который вам сообщил врач:")
    
    # Если ожидаем пароль
    elif context.user_data.get('awaiting_password'):
        # Проверяем пароль
        phone = context.user_data.get('phone')
        password = user_message
        
        logger.info(f"Пользователь {user_id} ввел пароль для телефона {phone}")
        
        db = SessionLocal()
        try:
            parent = db.query(Parent).filter(Parent.phone == phone, Parent.password == password).first()
            if parent:
                context.user_data['authenticated'] = True
                context.user_data['parent_id'] = parent.id
                context.user_data['parent_name'] = f"{parent.first_name} {parent.last_name}"
                context.user_data['awaiting_password'] = False
                
                logger.info(f"Успешная авторизация пользователя {user_id} как {parent.first_name}")
                await update.message.reply_text(f"✅ Успешная авторизация! Добро пожаловать, {parent.first_name}!")
                await show_main_menu(update, context)
            else:
                logger.warning(f"Неудачная попытка авторизации для телефона {phone}")
                await update.message.reply_text("❌ Неверный телефон или пароль. Попробуйте снова.")
                # Сбрасываем состояние для повторной попытки
                context.user_data['awaiting_password'] = False
                context.user_data['awaiting_phone'] = True
                await update.message.reply_text("Введите телефонный номер еще раз:")
                
        except Exception as e:
            logger.error(f"Ошибка при авторизации пользователя {user_id}: {e}")
            await update.message.reply_text("❌ Произошла ошибка при авторизации. Попробуйте позже.")
        finally:
            db.close()
    
    # Если пользователь в процессе записи на прием
    elif context.user_data.get('making_appointment'):
        await handle_appointment_flow(update, context)
    
    # Если пользователь авторизован
    elif context.user_data.get('authenticated'):
        await update.message.reply_text("Используйте меню для навигации.")
    
    # Если пользователь не авторизован и не в процессе авторизации
    else:
        keyboard = [
            [InlineKeyboardButton("🔐 АВТОРИЗОВАТЬСЯ", callback_data="auth")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Для доступа к функциям бота необходимо авторизоваться.",
            reply_markup=reply_markup
        )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать главное меню только после авторизации"""
    if not context.user_data.get('authenticated'):
        await handle_auth(update, context)
        return
    
    keyboard = [
        [InlineKeyboardButton("👶 МОИ ДЕТИ", callback_data="my_children")],
        [InlineKeyboardButton("📅 ЗАПИСЬ НА ПРИЕМ", callback_data="make_appointment")],
        [InlineKeyboardButton("📋 ИСТОРИЯ", callback_data="history")],
        [InlineKeyboardButton("⚙️ НАСТРОЙКИ", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text("Выберите действие:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    user_id = query.from_user.id
    
    logger.info(f"Пользователь {user_id} нажал кнопку: {action}")
    
    # Проверяем авторизацию для всех действий кроме auth
    if action != "auth" and not context.user_data.get('authenticated'):
        await query.edit_message_text("❌ Необходима авторизация. Нажмите /start")
        return
    
    if action == "auth":
        await handle_auth(update, context)
    
    elif action == "my_children":
        await show_my_children(query, context)
    
    elif action == "make_appointment":
        await start_appointment_flow(query, context)
    
    elif action == "history":
        await show_history(query, context)
    
    elif action == "settings":
        await show_settings(query, context)
    
    elif action == "back_to_menu":
        await show_main_menu(update, context)
    
    # Обработка выбора ребенка для записи
    elif action.startswith("select_child_"):
        await handle_child_selection(query, context)
    
    # Обработка выбора типа приема
    elif action.startswith("select_type_"):
        await handle_type_selection(query, context)
    
    # Обработка выбора даты
    elif action.startswith("select_date_"):
        await handle_date_selection(query, context)
    
    # Обработка выбора времени - ДОБАВЛЕНО!
    elif action.startswith("select_time_"):
        await complete_appointment(update, context)

async def show_my_children(query, context):
    """Показать список детей"""
    db = SessionLocal()
    try:
        parent_id = context.user_data.get('parent_id')
        
        # Получаем детей из базы данных
        children = db.query(Patient).all()  # TODO: Добавить связь с родителем
        
        if not children:
            keyboard = [
                [InlineKeyboardButton("➕ ДОБАВИТЬ РЕБЕНКА", callback_data="add_child")],
                [InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("У вас пока нет добавленных детей.", reply_markup=reply_markup)
        else:
            message = "👶 ВАШИ ДЕТИ:\n\n"
            for i, child in enumerate(children, 1):
                age = calculate_age(child.birth_date) if child.birth_date else "возраст не указан"
                message += f"{i}. {child.last_name} {child.first_name} ({age})\n"
            
            keyboard = [
                [InlineKeyboardButton("➕ ДОБАВИТЬ РЕБЕНКА", callback_data="add_child")],
                [InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка при получении списка детей: {e}")
        await query.edit_message_text("❌ Ошибка при загрузке данных")
    finally:
        db.close()

async def start_appointment_flow(query, context):
    """Начало процесса записи на прием"""
    db = SessionLocal()
    try:
        # Получаем список детей
        children = db.query(Patient).all()
        
        if not children:
            await query.edit_message_text("❌ Нет пациентов для записи. Сначала добавьте ребенка.")
            return
        
        # Создаем клавиатуру с детьми
        keyboard = []
        for child in children:
            age = calculate_age(child.birth_date) if child.birth_date else "возраст не указан"
            keyboard.append([InlineKeyboardButton(
                f"{child.last_name} {child.first_name} ({age})",
                callback_data=f"select_child_{child.id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Сохраняем состояние записи
        context.user_data['making_appointment'] = True
        context.user_data['appointment_step'] = 'select_child'
        context.user_data['appointment_data'] = {}
        
        await query.edit_message_text(
            "👶 Выберите ребенка для записи:",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Ошибка при начале записи: {e}")
        await query.edit_message_text("❌ Ошибка при загрузке списка пациентов")
    finally:
        db.close()

async def handle_child_selection(query, context):
    """Обработка выбора ребенка"""
    child_id = int(query.data.split('_')[2])
    
    db = SessionLocal()
    try:
        child = db.query(Patient).filter(Patient.id == child_id).first()
        if not child:
            await query.edit_message_text("❌ Ребенок не найден")
            return
        
        # Сохраняем данные ребенка
        context.user_data['appointment_data']['child_id'] = child_id
        context.user_data['appointment_data']['child_name'] = f"{child.last_name} {child.first_name}"
        context.user_data['appointment_step'] = 'select_type'
        
        # Создаем клавиатуру с типами приема
        keyboard = [
            [InlineKeyboardButton("🩺 Первичный прием", callback_data="select_type_primary")],
            [InlineKeyboardButton("🔄 Повторный прием", callback_data="select_type_repeat")],
            [InlineKeyboardButton("💉 Прививка", callback_data="select_type_vaccination")],
            [InlineKeyboardButton("💬 Консультация", callback_data="select_type_consultation")],
            [InlineKeyboardButton("🔙 НАЗАД", callback_data="make_appointment")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"👶 Ребенок: {child.last_name} {child.first_name}\n"
            "🎯 Выберите тип приема:",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Ошибка при выборе ребенка: {e}")
        await query.edit_message_text("❌ Ошибка при выборе ребенка")
    finally:
        db.close()

async def handle_type_selection(query, context):
    """Обработка выбора типа приема"""
    appointment_type = query.data.split('_')[2]
    
    # Сохраняем тип приема
    context.user_data['appointment_data']['type'] = appointment_type
    context.user_data['appointment_step'] = 'select_date'
    
    # Генерируем даты на ближайшие 7 дней
    today = date.today()
    keyboard = []
    
    for i in range(7):
        appointment_date = today + timedelta(days=i)
        date_str = appointment_date.strftime('%Y-%m-%d')
        display_date = appointment_date.strftime('%d.%m.%Y')
        
        if i == 0:
            display_text = f"📅 Сегодня ({display_date})"
        elif i == 1:
            display_text = f"📅 Завтра ({display_date})"
        else:
            day_name = get_weekday_name(appointment_date.weekday())
            display_text = f"📅 {day_name} ({display_date})"
        
        keyboard.append([InlineKeyboardButton(display_text, callback_data=f"select_date_{date_str}")])
    
    keyboard.append([InlineKeyboardButton("🔙 НАЗАД", callback_data=f"select_child_{context.user_data['appointment_data']['child_id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    type_names = {
        'primary': 'Первичный прием',
        'repeat': 'Повторный прием', 
        'vaccination': 'Прививка',
        'consultation': 'Консультация'
    }
    
    await query.edit_message_text(
        f"👶 Ребенок: {context.user_data['appointment_data']['child_name']}\n"
        f"🎯 Тип: {type_names.get(appointment_type, appointment_type)}\n"
        "📅 Выберите дату приема:",
        reply_markup=reply_markup
    )

async def handle_date_selection(query, context):
    """Обработка выбора даты"""
    selected_date = query.data.split('_')[2]
    
    # Сохраняем дату
    context.user_data['appointment_data']['date'] = selected_date
    context.user_data['appointment_step'] = 'select_time'
    
    # Предлагаем стандартные временные слоты
    time_slots = [
        "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
        "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00"
    ]
    
    keyboard = []
    row = []
    for i, time_slot in enumerate(time_slots):
        row.append(InlineKeyboardButton(time_slot, callback_data=f"select_time_{time_slot}"))
        if (i + 1) % 3 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Добавляем кнопку для ручного ввода времени
    keyboard.append([InlineKeyboardButton("✏️ Ввести время вручную", callback_data="manual_time_input")])
    keyboard.append([InlineKeyboardButton("🔙 НАЗАД", callback_data=f"select_type_{context.user_data['appointment_data']['type']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    display_date = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%d.%m.%Y')
    
    type_names = {
        'primary': 'Первичный прием',
        'repeat': 'Повторный прием',
        'vaccination': 'Прививка',
        'consultation': 'Консультация'
    }
    
    await query.edit_message_text(
        f"👶 Ребенок: {context.user_data['appointment_data']['child_name']}\n"
        f"🎯 Тип: {type_names.get(context.user_data['appointment_data']['type'])}\n"
        f"📅 Дата: {display_date}\n"
        "⏰ Выберите время приема:",
        reply_markup=reply_markup
    )

async def handle_appointment_flow(update, context):
    """Обработка потока записи на прием"""
    user_message = update.message.text
    
    if context.user_data.get('appointment_step') == 'select_time':
        # Пользователь ввел время вручную
        try:
            # Проверяем формат времени
            datetime.strptime(user_message, '%H:%M')
            await complete_appointment(update, context, user_message)
        except ValueError:
            await update.message.reply_text("❌ Неверный формат времени. Введите время в формате ЧЧ:ММ (например, 14:30)")

async def complete_appointment(update, context, selected_time=None):
    """Завершение создания записи"""
    if hasattr(update, 'callback_query'):
        # Если это callback от кнопки выбора времени
        if selected_time is None:
            if update.callback_query.data.startswith("select_time_"):
                selected_time = update.callback_query.data.split('_')[2]
            elif update.callback_query.data == "manual_time_input":
                # Запрашиваем ручной ввод времени
                await update.callback_query.edit_message_text(
                    "⏰ Введите время приема в формате ЧЧ:ММ (например, 14:30):"
                )
                return
        
        chat_id = update.callback_query.message.chat_id
        message_id = update.callback_query.message.message_id
    else:
        # Если время введено вручную
        chat_id = update.message.chat_id
        message_id = None
    
    if not selected_time:
        await context.bot.send_message(chat_id=chat_id, text="❌ Время не выбрано")
        return
    
    appointment_data = context.user_data['appointment_data']
    
    try:
        # Создаем запись через API
        async with aiohttp.ClientSession() as session:
            form_data = aiohttp.FormData()
            form_data.add_field('patient_id', str(appointment_data['child_id']))
            form_data.add_field('date', appointment_data['date'])
            form_data.add_field('time', selected_time)
            form_data.add_field('type', appointment_data['type'])
            form_data.add_field('notes', 'Запись создана через бота')
            
            async with session.post(f'{API_URL}/api/appointments', data=form_data) as response:
                result = await response.json()
                
                if response.status == 200:
                    # Очищаем состояние записи
                    context.user_data.pop('making_appointment', None)
                    context.user_data.pop('appointment_step', None)
                    context.user_data.pop('appointment_data', None)
                    
                    display_date = datetime.strptime(appointment_data['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
                    
                    type_names = {
                        'primary': 'Первичный прием',
                        'repeat': 'Повторный прием',
                        'vaccination': 'Прививка',
                        'consultation': 'Консультация'
                    }
                    
                    success_message = (
                        "✅ Запись успешно создана!\n\n"
                        f"👶 Ребенок: {appointment_data['child_name']}\n"
                        f"🎯 Тип: {type_names.get(appointment_data['type'])}\n"
                        f"📅 Дата: {display_date}\n"
                        f"⏰ Время: {selected_time}\n\n"
                        "За день до приема вам придет напоминание."
                    )
                    
                    if hasattr(update, 'callback_query'):
                        await update.callback_query.edit_message_text(success_message)
                    else:
                        await context.bot.send_message(chat_id=chat_id, text=success_message)
                        
                    await show_main_menu(update, context)
                else:
                    error_msg = result.get('detail', 'Неизвестная ошибка')
                    error_message = f"❌ Ошибка при создании записи: {error_msg}"
                    
                    if hasattr(update, 'callback_query'):
                        await update.callback_query.edit_message_text(error_message)
                    else:
                        await context.bot.send_message(chat_id=chat_id, text=error_message)
                        
    except Exception as e:
        logger.error(f"Ошибка при создании записи: {e}")
        error_message = "❌ Ошибка при создании записи. Попробуйте позже."
        
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(error_message)
        else:
            await context.bot.send_message(chat_id=chat_id, text=error_message)

async def show_history(query, context):
    """Показать историю посещений"""
    keyboard = [
        [InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("📋 Функция истории посещений будет доступна в ближайшее время.", reply_markup=reply_markup)

async def show_settings(query, context):
    """Показать настройки"""
    keyboard = [
        [InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("⚙️ Функция настроек будет доступна в ближайшее время.", reply_markup=reply_markup)

def calculate_age(birth_date):
    """Расчет возраста"""
    from datetime import date
    if not birth_date:
        return "возраст не указан"
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return f"{age} лет"

def get_weekday_name(weekday):
    """Получить название дня недели"""
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    return days[weekday]

async def send_visit_results_to_parents(medical_record_id: int, db: Session):
    """Отправка результатов визита родителям через бота"""
    # TODO: Реализовать отправку результатов
    logger.info(f"Отправка результатов визита {medical_record_id} родителям")
    return True

def run_bot():
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен")
        return

    logger.info("🚀 Запуск Telegram бота...")
    logger.info(f"📁 Рабочая директория: {os.getcwd()}")
    logger.info(f"🔑 Токен: {BOT_TOKEN[:10]}...")
    logger.info(f"🌐 API URL: {API_URL}")

    try:
        application = Application.builder().token(BOT_TOKEN).build()

        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Запускаем бота
        logger.info("✅ Бот запущен и готов к работе!")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    run_bot()