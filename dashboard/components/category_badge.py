import reflex as rx
from reflex.components.radix.themes.base import LiteralAccentColor

from dashboard.expenses.model import Item
from dashboard.expenses.state import TableState
from dashboard.llm.llm_call import CATEGORY_TAXONOMY


CATEGORY_COLORS: dict[str, LiteralAccentColor] = {
    "Deuda": "ruby",
    "Educación": "indigo",
    "Ocio": "purple",
    "Gastos diarios": "amber",
    "Regalos": "pink",
    "Salud/médicos": "tomato",
    "Vivienda": "blue",
    "Tecnología": "iris",
    "Transporte": "cyan",
    "Viajes": "teal",
    "Servicios básicos": "green",
    "Otros": "gray",
}

CATEGORY_NAMES = list(CATEGORY_TAXONOMY.keys())


def _color_var_for(category: rx.Var[str | None]) -> rx.Var[str]:
    """Map a category Var to a Radix color name via rx.match."""
    cases = []
    for name, color in CATEGORY_COLORS.items():
        cases.append((name, color))
    cases.append("gray")
    return rx.match(category, *cases)


def category_badge(item: Item) -> rx.Component:
    color = _color_var_for(item.category)
    label = rx.cond(
        item.category,
        item.category,
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
        variant="soft",
        size="1",
        radius="medium",
        cursor="pointer",
        style={"_hover": {"opacity": 0.85}},
        custom_attrs={"title": "Cambiar categoría"},
    )

    return rx.popover.root(
        rx.popover.trigger(trigger),
        rx.popover.content(
            _category_picker(item),
            side="bottom",
            align="start",
            max_width="320px",
        ),
    )


def _category_picker(item: Item) -> rx.Component:
    return rx.vstack(
        rx.text("Categoría", size="2", weight="medium"),
        rx.scroll_area(
            rx.vstack(
                *[
                    rx.button(
                        category,
                        variant=rx.cond(item.category == category, "solid", "soft"),
                        color_scheme=CATEGORY_COLORS[category],
                        size="2",
                        width="100%",
                        justify_content="flex-start",
                        on_click=TableState.update_expense_category(
                            item.id, category, CATEGORY_TAXONOMY[category][0]
                        ),
                    )
                    for category in CATEGORY_NAMES
                ],
                spacing="1",
                width="100%",
            ),
            type="auto",
            scrollbars="vertical",
            style={"max_height": "260px"},
            width="100%",
        ),
        spacing="2",
        width="100%",
    )
