"""One-shot migration from the v1 schema (string amount/balance, dd/mm/yyyy dates)
to the v2 schema (float amount/balance, ISO dates, dedupe_hash, bank_name, etc.).

Usage:
    python scripts/migrate_v2.py [old_db] [new_db]

Default paths: old=data/expenses.db, new=data/expenses_v2.db.

After running:
    mv data/expenses.db data/expenses.db.v1.bak
    mv data/expenses_v2.db data/expenses.db
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dashboard.database.models import Expense, ExpenseCreate  # noqa: E402
from dashboard.database.operations import DatabaseManager  # noqa: E402
from dashboard.utils.file_reader import (  # noqa: E402
    compute_dedupe_hash,
    european_to_float,
    infer_bank_from_filename,
    to_iso_date,
)


def migrate(old_db: str = "data/expenses.db", new_db: str = "data/expenses_v2.db") -> None:
    old_path = Path(old_db)
    new_path = Path(new_db)
    if not old_path.exists():
        print(f"[migrate] no old database at {old_db}, nothing to migrate")
        return
    if new_path.exists():
        print(f"[migrate] removing stale {new_db}")
        new_path.unlink()

    target = DatabaseManager(str(new_path))

    conn = sqlite3.connect(old_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT operation_date, value_date, concept, amount, salary, "
        "category, file_source, created_at FROM expense"
    )

    seen: set[str] = set()
    converted: list[ExpenseCreate] = []
    skipped_invalid = 0
    skipped_duplicate = 0

    for row in cursor.fetchall():
        op_date = to_iso_date(row["operation_date"])
        val_date = to_iso_date(row["value_date"]) or op_date
        concept = (row["concept"] or "").strip()
        amount = european_to_float(row["amount"])
        balance = european_to_float(row["salary"])
        if not op_date or amount is None or balance is None or not concept:
            skipped_invalid += 1
            continue

        bank = infer_bank_from_filename(row["file_source"] or "")
        dedupe = compute_dedupe_hash(op_date, amount, concept, bank)
        if dedupe in seen:
            skipped_duplicate += 1
            continue
        seen.add(dedupe)

        category = row["category"]
        converted.append(
            ExpenseCreate(
                operation_date=op_date,
                value_date=val_date,
                concept=concept,
                amount=amount,
                balance=balance,
                category=category,
                is_categorized=bool(category),
                bank_name=bank,
                dedupe_hash=dedupe,
                file_source=row["file_source"],
            )
        )

    conn.close()

    result = target.bulk_insert_with_dedupe(converted)
    print(
        f"[migrate] inserted={result['inserted']} "
        f"skipped_in_db={result['skipped']} "
        f"skipped_invalid={skipped_invalid} "
        f"skipped_duplicate_in_source={skipped_duplicate}"
    )
    print(f"[migrate] new database written to {new_path}")
    print("[migrate] next: mv data/expenses.db data/expenses.db.v1.bak && "
          "mv data/expenses_v2.db data/expenses.db")


if __name__ == "__main__":
    old = sys.argv[1] if len(sys.argv) > 1 else "data/expenses.db"
    new = sys.argv[2] if len(sys.argv) > 2 else "data/expenses_v2.db"
    migrate(old, new)
