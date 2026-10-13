import reflex as rx

from dashboard.expenses.model import Item
from dashboard.expenses.state import TableState
from dashboard.taxonomy_state import TaxonomyState


def category_badge(item: Item) -> rx.Component:
    color = rx.cond(item.category, TaxonomyState.colors[item.category], "gray")
    label = rx.cond(
        item.category,
        rx.cond(item.subcategory, item.category + " · " + item.subcategory, item.category),
        rx.cond(TableState.is_categorizing, "Categorizando…", "Sin categorizar"),
    )
    spinner = rx.cond(
        item.category,
        rx.fragment(),
        rx.cond(TableState.is_categorizing, rx.spinner(size="1"), rx.fragment()),
    )

    trigger = rx.badge(
        spinner,
        label,
        color_scheme=color,
        variant=rx.cond(item.needs_review, "outline", "soft"),
        size="1",
        radius="medium",
        cursor="pointer",
        style={"_hover": {"opacity": 0.85}},
        custom_attrs={
            "title": rx.cond(
                item.needs_review,
                "El modelo no está seguro: revísala o cámbiala",
                rx.cond(item.source == "memory", "Categoría aprendida de tus correcciones", "Cambiar categoría"),
            )
        },
    )

    return rx.popover.root(
        rx.popover.trigger(trigger),
        rx.popover.content(
            _category_picker(item),
            side="bottom",
            align="start",
            max_width="320px",
        ),
        on_open_change=lambda _: TaxonomyState.open_picker(item.category, item.subcategory, item.is_expense),
    )


def _category_picker(item: Item) -> rx.Component:
    return rx.vstack(
        rx.text("Categoría", size="2", weight="medium"),
        rx.select(
            TaxonomyState.picker_categories,
            value=TaxonomyState.picker_category,
            on_change=TaxonomyState.set_picker_category,
            size="2",
            width="100%",
        ),
        rx.text("Subcategoría", size="2", weight="medium"),
        rx.select(
            TaxonomyState.picker_subcategories,
            value=TaxonomyState.picker_subcategory,
            on_change=TaxonomyState.set_picker_subcategory,
            size="2",
            width="100%",
        ),
        rx.hstack(
            rx.link("Gestionar categorías", href="/categories", size="1", underline="always"),
            rx.spacer(),
            rx.popover.close(
                rx.button(
                    "Guardar",
                    size="2",
                    color_scheme="gray",
                    high_contrast=True,
                    disabled=TaxonomyState.picker_category == "",
                    on_click=TableState.update_expense_category(
                        item.id, TaxonomyState.picker_category, TaxonomyState.picker_subcategory
                    ),
                ),
            ),
            width="100%",
            align="center",
        ),
        spacing="2",
        width="100%",
    )
