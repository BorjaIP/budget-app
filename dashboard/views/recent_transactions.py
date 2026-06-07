import reflex as rx

from dashboard.views.charts import RecentRow, StatsState


def _row(item: RecentRow) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(item.operation_date, size="1", color=rx.color("gray", 11)),
            rx.text(
                item.concept,
                size="2",
                weight="medium",
                style={
                    "text_overflow": "ellipsis",
                    "overflow": "hidden",
                    "white_space": "nowrap",
                    "max_width": "20em",
                },
            ),
            rx.badge(item.category, size="1", variant="soft"),
            spacing="1",
            align_items="start",
            flex="1",
            min_width="0",
        ),
        rx.text(
            item.amount_fmt,
            size="3",
            weight="bold",
            color=rx.cond(item.is_expense, rx.color("red", 11), rx.color("green", 11)),
        ),
        align="center",
        spacing="3",
        width="100%",
        padding="0.5em 0",
        border_bottom=f"1px solid {rx.color('gray', 4)}",
    )


def recent_transactions() -> rx.Component:
    return rx.cond(
        StatsState.recent_expenses.length() == 0,
        rx.center(
            rx.vstack(
                rx.icon("receipt", size=32, color="gray"),
                rx.text("Aún no hay movimientos", size="3", color="gray"),
                spacing="2",
                align="center",
            ),
            height="280px",
        ),
        rx.vstack(
            rx.foreach(StatsState.recent_expenses, _row),
            spacing="0",
            width="100%",
        ),
    )
