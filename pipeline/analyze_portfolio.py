"""Create reusable KPI findings for the portfolio case study."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def money(value: float) -> str:
    return f"RD$ {value:,.0f}"


def analyze(root: Path) -> dict:
    connection = sqlite3.connect(root / "data" / "warehouse" / "aurora_retail.db")
    try:
        overview = pd.read_sql_query(
            """
            SELECT
                SUM(revenue) AS revenue,
                SUM(gross_profit) AS gross_profit,
                100.0 * SUM(gross_profit) / SUM(revenue) AS margin_pct,
                COUNT(DISTINCT order_key) AS orders,
                COUNT(DISTINCT customer_key) AS active_customers,
                SUM(CASE WHEN is_return = 1 THEN 1 ELSE 0 END) AS return_lines,
                COUNT(*) AS sales_lines
            FROM fact_sales
            """,
            connection,
        ).iloc[0]
        monthly = pd.read_sql_query(
            "SELECT * FROM vw_monthly_kpis ORDER BY month_start",
            connection,
        )
        yearly = pd.read_sql_query(
            """
            SELECT
                d.year,
                SUM(f.revenue) AS revenue,
                100.0 * SUM(f.gross_profit) / SUM(f.revenue) AS margin_pct,
                COUNT(DISTINCT f.order_key) AS orders
            FROM fact_sales f
            JOIN dim_date d ON d.date_key = f.date_key
            GROUP BY d.year
            ORDER BY d.year
            """,
            connection,
        )
        stores = pd.read_sql_query(
            "SELECT * FROM vw_store_performance ORDER BY revenue DESC",
            connection,
        )
        categories = pd.read_sql_query(
            "SELECT * FROM vw_category_performance ORDER BY revenue DESC",
            connection,
        )
        channels = pd.read_sql_query(
            """
            SELECT
                ch.channel_name,
                SUM(f.revenue) AS revenue,
                100.0 * SUM(f.gross_profit) / SUM(f.revenue) AS margin_pct,
                COUNT(DISTINCT f.order_key) AS orders
            FROM fact_sales f
            JOIN dim_channel ch ON ch.channel_key = f.channel_key
            GROUP BY ch.channel_name
            ORDER BY revenue DESC
            """,
            connection,
        )
        payments = pd.read_sql_query(
            """
            SELECT
                payment_method,
                SUM(revenue) AS revenue,
                COUNT(DISTINCT order_key) AS orders
            FROM fact_sales
            GROUP BY payment_method
            ORDER BY revenue DESC
            """,
            connection,
        )
        segments = pd.read_sql_query(
            """
            SELECT
                c.segment,
                SUM(f.revenue) AS revenue,
                COUNT(DISTINCT f.order_key) AS orders,
                COUNT(DISTINCT f.customer_key) AS customers,
                100.0 * SUM(f.gross_profit) / SUM(f.revenue) AS margin_pct
            FROM fact_sales f
            JOIN dim_customer c ON c.customer_key = f.customer_key
            GROUP BY c.segment
            ORDER BY revenue DESC
            """,
            connection,
        )
        returns_by_category = pd.read_sql_query(
            """
            SELECT
                p.category,
                100.0 * SUM(CASE WHEN f.is_return = 1 THEN 1 ELSE 0 END) / COUNT(*) AS return_rate_pct
            FROM fact_sales f
            JOIN dim_product p ON p.product_key = f.product_key
            GROUP BY p.category
            ORDER BY return_rate_pct DESC
            """,
            connection,
        )
        monthly_targets = pd.read_sql_query(
            """
            SELECT
                substr(target_month, 1, 7) AS target_month,
                SUM(target_revenue) AS target_revenue
            FROM fact_targets
            GROUP BY substr(target_month, 1, 7)
            ORDER BY target_month
            """,
            connection,
        )
        monthly = monthly.merge(
            monthly_targets.rename(columns={"target_month": "month_start"}),
            on="month_start",
            how="left",
        )
        monthly["target_attainment_pct"] = monthly["revenue"] / monthly["target_revenue"] * 100
        customer_orders = pd.read_sql_query(
            """
            SELECT customer_key, COUNT(DISTINCT order_key) AS order_count
            FROM fact_sales
            GROUP BY customer_key
            """,
            connection,
        )
        target_total = connection.execute("SELECT SUM(target_revenue) FROM fact_targets").fetchone()[0]

        completed_2025 = monthly[monthly["month_start"].str.startswith("2025")]
        current_ytd = monthly[monthly["month_start"].str.startswith("2026")]
        ytd_month_count = len(current_ytd)
        prior_ytd = completed_2025.head(ytd_month_count)
        ytd_growth = current_ytd["revenue"].sum() / prior_ytd["revenue"].sum() - 1
        peak_row = monthly.loc[monthly["revenue"].idxmax()]
        repeat_customers = int((customer_orders["order_count"] > 1).sum())

        summary = {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "period": {
                "start": monthly.iloc[0]["month_start"],
                "end": monthly.iloc[-1]["month_start"],
                "months": len(monthly),
            },
            "headline": {
                "revenue": round(float(overview["revenue"]), 2),
                "gross_profit": round(float(overview["gross_profit"]), 2),
                "margin_pct": round(float(overview["margin_pct"]), 2),
                "orders": int(overview["orders"]),
                "average_ticket": round(float(overview["revenue"] / overview["orders"]), 2),
                "active_customers": int(overview["active_customers"]),
                "repeat_customers": repeat_customers,
                "repeat_customer_rate": round(repeat_customers / len(customer_orders), 4),
                "return_line_rate": round(float(overview["return_lines"] / overview["sales_lines"]), 4),
                "ytd_growth_pct": round(float(ytd_growth * 100), 2),
                "target_revenue": round(float(target_total), 2),
                "target_attainment_pct": round(float(overview["revenue"] / target_total * 100), 2),
            },
            "monthly": monthly.to_dict(orient="records"),
            "yearly": yearly.to_dict(orient="records"),
            "stores": stores.to_dict(orient="records"),
            "categories": categories.to_dict(orient="records"),
            "channels": channels.to_dict(orient="records"),
            "payments": payments.to_dict(orient="records"),
            "segments": segments.to_dict(orient="records"),
            "returns_by_category": returns_by_category.to_dict(orient="records"),
            "peak_month": {
                "month": str(peak_row["month_start"]),
                "revenue": round(float(peak_row["revenue"]), 2),
            },
        }

        export_dir = root / "data" / "export"
        export_dir.mkdir(parents=True, exist_ok=True)
        (export_dir / "executive_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        write_findings(root, summary)
        return summary
    finally:
        connection.close()


def write_findings(root: Path, summary: dict) -> None:
    headline = summary["headline"]
    peak = summary["peak_month"]
    top_store = summary["stores"][0]
    top_category = summary["categories"][0]
    top_channel = summary["channels"][0]
    lowest_margin_category = min(summary["categories"], key=lambda row: row["margin_pct"])
    highest_margin_category = max(summary["categories"], key=lambda row: row["margin_pct"])

    markdown = f"""# Hallazgos del tablero

