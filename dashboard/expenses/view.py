import reflex as rx

from dashboard.components.card import card
from dashboard.components.category_badge import category_badge
from dashboard.taxonomy_state import TaxonomyState
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
        color=rx.cond(item.is_expense, rx.color("red", 11), rx.color("green", 11)),
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


def _concept_text(item: Item) -> rx.Component:
    """Concept with the searched term highlighted."""
    return rx.text(
        rx.foreach(
            item.concept_segments,
            lambda seg: rx.cond(
                seg["m"],
                rx.el.mark(seg["t"], style={"background": "var(--gray-a5)", "color": "inherit", "border_radius": "2px"}),
                seg["t"],
            ),
        ),
        weight="medium",
        style={**_TRUNCATE, "max_width": "28em"},
    )


def _concept_link(item: Item) -> rx.Component:
    """The concept opens the transaction detail; a small bubble marks the ones that have a note."""
    return rx.hstack(
        rx.el.button(
            _concept_text(item),
            type="button",
            on_click=TableState.open_detail(item.id),
            title="Ver detalle y añadir una nota",
            class_name="row-link",
            style={"width": "auto", "padding": "0 0.25rem", "text_align": "left", "max_width": "100%"},
        ),
        rx.cond(item.note != "", icon("note", size=13, color=rx.color("gray", 10), title="Tiene una nota"), rx.fragment()),
        spacing="1",
        align="center",
    )


def _select_box(item: Item) -> rx.Component:
    return rx.checkbox(
        checked=TableState.selected_ids.contains(item.id),
        on_change=lambda _: TableState.toggle_selected(item.id),
        size="2",
        color_scheme="gray",
        custom_attrs={"aria-label": "Seleccionar movimiento"},
    )


def _row(item: Item) -> rx.Component:
    return rx.table.row(
        rx.table.cell(_select_box(item), width="2.5em"),
        rx.table.cell(rx.text(item.operation_date_human, class_name="num", white_space="nowrap")),
        rx.table.cell(_concept_link(item)),
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
        rx.hstack(
            rx.el.button(
                rx.text(item.concept, size="2", weight="medium", style=_TRUNCATE),
                type="button",
                on_click=TableState.open_detail(item.id),
                class_name="row-link",
                style={"width": "auto", "padding": "0", "text_align": "left", "min_width": "0"},
            ),
            rx.cond(item.note != "", icon("note", size=13, color=rx.color("gray", 10)), rx.fragment()),
            spacing="1",
            align="center",
            width="100%",
        ),
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
                rx.table.column_header_cell(
                    rx.checkbox(
                        checked=TableState.page_all_selected,
                        on_change=lambda _: TableState.toggle_page_selection(),
                        size="2",
                        color_scheme="gray",
                        custom_attrs={"aria-label": "Seleccionar todos los movimientos de la página"},
                    ),
                    width="2.5em",
                ),
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
        size="1",
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
                        rx.foreach(
                            TaxonomyState.categories_and_unassigned,
                            lambda name: rx.checkbox(
                                name,
                                checked=TableState.selected_categories.contains(name),
                                on_change=lambda _: TableState.toggle_category(name),
                            ),
                        ),
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


def _review_chip() -> rx.Component:
    return rx.cond(
        TableState.review_only,
        rx.badge("Por revisar", color_scheme="violet", variant="soft", size="2"),
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
        id="search-input",
        placeholder="Buscar concepto (pulsa /)",
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
            _review_chip(),
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
                flex=["1", "1", "none"],
            ),
            rx.button(
                "Subir archivo",
                size="2",
                color_scheme="gray",
                high_contrast=True,
                on_click=TableState.open_upload_modal,
                flex=["1", "1", "none"],
            ),
            spacing="2",
            width=["100%", "100%", "auto"],
        ),
        wrap="wrap",
        align="center",
        gap="0.75rem",
        width="100%",
    )


