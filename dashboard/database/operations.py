from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, SQLModel, asc, create_engine, desc, select

from .models import Expense, ExpenseCreate


SORTABLE_COLUMNS = {
    "operation_date": Expense.operation_date,
    "value_date": Expense.value_date,
    "concept": Expense.concept,
    "amount": Expense.amount,
    "balance": Expense.balance,
    "category": Expense.category,
}


class DatabaseManager:
    def __init__(self, db_path: str = "expenses.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.create_tables()

    def create_tables(self) -> None:
        SQLModel.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        return Session(self.engine)

    def bulk_insert_with_dedupe(
        self, expenses: list[ExpenseCreate], file_source: str | None = None
    ) -> dict[str, int]:
        """Insert expenses skipping rows whose dedupe_hash already exists."""
        if not expenses:
            return {"inserted": 0, "skipped": 0}

        with self.get_session() as session:
            existing_hashes = set(
                session.exec(
                    select(Expense.dedupe_hash).where(
                        Expense.dedupe_hash.in_([e.dedupe_hash for e in expenses])  # type: ignore[attr-defined]
                    )
                ).all()
            )

            inserted = 0
            skipped = 0
            for expense in expenses:
                if expense.dedupe_hash in existing_hashes:
                    skipped += 1
                    continue
                payload = expense.model_dump()
                payload["file_source"] = file_source or payload.get("file_source")
                session.add(Expense(**payload))
                existing_hashes.add(expense.dedupe_hash)
                inserted += 1

            session.commit()
            return {"inserted": inserted, "skipped": skipped}

    def get_all_expenses(self, limit: int | None = None) -> list[Expense]:
        with self.get_session() as session:
            statement = select(Expense).order_by(desc(Expense.operation_date), desc(Expense.id))
            if limit:
                statement = statement.limit(limit)
            return list(session.exec(statement).all())

    def get_expenses_paginated(
        self,
        offset: int = 0,
        limit: int = 12,
        search: str | None = None,
        categories: list[str] | None = None,
        banks: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        amount_min: float | None = None,
        amount_max: float | None = None,
        flow: str = "all",  # "all" | "income" | "expense"
        sort: str = "operation_date",
        sort_dir: str = "desc",
    ) -> tuple[list[Expense], int]:
        """Server-side filtering/sorting/pagination. Returns (rows, total_count)."""
        with self.get_session() as session:
            statement = select(Expense)
            count_statement = select(func.count()).select_from(Expense)

            filters = []
            if search:
                like = f"%{search.lower()}%"
                filters.append(func.lower(Expense.concept).like(like))
            if categories:
                if "Sin categorizar" in categories:
                    rest = [c for c in categories if c != "Sin categorizar"]
                    if rest:
                        filters.append((Expense.category.is_(None)) | (Expense.category.in_(rest)))  # type: ignore[union-attr]
                    else:
                        filters.append(Expense.category.is_(None))
                else:
                    filters.append(Expense.category.in_(categories))  # type: ignore[union-attr]
            if banks:
                filters.append(Expense.bank_name.in_(banks))  # type: ignore[union-attr]
            if date_from:
                filters.append(Expense.operation_date >= date_from)
            if date_to:
                filters.append(Expense.operation_date <= date_to)
            if amount_min is not None:
                filters.append(Expense.amount >= amount_min)
            if amount_max is not None:
                filters.append(Expense.amount <= amount_max)
            if flow == "income":
                filters.append(Expense.amount > 0)
            elif flow == "expense":
                filters.append(Expense.amount < 0)

            for f in filters:
                statement = statement.where(f)
                count_statement = count_statement.where(f)

            sort_col = SORTABLE_COLUMNS.get(sort, Expense.operation_date)
            order = desc(sort_col) if sort_dir == "desc" else asc(sort_col)
            statement = statement.order_by(order, desc(Expense.id))
            statement = statement.offset(offset).limit(limit)

            rows = list(session.exec(statement).all())
            total = session.exec(count_statement).one()
            return rows, int(total)

    def get_uncategorized_expenses(self, limit: int = 500) -> list[Expense]:
        with self.get_session() as session:
            statement = (
                select(Expense)
                .where(Expense.is_categorized == False)  # noqa: E712
                .order_by(desc(Expense.id))
                .limit(limit)
            )
            return list(session.exec(statement).all())

    def update_category(
        self, expense_id: int, category: str | None, subcategory: str | None = None
    ) -> bool:
        with self.get_session() as session:
            expense = session.get(Expense, expense_id)
            if expense is None:
                return False
            expense.category = category
            expense.subcategory = subcategory
            expense.is_categorized = True
            session.add(expense)
            session.commit()
            return True

    def reset_categorization(self) -> int:
        """Mark every row as not categorized (forces full re-run)."""
        with self.get_session() as session:
            rows = list(session.exec(select(Expense)).all())
            for row in rows:
                row.is_categorized = False
            session.add_all(rows)
            session.commit()
            return len(rows)

    def delete_expense(self, expense_id: int) -> bool:
        with self.get_session() as session:
            expense = session.get(Expense, expense_id)
            if expense is None:
                return False
            session.delete(expense)
            session.commit()
            return True

    def clear_all_expenses(self) -> int:
        with self.get_session() as session:
            rows = list(session.exec(select(Expense)).all())
            count = len(rows)
            for row in rows:
                session.delete(row)
            session.commit()
            return count

    def get_unique_banks(self) -> list[str]:
        with self.get_session() as session:
            rows = session.exec(select(Expense.bank_name).distinct()).all()
            return sorted([r for r in rows if r])

    def get_unique_file_sources(self) -> list[str]:
        with self.get_session() as session:
            rows = session.exec(select(Expense.file_source).distinct()).all()
            return [r for r in rows if r]

    def get_category_breakdown(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        bank: str | None = None,
    ) -> list[dict[str, Any]]:
        """Aggregate spending (negative amounts) by category. Returns sorted list."""
        with self.get_session() as session:
            statement = select(Expense).where(Expense.amount < 0)
            if date_from:
                statement = statement.where(Expense.operation_date >= date_from)
            if date_to:
                statement = statement.where(Expense.operation_date <= date_to)
            if bank:
                statement = statement.where(Expense.bank_name == bank)
            rows = session.exec(statement).all()

            totals: dict[str, float] = defaultdict(float)
            for row in rows:
                key = row.category or "Sin categorizar"
                totals[key] += abs(row.amount)

            return [
                {"name": name, "value": round(total, 2)}
                for name, total in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
            ]

    def get_top_concepts(
        self,
        limit: int = 10,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        with self.get_session() as session:
            statement = select(Expense).where(Expense.amount < 0)
            if date_from:
                statement = statement.where(Expense.operation_date >= date_from)
            if date_to:
                statement = statement.where(Expense.operation_date <= date_to)
            rows = session.exec(statement).all()

            totals: dict[str, float] = defaultdict(float)
            counts: dict[str, int] = defaultdict(int)
            for row in rows:
                key = row.concept[:60]
                totals[key] += abs(row.amount)
                counts[key] += 1

            ordered = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:limit]
            return [
                {"concept": name, "total": round(total, 2), "count": counts[name]}
                for name, total in ordered
            ]

    def get_recent_expenses(self, limit: int = 8) -> list[Expense]:
        with self.get_session() as session:
            statement = (
                select(Expense)
                .order_by(desc(Expense.operation_date), desc(Expense.id))
                .limit(limit)
            )
            return list(session.exec(statement).all())


db_manager = DatabaseManager()
