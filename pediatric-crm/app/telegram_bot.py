import os
import logging
import sys
import asyncio
import aiohttp
import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Patient
import json

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
AUTH_PHONE, AUTH_PASSWORD, MAIN_MENU, ADD_CHILD_NAME, ADD_CHILD_GENDER, ADD_CHILD_BIRTHDATE, ADD_CHILD_WEIGHT, ADD_CHILD_HEIGHT, ADD_CHILD_ADDRESS = range(9)
APPOINTMENT_CHILD, APPOINTMENT_TYPE, APPOINTMENT_DATE, APPOINTMENT_TIME = range(13, 17)

class TelegramBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле")
        
        self.api_url = os.getenv("API_URL", "http://localhost:8000")
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
        
    def setup_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                AUTH_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth_phone)],
                AUTH_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth_password)],
                MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.main_menu)],
                ADD_CHILD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_child_name)],
                ADD_CHILD_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_child_gender)],
                ADD_CHILD_BIRTHDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_child_birthdate)],
                ADD_CHILD_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_child_weight)],
                ADD_CHILD_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_child_height)],
                ADD_CHILD_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_child_address)],
                APPOINTMENT_CHILD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.appointment_child)],
                APPOINTMENT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.appointment_type)],
                APPOINTMENT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.appointment_date)],
                APPOINTMENT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.appointment_time)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
            allow_reentry=True
        )
        
        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler("start", self.start))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "👋 Добро пожаловать в Кабинет доктора Попова!\n\n"
            "Для доступа к данным ребенка необходимо авторизоваться.\n\n"
            "Введите телефонный номер, который указан у врача:"
        )
        return AUTH_PHONE

    async def auth_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        phone = update.message.text
        context.user_data['phone'] = phone
        
        await update.message.reply_text(
            f"Телефон: {phone}\n"
            "Введите пароль, который вам сообщил врач:"
        )
        return AUTH_PASSWORD

    async def auth_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        password = update.message.text
        phone = context.user_data.get('phone')
        
        # Аутентификация через API
        auth_result = await self.verify_credentials_api(phone, password)
        
        if auth_result["status"] == "success":
            context.user_data['authenticated'] = True
            context.user_data['parent'] = auth_result["parent"]
            context.user_data['children'] = auth_result["children"]
            
            await update.message.reply_text(
                f"✅ Успешная авторизация! Добро пожаловать, {auth_result['parent']['name']}!\n\n"
                "Выберите действие:",
                reply_markup=self.get_main_menu_keyboard()
            )
            return MAIN_MENU
        else:
            await update.message.reply_text(
                "❌ Неверный телефон или пароль. Попробуйте снова.\n\n"
                "Введите телефонный номер:"
            )
            return AUTH_PHONE

    async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.user_data.get('authenticated'):
            await update.message.reply_text("❌ Пожалуйста, авторизуйтесь с помощью /start")
            return AUTH_PHONE
        
        text = update.message.text
        
        if text == "👶 МОИ ДЕТИ":
            await self.show_my_children(update, context)
            return MAIN_MENU
        elif text == "📅 ЗАПИСЬ НА ПРИЕМ":
            return await self.start_appointment(update, context)
        elif text == "📋 ИСТОРИЯ":
            await self.show_history(update, context)
            return MAIN_MENU
        elif text == "⚙️ НАСТРОЙКИ":
            await self.show_settings(update, context)
            return MAIN_MENU
        elif text == "➕ ДОБАВИТЬ РЕБЕНКА":
            await update.message.reply_text(
                "👶 ДОБАВЛЕНИЕ НОВОГО РЕБЕНКА\n\n"
                "Введите ФИО ребенка:",
                reply_markup=ReplyKeyboardRemove()
            )
            return ADD_CHILD_NAME
        else:
            await update.message.reply_text(
                "Выберите действие из меню:",
                reply_markup=self.get_main_menu_keyboard()
            )
            return MAIN_MENU

    async def start_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        children = context.user_data.get('children', [])
        
        if not children:
            await update.message.reply_text(
                "❌ У вас нет привязанных детей. Сначала добавьте ребенка.",
                reply_markup=self.get_main_menu_keyboard()
            )
            return MAIN_MENU
        
        # Создаем клавиатуру с детьми
        keyboard = []
        for child in children:
            keyboard.append([KeyboardButton(child["name"])])
        keyboard.append([KeyboardButton("🔙 НАЗАД")])
        
        await update.message.reply_text(
            "Выберите ребенка для записи:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return APPOINTMENT_CHILD

    async def appointment_child(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        child_name = update.message.text
        
        if child_name == "🔙 НАЗАД":
            await update.message.reply_text(
                "Выберите действие:",
                reply_markup=self.get_main_menu_keyboard()
            )
            return MAIN_MENU
        
        # Находим ребенка
        children = context.user_data.get('children', [])
        selected_child = next((child for child in children if child["name"] == child_name), None)
        
        if not selected_child:
            await update.message.reply_text("❌ Ребенок не найден. Попробуйте снова.")
            return APPOINTMENT_CHILD
        
        context.user_data['selected_child'] = selected_child
        
        # Типы приемов
        keyboard = [
            [KeyboardButton("🩺 Первичный"), KeyboardButton("🔄 Повторный")],
            [KeyboardButton("💉 Прививка"), KeyboardButton("💬 Консультация")],
            [KeyboardButton("🔙 НАЗАД")]
        ]
        
        await update.message.reply_text(
            "Выберите тип приема:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return APPOINTMENT_TYPE

    async def appointment_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        appointment_type = update.message.text
        
        if appointment_type == "🔙 НАЗАД":
            return await self.start_appointment(update, context)
        
        # Маппинг типов
        type_mapping = {
            "🩺 Первичный": "primary",
            "🔄 Повторный": "repeat", 
            "💉 Прививка": "vaccination",
            "💬 Консультация": "consultation"
        }
        
        context.user_data['appointment_type'] = type_mapping.get(appointment_type, "consultation")
        
        # Показываем доступные даты (ближайшие 7 дней)
        dates = []
        today = datetime.datetime.now()
        for i in range(1, 8):
            date = today + datetime.timedelta(days=i)
            if date.weekday() < 5:  # Только рабочие дни
                dates.append(date.strftime("%d.%m.%Y"))
        
        keyboard = [[KeyboardButton(date)] for date in dates]
        keyboard.append([KeyboardButton("🔙 НАЗАД")])
        
        await update.message.reply_text(
            "Выберите дату:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return APPOINTMENT_DATE

    async def appointment_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        date_str = update.message.text
        
        if date_str == "🔙 НАЗАД":
            return await self.start_appointment(update, context)
        
        try:
            # Преобразуем дату
            date_obj = datetime.datetime.strptime(date_str, "%d.%m.%Y").date()
            context.user_data['appointment_date'] = date_obj
            
            # Получаем свободные слоты через API
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/api/bot/free-slots?date={date_obj.strftime('%Y-%m-%d')}"
                ) as response:
                    slots_data = await response.json()
            
            if slots_data.get("slots"):
                keyboard = [[KeyboardButton(slot)] for slot in slots_data["slots"]]
                keyboard.append([KeyboardButton("🔙 НАЗАД")])
                
                await update.message.reply_text(
                    f"Свободное время на {date_str}:",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return APPOINTMENT_TIME
            else:
                await update.message.reply_text(
                    "❌ На выбранную дату нет свободных слотов. Выберите другую дату."
                )
                return APPOINTMENT_DATE
                
        except ValueError:
            await update.message.reply_text("❌ Неверный формат даты. Попробуйте снова.")
            return APPOINTMENT_DATE

    async def appointment_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        time_str = update.message.text
        
        if time_str == "🔙 НАЗАД":
            return await self.appointment_type(update, context)
        
        context.user_data['appointment_time'] = time_str
        
        # Создаем запись через API
        appointment_data = {
            "patient_id": context.user_data['selected_child']['id'],
            "parent_id": context.user_data['parent']['id'],
            "date": context.user_data['appointment_date'].strftime("%Y-%m-%d"),
            "time": time_str,
            "type": context.user_data['appointment_type']
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/api/bot/create-appointment",
                json=appointment_data
            ) as response:
                result = await response.json()
        
        if result.get("status") == "success":
            child_name = context.user_data['selected_child']['name']
            date_str = context.user_data['appointment_date'].strftime("%d.%m.%Y")
            
            await update.message.reply_text(
                f"✅ Запись подтверждена!\n\n"
                f"👶 Пациент: {child_name}\n"
                f"📅 Дата: {date_str}, {time_str}\n"
                f"🎯 Тип: {context.user_data['appointment_type']}\n\n"
                f"За день до приема вам придет напоминание.",
                reply_markup=self.get_main_menu_keyboard()
            )
            
            # Очищаем временные данные
            context.user_data.pop('selected_child', None)
            context.user_data.pop('appointment_type', None)
            context.user_data.pop('appointment_date', None)
            context.user_data.pop('appointment_time', None)
            
            return MAIN_MENU
        else:
            await update.message.reply_text(
                "❌ Ошибка при создании записи. Попробуйте позже.",
                reply_markup=self.get_main_menu_keyboard()
            )
            return MAIN_MENU

    async def add_child_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['child_name'] = update.message.text
        
        keyboard = [
            [KeyboardButton("👦 Мальчик"), KeyboardButton("👧 Девочка")],
            [KeyboardButton("🔙 НАЗАД")]
        ]
        
        await update.message.reply_text(
            "Выберите пол ребенка:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return ADD_CHILD_GENDER

    async def add_child_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        gender_text = update.message.text
        
        if gender_text == "🔙 НАЗАД":
            await update.message.reply_text(
                "Введите ФИО ребенка:",
                reply_markup=ReplyKeyboardRemove()
            )
            return ADD_CHILD_NAME
        
        gender = "М" if "Мальчик" in gender_text else "Ж"
        context.user_data['child_gender'] = gender
        
        await update.message.reply_text(
            "Введите дату рождения ребенка (ДД.ММ.ГГГГ):",
            reply_markup=ReplyKeyboardRemove()
        )
        return ADD_CHILD_BIRTHDATE

    async def add_child_birthdate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        birthdate_str = update.message.text
        
        try:
            birthdate = datetime.datetime.strptime(birthdate_str, "%d.%m.%Y").date()
            context.user_data['child_birthdate'] = birthdate
            
            await update.message.reply_text(
                "Введите вес при рождении (граммы):"
            )
            return ADD_CHILD_WEIGHT
        except ValueError:
            await update.message.reply_text("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ:")
            return ADD_CHILD_BIRTHDATE

    async def add_child_weight(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            weight = int(update.message.text)
            context.user_data['child_weight'] = weight
            
            await update.message.reply_text(
                "Введите рост при рождении (см):"
            )
            return ADD_CHILD_HEIGHT
        except ValueError:
            await update.message.reply_text("❌ Введите число (граммы):")
            return ADD_CHILD_WEIGHT

    async def add_child_height(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            height = int(update.message.text)
            context.user_data['child_height'] = height
            
            await update.message.reply_text(
                "Введите адрес:"
            )
            return ADD_CHILD_ADDRESS
        except ValueError:
            await update.message.reply_text("❌ Введите число (см):")
            return ADD_CHILD_HEIGHT

    async def add_child_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        address = update.message.text
        context.user_data['child_address'] = address
        
        # Отправляем данные на сервер
        child_data = {
            "first_name": context.user_data['child_name'].split()[0],
            "last_name": " ".join(context.user_data['child_name'].split()[1:]) if len(context.user_data['child_name'].split()) > 1 else "",
            "birth_date": context.user_data['child_birthdate'].strftime("%Y-%m-%d"),
            "phone": context.user_data['parent']['phone'],
            "parent_name": context.user_data['parent']['name'],
            "address": address,
            "gender": context.user_data['child_gender'],
            "birth_weight": context.user_data['child_weight'],
            "birth_height": context.user_data['child_height'],
            "parent_phone": context.user_data['parent']['phone']
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/api/bot/create-patient",
                json=child_data
            ) as response:
                result = await response.json()
        
        if result.get("status") == "success":
            await update.message.reply_text(
                "✅ Данные ребенка отправлены врачу на проверку. "
                "После подтверждения врачом ребенок будет добавлен в вашу карточку.",
                reply_markup=self.get_main_menu_keyboard()
            )
            
            # Очищаем временные данные
            for key in ['child_name', 'child_gender', 'child_birthdate', 'child_weight', 'child_height', 'child_address']:
                context.user_data.pop(key, None)
            
            return MAIN_MENU
        else:
            await update.message.reply_text(
                "❌ Ошибка при отправке данных. Попробуйте позже.",
                reply_markup=self.get_main_menu_keyboard()
            )
            return MAIN_MENU

    async def show_my_children(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        children = context.user_data.get('children', [])
        
        if children:
            message = "👶 Ваши дети:\n\n"
            for child in children:
                age = self.calculate_age(datetime.datetime.strptime(child['birth_date'], '%Y-%m-%d').date()) if child.get('birth_date') else "возраст не указан"
                status = "🟢 Активен" if child['status'] == 'confirmed' else "🟡 Ожидает подтверждения"
                message += f"▸ {child['name']} ({age})\n{status}\n\n"
            
            # Добавляем кнопку добавления ребенка
            keyboard = [
                [KeyboardButton("➕ ДОБАВИТЬ РЕБЕНКА")],
                [KeyboardButton("📅 ЗАПИСЬ НА ПРИЕМ"), KeyboardButton("📋 ИСТОРИЯ")],
                [KeyboardButton("⚙️ НАСТРОЙКИ")]
            ]
            
            await update.message.reply_text(
                message,
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        else:
            await update.message.reply_text(
                "❌ У вас нет привязанных детей.",
                reply_markup=self.get_main_menu_keyboard()
            )

    async def show_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📋 История посещений будет доступна после первого приема.",
            reply_markup=self.get_main_menu_keyboard()
        )

    async def show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "⚙️ Настройки:\n\n"
            "• Сменить пароль\n"
            "• Уведомления\n"
            "• Обратная связь\n\n"
            "Функционал в разработке",
            reply_markup=self.get_main_menu_keyboard()
        )

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Действие отменено.",
            reply_markup=self.get_main_menu_keyboard()
        )
        return MAIN_MENU

    def get_main_menu_keyboard(self):
        keyboard = [
            [KeyboardButton("👶 МОИ ДЕТИ"), KeyboardButton("📅 ЗАПИСЬ НА ПРИЕМ")],
            [KeyboardButton("📋 ИСТОРИЯ"), KeyboardButton("⚙️ НАСТРОЙКИ")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    async def verify_credentials_api(self, phone: str, password: str) -> dict:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/api/bot/auth",
                    json={"phone": phone, "password": password}
                ) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"Error verifying credentials: {e}")
            return {"status": "error", "message": "Ошибка соединения"}

    def calculate_age(self, birth_date: datetime.date) -> str:
        today = datetime.date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        
        if age == 0:
            # Возраст в месяцах для детей до 1 года
            months = (today.year - birth_date.year) * 12 + today.month - birth_date.month
            if today.day < birth_date.day:
                months -= 1
            return f"{months} мес."
        elif age == 1:
            return "1 год"
        elif 2 <= age <= 4:
            return f"{age} года"
        else:
            return f"{age} лет"

def run_bot():
    try:
        bot = TelegramBot()
        print("🤖 Бот успешно инициализирован!")
        print("📞 Бот готов к работе")
        print("⏹️  Для остановки нажмите Ctrl+C")
        
        bot.application.run_polling()
        
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        print(f"❌ Ошибка запуска бота: {e}")

if __name__ == "__main__":
    run_bot()