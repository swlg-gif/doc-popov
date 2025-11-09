#!/usr/bin/env python3
import os
import sys
from sqlalchemy import text
from app.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def advanced_migration():
    """Добавляем расширенные таблицы для полного функционала"""
    
    migration_commands = [
        # Медицинские записи с дополнительными полями
        """
        ALTER TABLE medical_records 
        ADD COLUMN IF NOT EXISTS temperature FLOAT,
        ADD COLUMN IF NOT EXISTS weight FLOAT,
        ADD COLUMN IF NOT EXISTS height FLOAT,
        ADD COLUMN IF NOT EXISTS condition VARCHAR(100),
        ADD COLUMN IF NOT EXISTS skin VARCHAR(100),
        ADD COLUMN IF NOT EXISTS breathing VARCHAR(100),
        ADD COLUMN IF NOT EXISTS heart VARCHAR(100),
        ADD COLUMN IF NOT EXISTS abdomen VARCHAR(100)
        """,
        
        # Таблица медицинских шаблонов
        """
        CREATE TABLE IF NOT EXISTS medical_templates (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            diagnosis TEXT,
            complaints_template TEXT,
            examination_template TEXT,
            treatment_template TEXT,
            prescriptions_template TEXT,
            recommendations_template TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Таблица тегов пациентов
        """
        CREATE TABLE IF NOT EXISTS patient_tags (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            color VARCHAR(20) DEFAULT '#3b82f6'
        )
        """,
        
        # Связь пациентов с тегами
        """
        CREATE TABLE IF NOT EXISTS patient_tag_assignments (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER REFERENCES patients(id),
            tag_id INTEGER REFERENCES patient_tags(id)
        )
        """,
        
        # Заметки врача
        """
        CREATE TABLE IF NOT EXISTS doctor_notes (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER REFERENCES patients(id),
            note_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            content TEXT NOT NULL,
            created_by VARCHAR(100)
        )
        """,
        
        # Напоминания
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER REFERENCES patients(id),
            reminder_date TIMESTAMP NOT NULL,
            content TEXT NOT NULL,
            completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]
    
    try:
        with engine.connect() as connection:
            for i, command in enumerate(migration_commands, 1):
                logger.info(f"Выполняем команду {i}/{len(migration_commands)}")
                if command.strip():
                    connection.execute(text(command))
                    connection.commit()
            
        logger.info("✅ Расширенная миграция базы данных успешно завершена!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def add_sample_data():
    """Добавляем тестовые данные"""
    try:
        with engine.connect() as connection:
            # Тестовые теги
            connection.execute(text("""
                INSERT INTO patient_tags (name, color) VALUES 
                ('Часто болеющий', '#ef4444'),
                ('Аллергик', '#f59e0b'),
                ('Спортсмен', '#10b981'),
                ('Грудничок', '#8b5cf6'),
                ('Астматик', '#6366f1'),
                ('Диабет', '#ec4899'),
                ('Недоношенный', '#06b6d4')
                ON CONFLICT DO NOTHING
            """))
            
            # Тестовые медицинские шаблоны
            connection.execute(text("""
                INSERT INTO medical_templates (name, diagnosis, complaints_template, examination_template, treatment_template, prescriptions_template, recommendations_template) VALUES 
                ('ОРВИ', 'J06.9 Острая инфекция верхних дыхательных путей неуточненная', 'Температура, кашель, насморк', 'Температура: {temperature}°C\nСостояние: {condition}\nДыхание: {breathing}', 'Парацетамол по весу при t > 38.5\nСолевой раствор в нос\nОбильное питье\nПостельный режим', 'Парацетамол 100мг при t > 38.5\nАквалор в нос 3 раза в день\nОбильное питье', 'Контроль через 3 дня'),
                ('Плановый осмотр', 'Z00.1 Обследование и осмотр ребенка', 'Жалоб нет', 'Состояние: удовлетворительное\nКожные покровы: чистые\nДыхание: везикулярное\nСердце: тоны ясные', 'Рекомендации по режиму дня', 'Витамины по возрасту', 'Повторный осмотр через 6 месяцев')
                ON CONFLICT DO NOTHING
            """))
            
            connection.commit()
            logger.info("✅ Тестовые данные добавлены")
            
    except Exception as e:
        logger.error(f"❌ Ошибка добавления тестовых данных: {e}")

if __name__ == "__main__":
    print("🚀 Запуск расширенной миграции базы данных...")
    advanced_migration()
    add_sample_data()
    print("🎉 Миграция завершена! База готова для полного функционала.")