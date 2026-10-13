"""Stores the user's categories and subcategories and keeps everything that names them consistent.

Rules (see taxonomy.py): "Otros / General" is reserved; renaming follows through expenses, merchant labels and
budgets; deleting a subcategory leaves its expenses in the parent category; deleting a category moves its expenses
to Otros / General and drops its merchant labels and budget.
"""

from typing import Callable

from sqlalchemy import func
from sqlmodel import Session, select

from dashboard.taxonomy import (
    FALLBACK,
    OTHERS,
    OTHERS_SUB,
    CategoryEntry,
    SubEntry,
    Taxonomy,
    clean_description,
    clean_name,
    default_taxonomy,
)

from .models import Category, CategoryBudget, Expense, MerchantLabel, Subcategory


class TaxonomyError(ValueError):
    """A change the taxonomy does not allow; the message is meant for the user."""


class TaxonomyRepository:
    def __init__(self, get_session: Callable[[], Session]):
        self._session = get_session

    # ------------------------------------------------------------------ read
    def load(self) -> Taxonomy:
        with self._session() as session:
            if session.exec(select(func.count()).select_from(Category)).one() == 0:
                self._write(session, default_taxonomy())
                session.commit()
            return self._read(session)

    @staticmethod
    def _read(session: Session) -> Taxonomy:
        subs: dict[str, list[SubEntry]] = {}
        for sub in session.exec(select(Subcategory).order_by(Subcategory.position, Subcategory.id)).all():
            subs.setdefault(sub.category, []).append(SubEntry(sub.name, sub.description))
        return [
            CategoryEntry(c.name, c.description, subs.get(c.name, []))
            for c in session.exec(select(Category).order_by(Category.position, Category.name)).all()
        ]

    @staticmethod
    def _write(session: Session, taxonomy: Taxonomy) -> None:
        for position, category in enumerate(taxonomy):
            session.add(Category(name=category.name, description=category.description, position=position))
            for sub_position, sub in enumerate(category.subcategories):
                session.add(
                    Subcategory(
                        category=category.name, name=sub.name, description=sub.description, position=sub_position
                    )
                )

    # ------------------------------------------------------------------ add
    def add_category(self, name: str, description: str = "") -> None:
        name, description = clean_name(name), clean_description(description)
        with self._session() as session:
            self._ensure_seeded(session)
            if self._category(session, name) is not None:
                raise TaxonomyError(f"Ya existe la categoría «{name}»")
            position = session.exec(select(func.coalesce(func.max(Category.position), -1))).one() + 1
            session.add(Category(name=name, description=description, position=position))
            session.commit()

    def add_subcategory(self, category: str, name: str, description: str = "") -> None:
        name, description = clean_name(name), clean_description(description)
        with self._session() as session:
            self._ensure_seeded(session)
            if self._category(session, category) is None:
                raise TaxonomyError(f"No existe la categoría «{category}»")
            if self._subcategory(session, category, name) is not None:
                raise TaxonomyError(f"«{category}» ya tiene la subcategoría «{name}»")
            position = (
                session.exec(
                    select(func.coalesce(func.max(Subcategory.position), -1)).where(Subcategory.category == category)
                ).one()
                + 1
            )
            session.add(Subcategory(category=category, name=name, description=description, position=position))
            session.commit()

    # --------------------------------------------------------------- update
    def update_category(self, name: str, new_name: str | None = None, description: str | None = None) -> int:
        """Rename and/or describe a category. Returns how many expenses followed a rename."""
        with self._session() as session:
            self._ensure_seeded(session)
            category = self._category(session, name)
            if category is None:
                raise TaxonomyError(f"No existe la categoría «{name}»")
            if description is not None:
                category.description = clean_description(description)
            moved = 0
            if new_name is not None and clean_name(new_name) != name:
                new_name = clean_name(new_name)
                if name == OTHERS:
                    raise TaxonomyError(f"«{OTHERS}» es la categoría de reserva y no se puede renombrar")
                if self._category(session, new_name) is not None:
                    raise TaxonomyError(f"Ya existe la categoría «{new_name}»")
                moved = self._rename_category(session, category, new_name)
            else:
                session.add(category)
            session.commit()
            return moved

    def update_subcategory(
        self, category: str, name: str, new_name: str | None = None, description: str | None = None
    ) -> int:
        with self._session() as session:
            self._ensure_seeded(session)
            sub = self._subcategory(session, category, name)
            if sub is None:
                raise TaxonomyError(f"«{category}» no tiene la subcategoría «{name}»")
            if description is not None:
                sub.description = clean_description(description)
            moved = 0
            if new_name is not None and clean_name(new_name) != name:
                new_name = clean_name(new_name)
                if (category, name) == FALLBACK:
                    raise TaxonomyError(f"«{OTHERS} / {OTHERS_SUB}» es la reserva y no se puede renombrar")
                if self._subcategory(session, category, new_name) is not None:
                    raise TaxonomyError(f"«{category}» ya tiene la subcategoría «{new_name}»")
                moved = self._rename_subcategory(session, sub, new_name)
            session.add(sub)
            session.commit()
            return moved

    # --------------------------------------------------------------- delete
    def delete_subcategory(self, category: str, name: str) -> int:
        """Remove a subcategory; its expenses stay in the parent category. Returns how many expenses."""
        if (category, name) == FALLBACK:
            raise TaxonomyError(f"«{OTHERS} / {OTHERS_SUB}» es la reserva y no se puede borrar")
        with self._session() as session:
            self._ensure_seeded(session)
            sub = self._subcategory(session, category, name)
            if sub is None:
                raise TaxonomyError(f"«{category}» no tiene la subcategoría «{name}»")
            moved = 0
            for expense in session.exec(
                select(Expense).where(Expense.category == category, Expense.subcategory == name)
            ).all():
                expense.subcategory = None
                session.add(expense)
                moved += 1
            for label in session.exec(
                select(MerchantLabel).where(MerchantLabel.category == category, MerchantLabel.subcategory == name)
            ).all():
                label.subcategory = None
                session.add(label)
            session.delete(sub)
            session.commit()
            return moved

    def delete_category(self, name: str) -> int:
        """Remove a category with its subcategories; its expenses go to Otros / General. Returns how many."""
        if name == OTHERS:
            raise TaxonomyError(f"«{OTHERS}» es la categoría de reserva y no se puede borrar")
        with self._session() as session:
            self._ensure_seeded(session)
            category = self._category(session, name)
            if category is None:
                raise TaxonomyError(f"No existe la categoría «{name}»")
            moved = self._drop_category(session, name)
            session.delete(category)
            session.commit()
            return moved

    def reset_to_defaults(self) -> int:
        """Back to the owner's defaults. Expenses whose category disappears go to Otros / General."""
        with self._session() as session:
            for model in (Subcategory, Category):
                for row in session.exec(select(model)).all():
                    session.delete(row)
            session.flush()
            defaults = default_taxonomy()
            self._write(session, defaults)
            session.flush()
            valid = {c.name: {s.name for s in c.subcategories} for c in defaults}
            moved = 0
            for expense in session.exec(select(Expense).where(Expense.category.is_not(None))).all():  # type: ignore[union-attr]
                if expense.category not in valid:
                    expense.category, expense.subcategory = FALLBACK
                    moved += 1
                elif expense.subcategory and expense.subcategory not in valid[expense.category]:
                    expense.subcategory = None
                else:
                    continue
                session.add(expense)
            for label in session.exec(select(MerchantLabel)).all():
                if label.category not in valid:
                    session.delete(label)
                elif label.subcategory and label.subcategory not in valid[label.category]:
                    label.subcategory = None
                    session.add(label)
            for budget in session.exec(select(CategoryBudget)).all():
                if budget.category not in valid:
                    session.delete(budget)
            session.commit()
            return moved

    # -------------------------------------------------------------- helpers
    def _ensure_seeded(self, session: Session) -> None:
        if session.exec(select(func.count()).select_from(Category)).one() == 0:
            self._write(session, default_taxonomy())
            session.flush()

    @staticmethod
    def _category(session: Session, name: str) -> Category | None:
        return session.get(Category, name)

    @staticmethod
    def _subcategory(session: Session, category: str, name: str) -> Subcategory | None:
        return session.exec(
            select(Subcategory).where(Subcategory.category == category, Subcategory.name == name)
        ).first()

    def _rename_category(self, session: Session, category: Category, new_name: str) -> int:
        old = category.name
        moved = 0
        for expense in session.exec(select(Expense).where(Expense.category == old)).all():
            expense.category = new_name
            session.add(expense)
            moved += 1
        for label in session.exec(select(MerchantLabel).where(MerchantLabel.category == old)).all():
            label.category = new_name
            session.add(label)
        for sub in session.exec(select(Subcategory).where(Subcategory.category == old)).all():
            sub.category = new_name
            session.add(sub)
        budget = session.get(CategoryBudget, old)
        if budget is not None:  # the category name is the budget's primary key
            session.add(CategoryBudget(category=new_name, monthly_limit=budget.monthly_limit))
            session.delete(budget)
        session.add(Category(name=new_name, description=category.description, position=category.position))
        session.delete(category)
        session.flush()
        return moved

    @staticmethod
    def _rename_subcategory(session: Session, sub: Subcategory, new_name: str) -> int:
        old, moved = sub.name, 0
        for expense in session.exec(
            select(Expense).where(Expense.category == sub.category, Expense.subcategory == old)
        ).all():
            expense.subcategory = new_name
            session.add(expense)
            moved += 1
        for label in session.exec(
            select(MerchantLabel).where(MerchantLabel.category == sub.category, MerchantLabel.subcategory == old)
        ).all():
            label.subcategory = new_name
            session.add(label)
        sub.name = new_name
        return moved

    @staticmethod
    def _drop_category(session: Session, name: str) -> int:
        moved = 0
        for expense in session.exec(select(Expense).where(Expense.category == name)).all():
            expense.category, expense.subcategory = FALLBACK
            session.add(expense)
            moved += 1
        for label in session.exec(select(MerchantLabel).where(MerchantLabel.category == name)).all():
            session.delete(label)
        for sub in session.exec(select(Subcategory).where(Subcategory.category == name)).all():
            session.delete(sub)
        budget = session.get(CategoryBudget, name)
        if budget is not None:
            session.delete(budget)
        return moved
