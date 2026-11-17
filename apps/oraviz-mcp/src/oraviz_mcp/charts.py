#!/usr/bin/env python
"""Chart rendering for the Oracle Viz MCP server.

Pure functions: this module knows nothing about Oracle. It takes column names
and rows and renders a PNG with matplotlib's Agg backend, so the server stays
portable -- no display, no JavaScript, works inside a container.

VECTOR columns are handled generically: dense values (``array.array`` or plain
numeric sequences) and sparse values (objects with dimensions, indices and
values) are converted to float lists, and the ``vector`` chart type projects
them to two dimensions with PCA.
"""

from __future__ import annotations

import array
import io
import math
from typing import Any, List, Optional, Sequence, Tuple

import numpy
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

CHART_TYPES = ("bar", "line", "area", "scatter", "pie", "histogram", "vector")

# Oracle red first, followed by a muted, print-friendly palette.
PALETTE = [
    "#C74634",  # Oracle red
    "#3E6C88",  # steel blue
    "#8A9A5B",  # sage
    "#B88A44",  # ochre
    "#6B5B95",  # muted violet
    "#5F7A76",  # slate teal
    "#A0522D",  # sienna
    "#7D8491",  # grey blue
]

MAX_SERIES = 8
MAX_PIE_SLICES = 12
MAX_ANNOTATED_BARS = 12
MAX_ANNOTATED_POINTS = 12
ROTATE_LABELS_AFTER = 6
THIN_TICKS_AFTER = 40
WATERMARK = "oraviz-mcp"


class ChartError(ValueError):
    """Raised when rows and columns cannot produce the requested chart."""


