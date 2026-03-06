"""SQLAlchemy models for EMC Assistant."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class UrgencyLevel(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class ContainerStatus(str, enum.Enum):
    booking = "booking"               # Booking emitido, carga não estufada
    depositado = "depositado"         # Container depositado, pronto p/ viagem
    saida_confirmada = "saida_confirmada"  # Saída confirmada
    em_transito = "em_transito"       # Em trânsito marítimo
    atrasado = "atrasado"             # ETD < hoje sem confirmação de chegada
    confirmacao_chegada = "confirmacao_chegada"  # Navio chegou ao destino
    aduana = "aduana"                 # Em liberação aduaneira (RFB ou CBP)
    liberado = "liberado"             # Aduana finalizada
    remocao = "remocao"               # Em trânsito para armazém de desova
    entregue = "entregue"             # Retirada confirmada pelo cliente


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    original_id = Column(Integer, nullable=True)  # item_id from JSON
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    urgency = Column(String(20), default="medium")
    category = Column(String(50), default="")
    status = Column(String(50), default="Pendente")
    contacts = Column(Text, default="")
    amount = Column(String(100), default="")
    amount_type = Column(String(20), default="")
    deadline = Column(String(100), default="")
    source = Column(String(50), default="")
    thread_id = Column(String(100), default="")
    notes = Column(Text, default="")
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    user_status_at = Column(DateTime, nullable=True)  # set when user manually changes status/resolved
    is_container_op = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Container(Base):
    __tablename__ = "containers"

    id = Column(Integer, primary_key=True, index=True)
    operation = Column(String(20), nullable=False)
    booking = Column(String(50), default="")
    container_number = Column(String(20), default="")
    vessel = Column(String(100), default="")
    route = Column(String(100), default="")
    etd = Column(String(20), default="")
    eta = Column(String(20), default="")
    status = Column(String(20), default="transit")
    status_text = Column(String(50), default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
