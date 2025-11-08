#!/bin/bash
echo "🛑 Остановка Pediatric CRM..."
pkill -f uvicorn
pkill -f run_bot.py
echo "✅ Все процессы остановлены"
ps aux | grep uvicorn | wc -l
