import reflex as rx

from dashboard.views.charts import ConceptRow, StatsState

_TRUNCATE = {"overflow": "hidden", "text_overflow": "ellipsis", "white_space": "nowrap"}


def _row(item: ConceptRow) -> rx.Component:
    content = rx.hstack(
        rx.text(item.concept, size="2", flex="1", min_width="0", style=_TRUNCATE),
        rx.text(
            item.count,
            size="1",
            color=rx.color("gray", 11),
            class_name="num",
            flex_shrink="0",
            title="Número de movimientos",
        ),
        rx.text(
            item.total_fmt,
            size="2",
            weight="medium",
            class_name="num",
            flex_shrink="0",
            style={"white_space": "nowrap"},
        ),
        align="center",
        spacing="3",
        width="100%",
        padding_y="0.5em",
        border_bottom=f"1px solid {rx.color('gray', 4, True)}",
    )
    return rx.el.button(
        content,
        type="button",
        on_click=StatsState.open_concept(item.concept),
        title="Ver estos movimientos",
        class_name="row-link",
    )


def top_concepts() -> rx.Component:
    return rx.cond(
        StatsState.top_concepts.length() == 0,
        rx.center(
            rx.text("Sin movimientos en este periodo", size="2", color=rx.color("gray", 11)),
            height="200px",
        ),
        rx.vstack(
            rx.foreach(StatsState.top_concepts, _row),
            spacing="0",
            width="100%",
        ),
    )
