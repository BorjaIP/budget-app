"""Create a synthetic SQLite database for UI development and screenshots.

Usage: python scripts/seed_demo_data.py <path-to-new-db>

Every concept, amount and date is invented. The script refuses to overwrite an
existing file and never reads the real database.
"""

import hashlib
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from dashboard.database.models import CategoryBudget, Expense
from dashboard.taxonomy import DEFAULT_TAXONOMY

# (category, subcategory, concepts, typical amount range, monthly occurrences)
SPENDING = [
    ("Gastos diarios", "Comida", ["Compra supermercado Los Olivos", "Frutería La Huerta", "Panadería San Roque"], (12, 95), 7),
    ("Gastos diarios", "Restaurantes", ["Restaurante El Rincón", "Cervecería La Plaza", "Taberna Casa Pepe"], (14, 62), 3),
    ("Gastos diarios", "Suscripciones", ["Suscripción música en streaming", "Suscripción vídeo bajo demanda"], (8, 16), 2),
    ("Transporte", "Combustible", ["Gasolinera Ribera", "Estación de servicio Norte"], (28, 70), 2),
    ("Transporte", "Transporte público", ["Abono transporte mensual"], (30, 40), 1),
    ("Vivienda", "Alquiler o hipoteca", ["Recibo alquiler piso"], (750, 750), 1),
    ("Servicios básicos", "Electricidad", ["Recibo luz Comercializadora Sol"], (38, 96), 1),
    ("Servicios básicos", "Internet", ["Recibo fibra Costa Telecom"], (39, 39), 1),
    ("Servicios básicos", "Calefacción o gas", ["Recibo gas Hogar Natural"], (18, 84), 1),
    ("Ocio", "Cine o teatro", ["Entradas Cine Aurora", "Teatro Municipal"], (9, 38), 1),
    ("Ocio", "Deporte", ["Cuota gimnasio Fénix"], (32, 32), 1),
    ("Salud/médicos", "Farmacia", ["Farmacia Central"], (6, 42), 1),
    ("Tecnología", "Servicios online", ["Almacenamiento en la nube anual", "Dominio y alojamiento web"], (11, 60), 1),
    ("Regalos", "Donativos (ONG)", ["Donativo ONG Horizonte"], (10, 20), 1),
    ("Educación", "Cursos", ["Curso de fotografía en línea"], (25, 90), 1),
]
INCOME = [("Transferencia nómina Empresa Faro", (2090, 2210)), ("Devolución compra Tienda Norte", (14, 80))]
BANKS = ["Banco Sierra", "Banco Costa"]
ANCHOR = date(2026, 10, 10)
MONTHS = 26


def month_start(anchor: date, back: int) -> date:
    year, month = anchor.year, anchor.month - back
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def build_rows(rng: random.Random) -> list[Expense]:
    assert all(c in DEFAULT_TAXONOMY and s in DEFAULT_TAXONOMY[c] for c, s, *_ in SPENDING)
    rows: list[Expense] = []
    for back in range(MONTHS - 1, -1, -1):
        start = month_start(ANCHOR, back)
        days = 28 if back else ANCHOR.day
        pay_day = min(27, days)
        rows.append(_row(rng, start + timedelta(days=pay_day - 1), INCOME[0][0], rng.uniform(*INCOME[0][1]), "Nómina", None))
        if rng.random() < 0.3:
            rows.append(_row(rng, start + timedelta(days=rng.randrange(days)), INCOME[1][0], rng.uniform(*INCOME[1][1]), None, None))
        for category, sub, concepts, (low, high), times in SPENDING:
            for _ in range(times):
                if times == 1 and len(concepts) == 1:  # a monthly bill arrives on the same day every month
                    day = start + timedelta(days=min(sum(map(ord, concepts[0])) % 27, days - 1))
                else:
                    day = start + timedelta(days=rng.randrange(days))
                rows.append(_row(rng, day, rng.choice(concepts), -rng.uniform(low, high), category, sub))
    rows.sort(key=lambda r: r.operation_date)
    balance = 3200.0
    for index, row in enumerate(rows):
        balance += row.amount
        row.balance = round(balance, 2)
        row.dedupe_hash = hashlib.sha1(f"demo-{index}-{row.operation_date}-{row.concept}-{row.amount}".encode()).hexdigest()
    return rows


def _row(rng: random.Random, day: date, concept: str, amount: float, category: str | None, sub: str | None) -> Expense:
    categorized = category is not None and rng.random() > 0.12
    source = ("manual" if rng.random() < 0.15 else "llm") if categorized else None
    return Expense(
        operation_date=day.isoformat(),
        value_date=(day + timedelta(days=rng.choice([0, 0, 1]))).isoformat(),
        concept=concept,
        amount=round(amount, 2),
        balance=0.0,
        category=category if categorized else None,
        subcategory=sub if categorized else None,
        bank_name=rng.choice(BANKS),
        is_categorized=categorized,
        category_source=source,
        category_confidence=round(rng.uniform(0.25, 0.99), 2) if source == "llm" else None,
        dedupe_hash="",
    )


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    target = Path(sys.argv[1])
    if target.exists():
        sys.exit(f"{target} already exists; refusing to overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{target}")
    SQLModel.metadata.create_all(engine)
    rows = build_rows(random.Random(20261010))
    with Session(engine) as session:
        session.add_all(rows)
        session.add_all(
            CategoryBudget(category=name, monthly_limit=limit)
            for name, limit in {"Vivienda": 800.0, "Gastos diarios": 350.0, "Ocio": 60.0, "Transporte": 200.0}.items()
        )
        session.commit()
    print(f"seeded {len(rows)} synthetic expenses into {target}")


if __name__ == "__main__":
    main()
