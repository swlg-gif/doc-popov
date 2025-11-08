import sys
import os
from datetime import datetime

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Parent

def create_test_parents():
    db = SessionLocal()
    try:
        # Удаляем старых тестовых родителей
        db.query(Parent).delete()
        
        # Создаем тестовых родителей
        parents = [
            Parent(
                phone="+79111234567",
                password="123456",
                first_name="Мария",
                last_name="Иванова",
                created_at=datetime.now()
            ),
            Parent(
                phone="+79119876543", 
                password="654321",
                first_name="Петр",
                last_name="Сидоров",
                created_at=datetime.now()
            )
        ]
        
        for parent in parents:
            db.add(parent)
        
        db.commit()
        print("✅ Тестовые родители созданы успешно!")
        print("📞 Телефоны и пароли для авторизации в боте:")
        for parent in parents:
            print(f"   📱 {parent.phone} | 🔑 {parent.password} | 👤 {parent.first_name} {parent.last_name}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при создании тестовых родителей: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_parents()