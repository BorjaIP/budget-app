import reflex as rx

from dashboard.components.category_badge import CATEGORY_NAMES, category_badge
from dashboard.components.empty_state import empty_state
from dashboard.components.icon import icon
from dashboard.expenses.model import Item
from dashboard.expenses.state import TableState


SORT_OPTIONS = [
    ("operation_date", "Fecha"),
    ("amount", "Importe"),
    ("balance", "Saldo"),
    ("concept", "Concepto"),
    ("category", "Categoría"),
]

_TRUNCATE = {"overflow": "hidden", "text_overflow": "ellipsis", "white_space": "nowrap"}


def _hairline() -> str:
    return f"1px solid {rx.color('gray', 4, True)}"


def _amount_text(item: Item) -> rx.Component:
    return rx.text(
        item.amount_fmt,
        color=rx.cond(item.is_expense, rx.color("gray", 12), rx.color("green", 11)),
        weight="medium",
        class_name="num",
        white_space="nowrap",
    )


def _balance_text(item: Item) -> rx.Component:
    return rx.text(
        item.balance_fmt,
        color=rx.color("gray", 11),
        class_name="num",
        white_space="nowrap",
    )


def _delete_action(item: Item) -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.trigger(
            rx.icon_button(
                icon("trash-2", size=14),
                variant="ghost",
                color_scheme="gray",
                size="1",
                cursor="pointer",
                custom_attrs={"aria-label": "Borrar movimiento", "title": "Borrar movimiento"},
                style={"color": rx.color("gray", 9), "_hover": {"color": rx.color("red", 11)}},
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


def _header_cell(text: str, end: bool = False) -> rx.Component:
    return rx.table.column_header_cell(text, justify="end" if end else "start")


def _row(item: Item) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item.operation_date_human, class_name="num", white_space="nowrap")),
        rx.table.cell(
            rx.text(item.concept, weight="medium", style={**_TRUNCATE, "max_width": "28em"}),
        ),
        rx.table.cell(category_badge(item)),
        rx.table.cell(_amount_text(item), justify="end"),
        rx.table.cell(_balance_text(item), justify="end"),
        rx.table.cell(
            rx.cond(
                item.bank_name,
                rx.text(item.bank_name, size="1", color=rx.color("gray", 11), white_space="nowrap"),
                rx.text("-", size="1", color=rx.color("gray", 9)),
            ),
        ),
        rx.table.cell(_delete_action(item), justify="end", width="3em"),
        style={"_hover": {"background_color": rx.color("gray", 2)}},
        align="center",
    )


def _mobile_item(item: Item) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(item.operation_date_human, size="1", color=rx.color("gray", 11), class_name="num"),
            rx.spacer(),
            _amount_text(item),
            width="100%",
            align="center",
        ),
        rx.text(item.concept, size="2", weight="medium", width="100%", style=_TRUNCATE),
        rx.hstack(
            category_badge(item),
            rx.spacer(),
            rx.cond(
                item.bank_name,
                rx.text(item.bank_name, size="1", color=rx.color("gray", 11)),
                rx.fragment(),
            ),
            _delete_action(item),
            width="100%",
            align="center",
        ),
        spacing="2",
        width="100%",
        padding_y="0.75rem",
        border_bottom=_hairline(),
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                _header_cell("Fecha"),
                _header_cell("Concepto"),
                _header_cell("Categoría"),
                _header_cell("Importe", end=True),
                _header_cell("Saldo", end=True),
                _header_cell("Banco"),
                _header_cell(""),
            ),
        ),
        rx.table.body(
            rx.foreach(TableState.items, _row),
        ),
        variant="surface",
        size="2",
        width="100%",
    )


def _mobile_list() -> rx.Component:
    return rx.vstack(
        rx.foreach(TableState.items, _mobile_item),
        spacing="0",
        width="100%",
    )


