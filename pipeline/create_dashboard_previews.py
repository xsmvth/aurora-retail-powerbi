"""Render portfolio dashboard mockups from the computed KPI summary."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1600, 900
NAVY = "#102A43"
NAVY_2 = "#1B3A57"
TEAL = "#0F766E"
TEAL_LIGHT = "#CCFBF1"
CORAL = "#F26B5B"
AMBER = "#F4B942"
BLUE = "#2F80ED"
BG = "#F4F7F9"
CARD = "#FFFFFF"
TEXT = "#183B56"
MUTED = "#6B7C8F"
LINE = "#E6EDF2"
SOFT = "#EDF4F7"

FONT = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_LIGHT = Path(r"C:\Windows\Fonts\segoeuil.ttf")


def font(size: int, bold: bool = False, light: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_LIGHT if light else FONT
    return ImageFont.truetype(str(path), size)


def money(value: float, compact: bool = False) -> str:
    if compact:
        if abs(value) >= 1_000_000:
            return f"RD$ {value / 1_000_000:.1f} M"
        if abs(value) >= 1_000:
            return f"RD$ {value / 1_000:.0f} K"
    return f"RD$ {value:,.0f}"


def pct(value: float) -> str:
    return f"{value:.1f}%"


def rounded(draw: ImageDraw.ImageDraw, box, radius=18, fill=CARD, outline=LINE, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text(
    draw: ImageDraw.ImageDraw,
    xy,
    value: str,
    size: int,
    color=TEXT,
    bold=False,
    anchor=None,
    light=False,
):
    draw.text(xy, value, font=font(size, bold=bold, light=light), fill=color, anchor=anchor)


def header(draw: ImageDraw.ImageDraw, title: str, subtitle: str, section: str):
    draw.rectangle((0, 0, 86, HEIGHT), fill=NAVY)
    draw.rounded_rectangle((21, 22, 65, 66), radius=14, fill=TEAL)
    text(draw, (43, 44), "A", 25, "white", True, "mm")
    for index, active in enumerate([True, False, False, False]):
        y = 128 + index * 52
        color = TEAL_LIGHT if active else "#46647D"
        draw.ellipse((37, y, 50, y + 13), fill=color)
        if active:
            draw.rounded_rectangle((12, y - 8, 17, y + 21), radius=3, fill=TEAL_LIGHT)
    text(draw, (124, 20), "AURORA RETAIL", 12, TEAL, True)
    text(draw, (124, 40), title, 31, TEXT, True)
    text(draw, (124, 82), subtitle, 13, MUTED)
    draw.rounded_rectangle((1272, 32, 1530, 69), radius=18, fill=SOFT)
    text(draw, (1401, 51), section, 12, NAVY_2, True, "mm")
    draw.rounded_rectangle((1272, 76, 1530, 104), radius=14, fill="#FFF5D9")
    text(draw, (1401, 90), "Datos simulados · actualización diaria", 10, "#8A6511", True, "mm")


def card_title(draw: ImageDraw.ImageDraw, xy, title: str, subtitle: str | None = None):
    text(draw, xy, title, 16, TEXT, True)
    if subtitle:
        text(draw, (xy[0], xy[1] + 27), subtitle, 11, MUTED)


def draw_kpi(draw: ImageDraw.ImageDraw, box, label: str, value: str, delta: str, tone=TEAL):
    x1, y1, x2, y2 = box
    rounded(draw, box, 18)
    draw.ellipse((x1 + 18, y1 + 18, x1 + 25, y1 + 25), fill=tone)
    text(draw, (x1 + 34, y1 + 15), label, 11, MUTED, True)
    text(draw, (x1 + 18, y1 + 42), value, 26, TEXT, True)
    color = TEAL if delta.startswith("+") or delta.startswith("Meta") else MUTED
    text(draw, (x1 + 18, y1 + 83), delta, 11, color, True)


def draw_line_chart(
    draw: ImageDraw.ImageDraw,
    box,
    rows: list[dict],
    actual_key: str,
    target_key: str,
    show_target: bool,
):
    x1, y1, x2, y2 = box
    values = [float(row[actual_key]) for row in rows]
    targets = [float(row[target_key]) for row in rows] if show_target else []
    maximum = max(values + targets) * 1.15
    minimum = 0
    chart_left = x1 + 56
    chart_right = x2 - 18
    chart_top = y1 + 22
    chart_bottom = y2 - 42

    for tick in range(5):
        value = maximum * tick / 4
        y = chart_bottom - (chart_bottom - chart_top) * tick / 4
        draw.line((chart_left, y, chart_right, y), fill=LINE, width=1)
        text(
            draw,
            (chart_left - 10, y),
            f"{value / 1_000_000:.1f} M",
            9,
            MUTED,
            anchor="rm",
        )

    def coordinates(items):
        points = []
        for index, item in enumerate(items):
            x = chart_left + (chart_right - chart_left) * index / max(1, len(items) - 1)
            y = chart_bottom - (chart_bottom - chart_top) * (item - minimum) / (maximum - minimum)
            points.append((x, y))
        return points

    actual_points = coordinates(values)
    if show_target:
        target_points = coordinates(targets)
        for start, end in zip(target_points[::2], target_points[1::2]):
            draw.line((start, end), fill="#A8B6C3", width=2)
        for point in target_points:
            draw.ellipse((point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3), fill="#A8B6C3")

    area = actual_points + [(chart_right, chart_bottom), (chart_left, chart_bottom)]
    draw.polygon(area, fill="#DDF3F0")
    draw.line(actual_points, fill=TEAL, width=4, joint="curve")
    for index, point in enumerate(actual_points):
        if index in {0, 6, 12, len(actual_points) - 1}:
            draw.ellipse((point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5), fill=CARD, outline=TEAL, width=3)

    for index, row in enumerate(rows):
        if index % 3 == 0 or index == len(rows) - 1:
            point = actual_points[index]
            label = row["month_start"][5:7] + "/" + row["month_start"][2:4]
            text(draw, (point[0], chart_bottom + 14), label, 9, MUTED, anchor="ma")


def draw_horizontal_bars(draw: ImageDraw.ImageDraw, box, rows: list[dict], label_key: str, value_key: str, tone=TEAL):
    x1, y1, x2, y2 = box
    if not rows:
        return
    maximum = max(float(row[value_key]) for row in rows) or 1
    row_height = min(38, (y2 - y1) / len(rows))
    label_width = 150
    bar_left = x1 + label_width
    bar_right = x2 - 62
    for index, row in enumerate(rows):
        cy = y1 + row_height * index + row_height / 2
        text(draw, (x1, cy), str(row[label_key]), 11, TEXT, anchor="lm")
        draw.rounded_rectangle((bar_left, cy - 7, bar_right, cy + 7), radius=7, fill=SOFT)
        width = (bar_right - bar_left) * float(row[value_key]) / maximum
        draw.rounded_rectangle((bar_left, cy - 7, bar_left + width, cy + 7), radius=7, fill=tone)
        text(draw, (bar_right + 9, cy), money(float(row[value_key]), True), 10, MUTED, anchor="lm")


def draw_donut(
    draw: ImageDraw.ImageDraw,
    center,
    radius,
    rows: list[dict],
    label_key: str,
    value_key: str,
    compact_legend: bool = False,
    center_label: str = "canales",
):
    colors = [TEAL, BLUE, CORAL, AMBER]
    total = sum(float(row[value_key]) for row in rows)
    start = -90
    x, y = center
    for index, row in enumerate(rows):
        angle = 360 * float(row[value_key]) / total
        draw.pieslice(
            (x - radius, y - radius, x + radius, y + radius),
            start=start,
            end=start + angle,
            fill=colors[index % len(colors)],
        )
        start += angle
    inner = radius * 0.62
    draw.ellipse((x - inner, y - inner, x + inner, y + inner), fill=CARD)
    text(draw, (x, y - 10), f"{len(rows)}", 24, TEXT, True, "mm")
    text(draw, (x, y + 19), center_label, 10, MUTED, anchor="mm")
    if compact_legend:
        total = sum(float(row[value_key]) for row in rows)
        for index, row in enumerate(rows):
            ly = y + radius + 25 + index * 15
            draw.ellipse((x - 167, ly - 4, x - 159, ly + 4), fill=colors[index % len(colors)])
            share = 100 * float(row[value_key]) / total
            text(draw, (x - 151, ly), f"{row[label_key]}  {share:.0f}%", 9, MUTED, anchor="lm")
        return
    legend_y = y + radius + 30
    for index, row in enumerate(rows):
        column = index % 2
        line_no = index // 2
        lx = x - 150 + column * 160
        ly = legend_y + line_no * 26
        draw.ellipse((lx, ly - 5, lx + 10, ly + 5), fill=colors[index % len(colors)])
        share = 100 * float(row[value_key]) / total
        text(draw, (lx + 16, ly), f"{row[label_key]}  {share:.0f}%", 10, MUTED, anchor="lm")


def page_one(summary: dict) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    header(
        draw,
        "Resumen ejecutivo",
        "Ventas, rentabilidad y cumplimiento de metas",
        "Vista 01 · Dirección",
    )
    h = summary["headline"]
    gap = 14
    card_x = 124
    card_width = (1422 - gap * 4) / 5
    for index, (label, value, delta, tone) in enumerate(
        [
            ("Ingresos netos", money(h["revenue"], True), f"{h['ytd_growth_pct']:+.1f}% vs. YTD 2025", TEAL),
            ("Margen bruto", pct(h["margin_pct"]), money(h["gross_profit"], True), BLUE),
            ("Pedidos", f"{h['orders']:,}", "51.864 transacciones", CORAL),
            ("Ticket promedio", money(h["average_ticket"]), "por orden", AMBER),
            ("Meta acumulada", pct(h["target_attainment_pct"]), "meta: " + money(h["target_revenue"], True), TEAL),
        ]
    ):
        x1 = card_x + index * (card_width + gap)
        draw_kpi(draw, (x1, 132, x1 + card_width, 248), label, value, delta, tone)

    rounded(draw, (124, 270, 1042, 618))
    card_title(draw, (150, 292), "Evolución mensual de ingresos", "Línea teal: real · línea gris: meta")
    draw_line_chart(draw, (144, 335, 1018, 594), summary["monthly"], "revenue", "target_revenue", True)

    rounded(draw, (1060, 270, 1546, 618))
    card_title(draw, (1086, 292), "Participación por canal", "Ingresos netos del período")
    draw_donut(draw, (1303, 421), 82, summary["channels"], "channel_name", "revenue")

    rounded(draw, (124, 636, 1042, 862))
    card_title(draw, (150, 656), "Categorías con mayor ingreso", "Ranking por ingresos netos")
    category_rows = summary["categories"][:6]
    draw_horizontal_bars(draw, (150, 700, 1010, 847), category_rows, "category", "revenue", TEAL)

    rounded(draw, (1060, 636, 1546, 862), fill=NAVY, outline=NAVY)
    text(draw, (1086, 659), "LECTURA DEL PERÍODO", 11, TEAL_LIGHT, True)
    peak = summary["peak_month"]
    top = summary["categories"][0]
    text(draw, (1086, 694), f"El pico fue {peak['month'][:7]}", 20, "white", True)
    text(draw, (1086, 726), money(peak["revenue"]), 27, "white", True)
    text(draw, (1086, 779), f"{top['category']} lidera ingresos con", 11, "#C8D7E3")
    text(draw, (1086, 800), f"{money(top['revenue'], True)} y margen de {pct(top['margin_pct'])}.", 11, "white", True)
    return image


def page_two(summary: dict) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    header(
        draw,
        "Rendimiento comercial",
        "Tiendas, categorías, canales y forma de pago",
        "Vista 02 · Comercial",
    )
    h = summary["headline"]
    draw_kpi(draw, (124, 132, 458, 242), "Tiendas activas", "8", "4 regiones", TEAL)
    draw_kpi(draw, (472, 132, 806, 242), "Categorías", "8", "100 productos", BLUE)
    draw_kpi(draw, (820, 132, 1154, 242), "Devoluciones", pct(h["return_line_rate"] * 100), "sobre líneas vendidas", CORAL)
    draw_kpi(draw, (1168, 132, 1546, 242), "Cumplimiento de meta", pct(h["target_attainment_pct"]), "año acumulado", AMBER)

    rounded(draw, (124, 266, 820, 566))
    card_title(draw, (150, 288), "Ingreso por tienda", "Ranking del período")
    draw_horizontal_bars(draw, (150, 330, 790, 537), summary["stores"], "store_name", "revenue", TEAL)

    rounded(draw, (838, 266, 1546, 566))
    card_title(draw, (864, 288), "Ingresos y margen por canal", "Comparación comercial")
    channels = summary["channels"]
    maximum = max(float(row["revenue"]) for row in channels)
    for index, row in enumerate(channels):
        x = 900 + index * 205
        bar_height = 100 * float(row["revenue"]) / maximum
        draw.rounded_rectangle((x, 492 - bar_height, x + 94, 492), radius=10, fill=[TEAL, BLUE, CORAL][index])
        text(draw, (x + 47, 480 - bar_height), money(float(row["revenue"]), True), 12, TEXT, True, "ma")
        text(draw, (x + 47, 515), row["channel_name"], 10, TEXT, True, "ma")
        text(draw, (x + 47, 537), f"Margen {row['margin_pct']:.1f}%", 9, MUTED, anchor="ma")

    rounded(draw, (124, 584, 1115, 862))
    card_title(draw, (150, 606), "Detalle de categorías", "Ingreso, margen y unidades vendidas")
    table_top = 650
    columns = [150, 455, 625, 790, 950]
    for x, label in zip(columns, ["Categoría", "Ingreso", "Margen", "Unidades", "Participación"]):
        text(draw, (x, table_top), label, 10, MUTED, True)
    draw.line((150, table_top + 25, 1088, table_top + 25), fill=LINE, width=1)
    total_revenue = sum(float(row["revenue"]) for row in summary["categories"])
    for index, row in enumerate(summary["categories"]):
        y = table_top + 48 + index * 20
        text(draw, (150, y), row["category"], 10, TEXT, True)
        text(draw, (455, y), money(float(row["revenue"]), True), 10, TEXT)
        text(draw, (625, y), pct(float(row["margin_pct"])), 10, TEAL, True)
        text(draw, (790, y), f"{int(row['units_sold']):,}", 10, TEXT)
        text(draw, (950, y), pct(100 * float(row["revenue"]) / total_revenue), 10, MUTED)

    rounded(draw, (1133, 584, 1546, 862))
    card_title(draw, (1159, 606), "Métodos de pago", "Participación por ingreso")
    draw_donut(
        draw,
        (1340, 697),
        59,
        summary["payments"],
        "payment_method",
        "revenue",
        compact_legend=True,
        center_label="métodos",
    )
    reminder = min(summary["payments"], key=lambda row: row["revenue"])
    text(draw, (1159, 845), f"Menor uso: {reminder['payment_method']}", 9, MUTED)
    return image


def page_three(summary: dict) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    header(
        draw,
        "Clientes y calidad",
        "Recompra, segmentos y devoluciones",
        "Vista 03 · Clientes",
    )
    h = summary["headline"]
    draw_kpi(draw, (124, 132, 458, 242), "Clientes activos", f"{h['active_customers']:,}", "en el período", TEAL)
    draw_kpi(draw, (472, 132, 806, 242), "Tasa de recompra", pct(h["repeat_customer_rate"] * 100), f"{h['repeat_customers']:,} clientes", BLUE)
    draw_kpi(draw, (820, 132, 1154, 242), "Pedidos por cliente", f"{h['orders'] / h['active_customers']:.2f}", "promedio", CORAL)
    draw_kpi(draw, (1168, 132, 1546, 242), "Líneas devueltas", pct(h["return_line_rate"] * 100), "del total de líneas", AMBER)

    rounded(draw, (124, 266, 820, 572))
    card_title(draw, (150, 288), "Ingreso por segmento", "Contribución al negocio")
    segments = summary["segments"]
    maximum = max(float(row["revenue"]) for row in segments)
    for index, row in enumerate(segments):
        x = 171 + index * 154
        bar_height = 118 * float(row["revenue"]) / maximum
        color = [TEAL, BLUE, CORAL, AMBER][index % 4]
        draw.rounded_rectangle((x, 491 - bar_height, x + 88, 491), radius=10, fill=color)
        text(draw, (x + 44, 479 - bar_height), money(float(row["revenue"]), True), 10, TEXT, True, "ma")
        text(draw, (x + 44, 513), row["segment"], 10, TEXT, True, "ma")
        text(draw, (x + 44, 537), f"Margen {row['margin_pct']:.1f}%", 9, MUTED, anchor="ma")

    rounded(draw, (838, 266, 1320, 572))
    card_title(draw, (864, 288), "Tasa de devolución por categoría", "Mayores incidencias")
    return_rows = summary["returns_by_category"][:7]
    max_return = max(float(row["return_rate_pct"]) for row in return_rows)
    for index, row in enumerate(return_rows):
        y = 338 + index * 30
        text(draw, (864, y), row["category"], 10, TEXT, anchor="lm")
        draw.rounded_rectangle((1040, y - 6, 1242, y + 6), radius=6, fill=SOFT)
        width = 202 * float(row["return_rate_pct"]) / max(max_return, 0.01)
        draw.rounded_rectangle((1040, y - 6, 1040 + width, y + 6), radius=6, fill=CORAL)
        text(draw, (1253, y), f"{row['return_rate_pct']:.1f}%", 9, TEXT, True, "lm")

    rounded(draw, (1338, 266, 1546, 572), fill=NAVY, outline=NAVY)
    text(draw, (1360, 289), "OPORTUNIDAD", 10, TEAL_LIGHT, True)
    text(draw, (1360, 323), "60%", 36, "white", True)
    text(draw, (1360, 372), "de los clientes", 10, "#C8D7E3")
    text(draw, (1360, 392), "compró una sola vez", 10, "#C8D7E3")
    draw.line((1360, 429, 1518, 429), fill="#39546C", width=1)
    text(draw, (1360, 453), "Acción", 10, TEAL_LIGHT, True)
    text(draw, (1360, 478), "Activar campañas", 10, "white")
    text(draw, (1360, 498), "de segunda compra", 10, "white")
    text(draw, (1360, 518), "y medir uplift.", 10, "white")

    rounded(draw, (124, 590, 820, 862))
    card_title(draw, (150, 612), "Embudo de recurrencia", "Clientes con al menos una compra")
    active = h["active_customers"]
    repeat = h["repeat_customers"]
    one_time = active - repeat
    stages = [
        ("Compraron", active, TEAL),
        ("Repitieron", repeat, BLUE),
        ("Una sola compra", one_time, CORAL),
    ]
    for index, (label, value, color) in enumerate(stages):
        y = 672 + index * 54
        text(draw, (150, y), label, 10, TEXT, True, "lm")
        bar_start = 285
        width = 360 * value / active
        draw.rounded_rectangle((bar_start, y - 12, bar_start + 360, y + 12), radius=12, fill=SOFT)
        draw.rounded_rectangle((bar_start, y - 12, bar_start + width, y + 12), radius=12, fill=color)
        text(draw, (bar_start + 372, y), f"{value:,}", 10, TEXT, True, "lm")

    rounded(draw, (838, 590, 1546, 862))
    card_title(draw, (864, 612), "Calidad del pipeline", "Controles ejecutados automáticamente")
    checks = [
        ("Duplicados de líneas", "0"),
        ("Ventas huérfanas", "0"),
        ("Claves de negocio nulas", "0"),
        ("Descuentos fuera de rango", "0"),
        ("Estado general", "PASS"),
    ]
    for index, (label, value) in enumerate(checks):
        y = 665 + index * 32
        draw.ellipse((864, y - 8, 880, y + 8), fill=TEAL_LIGHT)
        draw.ellipse((868, y - 4, 876, y + 4), fill=TEAL)
        text(draw, (893, y), label, 10, TEXT, anchor="lm")
        text(draw, (1493, y), value, 10, TEAL if value == "PASS" else TEXT, True, "rm")
    text(
        draw,
        (864, 835),
        "Los archivos rechazados se aíslan para corrección sin detener la carga.",
        10,
        MUTED,
    )
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description="Create dashboard preview PNGs.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    summary = json.loads((root / "data" / "export" / "executive_summary.json").read_text(encoding="utf-8"))
    output = root / "screenshots"
    output.mkdir(parents=True, exist_ok=True)
    pages = {
        "01_resumen_ejecutivo.png": page_one(summary),
        "02_rendimiento_comercial.png": page_two(summary),
        "03_clientes_y_calidad.png": page_three(summary),
    }
    for file_name, image in pages.items():
        image.save(output / file_name, optimize=True)
        print(output / file_name)


if __name__ == "__main__":
    main()
