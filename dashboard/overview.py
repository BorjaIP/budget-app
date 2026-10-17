"""Numbers and pictures for the overview, as pure functions (no database, no UI framework).

The donut and the cash-flow diagram are small SVG strings built here. Names come from the user's data, so every
text that reaches the SVG is escaped.
"""

import math
from html import escape
from typing import Any

MAX_SEGMENTS = 6
MAX_FLOW_NODES = 7
OTHERS_LABEL = "Otras"
UNCATEGORIZED = "Sin categorizar"


def money(value: float) -> str:
    """Spanish euro format, no decimals when large: 1.234 € / 12,50 €."""
    text = f"{abs(value):,.0f}" if abs(value) >= 1000 else f"{abs(value):,.2f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def signed_money(value: float) -> str:
    return ("+" if value > 0 else "−" if value < 0 else "") + money(value)


def color_var(color: str, step: int = 9) -> str:
    return f"var(--{color}-{step})"


# ---------------------------------------------------------------- donut
def category_segments(
    breakdown: list[dict[str, Any]], colors: dict[str, str], limit: int = MAX_SEGMENTS
) -> list[dict[str, Any]]:
    """Largest categories first, the rest merged into "Otras". Each has name, value, percent and fill."""
    total = sum(row["value"] for row in breakdown) or 1.0
    ordered = sorted(breakdown, key=lambda row: row["value"], reverse=True)
    head, tail = ordered[:limit], ordered[limit:]
    segments = [
        {"name": row["name"], "value": row["value"], "color": colors.get(row["name"], "gray")} for row in head
    ]
    if tail:
        segments.append({"name": OTHERS_LABEL, "value": sum(row["value"] for row in tail), "color": "gray"})
    for segment in segments:
        segment["percent"] = segment["value"] / total * 100
        segment["fill"] = color_var(segment["color"])
        segment["value_fmt"] = money(segment["value"])
        segment["percent_fmt"] = f"{segment['percent']:.0f} %"
    return segments


def donut_svg(segments: list[dict[str, Any]], center_value: str, center_label: str, size: int = 200) -> str:
    """A ring split by `segments`; the total goes in the middle."""
    radius, thickness = size / 2 - 12, 22
    circumference = 2 * math.pi * radius
    total = sum(s["value"] for s in segments)
    parts = [
        f'<svg viewBox="0 0 {size} {size}" role="img" aria-label="{escape(center_label)}: {escape(center_value)}" '
        f'style="width:100%;max-width:{size}px;height:auto">',
        f'<circle cx="{size / 2}" cy="{size / 2}" r="{radius}" fill="none" stroke="var(--gray-4)" stroke-width="{thickness}"/>',
    ]
    offset = 0.0
    gap = 2.0 if len(segments) > 1 else 0.0
    for segment in segments:
        if total <= 0:
            break
        length = segment["value"] / total * circumference
        dash = max(length - gap, 0.0)
        parts.append(
            f'<circle cx="{size / 2}" cy="{size / 2}" r="{radius}" fill="none" stroke="{segment["fill"]}" '
            f'stroke-width="{thickness}" stroke-dasharray="{dash:.2f} {circumference - dash:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {size / 2} {size / 2})">'
            f"<title>{escape(segment['name'])}: {escape(segment['value_fmt'])} ({escape(segment['percent_fmt'])})</title></circle>"
        )
        offset += length
    parts.append(
        f'<text x="{size / 2}" y="{size / 2 - 2}" text-anchor="middle" font-size="22" font-weight="500" '
        f'fill="var(--gray-12)" style="font-variant-numeric:tabular-nums">{escape(center_value)}</text>'
        f'<text x="{size / 2}" y="{size / 2 + 18}" text-anchor="middle" font-size="12" fill="var(--gray-11)">'
        f"{escape(center_label)}</text></svg>"
    )
    return "".join(parts)


# ---------------------------------------------------------------- pace
def cumulative_series(daily: dict[str, float], start: str, days: int, until: str | None = None) -> list[float | None]:
    """Running total per day from `start` (a yyyy-mm-dd string) for `days` days; None after `until`."""
    from datetime import date, timedelta

    first = date.fromisoformat(start)
    last = date.fromisoformat(until) if until else None
    total, series = 0.0, []
    for offset in range(days):
        day = first + timedelta(days=offset)
        if last is not None and day > last:
            series.append(None)
            continue
        total += daily.get(day.isoformat(), 0.0)
        series.append(round(total, 2))
    return series


