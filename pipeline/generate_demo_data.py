"""Generate a deterministic, realistic retail dataset for the portfolio project.

The company, customers, stores and transactions are fictional. The script uses
only relative paths so the full project can be reproduced after cloning it.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class Store:
    store_id: str
    store_name: str
    region: str
    city: str
    store_type: str
    opening_date: str
    demand_weight: float


STORES = [
    Store("T001", "Aurora Naco", "Distrito Nacional", "Santo Domingo", "Urbana", "2019-03-18", 1.35),
    Store("T002", "Aurora Piantini", "Distrito Nacional", "Santo Domingo", "Urbana", "2020-08-07", 1.28),
    Store("T003", "Aurora Bella Vista", "Distrito Nacional", "Santo Domingo", "Urbana", "2021-02-12", 1.12),
    Store("T004", "Aurora Santiago Centro", "Cibao", "Santiago", "Urbana", "2018-11-23", 1.18),
    Store("T005", "Aurora Los Jardines", "Cibao", "Santiago", "Urbana", "2022-05-20", 1.03),
    Store("T006", "Aurora La Romana", "Este", "La Romana", "Regional", "2020-01-31", 0.82),
    Store("T007", "Aurora Punta Cana", "Este", "Punta Cana", "Turística", "2021-10-15", 0.94),
    Store("T008", "Aurora Puerto Plata", "Norte", "Puerto Plata", "Regional", "2023-04-14", 0.76),
]

CHANNELS = [
    ("CH01", "Tienda física", 0.56),
    ("CH02", "Ecommerce", 0.31),
    ("CH03", "Delivery", 0.13),
]

CATEGORY_CATALOG = {
    "Abarrotes": (["Arroz", "Aceite", "Pastas", "Conservas"], 0.22, (95, 520)),
    "Bebidas": (["Refrescos", "Jugos", "Agua", "Café"], 0.31, (60, 480)),
    "Lácteos": (["Leche", "Yogurt", "Quesos"], 0.25, (85, 460)),
    "Cuidado personal": (["Higiene", "Cuidado del cabello", "Cuidado corporal"], 0.40, (110, 950)),
    "Hogar": (["Limpieza", "Desechables", "Organización"], 0.36, (120, 1100)),
    "Snacks": (["Galletas", "Frutos secos", "Chocolates"], 0.47, (75, 620)),
    "Congelados": (["Vegetales", "Comidas preparadas", "Helados"], 0.34, (160, 890)),
    "Panadería": (["Pan", "Repostería"], 0.51, (55, 370)),
}

SEGMENTS = [("Frecuente", 0.23), ("Ocasional", 0.54), ("Nuevo", 0.15), ("Empresarial", 0.08)]
PAYMENT_METHODS = [("Tarjeta", 0.54), ("Efectivo", 0.21), ("Transferencia", 0.11), ("Billetera digital", 0.14)]


def weighted_choice(rng: random.Random, values):
    total = sum(item[-1] for item in values)
    point = rng.random() * total
    cumulative = 0.0
    for item in values:
        cumulative += item[-1]
        if point <= cumulative:
            return item
    return values[-1]


def month_starts(start: date, end: date) -> list[date]:
    cursor = date(start.year, start.month, 1)
    output = []
    while cursor <= end:
        output.append(cursor)
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return output


def build_customers(rng: random.Random, count: int = 60_000) -> list[dict]:
    region_weights = {
        "Distrito Nacional": 0.38,
        "Cibao": 0.27,
        "Este": 0.21,
        "Norte": 0.14,
    }
    region_list = list(region_weights.items())
    city_by_region = {
        "Distrito Nacional": ["Santo Domingo"],
        "Cibao": ["Santiago", "Moca", "La Vega"],
        "Este": ["La Romana", "Punta Cana", "Higüey"],
        "Norte": ["Puerto Plata", "Sosúa"],
    }
    customers = []
    for index in range(1, count + 1):
        region = weighted_choice(rng, region_list)[0]
        signup = date(2023, 1, 1) + timedelta(days=rng.randrange(0, 1_350))
        customers.append(
            {
                "customer_id": f"C{index:04d}",
                "customer_name": f"Cliente {index:04d}",
                "segment": weighted_choice(rng, SEGMENTS)[0],
                "region": region,
                "city": rng.choice(city_by_region[region]),
                "signup_date": signup.isoformat(),
                "is_active": 1,
            }
        )
    return customers


def build_products(rng: random.Random) -> list[dict]:
    products = []
    sequence = 1
    for category, (subcategories, margin, price_range) in CATEGORY_CATALOG.items():
        for subcategory in subcategories:
            for variant in range(1, 5):
                price = round(rng.uniform(*price_range), 2)
                product_margin = max(0.12, min(0.62, rng.gauss(margin, 0.045)))
                cost = round(price * (1 - product_margin), 2)
                popularity = round(rng.lognormvariate(0, 0.45), 3)
                products.append(
                    {
                        "product_id": f"P{sequence:04d}",
                        "product_name": f"{subcategory} {variant:02d}",
                        "category": category,
                        "subcategory": subcategory,
                        "list_price": price,
                        "unit_cost": cost,
                        "popularity_weight": popularity,
                        "is_active": 1,
                    }
                )
                sequence += 1
    return products


def build_stores() -> list[dict]:
    return [
        {
            "store_id": store.store_id,
            "store_name": store.store_name,
            "region": store.region,
            "city": store.city,
            "store_type": store.store_type,
            "opening_date": store.opening_date,
            "demand_weight": store.demand_weight,
        }
        for store in STORES
    ]


def daily_order_count(day: date, rng: random.Random) -> int:
    weekday_factor = [0.76, 0.80, 0.86, 0.92, 1.10, 1.29, 1.18][day.weekday()]
    month_factor = {
        1: 0.88,
        2: 0.91,
        3: 0.98,
        4: 1.00,
        5: 1.03,
        6: 1.02,
        7: 1.06,
        8: 1.10,
        9: 1.01,
        10: 1.03,
        11: 1.24,
        12: 1.38,
    }[day.month]
    trend = 1 + max(0, (day - date(2025, 1, 1)).days) * 0.00010
    holiday_boost = 1.28 if (day.month, day.day) in {(12, 24), (12, 31), (2, 27)} else 1.0
    base = 74 * weekday_factor * month_factor * trend * holiday_boost
    return max(35, int(rng.gauss(base, 8)))


def build_sales(
    rng: random.Random,
    customers: list[dict],
    products: list[dict],
    start: date,
    end: date,
) -> list[dict]:
    sales = []
    line_sequence = 1
    order_sequence = 1
    loyal_customers = [customer for customer in customers if customer["segment"] == "Frecuente"]
    product_weights = [(product, product["popularity_weight"]) for product in products]
    store_weights = [(store, store.demand_weight) for store in STORES]
    payment_weights = PAYMENT_METHODS

    day = start
    while day <= end:
        number_of_orders = daily_order_count(day, rng)
        for _ in range(number_of_orders):
            order_id = f"O{order_sequence:07d}"
            order_sequence += 1
            store = weighted_choice(rng, store_weights)[0]
            channel = weighted_choice(rng, CHANNELS)
            # A small loyal cohort creates repeat behavior without making every
            # profiling customer unrealistically active in a 22-month window.
            customer = rng.choice(loyal_customers if rng.random() < 0.31 else customers)
            payment = weighted_choice(rng, payment_weights)[0]
            line_count = min(5, max(1, int(rng.gauss(2.15, 0.9))))
            chosen_products = rng.sample(products, k=line_count)

            for product in chosen_products:
                quantity = min(4, max(1, int(rng.gauss(1.45, 0.62))))
                promotion_probability = 0.16 + (0.08 if day.weekday() >= 5 else 0)
                discount = 0.0
                if rng.random() < promotion_probability:
                    discount = rng.choice([0.05, 0.10, 0.15, 0.20, 0.25])
                unit_price = round(product["list_price"] * rng.uniform(0.97, 1.04), 2)
                is_return = rng.random() < 0.023
                if is_return:
                    quantity = -min(quantity, 2)

                sales.append(
                    {
                        "sale_line_id": f"SL{line_sequence:09d}",
                        "order_id": order_id,
                        "order_date": day.isoformat(),
                        "customer_id": customer["customer_id"],
                        "product_id": product["product_id"],
                        "store_id": store.store_id,
                        "channel_id": channel[0],
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "discount_pct": discount,
                        "unit_cost": product["unit_cost"],
                        "is_return": int(is_return),
                        "payment_method": payment,
                    }
                )
                line_sequence += 1
        day += timedelta(days=1)
    return sales


def build_targets(sales: list[dict], start: date, end: date) -> list[dict]:
    realized: dict[tuple[str, str, str], float] = {}
    for row in sales:
        revenue = row["quantity"] * row["unit_price"] * (1 - row["discount_pct"])
        key = (row["order_date"][:7], row["store_id"], row["channel_id"])
        realized[key] = realized.get(key, 0.0) + revenue

    targets = []
    for month in month_starts(start, end):
        month_label = month.strftime("%Y-%m")
        for store in STORES:
            for channel_id, _, _ in CHANNELS:
                actual = max(0.0, realized.get((month_label, store.store_id, channel_id), 0.0))
                # Targets intentionally vary between roughly 89% and 112% of actuals.
                stretch = 0.89 + ((sum(ord(c) for c in store.store_id + channel_id + month_label) % 24) / 100)
                targets.append(
                    {
                        "target_month": month_label,
                        "store_id": store.store_id,
                        "channel_id": channel_id,
                        "target_revenue": round(actual * stretch, 2),
                    }
                )
    return targets


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Cannot write empty dataset: {path}")
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_sales_batches(root: Path, sales: list[dict]) -> None:
    batches: dict[tuple[int, int], list[dict]] = {}
    for row in sales:
        parsed = datetime.strptime(row["order_date"], "%Y-%m-%d").date()
        quarter = math.ceil(parsed.month / 3)
        batches.setdefault((parsed.year, quarter), []).append(row)

    for (year, quarter), rows in sorted(batches.items()):
        write_csv(root / "data" / "landing" / "sales" / f"sales_{year}_Q{quarter}.csv", rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Aurora Retail demo data.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root (defaults to the parent of this script).",
    )
    parser.add_argument("--seed", type=int, default=20261105)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2025, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2026, 10, 31))
    args = parser.parse_args()

    rng = random.Random(args.seed)
    root = args.root.resolve()
    customers = build_customers(rng)
    products = build_products(rng)
    stores = build_stores()
    sales = build_sales(rng, customers, products, args.start, args.end)
    targets = build_targets(sales, args.start, args.end)

    write_csv(root / "data" / "raw" / "reference" / "customers.csv", customers)
    write_csv(root / "data" / "raw" / "reference" / "products.csv", products)
    write_csv(root / "data" / "raw" / "reference" / "stores.csv", stores)
    write_csv(
        root / "data" / "raw" / "reference" / "channels.csv",
        [{"channel_id": channel_id, "channel_name": channel_name} for channel_id, channel_name, _ in CHANNELS],
    )
    write_csv(root / "data" / "raw" / "reference" / "monthly_targets.csv", targets)
    write_sales_batches(root, sales)

    print(f"Generated {len(customers):,} customers")
    print(f"Generated {len(products):,} products")
    print(f"Generated {len(stores):,} stores")
    print(f"Generated {len(sales):,} sales lines")
    print(f"Generated {len(targets):,} target rows")
    print(f"Data written to: {root / 'data'}")


if __name__ == "__main__":
    main()
