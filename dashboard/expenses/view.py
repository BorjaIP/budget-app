import reflex as rx

from dashboard.components.category_badge import CATEGORY_NAMES, category_badge
from dashboard.components.empty_state import empty_state
from dashboard.expenses.model import Item
from dashboard.expenses.state import TableState
from dashboard.llm.llm_call import CATEGORY_TAXONOMY


SORT_OPTIONS = [
    ("operation_date", "Fecha"),
    ("amount", "Importe"),
    ("balance", "Saldo"),
    ("concept", "Concepto"),
    ("category", "Categoría"),
]


def _amount_text(item: Item) -> rx.Component:
    return rx.text(
        item.amount_fmt,
        color=rx.cond(item.is_expense, rx.color("red", 11), rx.color("green", 11)),
        weight="medium",
        white_space="nowrap",
    )


def _balance_text(item: Item) -> rx.Component:
    return rx.text(
        item.balance_fmt,
        color=rx.color("gray", 11),
        white_space="nowrap",
    )


def _delete_action(item: Item) -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.trigger(
            rx.icon_button(
                rx.icon("trash-2", size=16),
                variant="ghost",
                color_scheme="gray",
                size="2",
                cursor="pointer",
            ),
        ),
        rx.alert_dialog.content(
            rx.alert_dialog.title("Borrar movimiento"),
            rx.alert_dialog.description(
                "Esta acción no se puede deshacer. ¿Seguro que quieres borrar este movimiento?",
            ),
            rx.flex(
                rx.alert_dialog.cancel(rx.button("Cancelar", variant="soft", color_scheme="gray")),
                rx.alert_dialog.action(
                    rx.button(
                        "Borrar",
                        color_scheme="red",
                        on_click=TableState.delete_expense(item.id),
                    ),
                ),
                spacing="3",
                margin_top="1em",
                justify="end",
            ),
            max_width="420px",
        ),
    )


def _header_cell(text: str, icon: str | None = None) -> rx.Component:
    children = []
    if icon:
        children.append(rx.icon(icon, size=16))
    children.append(rx.text(text, weight="medium"))
    return rx.table.column_header_cell(rx.hstack(*children, align="center", spacing="2"))


def _row(item: Item, index: rx.Var[int]) -> rx.Component:
    bg = rx.cond(index % 2 == 0, rx.color("gray", 1), rx.color("gray", 2))
    return rx.table.row(
        rx.table.cell(item.operation_date_human),
        rx.table.cell(
            rx.text(
                item.concept,
                weight="medium",
                style={
                    "max_width": "28em",
                    "white_space": "nowrap",
                    "overflow": "hidden",
                    "text_overflow": "ellipsis",
                },
            ),
        ),
        rx.table.cell(category_badge(item)),
        rx.table.cell(_amount_text(item)),
        rx.table.cell(_balance_text(item)),
        rx.table.cell(
            rx.cond(
                item.bank_name,
                rx.badge(item.bank_name, variant="surface", size="1"),
                rx.text("—", size="1", color=rx.color("gray", 9)),
            ),
        ),
        rx.table.cell(_delete_action(item), width="3em"),
        style={"bg": bg, "_hover": {"bg": rx.color("accent", 2)}},
        align="center",
    )


def _mobile_card(item: Item, _index: rx.Var[int]) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.text(item.operation_date_human, size="1", color=rx.color("gray", 11)),
                rx.spacer(),
                _amount_text(item),
                width="100%",
                align="center",
            ),
            rx.text(
                item.concept,
                size="3",
                weight="medium",
                style={
                    "white_space": "nowrap",
                    "overflow": "hidden",
                    "text_overflow": "ellipsis",
                    "width": "100%",
                },
            ),
            rx.hstack(
                category_badge(item),
                rx.spacer(),
                rx.cond(
                    item.bank_name,
                    rx.badge(item.bank_name, variant="surface", size="1"),
                    rx.fragment(),
                ),
                _delete_action(item),
                width="100%",
                align="center",
            ),
            spacing="2",
            width="100%",
        ),
        size="2",
        width="100%",
        border_left=rx.cond(
            item.is_expense,
            f"3px solid {rx.color('red', 9)}",
            f"3px solid {rx.color('green', 9)}",
        ),
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                _header_cell("Fecha", "calendar"),
                _header_cell("Concepto", "notebook-pen"),
                _header_cell("Categoría", "tag"),
                _header_cell("Importe", "euro"),
                _header_cell("Saldo", "wallet"),
                _header_cell("Banco", "building"),
                _header_cell("", None),
            ),
        ),
        rx.table.body(
            rx.foreach(TableState.items, lambda item, idx: _row(item, idx)),
        ),
        variant="surface",
        size="2",
        width="100%",
    )


