import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List

import reflex as rx

from dashboard.config import settings as app_settings
from dashboard.database.operations import db_manager
from dashboard.expenses.model import Item
from dashboard.llm.merchant import merchant_key
from dashboard.taxonomy import NO_SUBCATEGORY
from dashboard.utils.file_processor import file_processor

logger = logging.getLogger(__name__)

# Categorization before the last "Recategorizar", per browser session. Kept out of the
# reactive state because it can hold thousands of rows that must not travel to the client.
_UNDO_SNAPSHOTS: dict[str, list[tuple]] = {}


def _format_currency(value: float) -> str:
    formatted = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "-" if value < 0 else ""
    return f"{sign}{formatted} €"


def _humanize_date(iso: str) -> str:
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return iso


def highlight_segments(text: str, term: str) -> list[dict]:
    """Split `text` into pieces flagged `m` when they match `term` (case-insensitive)."""
    if not term:
        return [{"t": text, "m": False}]
    lower, needle = text.lower(), term.lower()
    pieces, start = [], 0
    while (hit := lower.find(needle, start)) != -1:
        if hit > start:
            pieces.append({"t": text[start:hit], "m": False})
        pieces.append({"t": text[hit : hit + len(needle)], "m": True})
        start = hit + len(needle)
    if start < len(text):
        pieces.append({"t": text[start:], "m": False})
    return pieces or [{"t": text, "m": False}]


def source_text(source: str | None, confidence: float | None) -> str:
    """How a transaction got its category, in words the user understands."""
    if source == "manual":
        return "Categorizada por ti"
    if source == "memory":
        return "Regla aprendida de tus correcciones"
    if source == "similar":
        pct = f" ({confidence * 100:.0f} % parecida)" if confidence else ""
        return "Parecida a otra que ya etiquetaste" + pct
    if source == "llm":
        pct = f" (confianza {confidence * 100:.0f} %)" if confidence else ""
        return "Modelo local" + pct
    return "Sin categorizar"


def _to_item(expense, search: str = "") -> Item:
    amount = float(expense.amount)
    balance = float(expense.balance)
    return Item(
        id=expense.id or 0,
        operation_date=expense.operation_date,
        operation_date_human=_humanize_date(expense.operation_date),
        value_date=expense.value_date,
        concept=expense.concept,
        amount=amount,
        amount_fmt=("+" if amount > 0 else "") + _format_currency(amount),
        balance=balance,
        balance_fmt=_format_currency(balance),
        is_expense=amount < 0,
        category=expense.category,
        subcategory=expense.subcategory,
        bank_name=expense.bank_name,
        is_categorized=bool(expense.is_categorized),
        source=expense.category_source,
        note=expense.note or "",
        value_date_human=_humanize_date(expense.value_date),
        source_text=source_text(expense.category_source, expense.category_confidence),
        needs_review=(
            expense.category_source == "llm"
            and expense.category_confidence is not None
            and expense.category_confidence < app_settings.llm_confidence_threshold
        ),
        concept_segments=highlight_segments(expense.concept, search.strip()),
    )