def pace_points(
    current: list[float | None], previous: list[float | None] | None, max_points: int = 45
) -> list[dict[str, Any]]:
    """Chart rows {day, actual, anterior}; long periods are thinned to `max_points`."""
    days = len(current)
    step = max(1, math.ceil(days / max_points))
    indexes = list(range(0, days, step))
    if indexes and indexes[-1] != days - 1:
        indexes.append(days - 1)
    rows = []
    for i in indexes:
        row: dict[str, Any] = {"day": i + 1, "actual": current[i]}
        if previous is not None:
            row["anterior"] = previous[i] if i < len(previous) else None
        rows.append(row)
    return rows


# -------------------------------------------------------------- movers
def movers(
    current: list[dict[str, Any]], previous: list[dict[str, Any]], limit: int = 5
) -> list[dict[str, Any]]:
    """Categories whose spending changed most against the previous period, largest change first."""
    before = {row["name"]: row["value"] for row in previous}
    now = {row["name"]: row["value"] for row in current}
    rows = []
    for name in set(before) | set(now):
        if name == UNCATEGORIZED:
            continue  # a pile of movements nobody has classified is not a trend
        delta = now.get(name, 0.0) - before.get(name, 0.0)
        if abs(delta) < 0.5:
            continue
        rows.append({"name": name, "delta": delta, "now": now.get(name, 0.0), "before": before.get(name, 0.0)})
    rows.sort(key=lambda r: abs(r["delta"]), reverse=True)
    rows = rows[:limit]
    peak = max((abs(r["delta"]) for r in rows), default=1.0) or 1.0
    for row in rows:
        row["up"] = row["delta"] > 0
        row["delta_fmt"] = signed_money(row["delta"])
        row["now_fmt"] = money(row["now"])
        row["bar"] = f"{abs(row['delta']) / peak * 100:.0f}%"
    return rows


# ------------------------------------------------------------ insights
def insights(
    spending: float,
    previous_spending: float | None,
    top_category: tuple[str, float] | None,
    mover: dict[str, Any] | None,
    savings_rate: float | None,
    upcoming_total: float | None,
) -> list[str]:
    """A few plain sentences about the period."""
    lines: list[str] = []
    if spending > 0:
        sentence = f"Has gastado {money(spending)}"
        if previous_spending and previous_spending > 0:
            change = (spending - previous_spending) / previous_spending * 100
            if abs(change) >= 1:
                sentence += f", un {abs(change):.0f} % {'más' if change > 0 else 'menos'} que en el periodo anterior"
        lines.append(sentence + ".")
    if top_category and spending > 0:
        name, value = top_category
        lines.append(f"{name} es lo que más pesa: el {value / spending * 100:.0f} % de tus gastos.")
    if mover:
        verb = "sube" if mover["up"] else "baja"
        lines.append(f"Lo que más {verb} frente al periodo anterior es {mover['name']} ({mover['delta_fmt']}).")
    if savings_rate is not None:
        lines.append(f"Tu tasa de ahorro es del {savings_rate:.0f} %.")
    if upcoming_total:
        lines.append(f"Te quedan por pagar unos {money(upcoming_total)} en cargos fijos este mes.")
    return lines[:5]


# -------------------------------------------------------------- sankey
def sankey_model(
    income: list[dict[str, Any]],
    spending: list[dict[str, Any]],
    saved: float,
    colors: dict[str, str],
) -> dict[str, Any] | None:
    """Flows from where the money came to where it went. None when there is nothing to draw.

    `income` and `spending` are lists of {"name", "value"}. `saved` is the net amount moved to savings accounts.
    The diagram balances itself: a shortfall appears as "Saldo previo" on the left, a surplus as "Sobrante" on the
    right.
    """
    sources = [{"name": r["name"], "value": r["value"], "color": colors.get(r["name"], "green")} for r in income if r["value"] > 0]
    ordered = sorted((r for r in spending if r["value"] > 0), key=lambda r: r["value"], reverse=True)
    uses = [{"name": r["name"], "value": r["value"], "color": colors.get(r["name"], "gray")} for r in ordered[:MAX_FLOW_NODES]]
    rest = sum(r["value"] for r in ordered[MAX_FLOW_NODES:])
    if rest > 0:
        uses.append({"name": OTHERS_LABEL, "value": rest, "color": "gray"})
    if saved > 0.005:
        uses.append({"name": "Ahorro", "value": saved, "color": "blue"})
    elif saved < -0.005:
        sources.append({"name": "Desde ahorro", "value": -saved, "color": "blue"})

    inflow, outflow = sum(s["value"] for s in sources), sum(u["value"] for u in uses)
    if inflow <= 0 and outflow <= 0:
        return None
    if outflow > inflow:
        sources.append({"name": "Saldo previo", "value": outflow - inflow, "color": "gray"})
    elif inflow > outflow:
        uses.append({"name": "Sobrante", "value": inflow - outflow, "color": "green"})
    total = sum(s["value"] for s in sources)
    return {"sources": sources, "uses": uses, "total": total}