def _category_filter() -> rx.Component:
    return rx.popover.root(
        rx.popover.trigger(
            rx.button(
                rx.text(TableState.category_filter_label),
                variant="outline",
                color_scheme="gray",
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
                    color_scheme="gray",
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
                rx.text(TableState.bank_filter_label),
                variant="outline",
                color_scheme="gray",
                size="2",
            ),
        ),
        rx.popover.content(
            rx.cond(
                TableState.available_banks.length() == 0,
                rx.text("Aún no hay bancos registrados", size="2", color=rx.color("gray", 11)),
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
            size="2",
            custom_attrs={"aria-label": "Fecha desde"},
        ),
        rx.input(
            type="date",
            value=TableState.date_to,
            on_change=TableState.set_date_to,
            size="2",
            custom_attrs={"aria-label": "Fecha hasta"},
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
            custom_attrs={"aria-label": "Importe mínimo"},
        ),
        rx.input(
            type="number",
            placeholder="Máx €",
            value=TableState.amount_max,
            on_change=TableState.set_amount_max,
            size="2",
            width="6em",
            custom_attrs={"aria-label": "Importe máximo"},
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


def _summary_line() -> rx.Component:
    return rx.text(
        "Mostrando ",
        rx.text.strong(TableState.items.length(), class_name="num"),
        " de ",
        rx.text.strong(TableState.total_items, class_name="num"),
        " movimientos",
        size="2",
        color=rx.color("gray", 11),
    )


def _search_input() -> rx.Component:
    return rx.input(
        rx.input.slot(icon("search", size=16)),
        rx.input.slot(
            rx.icon_button(
                icon("x", size=14),
                variant="ghost",
                color_scheme="gray",
                size="1",
                on_click=TableState.set_search(""),
                custom_attrs={"aria-label": "Borrar búsqueda"},
            ),
            display=rx.cond(TableState.search_value, "flex", "none"),
        ),
        value=TableState.search_value,
        placeholder="Buscar concepto...",
        on_change=TableState.set_search,
        size="2",
        flex="1",
        min_width="14rem",
        max_width="24rem",
        custom_attrs={"aria-label": "Buscar concepto"},
    )


def _secondary_filters() -> rx.Component:
    return rx.flex(
        _date_range(),
        _amount_range(),
        rx.cond(
            TableState.has_filters,
            rx.button(
                "Limpiar filtros",
                variant="ghost",
                color_scheme="gray",
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


def _filters() -> rx.Component:
    """Dates and amounts are always visible on desktop and folded into a disclosure on mobile."""
    return rx.vstack(
        rx.flex(
            _search_input(),
            _category_filter(),
            _bank_filter(),
            spacing="2",
            wrap="wrap",
            align="center",
            width="100%",
        ),
        rx.box(
            _secondary_filters(),
            display=["none", "none", "block", "block", "block"],
            width="100%",
        ),
        rx.el.details(
            rx.el.summary(
                "Más filtros",
                style={
                    "cursor": "pointer",
                    "padding": "0.25rem 0",
                    "color": rx.color("gray", 11),
                    "font_size": "var(--font-size-2)",
                },
            ),
            rx.box(_secondary_filters(), padding_top="0.5rem"),
            display=["block", "block", "none", "none", "none"],
            width="100%",
        ),
        rx.flex(
            _flow_filter(),
            rx.spacer(),
            _summary_line(),
            spacing="3",
            wrap="wrap",
            align="center",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


def _toolbar() -> rx.Component:
    return rx.flex(
        rx.hstack(
            rx.cond(
                TableState.sort_reverse,
                rx.icon_button(
                    icon("arrow-down-z-a", size=16),
                    variant="ghost",
                    color_scheme="gray",
                    size="2",
                    on_click=TableState.toggle_sort,
                    cursor="pointer",
                    custom_attrs={"aria-label": "Orden descendente, pulsa para invertir"},
                ),
                rx.icon_button(
                    icon("arrow-down-a-z", size=16),
                    variant="ghost",
                    color_scheme="gray",
                    size="2",
                    on_click=TableState.toggle_sort,
                    cursor="pointer",
                    custom_attrs={"aria-label": "Orden ascendente, pulsa para invertir"},
                ),
            ),
            rx.text("Ordenar por", size="2", color=rx.color("gray", 11)),
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
            spacing="2",
            align="center",
        ),
        rx.spacer(),
        rx.hstack(
            rx.button(
                "Exportar",
                variant="soft",
                color_scheme="gray",
                size="2",
                on_click=TableState.export_csv,
            ),
            rx.button(
                "Subir archivo",
                size="2",
                color_scheme="gray",
                high_contrast=True,
                on_click=TableState.open_upload_modal,
            ),
            spacing="2",
        ),
        wrap="wrap",
        align="center",
        gap="0.75rem",
        width="100%",
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
            color_scheme="gray",
        ),
        rx.fragment(),
    )


def _page_button(glyph: str, label: str, handler, disabled) -> rx.Component:
    return rx.icon_button(
        icon(glyph, size=16),
        variant="soft",
        color_scheme="gray",
        size="2",
        on_click=handler,
        disabled=disabled,
        cursor="pointer",
        custom_attrs={"aria-label": label, "title": label},
    )


def _pagination() -> rx.Component:
    at_start = TableState.page_number == 1
    at_end = TableState.page_number == TableState.total_pages
    return rx.hstack(
        rx.text(
            "Página ",
            rx.text.strong(TableState.page_number, class_name="num"),
            " de ",
            rx.text.strong(TableState.total_pages, class_name="num"),
            size="2",
            color=rx.color("gray", 11),
        ),
        rx.spacer(),
        _page_button("chevrons-left", "Primera página", TableState.first_page, at_start),
        _page_button("chevron-left", "Página anterior", TableState.prev_page, at_start),
        _page_button("chevron-right", "Página siguiente", TableState.next_page, at_end),
        _page_button("chevrons-right", "Última página", TableState.last_page, at_end),
        spacing="2",
        align="center",
        width="100%",
        margin_top="0.5em",
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
                    custom_attrs={"aria-label": "Nombre del banco"},
                ),
                rx.upload(
                    rx.vstack(
                        icon("cloud-upload", size=24, color=rx.color("gray", 10)),
                        rx.text(
                            rx.cond(
                                TableState.is_uploading,
                                "Procesando archivo…",
                                "Arrastra un archivo o haz clic para seleccionar",
                            ),
                            size="2",
                            text_align="center",
                            color=rx.color("gray", 11),
                        ),
                        rx.foreach(
                            rx.selected_files("upload-excel"),
                            lambda f: rx.text(f, size="1", weight="medium"),
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
                    border=f"1px dashed {rx.color('gray', 7, True)}",
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
                        color_scheme=rx.cond(TableState.upload_error, "red", "green"),
                        width="100%",
                        custom_attrs={"role": "status"},
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
                    rx.cond(TableState.is_uploading, rx.spinner(size="1"), rx.fragment()),
                    "Procesar",
                    color_scheme="gray",
                    high_contrast=True,
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
                    rx.box(_table(), display=["none", "none", "block", "block", "block"], width="100%"),
                    rx.box(_mobile_list(), display=["block", "block", "none", "none", "none"], width="100%"),
                ),
            ),
        ),
    )


def main_table() -> rx.Component:
    return rx.vstack(
        _toolbar(),
        _filters(),
        _categorization_progress(),
        _upload_modal(),
        _table_or_empty(),
        rx.cond(TableState.total_items > 0, _pagination(), rx.fragment()),
        spacing="4",
        width="100%",
    )


# Backwards-compatible class API for callers expecting TableView().main_table()
class TableView:
    def main_table(self) -> rx.Component:
        return main_table()
