from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_, text
from sqlmodel import Session, SQLModel, asc, create_engine, desc, select

from dashboard.config import settings

from .models import CategoryBudget, Expense, ExpenseCreate


SORTABLE_COLUMNS = {
    "operation_date": Expense.operation_date,
    "value_date": Expense.value_date,
    "concept": Expense.concept,
    "amount": Expense.amount,
    "balance": Expense.balance,
    "category": Expense.category,
}


class DatabaseManager:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or settings.database_url
        self._engine = None

    @property
    def engine(self):
        if self._engine is None:
            # Only create the parent directory for SQLite paths
            if self.database_url.startswith("sqlite:///"):
                db_path = self.database_url.replace("sqlite:///", "")
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)

            self._engine = create_engine(self.database_url)
            SQLModel.metadata.create_all(self._engine)
            self._migrate_schema()
        return self._engine

    def create_tables(self) -> None:
        SQLModel.metadata.create_all(self.engine)

    def _migrate_schema(self) -> None:
        """Guarded, additive migration for existing SQLite databases.

        `SQLModel.metadata.create_all()` only creates missing tables; it does
        not add new columns to a table that already exists. This repo has no
        Alembic, so add any newly-introduced columns here defensively.
        Only runs for SQLite — PostgreSQL uses create_all() for new tables and
        relies on schema upgrades being handled out-of-band.
        """
        if not self.database_url.startswith("sqlite:///"):
            return

        table_name = Expense.__tablename__
        with self.engine.connect() as conn:
            existing_columns = {
                row[1] for row in conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
            }
            if not existing_columns:
                # Table doesn't exist yet (fresh DB) - create_tables() above
                # already handles that case; nothing to migrate.
                return
            if "category_source" not in existing_columns:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN category_source TEXT"))
                conn.commit()

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
        self,
        expense_id: int,
        category: str | None,
        subcategory: str | None = None,
        source: str = "manual",
    ) -> bool:
        with self.get_session() as session:
            expense = session.get(Expense, expense_id)
            if expense is None:
                return False
            expense.category = category
            expense.subcategory = subcategory
            expense.is_categorized = True
            expense.category_source = source
            session.add(expense)
            session.commit()
            return True

    def get_manually_tagged_examples(self, limit: int = 8) -> list[dict[str, Any]]:
        """Recent user-corrected rows, for the LLM few-shot prompt builder."""
        with self.get_session() as session:
            statement = (
                select(Expense)
                .where(Expense.category_source == "manual")
                .where(Expense.category.is_not(None))  # type: ignore[union-attr]
                .order_by(desc(Expense.id))
                .limit(max(limit * 4, limit))
            )
            rows = session.exec(statement).all()
            return [
                {
                    "concept": row.concept,
                    "category": row.category,
                    "subcategory": row.subcategory,
                }
                for row in rows
            ]

    def reset_categorization(self) -> int:
        """Mark LLM-assigned/uncategorized rows as not categorized, to force
        a full re-run. Rows the user tagged by hand (category_source ==
        "manual") are preserved as-is — they are the ground truth the
        few-shot prompt builder relies on, and recategorizing would overwrite
        them with the LLM's own guess.
        """
        with self.get_session() as session:
            # Plain `!= "manual"` would silently exclude rows where
            # category_source IS NULL (SQL's NULL != 'manual' is NULL, not
            # true) — that's every row categorized before this field existed.
            statement = select(Expense).where(
                or_(Expense.category_source.is_(None), Expense.category_source != "manual")  # type: ignore[union-attr]
            )
            rows = list(session.exec(statement).all())
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

    def get_date_bounds(self) -> tuple[str | None, str | None]:
        """Return (earliest, latest) operation_date across all expenses."""
        with self.get_session() as session:
            dates = session.exec(select(Expense.operation_date)).all()
        if not dates:
            return None, None
        return min(dates), max(dates)

    def get_available_years(self) -> list[str]:
        """Distinct calendar years present in the data, newest first."""
        with self.get_session() as session:
            dates = session.exec(select(Expense.operation_date)).all()
        years = {d[:4] for d in dates if d}
        return sorted(years, reverse=True)

    def get_yearly_summary(self) -> list[dict[str, Any]]:
        """Aggregate ingresos/gastos/ahorro per calendar year."""
        with self.get_session() as session:
            rows = session.exec(select(Expense)).all()

        totals: dict[str, dict[str, float]] = defaultdict(lambda: {"ingresos": 0.0, "gastos": 0.0})
        for row in rows:
            year = row.operation_date[:4]
            if row.amount > 0:
                totals[year]["ingresos"] += row.amount
            else:
                totals[year]["gastos"] += abs(row.amount)

        result = []
        for year in sorted(totals.keys()):
            ingresos = totals[year]["ingresos"]
            gastos = totals[year]["gastos"]
            ahorro = ingresos - gastos
            rate = (ahorro / ingresos * 100) if ingresos > 0 else 0.0
            result.append(
                {
                    "year": year,
                    "ingresos": round(ingresos, 2),
                    "gastos": round(gastos, 2),
                    "ahorro": round(ahorro, 2),
                    "savings_rate": round(rate, 1),
                }
            )
        return result

    def get_flow_totals(
        self, date_from: str | None = None, date_to: str | None = None
    ) -> dict[str, float]:
        """Total income and spending (positive numbers) within an optional date range."""
        with self.get_session() as session:
            statement = select(Expense.amount)
            if date_from:
                statement = statement.where(Expense.operation_date >= date_from)
            if date_to:
                statement = statement.where(Expense.operation_date <= date_to)
            amounts = session.exec(statement).all()
        return {
            "ingresos": round(sum(a for a in amounts if a > 0), 2),
            "gastos": round(sum(-a for a in amounts if a < 0), 2),
        }

    def count_existing_hashes(self, hashes: list[str]) -> int:
        """How many of these dedupe hashes are already stored."""
        if not hashes:
            return 0
        with self.get_session() as session:
            statement = (
                select(func.count())
                .select_from(Expense)
                .where(Expense.dedupe_hash.in_(hashes))  # type: ignore[attr-defined]
            )
            return int(session.exec(statement).one())

    def get_budgets(self) -> dict[str, float]:
        with self.get_session() as session:
            return {b.category: b.monthly_limit for b in session.exec(select(CategoryBudget)).all()}

    def set_budget(self, category: str, monthly_limit: float | None) -> None:
        """Store the monthly limit of a category; a missing or non-positive limit removes it."""
        with self.get_session() as session:
            budget = session.get(CategoryBudget, category)
            if monthly_limit is None or monthly_limit <= 0:
                if budget is not None:
                    session.delete(budget)
            elif budget is None:
                session.add(CategoryBudget(category=category, monthly_limit=monthly_limit))
            else:
                budget.monthly_limit = monthly_limit
                session.add(budget)
            session.commit()

    def count_uncategorized(self) -> int:
        with self.get_session() as session:
            statement = select(func.count()).select_from(Expense).where(Expense.category.is_(None))  # type: ignore[union-attr]
            return int(session.exec(statement).one())

    def get_recent_expenses(self, limit: int = 8) -> list[Expense]:
        with self.get_session() as session:
            statement = (
                select(Expense)
                .order_by(desc(Expense.operation_date), desc(Expense.id))
                .limit(limit)
            )
            return list(session.exec(statement).all())


db_manager = DatabaseManager()
