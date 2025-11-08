from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import app.models as models
from app.database import get_db, create_tables
from datetime import datetime, date, timedelta
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Pediatric CRM", version="1.0.0")

# Настройка путей к статическим файлам и шаблонам
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Создаем таблицы при запуске
@app.on_event("startup")
def startup_event():
    create_tables()

# Pydantic модели
class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    birth_date: Optional[date] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    parent_name: Optional[str] = None
    address: Optional[str] = None
    gender: Optional[str] = None
    birth_weight: Optional[int] = None
    birth_height: Optional[int] = None

class AppointmentCreate(BaseModel):
    patient_id: int
    appointment_date: date
    appointment_time: str
    type: str = "consultation"
    notes: Optional[str] = None

class BotPatientCreate(BaseModel):
    first_name: str
    last_name: str
    birth_date: Optional[date] = None
    phone: str
    parent_name: str
    address: Optional[str] = None
    gender: Optional[str] = None
    birth_weight: Optional[int] = None
    birth_height: Optional[int] = None
    parent_phone: str

class MedicalRecordCreate(BaseModel):
    patient_id: int
    appointment_id: Optional[int] = None
    complaints: Optional[str] = None
    examination: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    prescriptions: Optional[str] = None
    recommendations: Optional[str] = None
    notes: Optional[str] = None
    temperature: Optional[float] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    condition: Optional[str] = None
    skin: Optional[str] = None
    breathing: Optional[str] = None
    heart: Optional[str] = None
    abdomen: Optional[str] = None

class DoctorNoteCreate(BaseModel):
    patient_id: int
    content: str

class ReminderCreate(BaseModel):
    patient_id: int
    reminder_date: datetime
    content: str

# Вспомогательная функция для расчета возраста
def calculate_age(birth_date):
    if not birth_date:
        return ""
    
    if isinstance(birth_date, datetime):
        birth_date = birth_date.date()
    
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    if age == 0:
        # Возраст в месяцах для детей до 1 года
        months = (today.year - birth_date.year) * 12 + today.month - birth_date.month
        if today.day < birth_date.day:
            months -= 1
        return f"{months} мес."
    elif age == 1:
        return "1 год"
    elif 2 <= age <= 4:
        return f"{age} года"
    else:
        return f"{age} лет"

