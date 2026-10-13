"""Title block shared by every page so headings keep the same size and rhythm."""

import reflex as rx


def page_header(
    title: str,
    description: str | None = None,
    actions: rx.Component | None = None,
) -> rx.Component:
    text = [
        rx.heading(title, as_="h1", size="6", weight="medium", letter_spacing="-0.02em"),
    ]
    if description:
        text.append(rx.text(description, size="2", color=rx.color("gray", 11)))
    return rx.flex(
        rx.vstack(*text, spacing="1", align="start"),
        rx.box(actions, width=["100%", "100%", "auto"]) if actions is not None else rx.fragment(),
        justify="between",
        align="end",
        wrap="wrap",
        gap="1rem",
        width="100%",
    )
