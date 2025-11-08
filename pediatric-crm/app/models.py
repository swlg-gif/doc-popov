from sqlalchemy import Column, Integer, String, DateTime, Date, Time, Float, Text, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    birth_date = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)
    phone = Column(String(20), nullable=False)
    parent_name = Column(String(200))
    parent_phone = Column(String(20))
    address = Column(Text)
    email = Column(String(100))
    birth_weight = Column(Integer)  # в граммах
    birth_height = Column(Integer)  # в см
    allergies = Column(Text)
    chronic_diseases = Column(Text)
    health_group = Column(String(10))
    vaccinations = Column(Text)
    development_notes = Column(Text)
    status = Column(String(20), default="new")  # new, confirmed, archived
    created_at = Column(DateTime, default=datetime.now)
    
    appointments = relationship("Appointment", back_populates="patient")

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    type = Column(String(50), nullable=False)  # primary, repeat, vaccination, consultation
    status = Column(String(20), default="new")  # new, confirmed, completed, cancelled
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    patient = relationship("Patient", back_populates="appointments")
    medical_record = relationship("MedicalRecord", back_populates="appointment", uselist=False)

class MedicalRecord(Base):
    __tablename__ = "medical_records"
    
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), unique=True)
    complaints = Column(Text)
    examination = Column(JSON)  # {temp: 36.6, weight: 20.5, height: 110, condition: "satisfactory", ...}
    diagnosis = Column(JSON)  # {main: "J06.9", additional: []}
    prescriptions = Column(JSON)  # список назначений
    recommendations = Column(Text)
    next_visit_date = Column(Date)
    next_visit_time = Column(Time)
    next_visit_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)
    
    appointment = relationship("Appointment", back_populates="medical_record")
    payment = relationship("Payment", back_populates="medical_record", uselist=False)

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    medical_record_id = Column(Integer, ForeignKey("medical_records.id"), unique=True)
    amount = Column(Float, default=0)
    status = Column(String(20), default="pending")  # pending, paid, cancelled
    method = Column(String(20), default="cash")  # cash, card, transfer
    created_at = Column(DateTime, default=datetime.now)
    
    medical_record = relationship("MedicalRecord", back_populates="payment")

class MedicalTemplate(Base):
    __tablename__ = "medical_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    diagnosis = Column(JSON)
    prescriptions = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)

class Parent(Base):
    __tablename__ = "parents"
    
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)

class ParentChild(Base):
    __tablename__ = "parent_children"
    
    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parents.id"))
    patient_id = Column(Integer, ForeignKey("patients.id"))
    created_at = Column(DateTime, default=datetime.now)