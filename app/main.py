"""FastAPI main application — EMC Executive Assistant."""
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import init_db, get_db, SessionLocal
from app.models import Item, Container, User
from app.auth import (
    verify_password, create_token, decode_token,
    get_current_user, require_auth,
)
from app.api import router as api_router
from app.ingest import router as ingest_router
from app.seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and seed on startup."""
    init_db()
    db = SessionLocal()
    try:
        json_path = os.path.join(os.path.dirname(__file__), "..", "emc_data.json")
        seed_database(db, json_path)
    finally:
        db.close()
    yield


app = FastAPI(
    title="EMC Assistant",
    description="Assistente Executivo EMC — Frederico Junqueira",
    version="1.0.0",
    lifespan=lifespan,
)

# Static files & templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# API routes
app.include_router(api_router)
app.include_router(ingest_router)


# ─── HELPERS ─────────────────────────────────────────────────────────────

def categorize_items(items: list[Item]) -> dict:
    """Categorize items into urgent/pending/waiting/info buckets."""
    urgent, pending, waiting, info = [], [], [], []

    for item in items:
        if item.is_container_op:
            continue
        if item.is_resolved:
            info.append(item)
        elif item.urgency == "critical":
            urgent.append(item)
        elif item.status in ("Aguardando terceiro", "Estratégico"):
            waiting.append(item)
        elif item.urgency == "info" or item.status == "Resolvido":
            info.append(item)
        elif item.urgency == "high":
            pending.append(item)
        elif item.urgency in ("medium", "low"):
            if item.status == "Em andamento":
                pending.append(item)
            else:
                waiting.append(item)
        else:
            info.append(item)

    return {
        "urgent": urgent,
        "pending": pending,
        "waiting": waiting,
        "info": info,
    }


def priority_label(urgency: str) -> str:
    return {"critical": "CRÍTICO", "high": "ALTA", "medium": "MÉDIA", "low": "BAIXA", "info": "INFO"}.get(urgency, "MÉDIA")


def source_class(source: str) -> str:
    if not source:
        return "email"
    s = source.lower()
    if "whatsapp" in s:
        return "whatsapp"
    if "calendar" in s or "plaud" in s:
        return "calendar"
    return "email"


def source_label(source: str) -> str:
    if not source:
        return "Email"
    s = source.lower()
    if "whatsapp" in s:
        return "WhatsApp"
    if "calendar" in s:
        return "Calendar"
    if "plaud" in s:
        return "Plaud"
    if "dashboard" in s:
        return "Dashboard"
    return "Email"


def action_for_item(item: Item) -> tuple[str, str]:
    if "Cobran" in (item.title or "") or (item.amount and item.amount_type == "negative"):
        return ("pay", "💰 Pagar/Verificar")
    if item.status == "Resolvido" or item.is_resolved:
        return ("fyi", "✅ Resolvido")
    if "Aguardando" in (item.status or ""):
        return ("follow-up", "📩 Follow-up")
    if "Em andamento" in (item.status or ""):
        return ("review", "👀 Acompanhar")
    if "Pendente" in (item.status or ""):
        return ("respond", "✏️ Responder")
    return ("review", "👀 Revisar")


# Register template helpers
@app.middleware("http")
async def add_template_helpers(request: Request, call_next):
    response = await call_next(request)
    return response


# ─── HTML ROUTES ─────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Email ou senha incorretos",
        })
    token = create_token(user.id)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=72*3600)
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = await _get_user_from_request(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    items = db.query(Item).order_by(Item.id).all()
    # Filter out resolved containers (entregue, liberado)
    containers = db.query(Container).filter(
        ~Container.status.in_(["entregue", "liberado"])
    ).order_by(Container.id).all()
    cats = categorize_items(items)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "items": items,
        "containers": containers,
        "urgent": cats["urgent"],
        "pending": cats["pending"],
        "waiting": cats["waiting"],
        "info": cats["info"],
        "n_urgent": len(cats["urgent"]),
        "n_pending": len(cats["pending"]),
        "n_waiting": len(cats["waiting"]),
        "n_info": len(cats["info"]),
        "n_total": len(cats["urgent"]) + len(cats["pending"]) + len(cats["waiting"]) + len(cats["info"]),
        "n_containers": len(containers),
        # Helper functions
        "priority_label": priority_label,
        "source_class": source_class,
        "source_label": source_label,
        "action_for_item": action_for_item,
    })


# ─── HTMX PARTIALS ──────────────────────────────────────────────────────

@app.post("/htmx/items/{item_id}/resolve", response_class=HTMLResponse)
async def htmx_toggle_resolve(item_id: int, request: Request, db: Session = Depends(get_db)):
    user = await _get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401)

    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404)

    from datetime import datetime
    item.is_resolved = not item.is_resolved
    item.resolved_at = datetime.utcnow() if item.is_resolved else None
    item.user_status_at = datetime.utcnow()  # mark as manually edited
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)

    return templates.TemplateResponse("partials/item_card.html", {
        "request": request,
        "item": item,
        "priority_label": priority_label,
        "source_class": source_class,
        "source_label": source_label,
        "action_for_item": action_for_item,
    })


@app.get("/htmx/items/{item_id}/edit", response_class=HTMLResponse)
async def htmx_edit_form(item_id: int, request: Request, db: Session = Depends(get_db)):
    user = await _get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401)

    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404)

    return templates.TemplateResponse("partials/item_form.html", {
        "request": request,
        "item": item,
    })


@app.put("/htmx/items/{item_id}", response_class=HTMLResponse)
async def htmx_update_item(item_id: int, request: Request, db: Session = Depends(get_db)):
    user = await _get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401)

    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404)

    form = await request.form()
    status_changed = False
    for field in ["title", "description", "urgency", "category", "status", "contacts", "amount", "amount_type", "deadline", "source", "notes"]:
        val = form.get(field)
        if val is not None:
            if field in ("status", "urgency") and val != getattr(item, field):
                status_changed = True
            setattr(item, field, val)

    from datetime import datetime
    if status_changed:
        item.user_status_at = datetime.utcnow()  # mark as manually edited
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)

    return templates.TemplateResponse("partials/item_card.html", {
        "request": request,
        "item": item,
        "priority_label": priority_label,
        "source_class": source_class,
        "source_label": source_label,
        "action_for_item": action_for_item,
    })


@app.delete("/htmx/items/{item_id}", response_class=HTMLResponse)
async def htmx_delete_item(item_id: int, request: Request, db: Session = Depends(get_db)):
    user = await _get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401)

    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404)

    db.delete(item)
    db.commit()
    return HTMLResponse("")  # Remove from DOM


@app.get("/htmx/items/new", response_class=HTMLResponse)
async def htmx_new_form(request: Request, db: Session = Depends(get_db)):
    user = await _get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401)

    return templates.TemplateResponse("partials/item_form.html", {
        "request": request,
        "item": None,
    })


@app.post("/htmx/items", response_class=HTMLResponse)
async def htmx_create_item(request: Request, db: Session = Depends(get_db)):
    user = await _get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401)

    form = await request.form()
    item = Item(
        title=form.get("title", ""),
        description=form.get("description", ""),
        urgency=form.get("urgency", "medium"),
        category=form.get("category", ""),
        status=form.get("status", "Pendente"),
        contacts=form.get("contacts", ""),
        amount=form.get("amount", ""),
        amount_type=form.get("amount_type", ""),
        deadline=form.get("deadline", ""),
        source=form.get("source", "Manual"),
        notes=form.get("notes", ""),
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return templates.TemplateResponse("partials/item_card.html", {
        "request": request,
        "item": item,
        "priority_label": priority_label,
        "source_class": source_class,
        "source_label": source_label,
        "action_for_item": action_for_item,
    })


# ─── HELPERS ─────────────────────────────────────────────────────────────

async def _get_user_from_request(request: Request, db: Session) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    user_id = decode_token(token)
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()
