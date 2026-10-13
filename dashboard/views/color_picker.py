import reflex as rx
from reflex.components.radix.themes.base import LiteralAccentColor, LiteralGrayColor

from .. import styles
from ..templates.template import ThemeState


def _swatches(names: list[str]) -> dict[str, str]:
    return {name.capitalize(): f"{rx.color(name, 9)}" for name in names}


# Gray first: it is the neutral default of the minimalist theme.
primary_color_dict: dict[str, str] = _swatches(
    ["gray", *[c for c in LiteralAccentColor.__args__ if c != "gray"]]
)

secondary_color_dict: dict[str, str] = _swatches(
    [c for c in LiteralGrayColor.__args__ if c != "auto"]
)


class ColorPickerState(rx.State):
    primary_color_options: dict[str, str] = primary_color_dict
    secondary_color_options: dict[str, str] = secondary_color_dict


def _swatch(option: list, current_value, event) -> rx.Component:
    name, color = option[0], option[1]
    selected = name.lower() == current_value.lower()
    return rx.tooltip(
        rx.el.button(
            rx.cond(selected, rx.icon("check", size=14, color=rx.color("gray", 1)), rx.fragment()),
            type="button",
            on_click=event(name.lower()),
            style={
                **styles.color_picker_style,
                "background": color,
                "height": styles.color_box_size,
                "width": styles.color_box_size,
                "border": "none",
                "padding": "0",
                "outline": rx.cond(selected, f"2px solid {rx.color('gray', 12)}", "none"),
                "outline_offset": "2px",
            },
            custom_attrs={"aria-label": name, "aria-pressed": rx.cond(selected, "true", "false")},
        ),
        content=name,
    )


def _display_primary_color(option: list) -> rx.Component:
    return _swatch(option, ThemeState.accent_color, lambda value: ThemeState.setvar("accent_color", value))


def _display_secondary_color(option: list) -> rx.Component:
    return _swatch(option, ThemeState.gray_color, lambda value: ThemeState.setvar("gray_color", value))


def primary_color_picker() -> rx.Component:
    return rx.flex(
        rx.foreach(ColorPickerState.primary_color_options, _display_primary_color),
        width="100%",
        max_width="40rem",
        wrap="wrap",
        gap=["12px", "12px", "16px"],
    )


def secondary_color_picker() -> rx.Component:
    return rx.flex(
        rx.foreach(ColorPickerState.secondary_color_options, _display_secondary_color),
        width="100%",
        max_width="40rem",
        wrap="wrap",
        gap=["12px", "12px", "16px"],
    )
