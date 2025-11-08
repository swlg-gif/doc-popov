from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
import json
from typing import Optional

from .database import get_db, engine
from .models import Base, Patient, Appointment, MedicalRecord, MedicalTemplate, Payment, Parent, ParentChild

app = FastAPI()

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Создаем таблицы
Base.metadata.create_all(bind=engine)

# Вспомогательная функция для расчета возраста
def calculate_age(birth_date):
    if not birth_date:
        return 0
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

# Добавляем функцию в шаблоны
templates.env.globals["calculate_age"] = calculate_age

# ========== ГЛАВНЫЕ СТРАНИЦЫ ==========

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    patients = db.query(Patient).order_by(Patient.created_at.desc()).all()
    
    # Получаем статистику
    stats = {
        'total_patients': len(patients),
        'new_patients': len([p for p in patients if p.status == 'new']),
        'active_patients': len([p for p in patients if p.status == 'confirmed']),
        'today_appointments': db.query(Appointment).filter(Appointment.date == date.today()).count()
    }
    
    return templates.TemplateResponse("patients/list.html", {
        "request": request,
        "patients": patients,
        "stats": stats
    })

@app.get("/patients/{patient_id}", response_class=HTMLResponse)
async def patient_detail(request: Request, patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Получаем записи пациента
    appointments = db.query(Appointment).filter(Appointment.patient_id == patient_id).order_by(Appointment.date.desc()).all()
    
    # Получаем родителей
    parents = db.query(Parent).all()
    
    return templates.TemplateResponse("patients/detail.html", {
        "request": request,
        "patient": patient,
        "appointments": appointments,
        "parents": parents
    })

@app.get("/create-patient", response_class=HTMLResponse)
async def create_patient_page(request: Request):
    return templates.TemplateResponse("patients/create.html", {"request": request})

@app.get("/appointments", response_class=HTMLResponse)
async def appointments_page(request: Request, db: Session = Depends(get_db)):
    # Получаем даты для навигации
    today = date.today()
    tomorrow = today + timedelta(days=1)
    next_week = today + timedelta(days=7)
    
    # Получаем выбранную дату из параметра
    selected_date_str = request.query_params.get("selected_date", today.strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except:
        selected_date = today
    
    # Получаем записи на выбранную дату
    appointments = db.query(Appointment).filter(Appointment.date == selected_date).order_by(Appointment.time).all()
    
    # Формируем данные для отображения
    appointments_data = []
    for appointment in appointments:
        patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
        appointments_data.append({
            'id': appointment.id,
            'time': appointment.time.strftime('%H:%M'),
            'patient_name': f"{patient.last_name} {patient.first_name}" if patient else "Неизвестный",
            'patient_age': calculate_age(patient.birth_date) if patient and patient.birth_date else None,
            'type': appointment.type,
            'status': appointment.status,
            'notes': appointment.comment
        })
    
    return templates.TemplateResponse("appointments/list.html", {
        "request": request,
        "appointments": appointments_data,
        "selected_date": selected_date,
        "dates": {
            "today": today,
            "tomorrow": tomorrow,
            "next_week": next_week,
            "selected_date": selected_date
        }
    })

@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request, db: Session = Depends(get_db)):
    # Базовая статистика для отчетов
    total_patients = db.query(Patient).count()
    total_appointments = db.query(Appointment).count()
    completed_appointments = db.query(Appointment).filter(Appointment.status == 'completed').count()
    
    return templates.TemplateResponse("reports/list.html", {
        "request": request,
        "stats": {
            'total_patients': total_patients,
            'total_appointments': total_appointments,
            'completed_appointments': completed_appointments
        }
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    templates_list = db.query(MedicalTemplate).all()
    return templates.TemplateResponse("settings/list.html", {
        "request": request,
        "templates": templates_list
    })

# ========== API ЭНДПОИНТЫ ==========

# Пациенты
@app.post("/api/patients")
async def create_patient(
    first_name: str = Form(...),
    last_name: str = Form(...),
    birth_date: str = Form(...),
    gender: str = Form(...),
    phone: str = Form(...),
    parent_name: str = Form(""),
    parent_phone: str = Form(""),
    address: str = Form(""),
    email: str = Form(""),
    birth_weight: int = Form(0),
    birth_height: int = Form(0),
    db: Session = Depends(get_db)
):
    try:
        # Преобразуем дату рождения
        birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d").date()
        
        patient = Patient(
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date_obj,
            gender=gender,
            phone=phone,
            parent_name=parent_name,
            parent_phone=parent_phone,
            address=address,
            email=email,
            birth_weight=birth_weight,
            birth_height=birth_height,
            status="new",
            created_at=datetime.now()
        )
        
        db.add(patient)
        db.commit()
        db.refresh(patient)
        
        return JSONResponse({
            "status": "success", 
            "patient_id": patient.id,
            "message": "Пациент успешно создан"
        })
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patients")
async def get_patients(db: Session = Depends(get_db)):
    patients = db.query(Patient).all()
    return [{
        "id": p.id,
        "first_name": p.first_name,
        "last_name": p.last_name,
        "birth_date": p.birth_date.isoformat() if p.birth_date else None,
        "phone": p.phone,
        "status": p.status
    } for p in patients]

@app.put("/api/patients/{patient_id}/basic")
async def update_patient_basic(
    patient_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    try:
        patient.first_name = first_name
        patient.last_name = last_name
        db.commit()
        
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Записи
@app.post("/api/appointments")
async def create_appointment(
    patient_id: int = Form(...),
    date: str = Form(...),
    time: str = Form(...),
    type: str = Form("consultation"),
    notes: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        appointment_date = datetime.strptime(date, "%Y-%m-%d").date()
        appointment_time = datetime.strptime(time, "%H:%M").time()
        
        # Проверяем существование пациента
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        appointment = Appointment(
            patient_id=patient_id,
            date=appointment_date,
            time=appointment_time,
            type=type,
            comment=notes,
            status="new",
            created_at=datetime.now()
        )
        
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        
        return JSONResponse({
            "status": "success", 
            "appointment_id": appointment.id
        })
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date or time format: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/appointments")
async def get_appointments(db: Session = Depends(get_db)):
    appointments = db.query(Appointment).all()
    return [{
        "id": a.id,
        "patient_id": a.patient_id,
        "date": a.date.isoformat(),
        "time": a.time.strftime('%H:%M'),
        "type": a.type,
        "status": a.status
    } for a in appointments]

# Медицинские записи и шаблоны
@app.get("/visit-result/{appointment_id}", response_class=HTMLResponse)
async def visit_result_page(request: Request, appointment_id: int, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
    templates_list = db.query(MedicalTemplate).all()
    
    return templates.TemplateResponse("visit_result.html", {
        "request": request,
        "appointment": appointment,
        "patient": patient,
        "templates": templates_list
    })

@app.get("/api/medical-templates")
async def get_medical_templates(db: Session = Depends(get_db)):
    templates = db.query(MedicalTemplate).all()
    return {"templates": [{"id": t.id, "name": t.name, "diagnosis": t.diagnosis, "prescriptions": t.prescriptions} for t in templates]}

@app.post("/api/medical-records")
async def create_medical_record(
    appointment_id: int = Form(...),
    complaints: str = Form(""),
    examination: str = Form("{}"),
    diagnosis: str = Form("{}"),
    prescriptions: str = Form("[]"),
    recommendations: str = Form(""),
    next_visit_date: Optional[str] = Form(None),
    next_visit_time: Optional[str] = Form(None),
    next_visit_type: Optional[str] = Form(None),
    create_next_appointment: bool = Form(False),
    payment_amount: float = Form(0),
    payment_status: str = Form("pending"),
    payment_method: str = Form("cash"),
    send_to_parents: bool = Form(False),
    template_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        # Создаем медицинскую запись
        medical_record = MedicalRecord(
            appointment_id=appointment_id,
            complaints=complaints,
            examination=json.loads(examination),
            diagnosis=json.loads(diagnosis),
            prescriptions=json.loads(prescriptions),
            recommendations=recommendations,
            created_at=datetime.now()
        )
        
        db.add(medical_record)
        db.flush()
        
        # Создаем запись об оплате
        payment = Payment(
            medical_record_id=medical_record.id,
            amount=payment_amount,
            status=payment_status,
            method=payment_method
        )
        db.add(payment)
        
        # Обновляем статус записи на "завершено"
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if appointment:
            appointment.status = "completed"
        
        # Создаем следующую запись если нужно
        if create_next_appointment and next_visit_date and next_visit_time:
            next_appointment = Appointment(
                patient_id=appointment.patient_id,
                date=datetime.strptime(next_visit_date, "%Y-%m-%d").date(),
                time=next_visit_time,
                type=next_visit_type or "control",
                status="confirmed",
                created_at=datetime.now()
            )
            db.add(next_appointment)
        
        db.commit()
        
        return JSONResponse({"status": "success", "medical_record_id": medical_record.id})
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Родители для бота
@app.get("/api/parents")
async def get_parents(db: Session = Depends(get_db)):
    parents = db.query(Parent).all()
    return [{
        "id": p.id,
        "first_name": p.first_name,
        "last_name": p.last_name,
        "phone": p.phone,
        "password": p.password
    } for p in parents]

# Системные эндпоинты
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Pediatric CRM is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)