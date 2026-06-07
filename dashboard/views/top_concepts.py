import reflex as rx

from dashboard.views.charts import ConceptRow, StatsState


def _row(item: ConceptRow) -> rx.Component:
    return rx.hstack(
        rx.icon("repeat", size=14, color=rx.color("gray", 9)),
        rx.text(
            item.concept,
            size="2",
            weight="medium",
            flex="1",
            style={
                "text_overflow": "ellipsis",
                "overflow": "hidden",
                "white_space": "nowrap",
            },
        ),
        rx.badge(item.count, variant="soft", size="1"),
        rx.text(
            item.total_fmt,
            size="2",
            weight="medium",
            color=rx.color("red", 11),
        ),
        align="center",
        spacing="3",
        width="100%",
        padding_y="0.4em",
        border_bottom=f"1px solid {rx.color('gray', 4)}",
    )


def top_concepts() -> rx.Component:
    return rx.cond(
        StatsState.top_concepts.length() == 0,
        rx.center(
            rx.vstack(
                rx.icon("list", size=32, color="gray"),
                rx.text("Sin movimientos en este periodo", size="3", color="gray"),
                spacing="2",
                align="center",
            ),
            height="280px",
        ),
        rx.vstack(
            rx.foreach(StatsState.top_concepts, _row),
            spacing="0",
            width="100%",
        ),
    )
