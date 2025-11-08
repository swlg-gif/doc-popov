#!/bin/bash
echo "🛑 Останавливаем все процессы бота..."
pkill -f "python.*run_bot.py" 2>/dev/null || true
pkill -f "python.*telegram_bot" 2>/dev/null || true
pkill -f "telegram" 2>/dev/null || true
sleep 2
echo "✅ Все процессы остановлены"
