"""REST API endpoints for EMC Assistant."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Item, Container, User
from app.auth import (
    verify_password, create_token, require_auth,
    hash_password,
)
from app.schemas import (
    LoginRequest, TokenResponse, UserResponse,
    ItemCreate, ItemUpdate, ItemResponse,
    ContainerCreate, ContainerUpdate, ContainerResponse,
)

router = APIRouter(prefix="/api/v1")

# ─── AUTH ────────────────────────────────────────────────────────────────

@router.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    token = create_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/auth/me", response_model=UserResponse)
def me(user: User = Depends(require_auth)):
    return user


# ─── ITEMS CRUD ──────────────────────────────────────────────────────────

@router.get("/items", response_model=list[ItemResponse])
def list_items(
    urgency: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    is_resolved: Optional[bool] = None,
    skip_container_ops: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth),
):
    q = db.query(Item)
    if urgency:
        q = q.filter(Item.urgency == urgency)
    if status:
        q = q.filter(Item.status == status)
    if category:
        q = q.filter(Item.category == category)
    if is_resolved is not None:
        q = q.filter(Item.is_resolved == is_resolved)
    if skip_container_ops:
        q = q.filter(Item.is_container_op == False)
    return q.order_by(Item.id).all()


@router.get("/items/stats")
def item_stats(db: Session = Depends(get_db), user: User = Depends(require_auth)):
    """Stats for dashboard stat-cards."""
    items = db.query(Item).filter(Item.is_container_op == False).all()

    urgent = pending = waiting = info = 0
    for item in items:
        if item.is_resolved:
            info += 1
        elif item.urgency == "critical":
            urgent += 1
        elif item.status in ("Aguardando terceiro", "Estratégico"):
            waiting += 1
        elif item.urgency == "info" or item.status == "Resolvido":
            info += 1
        elif item.urgency == "high":
            pending += 1
        elif item.urgency in ("medium", "low"):
            if item.status == "Em andamento":
                pending += 1
            else:
                waiting += 1
        else:
            info += 1

    return {
        "urgent": urgent,
        "pending": pending,
        "waiting": waiting,
        "info": info,
        "total": len(items),
    }


@router.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(require_auth)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return item


@router.post("/items", response_model=ItemResponse, status_code=201)
def create_item(data: ItemCreate, db: Session = Depends(get_db), user: User = Depends(require_auth)):
    item = Item(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, data: ItemUpdate, db: Session = Depends(get_db), user: User = Depends(require_auth)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(item, k, v)
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return item


@router.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(require_auth)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True, "deleted": item_id}


@router.post("/items/{item_id}/resolve")
def toggle_resolve(item_id: int, db: Session = Depends(get_db), user: User = Depends(require_auth)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    item.is_resolved = not item.is_resolved
    item.resolved_at = datetime.utcnow() if item.is_resolved else None
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return {"id": item.id, "is_resolved": item.is_resolved}


# ─── CONTAINERS ──────────────────────────────────────────────────────────

@router.get("/containers", response_model=list[ContainerResponse])
def list_containers(db: Session = Depends(get_db), user: User = Depends(require_auth)):
    return db.query(Container).order_by(Container.id).all()


@router.post("/containers", response_model=ContainerResponse, status_code=201)
def create_container(data: ContainerCreate, db: Session = Depends(get_db), user: User = Depends(require_auth)):
    container = Container(**data.model_dump())
    db.add(container)
    db.commit()
    db.refresh(container)
    return container


@router.put("/containers/{container_id}", response_model=ContainerResponse)
def update_container(container_id: int, data: ContainerUpdate, db: Session = Depends(get_db), user: User = Depends(require_auth)):
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container não encontrado")
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(container, k, v)
    container.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(container)
    return container
