import sys
import os
from datetime import datetime

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import Base, MedicalTemplate

def create_medical_templates():
    db = SessionLocal()
    try:
        # Создаем таблицы
        Base.metadata.create_all(bind=engine)
        print("✅ Таблицы созданы успешно")

        # Проверяем, есть ли уже шаблоны
        existing_templates = db.query(MedicalTemplate).count()
        if existing_templates > 0:
            print("✅ Медицинские шаблоны уже существуют")
            return

        # Данные для шаблонов
        templates_data = [
            {
                "name": "ОРВИ",
                "diagnosis": {"code": "J06.9", "name": "Острая инфекция верхних дыхательных путей неуточненная"},
                "prescriptions": [
                    "Парацетамол по весу при t > 38.5",
                    "Солевой раствор в нос",
                    "Обильное питье", 
                    "Постельный режим"
                ]
            },
            {
                "name": "Плановый осмотр", 
                "diagnosis": {"code": "Z00.1", "name": "Плановый осмотр ребенка"},
                "prescriptions": [
                    "Рекомендации по режиму дня",
                    "Сбалансированное питание",
                    "Физическая активность"
                ]
            },
            {
                "name": "Острый бронхит",
                "diagnosis": {"code": "J20.9", "name": "Острый бронхит неуточненный"},
                "prescriptions": [
                    "Амброксол по возрасту 3 раза в день",
                    "Ингаляции с физраствором",
                    "Обильное питье",
                    "Постельный режим"
                ]
            },
            {
                "name": "Острый гастрит",
                "diagnosis": {"code": "K29.1", "name": "Другой острый гастрит"},
                "prescriptions": [
                    "Диета стол №1",
                    "Смекта по возрасту", 
                    "Дробное питание"
                ]
            }
        ]

        # Создаем шаблоны
        for template_info in templates_data:
            template = MedicalTemplate(
                name=template_info["name"],
                diagnosis=template_info["diagnosis"],
                prescriptions=template_info["prescriptions"],
                created_at=datetime.now()
            )
            db.add(template)

        db.commit()
        print("✅ Медицинские шаблоны успешно созданы!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при создании медицинских шаблонов: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_medical_templates()
    print("🎉 Миграция завершена успешно!")