def _one_per_merchant(expenses: list) -> list[Item]:
    """Review list: the most doubtful movement of each merchant, with how many share it."""
    groups: dict[str, list] = {}
    for expense in expenses:  # already ordered most doubtful first
        groups.setdefault(merchant_key(expense.concept) or f"id-{expense.id}", []).append(expense)
    items = []
    for group in groups.values():
        item = _to_item(group[0])
        item.repeat_count = len(group)
        items.append(item)
    return items


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
    upload_error: bool = False
    is_uploading: bool = False
    show_upload_modal: bool = False
    pending_bank_name: str = ""
    preview_ready: bool = False
    preview_path: str = ""
    preview_new: int = 0
    preview_duplicates: int = 0
    preview_range: str = ""
    preview_income_fmt: str = ""
    preview_spending_fmt: str = ""

    is_loading: bool = False
    is_categorizing: bool = False
    categorization_progress: int = 0
    categorization_total: int = 0
    can_undo_recategorize: bool = False
    has_results: bool = False
    show_results: bool = False
    results_total: int = 0
    results_memory: int = 0
    results_similar: int = 0
    results_high: int = 0
    results_mid: int = 0
    results_low: int = 0
    results_average: str = "-"
    review_items: list[Item] = []
    show_recategorize_dialog: bool = False
    recategorize_auto_count: int = 0
    recategorize_manual_count: int = 0
    selected_ids: list[int] = []
    show_detail: bool = False
    detail: Item = Item()
    detail_note: str = ""

    selected_categories: list[str] = []
    selected_banks: list[str] = []
    date_from: str = ""
    date_to: str = ""
    amount_min: str = ""
    amount_max: str = ""
    flow_filter: str = "all"  # all | income | expense
    review_only: bool = False

    @rx.var(cache=True)
    def selected_count(self) -> int:
        return len(self.selected_ids)

    @rx.var(cache=True)
    def page_all_selected(self) -> bool:
        return bool(self.items) and all(item.id in self.selected_ids for item in self.items)

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
            or self.review_only
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
                review_only=self.review_only,
                sort=self.sort_value,
                sort_dir="desc" if self.sort_reverse else "asc",
            )
            self.items = [_to_item(r, self.search_value) for r in rows]
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
        except Exception:
            logger.exception("Could not load the expenses")
            self.items = []
            self.total_items = 0
            return rx.toast.error("No se pudieron cargar los movimientos")
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

    def drill_down(self, category: str, date_from: str, date_to: str, flow: str):
        """Arrive from the overview with a category and period already applied."""
        self.search_value = ""
        self.selected_categories = [category]
        self.selected_banks = []
        self.date_from = date_from
        self.date_to = date_to
        self.amount_min = ""
        self.amount_max = ""
        self.flow_filter = flow
        self.review_only = False
        self.offset = 0
        return TableState.load_entries_from_database

    def drill_down_review(self):
        """Arrive from the overview with only the movements that need a human look."""
        self.drill_down("", "", "", "all")
        self.selected_categories = []
        self.review_only = True
        return TableState.load_entries_from_database

    def drill_down_search(self, text: str, date_from: str, date_to: str):
        """Arrive from the overview with a concept search and period already applied."""
        self.drill_down("", date_from, date_to, "expense")
        self.selected_categories = []
        self.search_value = text
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

    # -------------------------------------------------------------- detail
    def open_detail(self, expense_id: int):
        self._load_detail(expense_id)
        self.show_detail = self.detail.id == expense_id

    def _load_detail(self, expense_id: int):
        expense = db_manager.get_expense(expense_id)
        if expense is not None:
            self.detail = _to_item(expense)
            self.detail_note = self.detail.note

    @rx.event
    def set_show_detail(self, value: bool):
        self.show_detail = value

    @rx.event
    def set_detail_note(self, value: str):
        self.detail_note = value

    @rx.var(cache=True)
    def detail_note_changed(self) -> bool:
        return self.detail_note.strip() != self.detail.note

    def save_note(self):
        if not db_manager.update_note(self.detail.id, self.detail_note):
            return rx.toast.error("No se pudo guardar la nota")
        self._load_detail(self.detail.id)
        self.load_entries_from_database()
        return rx.toast.success("Nota guardada")

    def toggle_selected(self, expense_id: int):
        if expense_id in self.selected_ids:
            self.selected_ids = [i for i in self.selected_ids if i != expense_id]
        else:
            self.selected_ids = [*self.selected_ids, expense_id]

    def toggle_page_selection(self):
        page_ids = [item.id for item in self.items]
        if page_ids and all(i in self.selected_ids for i in page_ids):
            self.selected_ids = [i for i in self.selected_ids if i not in page_ids]
        else:
            self.selected_ids = [*self.selected_ids, *[i for i in page_ids if i not in self.selected_ids]]

    def clear_selection(self):
        self.selected_ids = []

    def apply_bulk_category(self, category: str):
        """Tag every selected movement by hand; manual tags feed the few-shot prompt."""
        if not self.selected_ids or not category:
            return
        done, applied = 0, 0
        for expense_id in self.selected_ids:
            if db_manager.update_category(expense_id, category, None, source="manual"):
                done += 1
                applied += db_manager.learn_from_correction(expense_id)
        self.selected_ids = []
        self.load_entries_from_database()
        message = f"{done} movimientos asignados a {category}"
        if applied:
            message += f" y {applied} más del mismo comercio"
        return rx.toast.success(message)

    def update_expense_category(self, expense_id: int, category: str, subcategory: str = ""):
        subcategory = "" if subcategory == NO_SUBCATEGORY else subcategory
        ok = db_manager.update_category(expense_id, category, subcategory or None, source="manual")
        if not ok:
            return rx.toast.error("No se pudo actualizar la categoría")
        applied = db_manager.learn_from_correction(expense_id)
        self._drop_reviewed(expense_id)
        if self.show_detail and self.detail.id == expense_id:
            self._load_detail(expense_id)
        message = f"Categoría actualizada a {category}"
        if applied:
            message += f" y aplicada a {applied} movimientos del mismo comercio"
        return [TableState.load_entries_from_database, rx.toast.success(message)]

    def delete_expense(self, expense_id: int):
        ok = db_manager.delete_expense(expense_id)
        if not ok:
            return rx.toast.error("No se pudo borrar el movimiento")
        return [
            TableState.load_entries_from_database,
            rx.toast.success("Movimiento borrado"),
        ]

    async def handle_preview(self, files: list[rx.UploadFile]):
        """Parse the chosen file and show what an import would do, without storing anything."""
        self._reset_preview()
        if not files:
            self.upload_status = "Sin archivo seleccionado"
            self.upload_error = True
            return
        file = files[0]
        if not file.filename or not file.filename.lower().endswith((".xls", ".xlsx")):
            self.upload_status = "Sólo se aceptan archivos .xls o .xlsx"
            self.upload_error = True
            return
        self.is_uploading = True
        self.upload_error = False
        self.upload_status = ""
        try:
            outfile = rx.get_upload_dir() / Path(file.filename).name
            outfile.parent.mkdir(parents=True, exist_ok=True)
            outfile.write_bytes(await file.read())
            preview = file_processor.preview_excel_file(
                str(outfile), bank_name=self.pending_bank_name.strip() or None
            )
            if preview["status"] != "success":
                outfile.unlink(missing_ok=True)
                self.upload_status = preview["message"]
                self.upload_error = True
                return
            self.preview_path = str(outfile)
            self.preview_new = preview["new"]
            self.preview_duplicates = preview["duplicates"]
            self.preview_range = (
                f"{_humanize_date(preview['date_from'])} a {_humanize_date(preview['date_to'])}"
            )
            self.preview_income_fmt = _format_currency(preview["income"])
            self.preview_spending_fmt = _format_currency(preview["spending"])
            self.preview_ready = True
        except Exception:
            logger.exception("Could not read the uploaded file")
            self.upload_status = "No se pudo leer el archivo. Comprueba que sea un extracto válido."
            self.upload_error = True
        finally:
            self.is_uploading = False

    def _reset_preview(self):
        if self.preview_path:
            Path(self.preview_path).unlink(missing_ok=True)
        self.preview_ready = False
        self.preview_path = ""
        self.preview_new = 0
        self.preview_duplicates = 0
        self.preview_range = ""
        self.preview_income_fmt = ""
        self.preview_spending_fmt = ""

    def discard_preview(self):
        self._reset_preview()
        self.upload_status = ""
        self.upload_error = False
        return rx.clear_selected_files("upload-excel")

    def confirm_import(self):
        """Store the previewed file (duplicates are skipped) and categorize the new rows."""
        if not self.preview_path:
            return
        self.is_uploading = True
        try:
            result = file_processor.process_excel_file(
                self.preview_path, bank_name=self.pending_bank_name.strip() or None
            )
        except Exception:
            logger.exception("Could not import the file")
            self.is_uploading = False
            return rx.toast.error("No se pudo importar el archivo")
        self.is_uploading = False
        if result["status"] != "success":
            self.upload_status = result["message"]
            self.upload_error = True
            return rx.toast.error(result["message"])
        self._reset_preview()
        self.show_upload_modal = False
        self.pending_bank_name = ""
        self.offset = 0
        self.upload_status = ""
        self.load_entries_from_database()
        return [rx.toast.success(result["message"]), TableState.categorize_pending_expenses]

    @rx.event(background=True)
    async def categorize_pending_expenses(self):
        """Categorize pending movements in the background, cheapest method first.

        1. merchant memory (exact merchant the user already corrected), 2. very similar labeled
        movement, 3. the local model with the most similar labeled examples. Blocking database
        work runs in threads so the app stays usable on every page while this goes on.
        """
        from dashboard.llm.llm_call import categorize_with_confidence
        from dashboard.llm.retrieval import SimilarityIndex, confident_match
        from dashboard.taxonomy import for_amount
        from dashboard.llm.run_stats import RunStats

        stats = RunStats()
        run_ids: list[int] = []

        async with self:
            self.is_categorizing = True
            self.categorization_progress = 0
            self.has_results = False
            pending = await asyncio.to_thread(db_manager.get_uncategorized_expenses, 500)
            self.categorization_total = len(pending)
        learned = await asyncio.to_thread(db_manager.sync_merchant_memory)
        labels = await asyncio.to_thread(db_manager.get_merchant_labels)
        taxonomy = await asyncio.to_thread(db_manager.taxonomy.load)
        index = SimilarityIndex(labels)
        logger.info("categorization run started: %d movements pending (%d labels backfilled)", len(pending), learned)

        if not pending:
            async with self:
                self.is_categorizing = False
            return

        assigned = 0
        for position, expense in enumerate(pending):
            started = time.perf_counter()
            allowed = {c.name for c in for_amount(taxonomy, expense.amount)}  # income vs expense categories
            remembered = await asyncio.to_thread(db_manager.get_merchant_label, merchant_key(expense.concept))
            if remembered and remembered["category"] not in allowed:
                remembered = None
            match = None if remembered else confident_match(index.search(expense.concept, 3))
            if match and match[1]["category"] not in allowed:
                match = None
            if remembered:  # the user already taught the app this merchant: same answer every time
                stats.record_memory()
                await asyncio.to_thread(
                    db_manager.update_category,
                    expense.id, remembered["category"], remembered["subcategory"], "memory",
                )
            elif match:  # looks almost exactly like something the user labeled
                score, label = match
                stats.record_similar()
                await asyncio.to_thread(
                    db_manager.update_category,
                    expense.id, label["category"], label["subcategory"], "similar", score,
                )
            else:
                try:
                    category, subcategory, confidence = await categorize_with_confidence(
                        expense.concept, taxonomy, labels=labels, index=index, amount=expense.amount
                    )
                except Exception:
                    stats.record_error()
                    logger.exception("The local model is not available")
                    logger.info(stats.summary())
                    async with self:
                        self.is_categorizing = False
                    yield rx.toast.warning(
                        "El modelo local no está disponible. Las filas restantes quedan sin categorizar."
                    )
                    return
                stats.record(category, subcategory, (time.perf_counter() - started) * 1000, confidence)
                await asyncio.to_thread(
                    db_manager.update_category,
                    expense.id, category, subcategory, "llm", confidence if confidence is not None else 0.0,
                )
            assigned += 1
            run_ids.append(expense.id)

            async with self:
                self.categorization_progress = position + 1
                if (position + 1) % 10 == 0:
                    self.load_entries_from_database()

        doubtful = await asyncio.to_thread(db_manager.get_expenses_by_ids, run_ids)
        doubtful = sorted(
            (e for e in doubtful if _to_item(e).needs_review), key=lambda e: e.category_confidence or 0.0
        )
        review_items = _one_per_merchant(doubtful)[:50]
        async with self:
            self.is_categorizing = False
            self.load_entries_from_database()
            self.can_undo_recategorize = self.router.session.client_token in _UNDO_SNAPSHOTS
            self.results_total = assigned
            self.results_memory = stats.from_memory
            self.results_similar = stats.from_similar
            self.results_high = stats.high_confidence
            self.results_mid = stats.mid_confidence
            self.results_low = stats.low_confidence
            average = stats.average_confidence
            self.results_average = f"{average * 100:.0f} %" if average is not None else "-"
            self.review_items = review_items
            self.has_results = True
            self.show_results = True
        logger.info(stats.summary())

    @rx.event
    def set_show_results(self, value: bool):
        self.show_results = value

    def open_results(self):
        self.show_results = True

    def confirm_review_item(self, expense_id: int):
        """The user checked the model's category and it is right: keep it as a hand-made label."""
        item = next((i for i in self.review_items if i.id == expense_id), None)
        if item is None or not item.category:
            return
        db_manager.update_category(expense_id, item.category, item.subcategory, source="manual")
        db_manager.learn_from_correction(expense_id)
        self._drop_reviewed(expense_id, item.concept)
        self.load_entries_from_database()

    def _drop_reviewed(self, expense_id: int, concept: str | None = None):
        """A reviewed merchant leaves the list: its other movements were updated with it."""
        if concept is None:
            item = next((i for i in self.review_items if i.id == expense_id), None)
            concept = item.concept if item else None
        key = merchant_key(concept) if concept else ""
        self.review_items = [
            i for i in self.review_items if i.id != expense_id and not (key and merchant_key(i.concept) == key)
        ]

    def undo_recategorize(self):
        snapshot = _UNDO_SNAPSHOTS.pop(self.router.session.client_token, None)
        self.can_undo_recategorize = False
        if not snapshot:
            return rx.toast.info("No hay nada que deshacer")
        restored = db_manager.restore_categorization(snapshot)
        self.load_entries_from_database()
        return rx.toast.success(f"Categorías anteriores restauradas en {restored} movimientos")

    def open_recategorize_dialog(self):
        counts = db_manager.count_by_source()
        self.recategorize_auto_count = counts["auto"]
        self.recategorize_manual_count = counts["manual"]
        self.show_recategorize_dialog = True

    @rx.event
    def set_show_recategorize_dialog(self, value: bool):
        self.show_recategorize_dialog = value

    def confirm_recategorize(self):
        self.show_recategorize_dialog = False
        return TableState.force_recategorize

    def force_recategorize(self):
        _UNDO_SNAPSHOTS[self.router.session.client_token] = db_manager.snapshot_categorization()
        self.can_undo_recategorize = False
        count = db_manager.reset_categorization()
        if count == 0:
            return rx.toast.info("No hay movimientos para recategorizar")
        return [
            rx.toast.info(f"Recategorizando {count} movimientos…"),
            TableState.categorize_pending_expenses,
        ]

    def open_upload_modal(self):
        self._reset_preview()
        self.upload_status = ""
        self.upload_error = False
        self.pending_bank_name = ""
        self.show_upload_modal = True
        return rx.clear_selected_files("upload-excel")

    def close_upload_modal(self):
        self.show_upload_modal = False

    @rx.event
    def set_show_upload_modal(self, value: bool):
        self.show_upload_modal = value
        if not value:
            self._reset_preview()

    def set_pending_bank_name(self, value: str):
        self.pending_bank_name = value
        if self.preview_ready:
            # The bank name is part of the duplicate check, so the preview no longer applies.
            self._reset_preview()
            return rx.clear_selected_files("upload-excel")

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
            review_only=self.review_only,
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
                "note",
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
                    r.note or "",
                ]
            )
        filename = f"transacciones_{datetime.now().strftime('%Y%m%d')}.csv"
        return rx.download(data=buf.getvalue().encode("utf-8"), filename=filename)
