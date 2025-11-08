import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
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
        await make_appointment(query, context)
    
    elif action == "history":
        await show_history(query, context)
    
    elif action == "settings":
        await show_settings(query, context)
    
    elif action == "back_to_menu":
        await show_main_menu(update, context)

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

async def make_appointment(query, context):
    """Запись на прием"""
    keyboard = [
        [InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("📅 Функция записи на прием будет доступна в ближайшее время.", reply_markup=reply_markup)

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