def _bulk_bar() -> rx.Component:
    return rx.cond(
        TableState.selected_count > 0,
        rx.flex(
            rx.text(
                rx.text.strong(TableState.selected_count, class_name="num"),
                " seleccionados",
                size="2",
            ),
            rx.select(
                TaxonomyState.categories,
                placeholder="Asignar categoría",
                on_change=TableState.apply_bulk_category,
                size="2",
                custom_attrs={"aria-label": "Asignar categoría a los seleccionados"},
            ),
            rx.button(
                "Quitar selección",
                variant="ghost",
                color_scheme="gray",
                size="2",
                on_click=TableState.clear_selection,
            ),
            align="center",
            wrap="wrap",
            gap="0.75rem",
            padding="0.5rem 0.75rem",
            border=f"1px solid {rx.color('gray', 6, True)}",
            border_radius="var(--radius-3)",
            width="100%",
            custom_attrs={"role": "status"},
        ),
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


def _preview_line(label: str, value) -> rx.Component:
    return rx.hstack(
        rx.text(label, size="2", color=rx.color("gray", 11)),
        rx.spacer(),
        rx.text(value, size="2", weight="medium", class_name="num"),
        width="100%",
    )


def _import_preview() -> rx.Component:
    """What importing the chosen file would do; nothing is stored until it is confirmed."""
    return rx.vstack(
        _preview_line("Movimientos nuevos", TableState.preview_new),
        _preview_line("Duplicados que se ignorarán", TableState.preview_duplicates),
        _preview_line("Periodo del archivo", TableState.preview_range),
        _preview_line("Ingresos", TableState.preview_income_fmt),
        _preview_line("Gastos", TableState.preview_spending_fmt),
        spacing="2",
        width="100%",
        padding="0.75rem 1rem",
        border=f"1px solid {rx.color('gray', 5, True)}",
        border_radius="var(--radius-3)",
        custom_attrs={"role": "status"},
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
                rx.cond(TableState.preview_ready, _import_preview(), rx.fragment()),
                rx.text(TableState.upload_stats, size="1", color=rx.color("gray", 11)),
                spacing="3",
                width="100%",
            ),
            rx.flex(
                rx.dialog.close(rx.button("Cerrar", variant="soft", color_scheme="gray")),
                rx.cond(
                    TableState.preview_ready,
                    rx.hstack(
                        rx.button(
                            "Elegir otro",
                            variant="soft",
                            color_scheme="gray",
                            on_click=TableState.discard_preview,
                        ),
                        rx.button(
                            rx.cond(TableState.is_uploading, rx.spinner(size="1"), rx.fragment()),
                            "Importar ",
                            TableState.preview_new,
                            " movimientos",
                            color_scheme="gray",
                            high_contrast=True,
                            on_click=TableState.confirm_import,
                            disabled=TableState.is_uploading | (TableState.preview_new == 0),
                        ),
                        spacing="3",
                    ),
                    rx.button(
                        rx.cond(TableState.is_uploading, rx.spinner(size="1"), rx.fragment()),
                        "Vista previa",
                        color_scheme="gray",
                        high_contrast=True,
                        on_click=TableState.handle_preview(rx.upload_files(upload_id="upload-excel")),
                        disabled=TableState.is_uploading,
                    ),
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


def _fact(label: str, value) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="1", color=rx.color("gray", 11)),
        value if not isinstance(value, str) else rx.text(value, size="2"),
        spacing="1",
        align="start",
    )


def _detail_dialog() -> rx.Component:
    """One transaction in full: its facts, its category and a free note."""
    item = TableState.detail
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(item.concept, style={"overflow_wrap": "anywhere", "padding_right": "1.5rem"}),
            rx.dialog.description(
                rx.text(
                    item.amount_fmt,
                    size="5",
                    weight="medium",
                    class_name="num",
                    color=rx.cond(item.is_expense, rx.color("red", 11), rx.color("green", 11)),
                ),
            ),
            rx.grid(
                _fact("Fecha", item.operation_date_human),
                _fact("Fecha valor", item.value_date_human),
                _fact("Banco", rx.cond(item.bank_name, item.bank_name, "-")),
                _fact("Saldo tras el movimiento", item.balance_fmt),
                _fact("Categoría", category_badge(item)),
                _fact("Cómo se categorizó", item.source_text),
                columns=rx.breakpoints(initial="1", sm="2"),
                gap="1rem",
                margin_top="1.25rem",
                width="100%",
            ),
            rx.vstack(
                rx.text("Nota", size="2", weight="medium"),
                rx.text_area(
                    value=TableState.detail_note,
                    on_change=TableState.set_detail_note,
                    placeholder="Por ejemplo: para qué fue este movimiento",
                    max_length=500,
                    rows="4",
                    size="2",
                    width="100%",
                    custom_attrs={"aria-label": "Nota de la transacción"},
                ),
                rx.text(
                    "Solo la ves tú: no se envía al modelo ni a ningún sitio. Se puede buscar desde Transacciones.",
                    size="1",
                    color=rx.color("gray", 11),
                ),
                spacing="2",
                width="100%",
                align="start",
                margin_top="1.25rem",
            ),
            rx.flex(
                rx.dialog.close(rx.button("Cerrar", variant="soft", color_scheme="gray")),
                rx.button(
                    "Guardar nota",
                    color_scheme="gray",
                    high_contrast=True,
                    disabled=~TableState.detail_note_changed,
                    on_click=TableState.save_note,
                ),
                spacing="3",
                margin_top="1.25rem",
                justify="end",
            ),
            max_width="560px",
        ),
        open=TableState.show_detail,
        on_open_change=TableState.set_show_detail,
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
        card(rx.vstack(_toolbar(), _filters(), spacing="3", width="100%"), padding=["0.75rem", "1rem", "1rem"]),
        _bulk_bar(),
        _upload_modal(),
        _detail_dialog(),
        _table_or_empty(),
        rx.cond(TableState.total_items > 0, _pagination(), rx.fragment()),
        spacing="4",
        width="100%",
    )


# Backwards-compatible class API for callers expecting TableView().main_table()
class TableView:
    def main_table(self) -> rx.Component:
        return main_table()
