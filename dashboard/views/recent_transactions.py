import reflex as rx

from dashboard.views.charts import RecentRow, StatsState

_TRUNCATE = {"overflow": "hidden", "text_overflow": "ellipsis", "white_space": "nowrap"}


def _row(item: RecentRow) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(item.concept, size="2", weight="medium", max_width="100%", style=_TRUNCATE),
            rx.hstack(
                rx.text(item.operation_date, size="1", color=rx.color("gray", 11), class_name="num"),
                rx.text(item.category, size="1", color=rx.color("gray", 11), style=_TRUNCATE),
                spacing="3",
                max_width="100%",
            ),
            spacing="1",
            align_items="start",
            flex="1",
            min_width="0",
        ),
        rx.text(
            item.amount_fmt,
            size="2",
            weight="medium",
            class_name="num",
            flex_shrink="0",
            style={"white_space": "nowrap"},
            color=rx.cond(item.is_expense, rx.color("red", 11), rx.color("green", 11)),
        ),
        align="center",
        spacing="3",
        width="100%",
        padding="0.6em 0",
        border_bottom=f"1px solid {rx.color('gray', 4, True)}",
    )


def recent_transactions() -> rx.Component:
    return rx.cond(
        StatsState.recent_expenses.length() == 0,
        rx.center(
            rx.text("Aún no hay movimientos", size="2", color=rx.color("gray", 11)),
            height="200px",
        ),
        rx.vstack(
            rx.foreach(StatsState.recent_expenses, _row),
            spacing="0",
            width="100%",
        ),
    )
