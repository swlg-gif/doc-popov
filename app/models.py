from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    birth_date = Column(DateTime)
    phone = Column(String(20))
    email = Column(String(100))
    parent_name = Column(String(200))
    address = Column(Text)
    status = Column(String(20), default="new")
    gender = Column(String(10))
    birth_weight = Column(Integer)
    birth_height = Column(Integer)
    allergies = Column(Text)
    chronic_diseases = Column(Text)
    health_group = Column(String(10))
    vaccinations = Column(Text)
    development_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_visit = Column(DateTime)

class Parent(Base):
    __tablename__ = "parents"
    
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class ParentChild(Base):
    __tablename__ = "parent_children"
    
    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parents.id"))
    patient_id = Column(Integer, ForeignKey("patients.id"))
    relationship = Column(String(50))

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    parent_id = Column(Integer, ForeignKey("parents.id"))
    appointment_date = Column(DateTime, nullable=False)
    appointment_time = Column(String(10))
    type = Column(String(50), default="consultation")
    status = Column(String(50), default="new")
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class MedicalRecord(Base):
    __tablename__ = "medical_records"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    appointment_id = Column(Integer, ForeignKey("appointments.id"))
    visit_date = Column(DateTime, default=datetime.utcnow)
    complaints = Column(Text)
    examination = Column(Text)
    diagnosis = Column(Text)
    treatment = Column(Text)
    prescriptions = Column(Text)
    recommendations = Column(Text)
    notes = Column(Text)
    temperature = Column(Float)
    weight = Column(Float)
    height = Column(Float)
    condition = Column(String(100))
    skin = Column(String(100))
    breathing = Column(String(100))
    heart = Column(String(100))
    abdomen = Column(String(100))

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"))
    amount = Column(DECIMAL(10, 2))
    status = Column(String(20), default="pending")
    method = Column(String(50))
    paid_at = Column(DateTime)

class MedicalTemplate(Base):
    __tablename__ = "medical_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    diagnosis = Column(Text)
    complaints_template = Column(Text)
    examination_template = Column(Text)
    treatment_template = Column(Text)
    prescriptions_template = Column(Text)
    recommendations_template = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class PatientTag(Base):
    __tablename__ = "patient_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    color = Column(String(20), default="#3b82f6")

class PatientTagAssignment(Base):
    __tablename__ = "patient_tag_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    tag_id = Column(Integer, ForeignKey("patient_tags.id"))

class DoctorNote(Base):
    __tablename__ = "doctor_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    note_date = Column(DateTime, default=datetime.utcnow)
    content = Column(Text, nullable=False)
    created_by = Column(String(100))

class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    reminder_date = Column(DateTime, nullable=False)
    content = Column(Text, nullable=False)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)