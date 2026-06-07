"""Common templates used between pages in the app."""

from __future__ import annotations

from typing import Callable

import reflex as rx

from .. import styles
from ..components.bottom_nav import bottom_nav
from ..components.navbar import navbar
from ..components.sidebar import sidebar


default_meta = [
    {
        "name": "viewport",
        "content": "width=device-width, shrink-to-fit=no, initial-scale=1",
    },
]


class ThemeState(rx.State):
    accent_color: str = "teal"
    gray_color: str = "gray"
    radius: str = "large"
    scaling: str = "100%"


def template(
    route: str | None = None,
    title: str | None = None,
    description: str | None = None,
    meta: list | None = None,
    script_tags: list[rx.Component] | None = None,
    on_load: rx.EventHandler | list[rx.EventHandler] | None = None,
) -> Callable[[Callable[[], rx.Component]], rx.Component]:
    def decorator(page_content: Callable[[], rx.Component]) -> rx.Component:
        all_meta = [*default_meta, *(meta or [])]

        def templated_page() -> rx.Component:
            return rx.flex(
                sidebar(),
                rx.flex(
                    navbar(),
                    rx.vstack(
                        page_content(),
                        width="100%",
                        **styles.template_content_style,
                    ),
                    bottom_nav(),
                    direction="column",
                    width="100%",
                    **styles.template_page_style,
                    max_width=[
                        "100%",
                        "100%",
                        "100%",
                        "100%",
                        "100%",
                        styles.max_width,
                    ],
                ),
                flex_direction=["column", "column", "row", "row", "row"],
                width="100%",
                margin="auto",
                position="relative",
            )

        @rx.page(
            route=route,
            title=title,
            description=description,
            meta=all_meta,
            script_tags=script_tags,
            on_load=on_load,
        )
        def theme_wrap() -> rx.Component:
            return rx.theme(
                templated_page(),
                has_background=True,
                accent_color=ThemeState.accent_color,
                gray_color=ThemeState.gray_color,
                radius=ThemeState.radius,
                scaling=ThemeState.scaling,
            )

        return theme_wrap

    return decorator