# Главная страница - список пациентов
@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: Session = Depends(get_db)):
    try:
        patients = db.query(models.Patient).order_by(models.Patient.created_at.desc()).all()
        
        # Статистика
        total_patients = len(patients)
        new_patients = len([p for p in patients if p.status == "new"])
        
        # Записи на сегодня
        today = datetime.now().date()
        today_appointments = db.query(models.Appointment).filter(
            models.Appointment.appointment_date == today
        ).count()
        
        stats = {
            "total_patients": total_patients,
            "today_appointments": today_appointments,
            "new_patients": new_patients
        }
        
        return templates.TemplateResponse(
            "patients/list.html", 
            {
                "request": request, 
                "patients": patients, 
                "stats": stats
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "error.html", 
            {
                "request": request,
                "error": f"Ошибка загрузки данных: {str(e)}"
            }
        )

# Страница записей
@app.get("/appointments", response_class=HTMLResponse)
async def appointments_page(request: Request, db: Session = Depends(get_db), selected_date: str = None):
    try:
        # Определяем дату для отображения
        if selected_date:
            target_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        else:
            target_date = datetime.now().date()
        
        # Получаем записи на выбранную дату
        appointments = db.query(models.Appointment).filter(
            models.Appointment.appointment_date == target_date
        ).order_by(models.Appointment.appointment_time).all()
        
        # Форматируем данные для шаблона
        appointments_data = []
        for appointment in appointments:
            patient = db.query(models.Patient).filter(models.Patient.id == appointment.patient_id).first()
            if patient:
                patient_name = f"{patient.last_name} {patient.first_name}"
                patient_age = calculate_age(patient.birth_date) if patient.birth_date else ""
            else:
                patient_name = "Неизвестный пациент"
                patient_age = ""
            
            appointments_data.append({
                "id": appointment.id,
                "patient_name": patient_name,
                "patient_age": patient_age,
                "time": getattr(appointment, 'appointment_time', '10:00'),
                "type": getattr(appointment, 'type', 'consultation'),
                "status": getattr(appointment, 'status', 'scheduled'),
                "notes": getattr(appointment, 'notes', '')
            })
        
        # Даты для навигации
        today = datetime.now().date()
        dates_navigation = {
            "today": today,
            "tomorrow": today + timedelta(days=1),
            "next_week": today + timedelta(days=7),
            "selected_date": target_date
        }
        
        return templates.TemplateResponse(
            "appointments/list.html", 
            {
                "request": request,
                "appointments": appointments_data,
                "dates": dates_navigation,
                "selected_date": target_date
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "appointments/list.html", 
            {
                "request": request,
                "appointments": [],
                "dates": {},
                "error": f"Ошибка загрузки записей: {str(e)}"
            }
        )

# Детальная карточка пациента
@app.get("/patients/{patient_id}", response_class=HTMLResponse)
async def patient_detail(request: Request, patient_id: int, db: Session = Depends(get_db)):
    try:
        patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
        if not patient:
            return templates.TemplateResponse("error.html", {"request": request, "error": "Пациент не найден"})
        
        # Получаем связанные данные
        appointments = db.query(models.Appointment).filter(
            models.Appointment.patient_id == patient_id
        ).order_by(models.Appointment.appointment_date.desc()).all()
        
        medical_records = db.query(models.MedicalRecord).filter(
            models.MedicalRecord.patient_id == patient_id
        ).order_by(models.MedicalRecord.visit_date.desc()).all()
        
        # Получаем теги пациента
        tags = db.query(models.PatientTag).join(
            models.PatientTagAssignment
        ).filter(
            models.PatientTagAssignment.patient_id == patient_id
        ).all()
        
        # Получаем заметки врача
        doctor_notes = db.query(models.DoctorNote).filter(
            models.DoctorNote.patient_id == patient_id
        ).order_by(models.DoctorNote.note_date.desc()).all()
        
        # Получаем напоминания
        reminders = db.query(models.Reminder).filter(
            models.Reminder.patient_id == patient_id
        ).order_by(models.Reminder.reminder_date).all()
        
        # Получаем родителей через связь
        parents = db.query(models.Parent).join(
            models.ParentChild
        ).filter(
            models.ParentChild.patient_id == patient_id
        ).all()
        
        # Получаем все доступные теги
        all_tags = db.query(models.PatientTag).all()
        
        # Медицинские шаблоны
        medical_templates = db.query(models.MedicalTemplate).all()
        
        return templates.TemplateResponse(
            "patients/detail.html",
            {
                "request": request,
                "patient": patient,
                "appointments": appointments,
                "medical_records": medical_records,
                "tags": tags,
                "all_tags": all_tags,
                "doctor_notes": doctor_notes,
                "reminders": reminders,
                "parents": parents,
                "medical_templates": medical_templates,
                "calculate_age": calculate_age
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": f"Ошибка загрузки карточки пациента: {str(e)}"}
        )

# Остальные страницы
@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    return templates.TemplateResponse("reports/list.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings/list.html", {"request": request})

# API для пациентов
@app.get("/api/patients", response_model=List[dict])
async def get_patients(db: Session = Depends(get_db)):
    try:
        patients = db.query(models.Patient).order_by(models.Patient.created_at.desc()).all()
        return [
            {
                "id": p.id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "birth_date": p.birth_date,
                "phone": p.phone,
                "email": p.email,
                "parent_name": p.parent_name,
                "address": p.address,
                "status": p.status,
                "created_at": p.created_at,
                "last_visit": p.last_visit
            }
            for p in patients
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения пациентов: {str(e)}")

@app.post("/api/patients")
async def create_patient(patient_data: PatientCreate, db: Session = Depends(get_db)):
    try:
        patient = models.Patient(
            first_name=patient_data.first_name,
            last_name=patient_data.last_name,
            birth_date=patient_data.birth_date,
            phone=patient_data.phone,
            email=patient_data.email,
            parent_name=patient_data.parent_name,
            address=patient_data.address,
            gender=patient_data.gender,
            birth_weight=patient_data.birth_weight,
            birth_height=patient_data.birth_height,
            status="new"
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return {
            "id": patient.id,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "status": patient.status
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка создания пациента: {str(e)}")

# API для записей
@app.get("/api/appointments")
async def get_appointments(date: str = None, db: Session = Depends(get_db)):
    try:
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        else:
            target_date = datetime.now().date()
        
        appointments = db.query(models.Appointment).filter(
            models.Appointment.appointment_date == target_date
        ).all()
        
        result = []
        for appointment in appointments:
            patient = db.query(models.Patient).filter(models.Patient.id == appointment.patient_id).first()
            patient_name = f"{patient.last_name} {patient.first_name}" if patient else "Неизвестный пациент"
            
            result.append({
                "id": appointment.id,
                "patient_name": patient_name,
                "patient_id": appointment.patient_id,
                "time": getattr(appointment, 'appointment_time', '10:00'),
                "type": getattr(appointment, 'type', 'consultation'),
                "status": getattr(appointment, 'status', 'scheduled'),
                "notes": getattr(appointment, 'notes', '')
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения записей: {str(e)}")

@app.post("/api/appointments")
async def create_appointment(appointment_data: AppointmentCreate, db: Session = Depends(get_db)):
    try:
        appointment = models.Appointment(
            patient_id=appointment_data.patient_id,
            appointment_date=appointment_data.appointment_date,
            appointment_time=appointment_data.appointment_time,
            type=appointment_data.type,
            notes=appointment_data.notes,
            status="confirmed"
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        return {"status": "success", "appointment_id": appointment.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка создания записи: {str(e)}")

# API для синхронизации с ботом
@app.post("/api/bot/create-patient")
async def create_patient_from_bot(patient_data: BotPatientCreate, db: Session = Depends(get_db)):
    try:
        # Создаем пациента
        patient = models.Patient(
            first_name=patient_data.first_name,
            last_name=patient_data.last_name,
            birth_date=patient_data.birth_date,
            phone=patient_data.phone,
            parent_name=patient_data.parent_name,
            address=patient_data.address,
            gender=patient_data.gender,
            birth_weight=patient_data.birth_weight,
            birth_height=patient_data.birth_height,
            status="new"
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        
        # Находим или создаем родителя
        parent = db.query(models.Parent).filter(
            models.Parent.phone == patient_data.parent_phone
        ).first()
        
        if not parent:
            # Создаем временный пароль
            import random
            temp_password = str(random.randint(100000, 999999))
            
            parent = models.Parent(
                phone=patient_data.parent_phone,
                password=temp_password,
                first_name=patient_data.parent_name.split()[0] if patient_data.parent_name else "",
                last_name=" ".join(patient_data.parent_name.split()[1:]) if patient_data.parent_name and len(patient_data.parent_name.split()) > 1 else ""
            )
            db.add(parent)
            db.commit()
            db.refresh(parent)
        
        # Связываем родителя и ребенка
        parent_child = models.ParentChild(
            parent_id=parent.id,
            patient_id=patient.id,
            relationship="parent"
        )
        db.add(parent_child)
        db.commit()
        
        return {
            "status": "success", 
            "patient_id": patient.id,
            "message": "Пациент создан и ожидает подтверждения врача"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка создания пациента: {str(e)}")

@app.post("/api/bot/create-appointment")
async def create_appointment_from_bot(appointment_data: dict, db: Session = Depends(get_db)):
    try:
        appointment = models.Appointment(
            patient_id=appointment_data["patient_id"],
            parent_id=appointment_data.get("parent_id"),
            appointment_date=datetime.strptime(appointment_data["date"], "%Y-%m-%d").date(),
            appointment_time=appointment_data["time"],
            type=appointment_data.get("type", "consultation"),
            status="new",
            notes=appointment_data.get("notes", "")
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        
        return {
            "status": "success", 
            "message": "Запись создана",
            "appointment_id": appointment.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bot/free-slots")
async def get_free_slots(date: str = None):
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Здесь будет логика получения свободных слотов из базы
        # Пока возвращаем тестовые данные
        return {
            "date": date,
            "slots": ["09:00", "10:30", "12:00", "14:00", "15:30", "17:00"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bot/auth")
async def bot_auth(auth_data: dict, db: Session = Depends(get_db)):
    try:
        parent = db.query(models.Parent).filter(
            models.Parent.phone == auth_data["phone"],
            models.Parent.password == auth_data["password"]
        ).first()
        
        if parent:
            # Получаем привязанных детей
            children = db.query(models.Patient).join(
                models.ParentChild,
                models.ParentChild.patient_id == models.Patient.id
            ).filter(
                models.ParentChild.parent_id == parent.id
            ).all()
            
            children_data = []
            for child in children:
                children_data.append({
                    "id": child.id,
                    "name": f"{child.first_name} {child.last_name}",
                    "birth_date": child.birth_date.strftime("%d.%m.%Y") if child.birth_date else None,
                    "status": child.status
                })
            
            return {
                "status": "success",
                "parent": {
                    "id": parent.id,
                    "name": f"{parent.first_name} {parent.last_name}",
                    "phone": parent.phone
                },
                "children": children_data
            }
        else:
            return {"status": "error", "message": "Неверный телефон или пароль"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API для обновления пациента
@app.put("/api/patients/{patient_id}/basic")
async def update_patient_basic(patient_id: int, patient_data: dict, db: Session = Depends(get_db)):
    try:
        patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Пациент не найден")
        
        # Обновляем только разрешенные поля
        allowed_fields = ['first_name', 'last_name', 'birth_date', 'phone', 'email', 
                         'parent_name', 'address', 'gender', 'birth_weight', 'birth_height',
                         'allergies', 'chronic_diseases', 'health_group', 'vaccinations', 
                         'development_notes', 'status']
        
        for field, value in patient_data.items():
            if field in allowed_fields and value is not None:
                setattr(patient, field, value)
        
        db.commit()
        return {"status": "success", "message": "Данные пациента обновлены"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка обновления: {str(e)}")

# API для добавления тега пациенту
@app.post("/api/patients/{patient_id}/tags")
async def add_patient_tag(patient_id: int, tag_data: dict, db: Session = Depends(get_db)):
    try:
        # Проверяем, существует ли уже такая связь
        existing = db.query(models.PatientTagAssignment).filter(
            models.PatientTagAssignment.patient_id == patient_id,
            models.PatientTagAssignment.tag_id == tag_data['tag_id']
        ).first()
        
        if not existing:
            assignment = models.PatientTagAssignment(
                patient_id=patient_id,
                tag_id=tag_data['tag_id']
            )
            db.add(assignment)
            db.commit()
        
        return {"status": "success", "message": "Тег добавлен"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка добавления тега: {str(e)}")

# API для удаления тега
@app.delete("/api/patients/{patient_id}/tags/{tag_id}")
async def remove_patient_tag(patient_id: int, tag_id: int, db: Session = Depends(get_db)):
    try:
        assignment = db.query(models.PatientTagAssignment).filter(
            models.PatientTagAssignment.patient_id == patient_id,
            models.PatientTagAssignment.tag_id == tag_id
        ).first()
        
        if assignment:
            db.delete(assignment)
            db.commit()
        
        return {"status": "success", "message": "Тег удален"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка удаления тега: {str(e)}")

# API для добавления заметки врача
@app.post("/api/patients/{patient_id}/notes")
async def add_doctor_note(patient_id: int, note_data: DoctorNoteCreate, db: Session = Depends(get_db)):
    try:
        note = models.DoctorNote(
            patient_id=patient_id,
            content=note_data.content,
            created_by="Врач"
        )
        db.add(note)
        db.commit()
        return {"status": "success", "message": "Заметка добавлена", "note_id": note.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка добавления заметки: {str(e)}")

# API для добавления напоминания
@app.post("/api/patients/{patient_id}/reminders")
async def add_reminder(patient_id: int, reminder_data: ReminderCreate, db: Session = Depends(get_db)):
    try:
        reminder = models.Reminder(
            patient_id=patient_id,
            reminder_date=reminder_data.reminder_date,
            content=reminder_data.content
        )
        db.add(reminder)
        db.commit()
        return {"status": "success", "message": "Напоминание добавлено", "reminder_id": reminder.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка добавления напоминания: {str(e)}")

# API для создания медицинской записи
@app.post("/api/medical-records")
async def create_medical_record(record_data: MedicalRecordCreate, db: Session = Depends(get_db)):
    try:
        record = models.MedicalRecord(
            patient_id=record_data.patient_id,
            appointment_id=record_data.appointment_id,
            complaints=record_data.complaints,
            examination=record_data.examination,
            diagnosis=record_data.diagnosis,
            treatment=record_data.treatment,
            prescriptions=record_data.prescriptions,
            recommendations=record_data.recommendations,
            notes=record_data.notes,
            temperature=record_data.temperature,
            weight=record_data.weight,
            height=record_data.height,
            condition=record_data.condition,
            skin=record_data.skin,
            breathing=record_data.breathing,
            heart=record_data.heart,
            abdomen=record_data.abdomen
        )
        db.add(record)
        
        # Обновляем дату последнего визита у пациента
        patient = db.query(models.Patient).filter(models.Patient.id == record_data.patient_id).first()
        if patient:
            patient.last_visit = datetime.utcnow()
        
        db.commit()
        return {"status": "success", "message": "Медицинская запись создана", "record_id": record.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка создания медицинской записи: {str(e)}")

# Health check и остальные эндпоинты
@app.get("/health")
async def health(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ok", 
        "message": "Pediatric CRM работает!", 
        "timestamp": datetime.utcnow(),
        "database": db_status
    }

# Дополнительные API endpoints
@app.get("/api/patients/{patient_id}")
async def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Пациент не найден")
    return {
        "id": patient.id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "birth_date": patient.birth_date,
        "phone": patient.phone,
        "email": patient.email,
        "parent_name": patient.parent_name,
        "address": patient.address,
        "status": patient.status,
        "created_at": patient.created_at,
        "last_visit": patient.last_visit
    }

@app.put("/api/patients/{patient_id}")
async def update_patient(patient_id: int, patient_data: PatientCreate, db: Session = Depends(get_db)):
    try:
        patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Пациент не найден")
        
        for field, value in patient_data.dict().items():
            if value is not None:
                setattr(patient, field, value)
        
        db.commit()
        db.refresh(patient)
        return {
            "id": patient.id,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "status": patient.status
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка обновления пациента: {str(e)}")

@app.delete("/api/patients/{patient_id}")
async def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    try:
        patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Пациент не найден")
        
        db.delete(patient)
        db.commit()
        return {"message": "Пациент удален"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка удаления пациента: {str(e)}")

# API для статистики
@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    total_patients = db.query(models.Patient).count()
    new_patients = db.query(models.Patient).filter(models.Patient.status == "new").count()
    
    return {
        "total_patients": total_patients,
        "new_patients": new_patients,
        "today_appointments": 0,
        "month_income": 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)