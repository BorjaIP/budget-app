"""Radix Icons (@radix-ui/react-icons) in place of Reflex's default Lucide set."""

import reflex as rx

_LIBRARY = "@radix-ui/react-icons@1.3.2"

# Glyph names used by the app -> Radix Icons component names.
_TAGS = {
    "home": "HomeIcon",
    "receipt": "FileTextIcon",
    "calendar-range": "CalendarIcon",
    "settings": "GearIcon",
    "search": "MagnifyingGlassIcon",
    "search-x": "MagnifyingGlassIcon",
    "x": "Cross2Icon",
    "trash-2": "TrashIcon",
    "check": "CheckIcon",
    "cloud-upload": "UploadIcon",
    "arrow-down-z-a": "ArrowDownIcon",
    "arrow-down-a-z": "ArrowUpIcon",
    "chevron-left": "ChevronLeftIcon",
    "chevron-right": "ChevronRightIcon",
    "chevrons-left": "DoubleArrowLeftIcon",
    "chevrons-right": "DoubleArrowRightIcon",
    "sun": "SunIcon",
    "moon": "MoonIcon",
    "info-circled": "InfoCircledIcon",
}


class RadixIcon(rx.Component):
    library = _LIBRARY
    width: rx.Var[int | str]
    height: rx.Var[int | str]


_classes: dict[str, type[RadixIcon]] = {}


def _icon_class(tag: str) -> type[RadixIcon]:
    if tag not in _classes:
        _classes[tag] = type(tag, (RadixIcon,), {"tag": tag, "__module__": __name__})
    return _classes[tag]


def icon(name: str, size: int = 16, color: str | None = None, **props) -> rx.Component:
    """Render the named glyph; it inherits the current text color unless `color` is given."""
    if color is not None:
        props["style"] = {**props.get("style", {}), "color": color}
    return _icon_class(_TAGS[name]).create(width=size, height=size, **props)
