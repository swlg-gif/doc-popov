#!/bin/bash
cd /home/deploy/pediatric-crm
source venv/bin/activate

# Проверяем импорты перед запуском
echo "Проверка импортов..."
python -c "
try:
    from app.main import app
    print('✅ Приложение импортировано успешно')
except Exception as e:
    print(f'❌ Ошибка импорта: {e}')
    exit(1)
"

# Запускаем приложение
echo "Запуск приложения..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
