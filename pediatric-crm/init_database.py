#!/usr/bin/env python3
from app.database import engine, create_tables
from app.models import Base
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Полная инициализация базы данных с тестовыми данными"""
    
    # Создаем все таблицы
    create_tables()
    logger.info("✅ Все таблицы созданы")
    
    # Добавляем тестовые данные
    try:
        with engine.connect() as connection:
            # Тестовые теги пациентов
            connection.execute(text("""
                INSERT INTO patient_tags (name, color) VALUES 
                ('Часто болеющий', '#ef4444'),
                ('Аллергик', '#f59e0b'),
                ('Спортсмен', '#10b981'),
                ('Грудничок', '#8b5cf6'),
                ('Астматик', '#6366f1'),
                ('Диабет', '#ec4899'),
                ('Недоношенный', '#06b6d4')
            """))
            
            # Медицинские шаблоны
            connection.execute(text("""
                INSERT INTO medical_templates (name, diagnosis, complaints_template, examination_template, treatment_template, prescriptions_template, recommendations_template) VALUES 
                ('ОРВИ', 'J06.9 Острая инфекция верхних дыхательных путей неуточненная', 'Температура, кашель, насморк', 'Температура: {temperature}°C\nСостояние: {condition}\nДыхание: {breathing}', 'Парацетамол по весу при t > 38.5\nСолевой раствор в нос\nОбильное питье\nПостельный режим', 'Парацетамол 100мг при t > 38.5\nАквалор в нос 3 раза в день\nОбильное питье', 'Контроль через 3 дня'),
                ('Плановый осмотр', 'Z00.1 Обследование и осмотр ребенка', 'Жалоб нет', 'Состояние: удовлетворительное\nКожные покровы: чистые\nДыхание: везикулярное\nСердце: тоны ясные', 'Рекомендации по режиму дня', 'Витамины по возрасту', 'Повторный осмотр через 6 месяцев')
            """))
            
            # Тестовый родитель
            connection.execute(text("""
                INSERT INTO parents (phone, password, first_name, last_name) VALUES 
                ('+79111234567', '123456', 'Мария', 'Иванова')
            """))
            
            # Тестовый пациент
            connection.execute(text("""
                INSERT INTO patients (first_name, last_name, birth_date, phone, parent_name, address, status, gender, birth_weight, birth_height) VALUES 
                ('Алексей', 'Иванов', '2018-03-15', '+79111234567', 'Иванова Мария Петровна', 'ул. Примерная, д. 1, кв. 2', 'confirmed', 'М', 3500, 52)
            """))
            
            # Связь родитель-ребенок
            connection.execute(text("""
                INSERT INTO parent_children (parent_id, patient_id, relationship) 
                VALUES (1, 1, 'мама')
            """))
            
            # Тестовая запись на прием
            connection.execute(text("""
                INSERT INTO appointments (patient_id, parent_id, appointment_date, appointment_time, type, status) VALUES 
                (1, 1, CURRENT_DATE + INTERVAL '1 day', '10:30', 'consultation', 'confirmed')
            """))
            
            connection.commit()
            logger.info("✅ Тестовые данные добавлены")
            
    except Exception as e:
        logger.error(f"❌ Ошибка добавления тестовых данных: {e}")

if __name__ == "__main__":
    print("🚀 Полная инициализация базы данных...")
    init_database()
    print("🎉 База данных полностью пересоздана и заполнена тестовыми данными!")