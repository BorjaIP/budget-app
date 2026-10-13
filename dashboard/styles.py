"""Shared style tokens. Colors come from the Radix theme; borders are 1px hairlines."""

import reflex as rx

border_radius = "var(--radius-2)"
border = f"1px solid {rx.color('gray', 5, True)}"
text_color = rx.color("gray", 11)
sidebar_width = "32em"
sidebar_content_width = "16em"
max_width = "1480px"


template_page_style = {
    "padding_top": ["1em", "1em", "2em"],
    "padding_x": ["auto", "auto", "2em"],
}

template_content_style = {
    "padding": "1em",
    "padding_bottom": ["6em", "6em", "2em"],  # leave room for mobile bottom nav
    "min_height": "90vh",
}

base_stylesheets = ["styles.css"]

base_style = {
    "font_family": "Geist, ui-sans-serif, system-ui, sans-serif",
}
