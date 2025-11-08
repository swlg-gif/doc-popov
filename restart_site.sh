#!/bin/bash
echo "🔄 Перезапуск Pediatric CRM..."
pkill -f uvicorn
sleep 2
cd ~/pediatric-crm
source venv/bin/activate
[ -d "app/models" ] && rm -rf app/models/
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > fastapi.log 2>&1 &
echo "✅ Сайт перезапущен"
sleep 2
ps aux | grep uvicorn | head -5
