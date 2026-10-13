"""Common templates used between pages in the app."""

from __future__ import annotations

from typing import Callable

import reflex as rx

from .. import styles
from ..components.bottom_nav import bottom_nav
from ..components.categorization_results import categorization_banner, results_dialog
from ..components.navbar import navbar
from ..components.sidebar import sidebar
from ..taxonomy_state import TaxonomyState


default_meta = [
    {
        "name": "viewport",
        "content": "width=device-width, shrink-to-fit=no, initial-scale=1",
    },
]


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
        extra = on_load if isinstance(on_load, list) else ([on_load] if on_load is not None else [])
        page_on_load = [TaxonomyState.load_taxonomy, *extra]  # every page needs the user's categories

        def templated_page() -> rx.Component:
            return rx.flex(
                sidebar(),
                rx.flex(
                    navbar(),
                    rx.vstack(
                        categorization_banner(),
                        page_content(),
                        width="100%",
                        **styles.template_content_style,
                    ),
                    results_dialog(),
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
            on_load=page_on_load,
        )
        def theme_wrap() -> rx.Component:
            return rx.theme(
                templated_page(),
                has_background=True,
                panel_background="solid",
                accent_color="gray",
                gray_color="sand",
                radius="medium",
                scaling="100%",
            )

        return theme_wrap

    return decorator
