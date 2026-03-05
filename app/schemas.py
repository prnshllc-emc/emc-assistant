"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# === Auth ===
class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    class Config:
        from_attributes = True


# === Items ===
class ItemCreate(BaseModel):
    title: str
    description: str = ""
    urgency: str = "medium"
    category: str = ""
    status: str = "Pendente"
    contacts: str = ""
    amount: str = ""
    amount_type: str = ""
    deadline: str = ""
    source: str = ""
    thread_id: str = ""
    notes: str = ""
    is_container_op: bool = False

class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    urgency: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    contacts: Optional[str] = None
    amount: Optional[str] = None
    amount_type: Optional[str] = None
    deadline: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    is_container_op: Optional[bool] = None

class ItemResponse(BaseModel):
    id: int
    original_id: Optional[int] = None
    title: str
    description: str
    urgency: str
    category: str
    status: str
    contacts: str
    amount: str
    amount_type: str
    deadline: str
    source: str
    thread_id: str
    notes: str
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    is_container_op: bool
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


# === Containers ===
class ContainerCreate(BaseModel):
    operation: str
    booking: str = ""
    container_number: str = ""
    vessel: str = ""
    route: str = ""
    etd: str = ""
    eta: str = ""
    status: str = "transit"
    status_text: str = ""

class ContainerUpdate(BaseModel):
    operation: Optional[str] = None
    booking: Optional[str] = None
    container_number: Optional[str] = None
    vessel: Optional[str] = None
    route: Optional[str] = None
    etd: Optional[str] = None
    eta: Optional[str] = None
    status: Optional[str] = None
    status_text: Optional[str] = None

class ContainerResponse(BaseModel):
    id: int
    operation: str
    booking: str
    container_number: str
    vessel: str
    route: str
    etd: str
    eta: str
    status: str
    status_text: str
    updated_at: datetime
    class Config:
        from_attributes = True
