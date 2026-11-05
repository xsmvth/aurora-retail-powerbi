"""Incremental ETL from CSV landing files to the Aurora Retail star schema.

Flow:
1. Validate reference and transaction files.
2. Upsert dimensions in SQLite.
3. Load only new transaction files (SHA-256 file registry).
4. Upsert facts by sale_line_id, making retries idempotent.
5. Export Power BI-ready CSV tables and a data-quality report.
6. Optionally synchronize the full star schema to PostgreSQL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_SALES_COLUMNS = {
    "sale_line_id",
    "order_id",
    "order_date",
    "customer_id",
    "product_id",
    "store_id",
    "channel_id",
    "quantity",
    "unit_price",
    "discount_pct",
    "unit_cost",
    "is_return",
    "payment_method",
}

MONTH_NAMES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}
MONTH_SHORT = {
    1: "ene",
    2: "feb",
    3: "mar",
    4: "abr",
    5: "may",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "sep",
    10: "oct",
    11: "nov",
    12: "dic",
}
WEEKDAY_NAMES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def migrate_sqlite(connection: sqlite3.Connection) -> None:
    """Apply small, non-destructive upgrades to warehouses created by older versions."""
    table_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'dim_date'"
    ).fetchone()
    if not table_exists:
        return
    columns = {row[1] for row in connection.execute("PRAGMA table_info(dim_date)")}
    if "month_key" not in columns:
        connection.execute("ALTER TABLE dim_date ADD COLUMN month_key TEXT")
        connection.execute("UPDATE dim_date SET month_key = substr(date, 1, 7)")
        connection.commit()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def require_columns(frame: pd.DataFrame, columns: set[str], source: Path) -> None:
    missing = columns.difference(frame.columns)
    if missing:
        raise ValueError(f"{source.name}: faltan columnas obligatorias: {sorted(missing)}")


def build_date_dimension(start: date, end: date) -> pd.DataFrame:
    rows = []
    for value in pd.date_range(start, end, freq="D"):
        current = value.date()
        rows.append(
            {
                "date_key": int(current.strftime("%Y%m%d")),
                "date": current.isoformat(),
                "year": current.year,
                "quarter": (current.month - 1) // 3 + 1,
                "month_number": current.month,
                "month_name": MONTH_NAMES[current.month],
                "month_short": MONTH_SHORT[current.month],
                "month_start": current.replace(day=1).isoformat(),
                "month_key": current.strftime("%Y-%m"),
                "week_number": current.isocalendar().week,
                "weekday_name": WEEKDAY_NAMES[current.weekday()],
                "is_weekend": int(current.weekday() >= 5),
            }
        )
    return pd.DataFrame(rows)


def upsert_frame(
    connection: sqlite3.Connection,
    frame: pd.DataFrame,
    table: str,
    conflict_columns: list[str],
) -> None:
    if frame.empty:
        return
    columns = list(frame.columns)
    placeholders = ", ".join("?" for _ in columns)
    update_columns = [column for column in columns if column not in conflict_columns]
    updates = ", ".join(f"{column} = excluded.{column}" for column in update_columns)
    statement = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT ({', '.join(conflict_columns)}) DO UPDATE SET {updates}"
    )
    connection.executemany(
        statement,
        [
            tuple(None if pd.isna(value) else value.item() if hasattr(value, "item") else value for value in row)
            for row in frame.itertuples(index=False, name=None)
        ],
    )


def load_reference_data(
    connection: sqlite3.Connection,
    reference_dir: Path,
) -> dict[str, pd.DataFrame]:
    customers = read_csv(reference_dir / "customers.csv")
    products = read_csv(reference_dir / "products.csv")
    stores = read_csv(reference_dir / "stores.csv")
    channels = read_csv(reference_dir / "channels.csv")

    require_columns(
        customers,
        {"customer_id", "customer_name", "segment", "region", "city", "signup_date", "is_active"},
        reference_dir / "customers.csv",
    )
    require_columns(
        products,
        {"product_id", "product_name", "category", "subcategory", "list_price", "unit_cost", "is_active"},
        reference_dir / "products.csv",
    )
    require_columns(
        stores,
        {"store_id", "store_name", "region", "city", "store_type", "opening_date"},
        reference_dir / "stores.csv",
    )
    require_columns(channels, {"channel_id", "channel_name"}, reference_dir / "channels.csv")

    customer_dim = customers[
        ["customer_id", "customer_name", "segment", "region", "city", "signup_date", "is_active"]
    ].rename(columns={"customer_id": "customer_key"})
    product_dim = products[
        ["product_id", "product_name", "category", "subcategory", "list_price", "unit_cost", "is_active"]
    ].rename(columns={"product_id": "product_key"})
    store_dim = stores[
        ["store_id", "store_name", "region", "city", "store_type", "opening_date"]
    ].rename(columns={"store_id": "store_key"})
    channel_dim = channels[["channel_id", "channel_name"]].rename(columns={"channel_id": "channel_key"})

    for frame, key in (
        (customer_dim, "customer_key"),
        (product_dim, "product_key"),
        (store_dim, "store_key"),
        (channel_dim, "channel_key"),
    ):
        if frame[key].duplicated().any():
            duplicates = frame.loc[frame[key].duplicated(), key].head(5).tolist()
            raise ValueError(f"Claves duplicadas en {key}: {duplicates}")

    upsert_frame(connection, customer_dim, "dim_customer", ["customer_key"])
    upsert_frame(connection, product_dim, "dim_product", ["product_key"])
    upsert_frame(connection, store_dim, "dim_store", ["store_key"])
    upsert_frame(connection, channel_dim, "dim_channel", ["channel_key"])

    return {
        "customers": customer_dim,
        "products": product_dim,
        "stores": store_dim,
        "channels": channel_dim,
    }


def discover_sales_files(sales_dir: Path) -> list[Path]:
    files = sorted(path for path in sales_dir.rglob("*.csv") if path.is_file())
    if not files:
        raise FileNotFoundError(f"No se encontraron CSV de ventas en {sales_dir}")
    return files


def get_date_bounds(files: list[Path], targets: pd.DataFrame) -> tuple[date, date]:
    minimum: date | None = None
    maximum: date | None = None
    for path in files:
        dates = pd.to_datetime(read_csv(path)["order_date"], errors="raise").dt.date
        file_min = dates.min()
        file_max = dates.max()
        minimum = file_min if minimum is None else min(minimum, file_min)
        maximum = file_max if maximum is None else max(maximum, file_max)
    target_months = pd.to_datetime(targets["target_month"] + "-01").dt.date
    minimum = min(minimum, target_months.min())  # type: ignore[arg-type]
    target_max = (target_months + pd.offsets.MonthEnd(0)).max()
    maximum = max(maximum, target_max.date() if hasattr(target_max, "date") else target_max)
    return minimum, maximum


def validate_sales(
    frame: pd.DataFrame,
    source: Path,
    keys: dict[str, set[str]],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    require_columns(frame, REQUIRED_SALES_COLUMNS, source)
    work = frame.copy()
    rejection_messages: dict[int, str] = {}

    for column in ("sale_line_id", "order_id", "customer_id", "product_id", "store_id", "channel_id"):
        work[column] = work[column].astype("string").str.strip()
    for column in ("quantity", "unit_price", "discount_pct", "unit_cost", "is_return"):
        work[column] = pd.to_numeric(work[column], errors="coerce")

    required_not_null = REQUIRED_SALES_COLUMNS - {"is_return"}
    null_mask = work[list(required_not_null)].isna().any(axis=1)
    for index in work.index[null_mask]:
        rejection_messages[int(index)] = "campos obligatorios vacíos o numéricos inválidos"

    invalid_quantity = work["quantity"].fillna(1).eq(0)
    invalid_discount = ~work["discount_pct"].fillna(-1).between(0, 0.95)
    invalid_price = work["unit_price"].fillna(-1).lt(0)
    invalid_cost = work["unit_cost"].fillna(-1).lt(0)
    invalid_return = work["is_return"].fillna(-1).isin([0, 1]) == False  # noqa: E712

    for mask, message in (
        (invalid_quantity, "cantidad igual a cero"),
        (invalid_discount, "descuento fuera de 0–0.95"),
        (invalid_price, "precio unitario negativo"),
        (invalid_cost, "costo unitario negativo"),
        (invalid_return, "is_return debe ser 0 o 1"),
    ):
        for index in work.index[mask]:
            rejection_messages.setdefault(int(index), message)

    missing_customer = ~work["customer_id"].isin(keys["customer"])
    missing_product = ~work["product_id"].isin(keys["product"])
    missing_store = ~work["store_id"].isin(keys["store"])
    missing_channel = ~work["channel_id"].isin(keys["channel"])
    for mask, message in (
        (missing_customer, "customer_id no existe en la dimensión"),
        (missing_product, "product_id no existe en la dimensión"),
        (missing_store, "store_id no existe en la dimensión"),
        (missing_channel, "channel_id no existe en la dimensión"),
    ):
        for index in work.index[mask]:
            rejection_messages.setdefault(int(index), message)

    parsed_dates = pd.to_datetime(work["order_date"], errors="coerce")
    for index in work.index[parsed_dates.isna()]:
        rejection_messages.setdefault(int(index), "order_date inválida")
    work["order_date"] = parsed_dates.dt.date.astype("string")

    valid = work.drop(index=list(rejection_messages)).copy()
    duplicates_before = len(valid)
    valid = valid.drop_duplicates(subset=["sale_line_id"], keep="last")
    if duplicates_before != len(valid):
        for sale_line_id in work.loc[work["sale_line_id"].duplicated(keep=False), "sale_line_id"].head(5):
            rejection_messages.setdefault(
                int(work.index[work["sale_line_id"].eq(sale_line_id)][0]),
                f"sale_line_id duplicado en archivo: {sale_line_id}",
            )

    valid["quantity"] = valid["quantity"].astype("int64")
    valid["is_return"] = valid["is_return"].astype("int64")
    valid["unit_price"] = valid["unit_price"].astype(float)
    valid["discount_pct"] = valid["discount_pct"].astype(float)
    valid["unit_cost"] = valid["unit_cost"].astype(float)
    valid["revenue"] = valid["quantity"] * valid["unit_price"] * (1 - valid["discount_pct"])
    valid["cost"] = valid["quantity"] * valid["unit_cost"]
    valid["gross_profit"] = valid["revenue"] - valid["cost"]
    valid["loaded_at"] = utc_now()

    rejected = [
        {
            "source_file": source.name,
            "source_row": int(index) + 2,
            "sale_line_id": str(work.at[index, "sale_line_id"]),
            "reason": reason,
        }
        for index, reason in sorted(rejection_messages.items())
    ]
    return valid, rejected


def ingest_sales_files(
    connection: sqlite3.Connection,
    files: list[Path],
    keys: dict[str, set[str]],
) -> tuple[int, list[dict[str, Any]], list[str]]:
    processed_hashes = {
        (row[0], row[1])
        for row in connection.execute(
            "SELECT file_name, file_hash FROM etl_file_registry WHERE status = 'SUCCESS'"
        ).fetchall()
    }
    total_seen = 0
    rejected: list[dict[str, Any]] = []
    processed_files: list[str] = []

    for path in files:
        digest = file_hash(path)
        relative_name = path.relative_to(path.parents[2]).as_posix()
        if (relative_name, digest) in processed_hashes:
            continue

        raw = read_csv(path)
        total_seen += len(raw)
        valid, file_rejected = validate_sales(raw, path, keys)
        rejected.extend(file_rejected)

        fact = valid.rename(
            columns={
                "sale_line_id": "sale_line_key",
                "order_id": "order_key",
                "customer_id": "customer_key",
                "product_id": "product_key",
                "store_id": "store_key",
                "channel_id": "channel_key",
            }
        )
        fact["date_key"] = pd.to_datetime(fact["order_date"]).dt.strftime("%Y%m%d").astype(int)
        fact_columns = [
            "sale_line_key",
            "order_key",
            "date_key",
            "customer_key",
            "product_key",
            "store_key",
            "channel_key",
            "quantity",
            "unit_price",
            "discount_pct",
            "revenue",
            "cost",
            "gross_profit",
            "is_return",
            "payment_method",
            "loaded_at",
        ]
        upsert_frame(connection, fact[fact_columns], "fact_sales", ["sale_line_key"])
        connection.execute(
            """
            INSERT INTO etl_file_registry
                (file_name, file_hash, row_count, processed_at, status)
            VALUES (?, ?, ?, ?, 'SUCCESS')
            """,
            (relative_name, digest, len(raw), utc_now()),
        )
        connection.commit()
        processed_files.append(relative_name)

    return total_seen, rejected, processed_files


def load_targets(connection: sqlite3.Connection, path: Path) -> pd.DataFrame:
    targets = read_csv(path)
    require_columns(targets, {"target_month", "store_id", "channel_id", "target_revenue"}, path)
    if targets.duplicated(["target_month", "store_id", "channel_id"]).any():
        raise ValueError("monthly_targets.csv contiene claves duplicadas")
    targets["target_revenue"] = pd.to_numeric(targets["target_revenue"], errors="raise")
    target_fact = targets.rename(columns={"store_id": "store_key", "channel_id": "channel_key"})
    upsert_frame(
        connection,
        target_fact[["target_month", "store_key", "channel_key", "target_revenue"]],
        "fact_targets",
        ["target_month", "store_key", "channel_key"],
    )
    connection.commit()
    return targets


def query_frame(connection: sqlite3.Connection, query: str) -> pd.DataFrame:
    return pd.read_sql_query(query, connection)


def atomic_csv(frame: pd.DataFrame, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8-sig")
    temporary.replace(destination)


def export_for_power_bi(connection: sqlite3.Connection, root: Path) -> dict[str, int]:
    export_dir = root / "data" / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    queries = {
        "dim_date.csv": "SELECT * FROM dim_date ORDER BY date_key",
        "dim_month.csv": "SELECT * FROM dim_month ORDER BY month_key",
        "dim_customer.csv": "SELECT * FROM dim_customer ORDER BY customer_key",
        "dim_product.csv": "SELECT * FROM dim_product ORDER BY product_key",
        "dim_store.csv": "SELECT * FROM dim_store ORDER BY store_key",
        "dim_channel.csv": "SELECT * FROM dim_channel ORDER BY channel_key",
        "fact_sales.csv": (
            "SELECT * FROM fact_sales "
            "ORDER BY date_key, order_key, sale_line_key"
        ),
        "fact_targets.csv": (
            "SELECT * FROM fact_targets "
            "ORDER BY target_month, store_key, channel_key"
        ),
        "vw_monthly_kpis.csv": "SELECT * FROM vw_monthly_kpis ORDER BY month_start",
        "vw_store_performance.csv": (
            "SELECT * FROM vw_store_performance ORDER BY revenue DESC"
        ),
        "vw_category_performance.csv": (
            "SELECT * FROM vw_category_performance ORDER BY revenue DESC"
        ),
    }

    counts = {}
    for file_name, query in queries.items():
        frame = query_frame(connection, query)
        atomic_csv(frame, export_dir / file_name)
        counts[file_name] = len(frame)

    manifest = {
        "generated_at": utc_now(),
        "source_database": "data/warehouse/aurora_retail.db",
        "tables": counts,
        "currency": "DOP",
        "note": "CSV reproducibles para importar desde Power BI Desktop.",
    }
    (export_dir / "_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return counts


def run_quality_checks(
    connection: sqlite3.Connection,
    rejection_count: int,
) -> dict[str, Any]:
    scalar_checks = {
        "duplicate_sale_lines": connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT sale_line_key FROM fact_sales
                GROUP BY sale_line_key HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0],
        "orphan_sales_rows": connection.execute(
            """
            SELECT COUNT(*)
            FROM fact_sales f
            LEFT JOIN dim_date d ON d.date_key = f.date_key
            LEFT JOIN dim_customer c ON c.customer_key = f.customer_key
            LEFT JOIN dim_product p ON p.product_key = f.product_key
            LEFT JOIN dim_store s ON s.store_key = f.store_key
            LEFT JOIN dim_channel ch ON ch.channel_key = f.channel_key
            WHERE d.date_key IS NULL OR c.customer_key IS NULL
               OR p.product_key IS NULL OR s.store_key IS NULL OR ch.channel_key IS NULL
            """
        ).fetchone()[0],
        "null_business_keys": connection.execute(
            """
            SELECT COUNT(*) FROM fact_sales
            WHERE order_key IS NULL OR customer_key IS NULL OR product_key IS NULL
            """
        ).fetchone()[0],
        "return_flag_mismatches": connection.execute(
            """
            SELECT COUNT(*) FROM fact_sales
            WHERE (is_return = 1 AND quantity >= 0)
               OR (is_return = 0 AND quantity < 0)
            """
        ).fetchone()[0],
        "unexpected_discounts": connection.execute(
            "SELECT COUNT(*) FROM fact_sales WHERE discount_pct < 0 OR discount_pct > 0.95"
        ).fetchone()[0],
    }
    hard_failures = sum(value for value in scalar_checks.values() if value)
    result = {
        "generated_at": utc_now(),
        "status": "PASS" if hard_failures == 0 else "FAIL",
        "rows_rejected_in_current_run": rejection_count,
        "checks": scalar_checks,
        "row_counts": {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "dim_customer",
                "dim_product",
                "dim_store",
                "dim_channel",
                "dim_month",
                "fact_sales",
                "fact_targets",
            )
        },
    }
    return result


def write_quality_report(root: Path, result: dict[str, Any], rejected: list[dict[str, Any]]) -> None:
    reports = root / "data" / "quality"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "data_quality_report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if rejected:
        pd.DataFrame(rejected).to_csv(
            reports / "rejected_rows.csv",
            index=False,
            encoding="utf-8-sig",
        )
    else:
        (reports / "rejected_rows.csv").write_text(
            "source_file,source_row,sale_line_id,reason\n",
            encoding="utf-8-sig",
        )

    lines = [
        "# Reporte de calidad de datos",
        "",
        f"Generado: {result['generated_at']}",
        "",
        f"**Estado:** {result['status']}",
        "",
        "## Controles",
        "",
        "| Control | Incidencias |",
        "|---|---:|",
    ]
    for name, value in result["checks"].items():
        lines.append(f"| {name} | {value} |")
    lines.extend(
        [
            "",
            f"Filas rechazadas en la última ejecución: **{result['rows_rejected_in_current_run']}**",
            "",
            "Los datos rechazados se registran en `rejected_rows.csv` para corrección en origen.",
        ]
    )
    (reports / "data_quality_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def synchronize_postgres(export_dir: Path) -> dict[str, int] | None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return None
    try:
        from sqlalchemy import create_engine, text
    except ImportError as exc:
        raise RuntimeError(
            "DATABASE_URL está configurada. Instala requirements.txt para sincronizar PostgreSQL."
        ) from exc

    engine = create_engine(database_url, pool_pre_ping=True)
    table_order = [
        "dim_date",
        "dim_customer",
        "dim_product",
        "dim_store",
        "dim_channel",
        "fact_sales",
        "fact_targets",
    ]
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE fact_targets, fact_sales, dim_channel, dim_store, "
                "dim_product, dim_customer, dim_date CASCADE"
            )
        )
        for table in table_order:
            frame = read_csv(export_dir / f"{table}.csv")
            if table in {"dim_customer", "dim_product"}:
                frame["is_active"] = frame["is_active"].astype(bool)
            if table == "fact_sales":
                frame["is_return"] = frame["is_return"].astype(bool)
            frame.to_sql(table, connection, if_exists="append", index=False, method="multi", chunksize=5000)
    return {table: len(read_csv(export_dir / f"{table}.csv")) for table in table_order}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Aurora Retail ETL.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root.",
    )
    parser.add_argument(
        "--skip-postgres",
        action="store_true",
        help="Do not synchronize PostgreSQL even when DATABASE_URL exists.",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    database_path = root / "data" / "warehouse" / "aurora_retail.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    migrate_sqlite(connection)
    schema_sql = (root / "database" / "schema_sqlite.sql").read_text(encoding="utf-8")
    connection.executescript(schema_sql)
    started_at = utc_now()
    cursor = connection.execute(
        "INSERT INTO etl_run_log (started_at, status) VALUES (?, 'RUNNING')",
        (started_at,),
    )
    run_id = cursor.lastrowid
    connection.commit()

    try:
        references = load_reference_data(connection, root / "data" / "raw" / "reference")
        targets_raw = read_csv(root / "data" / "raw" / "reference" / "monthly_targets.csv")
        sales_files = discover_sales_files(root / "data" / "landing" / "sales")
        minimum, maximum = get_date_bounds(sales_files, targets_raw)
        date_dim = build_date_dimension(minimum, maximum)
        upsert_frame(connection, date_dim, "dim_date", ["date_key"])
        targets = load_targets(connection, root / "data" / "raw" / "reference" / "monthly_targets.csv")

        keys = {
            "customer": set(references["customers"]["customer_key"]),
            "product": set(references["products"]["product_key"]),
            "store": set(references["stores"]["store_key"]),
            "channel": set(references["channels"]["channel_key"]),
        }
        total_seen, rejected, processed_files = ingest_sales_files(connection, sales_files, keys)
        connection.commit()

        quality = run_quality_checks(connection, len(rejected))
        write_quality_report(root, quality, rejected)
        export_counts = export_for_power_bi(connection, root)
        postgres_counts = None
        if not args.skip_postgres:
            postgres_counts = synchronize_postgres(root / "data" / "export")

        connection.execute(
            """
            UPDATE etl_run_log
            SET finished_at = ?, sale_rows_seen = ?, rows_rejected = ?, status = ?, message = ?
            WHERE run_id = ?
            """,
            (
                utc_now(),
                total_seen,
                len(rejected),
                quality["status"],
                json.dumps(
                    {
                        "processed_files": processed_files,
                        "exports": export_counts,
                        "postgres": postgres_counts,
                    },
                    ensure_ascii=False,
                ),
                run_id,
            ),
        )
        connection.commit()

        if quality["status"] != "PASS":
            raise RuntimeError("La validación de calidad produjo controles fallidos. Revisa data/quality/.")

        print(f"Pipeline OK: {len(processed_files)} archivo(s) nuevo(s), {len(rejected)} fila(s) rechazada(s).")
        print(f"SQLite: {database_path}")
        print(f"Export Power BI: {root / 'data' / 'export'}")
        print(f"Calidad: {quality['status']}")
        if postgres_counts is not None:
            print("PostgreSQL sincronizado correctamente.")
    except Exception as exc:
        connection.execute(
            """
            UPDATE etl_run_log
            SET finished_at = ?, status = 'FAILED', message = ?
            WHERE run_id = ?
            """,
            (utc_now(), str(exc), run_id),
        )
        connection.commit()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