def _mobile_list() -> rx.Component:
    return rx.vstack(
        rx.foreach(TableState.items, lambda item, idx: _mobile_card(item, idx)),
        spacing="3",
        width="100%",
    )


def _category_filter() -> rx.Component:
    return rx.popover.root(
        rx.popover.trigger(
            rx.button(
                rx.icon("tag", size=16),
                rx.text(TableState.category_filter_label),
                variant="surface",
                size="2",
            ),
        ),
        rx.popover.content(
            rx.vstack(
                rx.text("Filtrar por categoría", size="2", weight="medium"),
                rx.scroll_area(
                    rx.vstack(
                        *[
                            rx.checkbox(
                                name,
                                checked=TableState.selected_categories.contains(name),
                                on_change=lambda _, n=name: TableState.toggle_category(n),
                            )
                            for name in [*CATEGORY_NAMES, "Sin categorizar"]
                        ],
                        spacing="2",
                        align_items="start",
                        padding="0.25em 0.5em",
                    ),
                    type="auto",
                    style={"max_height": "260px"},
                ),
                rx.button(
                    "Limpiar",
                    size="1",
                    variant="ghost",
                    on_click=TableState.set_selected_categories([]),
                ),
                spacing="2",
                width="100%",
            ),
            max_width="260px",
        ),
    )


def _bank_filter() -> rx.Component:
    return rx.popover.root(
        rx.popover.trigger(
            rx.button(
                rx.icon("building", size=16),
                rx.text(TableState.bank_filter_label),
                variant="surface",
                size="2",
            ),
        ),
        rx.popover.content(
            rx.cond(
                TableState.available_banks.length() == 0,
                rx.text("Aún no hay bancos registrados", size="2", color="gray"),
                rx.vstack(
                    rx.text("Filtrar por banco", size="2", weight="medium"),
                    rx.foreach(
                        TableState.available_banks,
                        lambda b: rx.checkbox(
                            b,
                            checked=TableState.selected_banks.contains(b),
                            on_change=lambda _: TableState.toggle_bank(b),
                        ),
                    ),
                    spacing="2",
                    width="100%",
                ),
            ),
            max_width="240px",
        ),
    )


def _date_range() -> rx.Component:
    return rx.hstack(
        rx.input(
            type="date",
            value=TableState.date_from,
            on_change=TableState.set_date_from,
            placeholder="Desde",
            size="2",
        ),
        rx.input(
            type="date",
            value=TableState.date_to,
            on_change=TableState.set_date_to,
            placeholder="Hasta",
            size="2",
        ),
        spacing="2",
    )


def _amount_range() -> rx.Component:
    return rx.hstack(
        rx.input(
            type="number",
            placeholder="Mín €",
            value=TableState.amount_min,
            on_change=TableState.set_amount_min,
            size="2",
            width="6em",
        ),
        rx.input(
            type="number",
            placeholder="Máx €",
            value=TableState.amount_max,
            on_change=TableState.set_amount_max,
            size="2",
            width="6em",
        ),
        spacing="2",
    )


def _flow_filter() -> rx.Component:
    return rx.segmented_control.root(
        rx.segmented_control.item("Todo", value="all"),
        rx.segmented_control.item("Gastos", value="expense"),
        rx.segmented_control.item("Ingresos", value="income"),
        value=TableState.flow_filter,
        on_change=TableState.set_flow_filter,
        size="2",
    )


