"""Seed database from emc_data.json and container data."""
import json
import os
from sqlalchemy.orm import Session
from app.models import Item, Container, User
from app.auth import hash_password


CONTAINER_OPS_IDS = {3, 4, 15, 20}  # purely operational tracking duplicates

CONTAINERS = [
    {"op": "1039-E-ON", "booking": "265005727", "container": "MSKU1741282", "vessel": "RDO FORTUNE 602N", "route": "SSZ → PNJ", "etd": "18/Jan", "eta": "03/Mar", "status": "arrived", "status_text": "CBP Release"},
    {"op": "1040-E-ON", "booking": "265005786", "container": "SUDU895110-8", "vessel": "RDO FORTUNE 602N", "route": "SSZ → PEF", "etd": "18/Jan", "eta": "12/Fev", "status": "arrived", "status_text": "Entregue"},
    {"op": "1041-E-ON", "booking": "265005757", "container": "SUDU872956-0", "vessel": "MAERSK FRANKFURT 604N", "route": "SSZ → PNJ", "etd": "18/Jan", "eta": "03/Mar", "status": "arrived", "status_text": "Arrived PNJ"},
    {"op": "1044-E-ON", "booking": "265399692", "container": "BEAU5815003", "vessel": "MAERSK FORTALEZA 603N", "route": "SSZ → PEF → JAX → FTL", "etd": "25/Jan", "eta": "19/Fev", "status": "transit", "status_text": "Rail → FTL"},
    {"op": "1045-E-ON", "booking": "266319284", "container": "TXGU5230441", "vessel": "MAERSK FREEPORT 606N", "route": "SSZ → PEF", "etd": "15/Fev", "eta": "12/Mar", "status": "transit", "status_text": "Em trânsito"},
    {"op": "1046-E-ON", "booking": "266742326", "container": "MRSU558461-8", "vessel": "MAERSK MONTE ALEGRE 608N", "route": "SSZ → PEF", "etd": "01/Mar", "eta": "26/Mar", "status": "loading", "status_text": "Embarcado"},
    {"op": "1047-E-ON", "booking": "266742227", "container": "CAAU677806-1", "vessel": "MAERSK MONTE ALEGRE 608N", "route": "SSZ → PNJ", "etd": "01/Mar", "eta": "17/Mar", "status": "transit", "status_text": "Em trânsito"},
    {"op": "IMP-BMW E30", "booking": "Hapag-Lloyd", "container": "NNES8404834", "vessel": "Hapag-Lloyd", "route": "Hamburg → Santos", "etd": "A definir", "eta": "22-26d transit", "status": "loading", "status_text": "Cotação/Plan."},
    {"op": "1034-A-ON", "booking": "Allog/CME26003752", "container": "IKLZ7776576", "vessel": "—", "route": "BUE → Santos", "etd": "Dez/25", "eta": "~Jan/26", "status": "arrived", "status_text": "Retorno BR"},
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