def _to_float(value: Any) -> Optional[float]:
    """Best-effort numeric coercion; non-numeric or non-finite values yield None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        try:
            number = float(str(value).strip())
        except (TypeError, ValueError):
            return None
    return number if math.isfinite(number) else None


def _label(value: Any) -> str:
    if value is None:
        return "(null)"
    text = str(value)
    return text if len(text) <= 24 else text[:21] + "..."


def _vector_values(value: Any) -> Optional[List[float]]:
    """Return a vector cell as a float list, or None if the cell is not a vector.

    Dense VECTOR columns arrive as ``array.array``; sparse VECTOR columns arrive
    as an object with dimensions, indices and values (driver versions name the
    dimensions attribute differently). Plain numeric sequences are accepted too.
    """
    if isinstance(value, array.array):
        return [float(item) for item in value]
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        try:
            return [float(item) for item in value]
        except (TypeError, ValueError):
            return None
    dimensions = getattr(value, "num_dimensions", None)
    if dimensions is None:
        dimensions = getattr(value, "num_elements", None)
    values = getattr(value, "values", None)
    if dimensions is None or values is None:
        return None
    dense = [0.0] * int(dimensions)
    indices = getattr(value, "indices", range(len(values)))
    for index, item in zip(indices, values):
        position = int(index)
        if 0 <= position < len(dense):
            dense[position] = float(item)
    return dense


def _compact_number(value: float) -> str:
    """Human-friendly bar labels: thousands get separators, small values stay short."""
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:g}"


def _prepare(
    columns: Sequence[str], rows: Sequence[Sequence[Any]]
) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    if not columns:
        raise ChartError("The query returned no columns to plot.")
    if not rows:
        raise ChartError("The query returned no rows to plot.")
    return list(columns), [tuple(row) for row in rows]


def _numeric_indexes(columns: Sequence[str], rows: Sequence[Tuple[Any, ...]]) -> List[int]:
    """Column positions (including 0) that hold at least one finite number."""
    indexes: List[int] = []
    for index in range(len(columns)):
        if any(_to_float(row[index]) is not None for row in rows):
            indexes.append(index)
    return indexes


def _style_axes(ax, columns: Sequence[str], x_label: Optional[str], y_label: Optional[str]) -> None:
    ax.grid(True, axis="y", alpha=0.25, linewidth=0.7)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    if x_label:
        ax.set_xlabel(x_label)
    if y_label:
        ax.set_ylabel(y_label)


def _category_positions(ax, labels: Sequence[str]) -> List[int]:
    positions = list(range(len(labels)))
    ax.set_xticks(positions)
    ax.set_xticklabels(
        labels,
        rotation=45 if len(labels) > ROTATE_LABELS_AFTER else 0,
        ha="right" if len(labels) > ROTATE_LABELS_AFTER else "center",
        fontsize=9,
    )
    if len(labels) > THIN_TICKS_AFTER:
        step = max(1, math.ceil(len(labels) / 20))
        for index, tick in enumerate(ax.get_xticklabels()):
            if index % step:
                tick.set_visible(False)
    return positions


def _render_bar(ax, columns, rows, x_label, y_label) -> None:
    numeric = [index for index in _numeric_indexes(columns, rows) if index >= 1]
    if not numeric:
        raise ChartError("Bar charts need at least one numeric column after the label column.")
    numeric = numeric[:MAX_SERIES]
    labels = [_label(row[0]) for row in rows]
    positions = _category_positions(ax, labels)
    width = 0.8 / len(numeric)
    for series, index in enumerate(numeric):
        values = [_to_float(row[index]) or 0.0 for row in rows]
        offset = (series - (len(numeric) - 1) / 2) * width
        bars = ax.bar(
            [position + offset for position in positions],
            values,
            width=width,
            label=columns[index],
            color=PALETTE[series % len(PALETTE)],
        )
        if len(positions) <= MAX_ANNOTATED_BARS and len(numeric) <= 4:
            ax.bar_label(bars, fmt=_compact_number, padding=2, fontsize=8, color="#4A4A4A")
    if len(numeric) > 1:
        ax.legend(fontsize=9, frameon=False)
    _style_axes(ax, columns, x_label or columns[0], y_label)


def _render_line(ax, columns, rows, x_label, y_label, fill: bool) -> None:
    numeric = [index for index in _numeric_indexes(columns, rows) if index >= 1]
    if not numeric:
        kind = "Area" if fill else "Line"
        raise ChartError(f"{kind} charts need at least one numeric column after the label column.")
    numeric = numeric[:MAX_SERIES]
    labels = [_label(row[0]) for row in rows]
    positions = _category_positions(ax, labels)
    for series, index in enumerate(numeric):
        values = [_to_float(row[index]) for row in rows]
        color = PALETTE[series % len(PALETTE)]
        if fill:
            ax.fill_between(positions, [value or 0.0 for value in values], alpha=0.22, color=color)
        ax.plot(positions, values, label=columns[index], color=color, linewidth=2.0, marker="o", markersize=3.5)
    if len(numeric) > 1:
        ax.legend(fontsize=9, frameon=False)
    _style_axes(ax, columns, x_label or columns[0], y_label)


def _render_scatter(ax, columns, rows, x_label, y_label) -> None:
    numeric = _numeric_indexes(columns, rows)
    if len(numeric) < 2:
        raise ChartError("Scatter charts need two numeric columns.")
    x_index, y_index = numeric[0], numeric[1]
    xs = [_to_float(row[x_index]) for row in rows]
    ys = [_to_float(row[y_index]) for row in rows]
    points = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if not points:
        raise ChartError("Scatter charts need at least one row where both columns are numeric.")
    ax.scatter(
        [point[0] for point in points],
        [point[1] for point in points],
        color=PALETTE[0],
        s=28,
        alpha=0.75,
        edgecolors="white",
        linewidths=0.5,
    )
    _style_axes(ax, columns, x_label or columns[x_index], y_label or columns[y_index])


def _render_pie(ax, columns, rows, x_label, y_label) -> None:
    numeric = [index for index in _numeric_indexes(columns, rows) if index >= 1]
    if not numeric:
        raise ChartError("Pie charts need a label column plus one numeric column.")
    value_index = numeric[0]
    totals: dict[str, float] = {}
    for row in rows:
        value = _to_float(row[value_index])
        if value is None:
            continue
        if value < 0:
            raise ChartError("Pie charts need non-negative values.")
        label = _label(row[0])
        totals[label] = totals.get(label, 0.0) + value
    totals = {label: value for label, value in totals.items() if value > 0}
    if not totals:
        raise ChartError("Pie charts need at least one positive value.")
    items = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    if len(items) > MAX_PIE_SLICES:
        head, tail = items[: MAX_PIE_SLICES - 1], items[MAX_PIE_SLICES - 1 :]
        items = head + [("Other", sum(value for _, value in tail))]
    ax.pie(
        [value for _, value in items],
        labels=[label for label, _ in items],
        colors=[PALETTE[index % len(PALETTE)] for index in range(len(items))],
        autopct="%1.1f%%",
        pctdistance=0.75,
        startangle=90,
        counterclock=False,
        wedgeprops={"edgecolor": "white", "linewidth": 1.0},
        textprops={"fontsize": 9},
    )
    _style_axes(ax, columns, x_label, y_label)


def _render_histogram(ax, columns, rows, x_label, y_label) -> None:
    numeric = _numeric_indexes(columns, rows)
    if not numeric:
        raise ChartError("Histogram charts need a numeric column.")
    value_index = numeric[0]
    values = [value for value in (_to_float(row[value_index]) for row in rows) if value is not None]
    if not values:
        raise ChartError("Histogram charts need at least one numeric value.")
    bins = max(5, min(40, int(math.sqrt(len(values)))))
    ax.hist(values, bins=bins, color=PALETTE[0], edgecolor="white", linewidth=0.8)
    _style_axes(ax, columns, x_label or columns[value_index], y_label or "count")


def _project_vectors(
    vectors: Sequence[Sequence[float]],
) -> Tuple[List[float], List[float], List[float]]:
    """Project vectors onto their first two principal components (PCA via SVD).

    Returns the x scores, the y scores, and the explained-variance ratio of
    each component.
    """
    if len(vectors) < 2:
        raise ChartError("Vector charts need at least two vectors to project.")
    dimension = len(vectors[0])
    if dimension < 2:
        raise ChartError("Vector charts need vectors with at least two dimensions.")
    if any(len(vector) != dimension for vector in vectors):
        raise ChartError("Vector charts need vectors of the same length.")
    matrix = numpy.asarray(vectors, dtype=float)
    if not numpy.isfinite(matrix).all():
        raise ChartError("Vector charts need finite vector values.")
    centered = matrix - matrix.mean(axis=0)
    # Thin SVD: the principal-component scores are U * S.
    left, singular, _ = numpy.linalg.svd(centered, full_matrices=False)
    variance = singular**2
    total = float(variance.sum())
    if total <= 0:
        raise ChartError("Vector charts need vectors that are not all identical.")
    explained = (variance / total).tolist()
    scores = left * singular
    return scores[:, 0].tolist(), scores[:, 1].tolist(), [float(value) for value in explained[:2]]


def _render_vector(ax, columns, rows, x_label, y_label) -> None:
    vector_index = next(
        (
            index
            for index in range(len(columns))
            if any(_vector_values(row[index]) is not None for row in rows)
        ),
        None,
    )
    if vector_index is None:
        raise ChartError("Vector charts need a VECTOR column (select one from the database).")
    label_index = next((index for index in range(len(columns)) if index != vector_index), None)
    vectors: List[List[float]] = []
    labels: List[str] = []
    for row in rows:
        vector = _vector_values(row[vector_index])
        if vector is None:
            continue
        vectors.append(vector)
        labels.append(_label(row[label_index]) if label_index is not None else "")
    xs, ys, explained = _project_vectors(vectors)
    ax.scatter(xs, ys, color=PALETTE[0], s=28, alpha=0.75, edgecolors="white", linewidths=0.5)
    if len(xs) <= MAX_ANNOTATED_POINTS and any(labels):
        for x, y, label in zip(xs, ys, labels):
            ax.annotate(
                label,
                (x, y),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=7,
                color="#4A4A4A",
            )
    _style_axes(
        ax,
        columns,
        x_label or f"PC1 ({explained[0] * 100:.1f}% variance)",
        y_label or f"PC2 ({explained[1] * 100:.1f}% variance)",
    )


def render_chart(
    columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
    chart_type: str,
    title: Optional[str] = None,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
) -> bytes:
    """Render rows as a PNG chart and return the encoded image bytes."""
    chart_type = (chart_type or "").strip().lower()
    if chart_type not in CHART_TYPES:
        raise ChartError(
            f"Unsupported chart_type '{chart_type}'. Valid types: {', '.join(CHART_TYPES)}"
        )
    columns, rows = _prepare(columns, rows)

    figure = Figure(figsize=(9.0, 5.0), dpi=144)
    FigureCanvasAgg(figure)
    ax = figure.add_subplot()
    figure.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    try:
        if chart_type == "bar":
            _render_bar(ax, columns, rows, x_label, y_label)
        elif chart_type == "line":
            _render_line(ax, columns, rows, x_label, y_label, fill=False)
        elif chart_type == "area":
            _render_line(ax, columns, rows, x_label, y_label, fill=True)
        elif chart_type == "scatter":
            _render_scatter(ax, columns, rows, x_label, y_label)
        elif chart_type == "pie":
            _render_pie(ax, columns, rows, x_label, y_label)
        elif chart_type == "vector":
            _render_vector(ax, columns, rows, x_label, y_label)
        else:
            _render_histogram(ax, columns, rows, x_label, y_label)

        if title:
            ax.set_title(title, fontsize=13, fontweight="bold", color="#1B1B1B")
        figure.text(0.995, 0.01, WATERMARK, ha="right", va="bottom", fontsize=7, color="#9A9A9A")

        buffer = io.BytesIO()
        figure.savefig(buffer, format="png", bbox_inches="tight", facecolor=figure.get_facecolor())
        return buffer.getvalue()
    finally:
        figure.clear()
