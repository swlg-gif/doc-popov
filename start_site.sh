#!/bin/bash
echo "🚀 Запуск Pediatric CRM..."
pkill -f uvicorn
cd ~/pediatric-crm
source venv/bin/activate

# Удаляем конфликтующие директории если есть
[ -d "app/models" ] && rm -rf app/models/

nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > fastapi.log 2>&1 &
echo "✅ Сайт запущен на порту 8000"
ps aux | grep uvicorn | head -5
