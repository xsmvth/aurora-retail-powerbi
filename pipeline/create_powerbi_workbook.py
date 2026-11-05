"""Bundle exported star-schema tables into an Excel workbook for Power BI."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


TABLES = [
    "dim_date",
    "dim_month",
    "dim_customer",
    "dim_product",
    "dim_store",
    "dim_channel",
    "fact_sales",
    "fact_targets",
]


def create_workbook(export_dir: Path, file_name: str, exclude: set[str] | None = None) -> Path:
    excluded = exclude or set()
    destination = export_dir / file_name
    with pd.ExcelWriter(destination, engine="openpyxl") as writer:
        for table in TABLES:
            if table in excluded:
                continue
            frame = pd.read_csv(export_dir / f"{table}.csv", encoding="utf-8-sig")
            frame.to_excel(writer, sheet_name=table, index=False)
    return destination


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    export_dir = root / "data" / "export"
    full = create_workbook(export_dir, "AuroraRetail_Model.xlsx")
    remaining = create_workbook(
        export_dir,
        "AuroraRetail_RemainingModel.xlsx",
        exclude={"dim_customer"},
    )
    print(full)
    print(remaining)


if __name__ == "__main__":
    main()