> Dataset simulado con fines de portafolio. Período: {summary["period"]["start"]} a {summary["period"]["end"]}.

## Resumen ejecutivo

- Ingresos netos: **{money(headline["revenue"])}**.
- Utilidad bruta: **{money(headline["gross_profit"])}** con margen de **{headline["margin_pct"]:.1f}%**.
- Pedidos: **{headline["orders"]:,}**; ticket promedio: **{money(headline["average_ticket"])}**.
- Variación de ingresos año contra año comparable: **{headline["ytd_growth_pct"]:+.1f}%**.
- Cumplimiento global de meta: **{headline["target_attainment_pct"]:.1f}%**.
- Clientes activos: **{headline["active_customers"]:,}**; tasa de recompra: **{headline["repeat_customer_rate"] * 100:.1f}%**.

## Qué muestran los datos

1. **La estacionalidad es material.** {peak["month"][:7]} fue el mes de mayor ingreso
   ({money(peak["revenue"])}); conviene planificar inventario, personal y campañas con antelación.
2. **La tienda líder concentra la operación.** {top_store["store_name"]} aporta
   {money(top_store["revenue"])} y un margen de {top_store["margin_pct"]:.1f}%.
3. **Categoría principal.** {top_category["category"]} lidera en ingresos
   ({money(top_category["revenue"])}); {highest_margin_category["category"]} tiene el mejor margen
   ({highest_margin_category["margin_pct"]:.1f}%) y {lowest_margin_category["category"]} el menor
   ({lowest_margin_category["margin_pct"]:.1f}%).
4. **Canal de venta.** {top_channel["channel_name"]} representa la mayor contribución
   ({money(top_channel["revenue"])}). La mezcla de canal debe leerse junto con ticket y margen,
   no solo con volumen.
5. **Calidad comercial.** La tasa de líneas devueltas es {headline["return_line_rate"] * 100:.1f}%;
   el tablero permite segmentar devoluciones por producto, tienda y canal.

## Recomendaciones accionables

- Revisar precios y promociones en {lowest_margin_category["category"]} para mejorar rentabilidad sin perder volumen.
- Fortalecer campañas de recompra para clientes con una sola compra y medir el efecto en ticket promedio.
- Usar el cumplimiento por tienda/canal como tablero operativo semanal; reservar la lectura mensual para dirección.
- Incorporar costo logístico y unidades devueltas cuando la empresa disponga de esas fuentes para ampliar el análisis.

## Nota metodológica

Los ingresos son netos de descuentos y devoluciones. El pedido se cuenta con `DISTINCTCOUNT(order_key)`;
la granularidad de venta es una línea de pedido. El modelo usa dimensiones de fecha, cliente, producto,
tienda y canal, con hechos de venta y metas.
"""
    (root / "docs" / "HALLAZGOS.md").write_text(markdown, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Aurora Retail KPI tables.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    summary = analyze(args.root.resolve())
    print(json.dumps(summary["headline"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
