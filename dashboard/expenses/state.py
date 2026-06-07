from datetime import datetime
from pathlib import Path
from typing import List

import reflex as rx

from dashboard.database.operations import db_manager
from dashboard.expenses.model import Item
from dashboard.utils.file_processor import file_processor


def _format_currency(value: float) -> str:
    formatted = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "-" if value < 0 else ""
    return f"{sign}{formatted} €"


def _humanize_date(iso: str) -> str:
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return iso


def _to_item(expense) -> Item:
    amount = float(expense.amount)
    balance = float(expense.balance)
    return Item(
        id=expense.id or 0,
        operation_date=expense.operation_date,
        operation_date_human=_humanize_date(expense.operation_date),
        value_date=expense.value_date,
        concept=expense.concept,
        amount=amount,
        amount_fmt=_format_currency(amount),
        balance=balance,
        balance_fmt=_format_currency(balance),
        is_expense=amount < 0,
        category=expense.category,
        subcategory=expense.subcategory,
        bank_name=expense.bank_name,
        is_categorized=bool(expense.is_categorized),
    )


class TableState(rx.State):
    items: List[Item] = []
    items_list: List[str] = []

    search_value: str = ""
    sort_value: str = "operation_date"
    sort_reverse: bool = True  # newest first by default

    total_items: int = 0
    offset: int = 0
    limit: int = 12

    upload_status: str = ""
    is_uploading: bool = False
    show_upload_modal: bool = False
    pending_bank_name: str = ""

    is_loading: bool = False
    is_categorizing: bool = False
    categorization_progress: int = 0
    categorization_total: int = 0

    selected_categories: list[str] = []
    selected_banks: list[str] = []
    date_from: str = ""
    date_to: str = ""
    amount_min: str = ""
    amount_max: str = ""
    flow_filter: str = "all"  # all | income | expense

    @rx.var(cache=True)
    def filtered_count(self) -> int:
        return self.total_items

    @rx.var(cache=True)
    def page_number(self) -> int:
        if self.total_items == 0:
            return 1
        return (self.offset // self.limit) + 1

    @rx.var(cache=True)
    def total_pages(self) -> int:
        if self.total_items == 0:
            return 1
        return (self.total_items + self.limit - 1) // self.limit

    @rx.var(cache=True)
    def has_filters(self) -> bool:
        return bool(
            self.search_value
            or self.selected_categories
            or self.selected_banks
            or self.date_from
            or self.date_to
            or self.amount_min
            or self.amount_max
            or self.flow_filter != "all"
        )

    @rx.var(cache=True)
    def category_filter_label(self) -> str:
        if not self.selected_categories:
            return "Categorías"
        return f"Categorías ({len(self.selected_categories)})"

    @rx.var(cache=True)
    def bank_filter_label(self) -> str:
        if not self.selected_banks:
            return "Banco"
        return f"Banco ({len(self.selected_banks)})"

    @rx.var(cache=True)
    def categorization_label(self) -> str:
        return f"Categorizando con IA… {self.categorization_progress} / {self.categorization_total}"

    @rx.var(cache=True)
    def categorization_progress_pct(self) -> int:
        if self.categorization_total <= 0:
            return 0
        return min(100, int(self.categorization_progress * 100 / self.categorization_total))

    @rx.var(cache=True)
    def is_empty(self) -> bool:
        return self.total_items == 0 and not self.has_filters

    @rx.var(cache=True)
    def upload_stats(self) -> str:
        try:
            total = len(db_manager.get_all_expenses(limit=10_000))
            files = db_manager.get_unique_file_sources()
            return f"BD: {total} movimientos en {len(files)} archivos"
        except Exception:
            return "BD: sin datos"

    @rx.var(cache=True)
    def available_banks(self) -> list[str]:
        try:
            return db_manager.get_unique_banks()
        except Exception:
            return []

    def _safe_float(self, value: str) -> float | None:
        if not value:
            return None
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None

    def load_entries_from_database(self):
        self.is_loading = True
        try:
            rows, total = db_manager.get_expenses_paginated(
                offset=self.offset,
                limit=self.limit,
                search=self.search_value or None,
                categories=self.selected_categories or None,
                banks=self.selected_banks or None,
                date_from=self.date_from or None,
                date_to=self.date_to or None,
                amount_min=self._safe_float(self.amount_min),
                amount_max=self._safe_float(self.amount_max),
                flow=self.flow_filter,
                sort=self.sort_value,
                sort_dir="desc" if self.sort_reverse else "asc",
            )
            self.items = [_to_item(r) for r in rows]
            self.total_items = total
            self.items_list = [
                "operation_date",
                "value_date",
                "concept",
                "amount",
                "balance",
                "category",
            ]
            if self.offset >= max(self.total_items, 1):
                self.offset = 0
        except Exception as exc:
            self.items = []
            self.total_items = 0
            return rx.toast.error(f"Error cargando movimientos: {exc}")
        finally:
            self.is_loading = False

    def prev_page(self):
        if self.page_number > 1:
            self.offset -= self.limit
            return TableState.load_entries_from_database

    def next_page(self):
        if self.page_number < self.total_pages:
            self.offset += self.limit
            return TableState.load_entries_from_database

    def first_page(self):
        self.offset = 0
        return TableState.load_entries_from_database

    def last_page(self):
        self.offset = (self.total_pages - 1) * self.limit
        return TableState.load_entries_from_database

    def set_search(self, value: str):
        self.search_value = value
        self.offset = 0
        return TableState.load_entries_from_database

    def set_sort_value(self, value: str):
        self.sort_value = value or "operation_date"
        self.offset = 0
        return TableState.load_entries_from_database

    def toggle_sort(self):
        self.sort_reverse = not self.sort_reverse
        return TableState.load_entries_from_database

    def set_selected_categories(self, values: list[str]):
        self.selected_categories = values
        self.offset = 0
        return TableState.load_entries_from_database

    def toggle_category(self, category: str):
        if category in self.selected_categories:
            self.selected_categories = [c for c in self.selected_categories if c != category]
        else:
            self.selected_categories = [*self.selected_categories, category]
        self.offset = 0
        return TableState.load_entries_from_database

    def toggle_bank(self, bank: str):
        if bank in self.selected_banks:
            self.selected_banks = [b for b in self.selected_banks if b != bank]
        else:
            self.selected_banks = [*self.selected_banks, bank]
        self.offset = 0
        return TableState.load_entries_from_database

    def set_date_from(self, value: str):
        self.date_from = value
        self.offset = 0
        return TableState.load_entries_from_database

    def set_date_to(self, value: str):
        self.date_to = value
        self.offset = 0
        return TableState.load_entries_from_database

    def set_amount_min(self, value: str):
        self.amount_min = value
        self.offset = 0
        return TableState.load_entries_from_database

    def set_amount_max(self, value: str):
        self.amount_max = value
        self.offset = 0
        return TableState.load_entries_from_database

    def set_flow_filter(self, value: str | list[str]):
        normalized = value if isinstance(value, str) else (value[0] if value else "all")
        self.flow_filter = normalized or "all"
        self.offset = 0
        return TableState.load_entries_from_database

    def clear_filters(self):
        self.search_value = ""
        self.selected_categories = []
        self.selected_banks = []
        self.date_from = ""
        self.date_to = ""
        self.amount_min = ""
        self.amount_max = ""
        self.flow_filter = "all"
        self.offset = 0
        return TableState.load_entries_from_database

    def update_expense_category(self, expense_id: int, category: str, subcategory: str = ""):
        ok = db_manager.update_category(expense_id, category, subcategory or None)
        if not ok:
            return rx.toast.error("No se pudo actualizar la categoría")
        return [
            TableState.load_entries_from_database,
            rx.toast.success(f"Categoría actualizada a {category}"),
        ]

    def delete_expense(self, expense_id: int):
        ok = db_manager.delete_expense(expense_id)
        if not ok:
            return rx.toast.error("No se pudo borrar el movimiento")
        return [
            TableState.load_entries_from_database,
            rx.toast.success("Movimiento borrado"),
        ]

    async def handle_upload(self, files: list[rx.UploadFile]):
        if not files:
            self.upload_status = "Sin archivo seleccionado"
            return
        self.is_uploading = True
        self.upload_status = "Procesando archivo..."
        try:
            for file in files:
                if not file.filename:
                    self.upload_status = "❌ Archivo inválido"
                    continue
                if not file.filename.lower().endswith((".xls", ".xlsx")):
                    self.upload_status = "❌ Sólo se aceptan archivos .xls o .xlsx"
                    continue

                upload_data = await file.read()
                outfile = rx.get_upload_dir() / Path(file.filename).name
                outfile.parent.mkdir(parents=True, exist_ok=True)
                outfile.write_bytes(upload_data)

                bank = self.pending_bank_name.strip() or None
                result = file_processor.process_excel_file(str(outfile), bank_name=bank)

                if result["status"] == "success":
                    self.upload_status = f"✅ {result['message']}"
                    self.show_upload_modal = False
                    self.pending_bank_name = ""
                    self.offset = 0
                    self.load_entries_from_database()
                    try:
                        outfile.unlink()
                    except OSError:
                        pass
                    yield rx.toast.success(result["message"])
                    yield TableState.categorize_pending_expenses
                else:
                    self.upload_status = f"❌ {result['message']}"
                    yield rx.toast.error(result["message"])
        except Exception as exc:
            self.upload_status = f"❌ Error: {exc}"
            yield rx.toast.error(str(exc))
        finally:
            self.is_uploading = False

    @rx.event(background=True)
    async def categorize_pending_expenses(self):
        from dashboard.llm.llm_call import categorize_expense

        async with self:
            self.is_categorizing = True
            self.categorization_progress = 0
            pending = db_manager.get_uncategorized_expenses(limit=500)
            self.categorization_total = len(pending)

        if not pending:
            async with self:
                self.is_categorizing = False
            return

        for index, expense in enumerate(pending):
            try:
                category, subcategory = await categorize_expense(expense.concept)
            except Exception as exc:
                async with self:
                    self.is_categorizing = False
                yield rx.toast.warning(
                    f"Ollama no disponible ({exc.__class__.__name__}); las filas restantes "
                    "quedan sin categorizar."
                )
                return

            db_manager.update_category(expense.id, category, subcategory)

            async with self:
                self.categorization_progress = index + 1
                if (index + 1) % 5 == 0 or (index + 1) == len(pending):
                    self.load_entries_from_database()

        async with self:
            self.is_categorizing = False
            self.load_entries_from_database()

    def force_recategorize(self):
        count = db_manager.reset_categorization()
        if count == 0:
            return rx.toast.info("No hay movimientos para recategorizar")
        return [
            rx.toast.info(f"Recategorizando {count} movimientos…"),
            TableState.categorize_pending_expenses,
        ]

    def open_upload_modal(self):
        self.upload_status = ""
        self.pending_bank_name = ""
        self.show_upload_modal = True
        return rx.clear_selected_files("upload-excel")

    def close_upload_modal(self):
        self.show_upload_modal = False

    def set_pending_bank_name(self, value: str):
        self.pending_bank_name = value

    def export_csv(self):
        import csv
        import io

        rows, _ = db_manager.get_expenses_paginated(
            offset=0,
            limit=100_000,
            search=self.search_value or None,
            categories=self.selected_categories or None,
            banks=self.selected_banks or None,
            date_from=self.date_from or None,
            date_to=self.date_to or None,
            amount_min=self._safe_float(self.amount_min),
            amount_max=self._safe_float(self.amount_max),
            flow=self.flow_filter,
            sort=self.sort_value,
            sort_dir="desc" if self.sort_reverse else "asc",
        )

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "operation_date",
                "value_date",
                "concept",
                "amount",
                "balance",
                "category",
                "subcategory",
                "bank_name",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r.operation_date,
                    r.value_date,
                    r.concept,
                    f"{r.amount:.2f}",
                    f"{r.balance:.2f}",
                    r.category or "",
                    r.subcategory or "",
                    r.bank_name or "",
                ]
            )
        filename = f"gastos_{datetime.now().strftime('%Y%m%d')}.csv"
        return rx.download(data=buf.getvalue().encode("utf-8"), filename=filename)
