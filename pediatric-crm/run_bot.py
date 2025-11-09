#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Загружаем переменные окружения
load_dotenv()

from app.telegram_bot import run_bot

if __name__ == "__main__":
    print("🚀 Запуск Telegram бота...")
    print(f"📁 Рабочая директория: {os.getcwd()}")
    print(f"🔑 Токен: {os.getenv('BOT_TOKEN', 'NOT_SET')[:10]}...")
    print(f"🌐 API URL: {os.getenv('API_URL', 'https://doc-popov.ru')}")
    
    try:
        run_bot()
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        print("Установите зависимости: pip install python-telegram-bot python-dotenv sqlalchemy aiohttp")