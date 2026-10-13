"""Inline error notice with a retry action (toasts are only for transient events)."""

import reflex as rx


def error_notice(message: str, on_retry, retry_label: str = "Reintentar") -> rx.Component:
    return rx.hstack(
        rx.text(message, size="2", color=rx.color("red", 11)),
        rx.spacer(),
        rx.button(retry_label, size="2", variant="soft", color_scheme="gray", on_click=on_retry),
        align="center",
        width="100%",
        padding="0.75rem 1rem",
        border=f"1px solid {rx.color('red', 6)}",
        border_radius="var(--radius-3)",
        background=rx.color("red", 2),
        custom_attrs={"role": "alert"},
    )