def _filters_row() -> rx.Component:
    return rx.flex(
        rx.input(
            rx.input.slot(rx.icon("search", size=16)),
            rx.input.slot(
                rx.icon("x", size=14),
                cursor="pointer",
                on_click=TableState.set_search(""),
                display=rx.cond(TableState.search_value, "flex", "none"),
            ),
            value=TableState.search_value,
            placeholder="Buscar concepto...",
            on_change=TableState.set_search,
            size="2",
            max_width="240px",
            width="100%",
        ),
        _category_filter(),
        _bank_filter(),
        _date_range(),
        _amount_range(),
        _flow_filter(),
        rx.cond(
            TableState.has_filters,
            rx.button(
                rx.icon("filter-x", size=16),
                "Limpiar",
                variant="ghost",
                size="2",
                on_click=TableState.clear_filters,
            ),
            rx.fragment(),
        ),
        spacing="2",
        wrap="wrap",
        align="center",
        width="100%",
    )


def _toolbar() -> rx.Component:
    return rx.hstack(
        rx.cond(
            TableState.sort_reverse,
            rx.icon_button(
                rx.icon("arrow-down-z-a", size=16),
                variant="ghost",
                size="2",
                on_click=TableState.toggle_sort,
                cursor="pointer",
            ),
            rx.icon_button(
                rx.icon("arrow-down-a-z", size=16),
                variant="ghost",
                size="2",
                on_click=TableState.toggle_sort,
                cursor="pointer",
            ),
        ),
        rx.select(
            [label for _, label in SORT_OPTIONS],
            value=rx.match(
                TableState.sort_value,
                *[(value, label) for value, label in SORT_OPTIONS],
                "Fecha",
            ),
            on_change=lambda v: TableState.set_sort_value(
                rx.match(v, *[(label, value) for value, label in SORT_OPTIONS], "operation_date")
            ),
            size="2",
        ),
        rx.spacer(),
        rx.button(
            rx.icon("download", size=16),
            "Exportar",
            variant="surface",
            size="2",
            on_click=TableState.export_csv,
        ),
        rx.button(
            rx.icon("upload", size=16),
            "Subir archivo",
            size="2",
            on_click=TableState.open_upload_modal,
        ),
        spacing="2",
        align="center",
        width="100%",
        wrap="wrap",
    )


def _categorization_progress() -> rx.Component:
    return rx.cond(
        TableState.is_categorizing,
        rx.callout.root(
            rx.callout.icon(rx.spinner(size="1")),
            rx.callout.text(TableState.categorization_label),
            rx.progress(
                value=TableState.categorization_progress_pct,
                max=100,
                size="1",
                margin_top="0.5em",
            ),
            color_scheme="blue",
        ),
        rx.fragment(),
    )


def _pagination() -> rx.Component:
    return rx.hstack(
        rx.text(
            "Página ",
            rx.code(TableState.page_number),
            " de ",
            rx.code(TableState.total_pages),
            size="2",
        ),
        rx.spacer(),
        rx.icon_button(
            rx.icon("chevrons-left", size=16),
            variant="surface",
            size="2",
            on_click=TableState.first_page,
            disabled=TableState.page_number == 1,
            cursor="pointer",
        ),
        rx.icon_button(
            rx.icon("chevron-left", size=16),
            variant="surface",
            size="2",
            on_click=TableState.prev_page,
            disabled=TableState.page_number == 1,
            cursor="pointer",
        ),
        rx.icon_button(
            rx.icon("chevron-right", size=16),
            variant="surface",
            size="2",
            on_click=TableState.next_page,
            disabled=TableState.page_number == TableState.total_pages,
            cursor="pointer",
        ),
        rx.icon_button(
            rx.icon("chevrons-right", size=16),
            variant="surface",
            size="2",
            on_click=TableState.last_page,
            disabled=TableState.page_number == TableState.total_pages,
            cursor="pointer",
        ),
        spacing="2",
        align="center",
        width="100%",
        margin_top="1em",
    )


