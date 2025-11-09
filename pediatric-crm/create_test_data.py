import sys
import os
from datetime import datetime, date

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Patient, Parent, Appointment

def create_test_data():
    db = SessionLocal()
    try:
        # Создаем тестового пациента
        patient = Patient(
            first_name="Алексей",
            last_name="Иванов",
            birth_date=date(2018, 3, 15),
            gender="М",
            phone="+7-911-123-45-67",
            parent_name="Иванова Мария Петровна",
            parent_phone="+7-911-999-88-77",
            address="ул. Примерная, д. 1, кв. 2",
            email="parent@email.com",
            birth_weight=3500,
            birth_height=52,
            status="confirmed",
            created_at=datetime.now()
        )
        db.add(patient)
        db.flush()

        # Создаем тестового родителя
        parent = Parent(
            phone="+79111234567",
            password="123456",
            first_name="Мария",
            last_name="Иванова",
            created_at=datetime.now()
        )
        db.add(parent)

        # Создаем тестовую запись
        appointment = Appointment(
            patient_id=patient.id,
            date=date(2023, 10, 26),
            time=datetime.now().time(),
            type="primary",
            status="completed",
            created_at=datetime.now()
        )
        db.add(appointment)

        db.commit()
        print("✅ Тестовые данные созданы успешно!")
        print(f"👶 Пациент: {patient.last_name} {patient.first_name}")
        print(f"👨‍👩‍👧‍👦 Родитель: {parent.first_name} {parent.last_name}")
        print(f"📅 Запись: {appointment.date} {appointment.time}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при создании тестовых данных: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_data()