"""Ingest API — receives data from Make.com automation scenarios.

Authentication: API key via X-API-Key header or ?api_key= query param.
The key is set via INGEST_API_KEY env var on Render.

Endpoints:
  POST /api/v1/ingest/items       — upsert items (by source + thread_id)
  POST /api/v1/ingest/containers  — upsert containers (by booking)
  POST /api/v1/ingest/bulk        — bulk upsert items + containers
  GET  /api/v1/ingest/health      — health check (no auth)
"""
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Item, Container

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])

INGEST_API_KEY = os.environ.get("INGEST_API_KEY", "")


# ─── Auth ────────────────────────────────────────────────────────────────

def verify_api_key(
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = Query(None),
):
    """Verify API key from header or query param."""
    key = x_api_key or api_key
    if not INGEST_API_KEY:
        raise HTTPException(503, "INGEST_API_KEY not configured on server")
    if not key or key != INGEST_API_KEY:
        raise HTTPException(401, "Invalid or missing API key")
    return True


# ─── Schemas ─────────────────────────────────────────────────────────────

class IngestItem(BaseModel):
    title: str
    description: str = ""
    urgency: str = "medium"          # critical, high, medium, low, info
    category: str = ""
    status: str = "Pendente"
    contacts: str = ""
    amount: str = ""
    amount_type: str = ""            # positive, negative, ""
    deadline: str = ""
    source: str = ""                 # Gmail, Calendar, Plaud, Apple Mail, etc.
    thread_id: str = ""              # unique identifier from source (Gmail thread ID, calendar event ID, etc.)
    notes: str = ""
    is_container_op: bool = False


class IngestContainer(BaseModel):
    operation: str
    booking: str = ""
    container_number: str = ""
    vessel: str = ""
    route: str = ""
    etd: str = ""
    eta: str = ""
    status: str = "transit"          # transit, arrived, loading, alert
    status_text: str = ""


class BulkIngest(BaseModel):
    items: list[IngestItem] = []
    containers: list[IngestContainer] = []


class IngestResult(BaseModel):
    created: int = 0
    updated: int = 0
    errors: list[str] = []


# ─── Helpers ─────────────────────────────────────────────────────────────

def _upsert_item(db: Session, data: IngestItem) -> str:
    """Upsert item by (source, thread_id) if thread_id is set, else create new."""
    existing = None
    if data.thread_id:
        existing = db.query(Item).filter(
            Item.source == data.source,
            Item.thread_id == data.thread_id,
        ).first()

    if existing:
        for field in ["title", "description", "urgency", "category", "status",
                       "contacts", "amount", "amount_type", "deadline", "notes"]:
            val = getattr(data, field)
            if val:  # only update non-empty fields
                setattr(existing, field, val)
        existing.updated_at = datetime.utcnow()
        return "updated"
    else:
        item = Item(**data.model_dump())
        item.source = data.source or "Automação"
        db.add(item)
        return "created"


def _upsert_container(db: Session, data: IngestContainer) -> str:
    """Upsert container by booking number."""
    existing = None
    if data.booking:
        existing = db.query(Container).filter(
            Container.booking == data.booking,
        ).first()

    if existing:
        for field in ["operation", "container_number", "vessel", "route",
                       "etd", "eta", "status", "status_text"]:
            val = getattr(data, field)
            if val:
                setattr(existing, field, val)
        existing.updated_at = datetime.utcnow()
        return "updated"
    else:
        container = Container(**data.model_dump())
        db.add(container)
        return "created"


# ─── Endpoints ───────────────────────────────────────────────────────────

@router.get("/health")
def health():
    """Health check — no auth required."""
    return {
        "status": "ok",
        "service": "EMC Assistant Ingest API",
        "api_key_configured": bool(INGEST_API_KEY),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/items", response_model=IngestResult)
def ingest_items(
    items: list[IngestItem],
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_api_key),
):
    """Upsert one or more items. Deduplicates by (source, thread_id)."""
    result = IngestResult()
    for item_data in items:
        try:
            action = _upsert_item(db, item_data)
            if action == "created":
                result.created += 1
            else:
                result.updated += 1
        except Exception as e:
            result.errors.append(f"{item_data.title}: {str(e)}")
    db.commit()
    return result


@router.post("/containers", response_model=IngestResult)
def ingest_containers(
    containers: list[IngestContainer],
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_api_key),
):
    """Upsert one or more containers. Deduplicates by booking number."""
    result = IngestResult()
    for cont_data in containers:
        try:
            action = _upsert_container(db, cont_data)
            if action == "created":
                result.created += 1
            else:
                result.updated += 1
        except Exception as e:
            result.errors.append(f"{cont_data.booking}: {str(e)}")
    db.commit()
    return result


@router.post("/bulk", response_model=IngestResult)
def ingest_bulk(
    data: BulkIngest,
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_api_key),
):
    """Bulk upsert items and containers in one call."""
    result = IngestResult()

    for item_data in data.items:
        try:
            action = _upsert_item(db, item_data)
            if action == "created":
                result.created += 1
            else:
                result.updated += 1
        except Exception as e:
            result.errors.append(f"item '{item_data.title}': {str(e)}")

    for cont_data in data.containers:
        try:
            action = _upsert_container(db, cont_data)
            if action == "created":
                result.created += 1
            else:
                result.updated += 1
        except Exception as e:
            result.errors.append(f"container '{cont_data.booking}': {str(e)}")

    db.commit()
    return result