def _upload_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Subir archivo del banco"),
            rx.dialog.description(
                "Acepta archivos .xls/.xlsx. Los duplicados se detectan automáticamente.",
                size="2",
            ),
            rx.vstack(
                rx.input(
                    placeholder="Banco (ej. BBVA, Santander)",
                    value=TableState.pending_bank_name,
                    on_change=TableState.set_pending_bank_name,
                    size="2",
                ),
                rx.upload(
                    rx.vstack(
                        rx.icon("cloud-upload", size=32, color=rx.color("gray", 11)),
                        rx.text(
                            rx.cond(
                                TableState.is_uploading,
                                "Procesando archivo…",
                                "Arrastra un archivo o haz clic para seleccionar",
                            ),
                            size="2",
                            text_align="center",
                        ),
                        rx.foreach(
                            rx.selected_files("upload-excel"),
                            lambda f: rx.hstack(
                                rx.icon("file-spreadsheet", size=14),
                                rx.text(f, size="1", weight="medium"),
                                spacing="2",
                            ),
                        ),
                        align="center",
                        spacing="2",
                    ),
                    id="upload-excel",
                    multiple=False,
                    accept={
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                        "application/vnd.ms-excel": [".xls"],
                    },
                    max_files=1,
                    border=f"2px dashed {rx.color('gray', 6)}",
                    padding="1.5em",
                    border_radius="var(--radius-3)",
                    width="100%",
                    min_height="120px",
                    cursor="pointer",
                ),
                rx.cond(
                    TableState.upload_status != "",
                    rx.callout.root(
                        rx.callout.text(TableState.upload_status),
                        color_scheme=rx.cond(
                            TableState.upload_status.startswith("❌"), "red", "green"
                        ),
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                rx.text(TableState.upload_stats, size="1", color=rx.color("gray", 11)),
                spacing="3",
                width="100%",
            ),
            rx.flex(
                rx.dialog.close(rx.button("Cerrar", variant="soft", color_scheme="gray")),
                rx.button(
                    rx.cond(TableState.is_uploading, rx.spinner(size="1"), rx.icon("upload", size=16)),
                    "Procesar",
                    on_click=TableState.handle_upload(rx.upload_files(upload_id="upload-excel")),
                    disabled=TableState.is_uploading,
                ),
                spacing="3",
                margin_top="16px",
                justify="end",
                width="100%",
            ),
            max_width=["95vw", "95vw", "560px"],
        ),
        open=TableState.show_upload_modal,
        on_open_change=TableState.set_show_upload_modal,
    )


def _skeleton_rows() -> rx.Component:
    return rx.vstack(
        *[rx.skeleton(height="3em", width="100%") for _ in range(6)],
        spacing="2",
        width="100%",
    )


def _summary_line() -> rx.Component:
    return rx.text(
        "Mostrando ",
        rx.text.strong(TableState.items.length()),
        " de ",
        rx.text.strong(TableState.total_items),
        " movimientos",
        size="2",
        color=rx.color("gray", 11),
    )


def _table_or_empty() -> rx.Component:
    return rx.cond(
        TableState.is_loading,
        _skeleton_rows(),
        rx.cond(
            TableState.is_empty,
            empty_state(
                "cloud-upload",
                "Aún no hay movimientos",
                "Sube tu primer extracto bancario para empezar a ver tus gastos categorizados.",
                "Subir archivo",
                TableState.open_upload_modal,
            ),
            rx.cond(
                TableState.total_items == 0,
                empty_state(
                    "search-x",
                    "Sin resultados",
                    "Ningún movimiento coincide con los filtros aplicados.",
                    "Limpiar filtros",
                    TableState.clear_filters,
                ),
                rx.fragment(
                    rx.box(_table(), display=["none", "none", "block", "block", "block"]),
                    rx.box(_mobile_list(), display=["block", "block", "none", "none", "none"]),
                ),
            ),
        ),
    )


def main_table() -> rx.Component:
    return rx.box(
        _toolbar(),
        rx.box(_filters_row(), padding_top="0.5em", padding_bottom="0.5em"),
        _categorization_progress(),
        _upload_modal(),
        _summary_line(),
        _table_or_empty(),
        rx.cond(TableState.total_items > 0, _pagination(), rx.fragment()),
        width="100%",
    )


# Backwards-compatible class API for callers expecting TableView().main_table()
class TableView:
    def main_table(self) -> rx.Component:
        return main_table()