MIN_NODE_HEIGHT = 26  # room for a name and an amount


def _fit_scale(columns: list[list[dict[str, Any]]], total: float, usable: float, gap: float) -> float:
    """The largest pixels-per-euro at which every column still fits, giving each node at least its label height."""
    low, high = 0.0, usable / total if total > 0 else 0.0
    for _ in range(40):
        mid = (low + high) / 2
        fits = all(
            sum(max(i["value"] * mid, MIN_NODE_HEIGHT) for i in items) + gap * (len(items) - 1) <= usable
            for items in columns
        )
        low, high = (mid, high) if fits else (low, mid)
    return low


def sankey_svg(model: dict[str, Any] | None, width: int = 760, height: int | None = None) -> str:
    """The cash-flow diagram: sources -> total -> uses, ribbons as wide as the money they carry."""
    if not model:
        return ""
    sources, uses, total = model["sources"], model["uses"], model["total"]
    label_w, node_w, pad_y, gap = 150, 12, 8, 8
    if height is None:  # room for every label, and never a squat picture
        height = max(320, max(len(sources), len(uses)) * (MIN_NODE_HEIGHT + gap) + 2 * pad_y + 40)
    x_left, x_mid, x_right = label_w, width / 2 - node_w / 2, width - label_w - node_w
    usable = height - 2 * pad_y
    scale = _fit_scale([sources, uses], total, usable, gap)
    total_h = total * scale
    mid_y = pad_y + (usable - total_h) / 2

    def stack(items: list[dict[str, Any]]) -> list[tuple[float, float]]:
        """(top, height) of each node, centered as a column."""
        heights = [max(i["value"] * scale, MIN_NODE_HEIGHT) for i in items]
        y = pad_y + (usable - (sum(heights) + gap * (len(items) - 1))) / 2
        boxes = []
        for h in heights:
            boxes.append((y, h))
            y += h + gap
        return boxes

    def ribbon(x0: float, y0: float, x1: float, y1: float, h: float, fill: str, title: str) -> str:
        xm = (x0 + x1) / 2
        return (
            f'<path d="M{x0:.1f},{y0:.1f} C{xm:.1f},{y0:.1f} {xm:.1f},{y1:.1f} {x1:.1f},{y1:.1f} '
            f"L{x1:.1f},{y1 + h:.1f} C{xm:.1f},{y1 + h:.1f} {xm:.1f},{y0 + h:.1f} {x0:.1f},{y0 + h:.1f} Z\" "
            f'fill="{fill}" fill-opacity="0.28"><title>{escape(title)}</title></path>'
        )

    def label(x: float, top: float, h: float, anchor: str, name: str, value: float) -> str:
        shown = name if len(name) <= 22 else name[:21] + "…"
        y = top + h / 2 - 6
        return (
            f'<text x="{x}" y="{y:.1f}" text-anchor="{anchor}" font-size="13" fill="var(--gray-12)">{escape(shown)}</text>'
            f'<text x="{x}" y="{y + 15:.1f}" text-anchor="{anchor}" font-size="12" fill="var(--gray-11)" '
            f'style="font-variant-numeric:tabular-nums">{escape(money(value))}</text>'
        )

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Flujo de caja: de dónde viene el dinero y a dónde va" '
        f'style="width:100%;min-width:560px;height:auto">'
    ]
    cursor = mid_y
    for item, (top, node_h) in zip(sources, stack(sources)):
        h = item["value"] * scale
        fill = color_var(item["color"])
        parts.append(ribbon(x_left + node_w, top + (node_h - h) / 2, x_mid, cursor, h, fill, f"{item['name']}: {money(item['value'])}"))
        parts.append(f'<rect x="{x_left}" y="{top:.1f}" width="{node_w}" height="{node_h:.1f}" rx="3" fill="{fill}"/>')
        parts.append(label(x_left - 8, top, node_h, "end", item["name"], item["value"]))
        cursor += h
    cursor = mid_y
    for item, (top, node_h) in zip(uses, stack(uses)):
        h = item["value"] * scale
        fill = color_var(item["color"])
        parts.append(ribbon(x_mid + node_w, cursor, x_right, top + (node_h - h) / 2, h, fill, f"{item['name']}: {money(item['value'])}"))
        parts.append(f'<rect x="{x_right}" y="{top:.1f}" width="{node_w}" height="{node_h:.1f}" rx="3" fill="{fill}"/>')
        parts.append(label(x_right + node_w + 8, top, node_h, "start", item["name"], item["value"]))
        cursor += h
    parts.append(f'<rect x="{x_mid:.1f}" y="{mid_y:.1f}" width="{node_w}" height="{max(total_h, 1):.1f}" rx="3" fill="var(--gray-12)"/>')
    parts.append("</svg>")
    return "".join(parts)
