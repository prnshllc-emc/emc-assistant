"""Seed database from emc_data.json and container data."""
import json
import os
from sqlalchemy.orm import Session
from app.models import Item, Container, User
from app.auth import hash_password


CONTAINER_OPS_IDS = {3, 4, 15, 20}  # purely operational tracking duplicates

CONTAINERS = [
    # ── Exportações EUA ──────────────────────────────────────────────────
    {"op": "1039-E-ON", "booking": "265005727", "container": "MSKU1741282",
     "vessel": "RDO FORTUNE 602N", "route": "SSZ → EWR (Newark)",
     "etd": "18/Jan", "eta": "03/Mar",
     "status": "liberado", "status_text": "CBP Release 05/Fev — Entry 2620588-9"},

    {"op": "1040-E-ON", "booking": "265005786", "container": "SUDU895110-8",
     "vessel": "RDO FORTUNE 602N", "route": "SSZ → PEF",
     "etd": "18/Jan", "eta": "12/Fev",
     "status": "entregue", "status_text": "Entregue ao cliente"},

    {"op": "1041-E-ON", "booking": "265005757", "container": "SUDU872956-0",
     "vessel": "MAERSK FRANKFURT 604N", "route": "SSZ → EWR (Newark)",
     "etd": "18/Jan", "eta": "03/Mar",
     "status": "entregue", "status_text": "Entregue — CBP exam Newark APM, pickup 23/Fev"},

    {"op": "1044-E-ON", "booking": "265399692", "container": "BEAU5815003",
     "vessel": "MAERSK FORTALEZA 603N", "route": "SSZ → JAX → FTL → PEF",
     "etd": "25/Jan", "eta": "13/Mar",
     "status": "remocao", "status_text": "JAX discharge 28/Fev — Rail FEC dep 09/Mar → FTL arr 09/Mar — PEF ETA 13/Mar — Drayage Daytona Beach pendente"},

    {"op": "1045-E-ON", "booking": "266319284", "container": "TXGU5230441",
     "vessel": "MAERSK FREEPORT 606N", "route": "SSZ → PEF",
     "etd": "15/Fev", "eta": "17/Mar",
     "status": "em_transito", "status_text": "Em trânsito — A/N recebido"},

    {"op": "1046-E-ON", "booking": "266742326", "container": "MRSU558461-8",
     "vessel": "MAERSK MONTE ALEGRE 608N", "route": "SSZ → EWR (Newark)",
     "etd": "01/Mar", "eta": "17/Mar",
     "status": "em_transito", "status_text": "Em trânsito — ETA Newark APM 17/Mar 07:00"},

    {"op": "1047-E-ON", "booking": "266742227", "container": "CAAU677806-1",
     "vessel": "MAERSK MONTE ALEGRE 608N", "route": "SSZ → PEF",
     "etd": "01/Mar", "eta": "26/Mar",
     "status": "em_transito", "status_text": "Em trânsito — ETA Port Everglades FIT 26/Mar 14:00"},

    # ── Importação BMW E30 (Allog / Mundi) ────────────────────────────────
    {"op": "1025-I-ON", "booking": "A definir", "container": "1x FCL 20'",
     "vessel": "MAERSK LA PAZ 607S", "route": "Bremerhaven → Santos",
     "etd": "26/Fev", "eta": "21/Mar",
     "status": "em_transito", "status_text": "Em trânsito — embarcou 26/Fev"},

    # ── Retorno Argentina (Allog) ────────────────────────────────────────
    {"op": "1034-A-ON", "booking": "IM0226121586", "container": "IKLZ7776576",
     "vessel": "Mercosul Line / ZIM", "route": "BUE → Santos",
     "etd": "Fev/26", "eta": "05/Mar",
     "status": "desembarque", "status_text": "Atracou 05/Mar — Remoção DTA p/ AGESBEC em andamento"},
]


def seed_database(db: Session, json_path: str = None):
    """Seed DB from emc_data.json + containers. Skips if data already exists."""

    # Check if already seeded
    if db.query(Item).count() > 0:
        print("⏭️  Database already seeded, skipping.")
        return

    # Create default admin user
    admin = User(
        name="Fred Junqueira",
        email="prnsh.llc@gmail.com",
        password_hash=hash_password("emc2026"),
        role="admin",
    )
    db.add(admin)

    # Load items from JSON
    if json_path is None:
        # Try multiple paths
        for p in ["emc_data.json", "../emc_data.json", "app/../emc_data.json"]:
            if os.path.exists(p):
                json_path = p
                break

    if json_path and os.path.exists(json_path):
        with open(json_path, "r") as f:
            data = json.load(f)

        for item_data in data:
            item = Item(
                original_id=item_data.get("item_id"),
                title=item_data["title"],
                description=item_data.get("description", ""),
                urgency=item_data.get("urgency", "medium"),
                category=item_data.get("category", ""),
                status=item_data.get("status", "Pendente"),
                contacts=item_data.get("contacts", ""),
                amount=item_data.get("amount", ""),
                amount_type=item_data.get("amount_type", ""),
                deadline=item_data.get("deadline", ""),
                source=item_data.get("source", ""),
                thread_id=item_data.get("thread_id", ""),
                notes=item_data.get("notes", ""),
                is_resolved=(item_data.get("status") == "Resolvido"),
                is_container_op=(item_data.get("item_id") in CONTAINER_OPS_IDS),
            )
            db.add(item)

        print(f"✅ {len(data)} items imported from JSON")
    else:
        print("⚠️  emc_data.json not found, skipping items")

    # Seed containers
    for c in CONTAINERS:
        container = Container(
            operation=c["op"],
            booking=c["booking"],
            container_number=c["container"],
            vessel=c["vessel"],
            route=c["route"],
            etd=c["etd"],
            eta=c["eta"],
            status=c["status"],
            status_text=c["status_text"],
        )
        db.add(container)

    print(f"✅ {len(CONTAINERS)} containers imported")

    db.commit()
    print("✅ Database seeded successfully!")
    print(f"   👤 Admin: prnsh.llc@gmail.com / emc2026")
