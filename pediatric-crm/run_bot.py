#!/usr/bin/env python3
import os
import sys
import logging
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

load_dotenv()

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    api_url = os.getenv("API_URL", "http://localhost:8000")
    
    if not token:
        print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не найден в .env файле")
        print("TELEGRAM_BOT_TOKEN=ваш_токен_здесь")
        return
    
    print("🚀 Запуск Telegram бота...")
    print(f"📁 Рабочая директория: {current_dir}")
    print(f"🔑 Токен: {token[:10]}...")
    print(f"🌐 API URL: {api_url}")
    
    try:
        from app.telegram_bot import run_bot
        run_bot()
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("Установите зависимости: pip install python-telegram-bot python-dotenv sqlalchemy psycopg2-binary aiohttp")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")

if __name__ == "__main__":
    main()