"""
Demo Mode dataset (spec section 64).

"Demo Retail Co." is entirely synthetic. Every finding shown in demo mode is
produced by running the REAL detector engine against this synthetic data —
nothing here is a hand-typed fake finding. The web app is responsible for
labeling every screen that shows this data with "DEMO DATA" and must never
mix it with a real business's scan.

Generation is fully deterministic (seeded RNG) so demo mode looks the same
on every load and in every test run.
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from app.detectors.base import DatasetBundle, DetectionContext
from app.schemas.domain import DatasetKind, NormalizedRecord

DEMO_BUSINESS_NAME = "Demo Retail Co."
DEMO_BUSINESS_ID = "demo-business"
DEMO_SCAN_ID = "demo-scan"
DEMO_CURRENCY = "INR"

_TODAY = date(2026, 8, 30)
_PRODUCTS = ["SKU-KETTLE", "SKU-MIXER", "SKU-TOASTER", "SKU-BLENDER", "SKU-FRYER"]
_LIST_PRICES = {"SKU-KETTLE": 1200, "SKU-MIXER": 3500, "SKU-TOASTER": 1800, "SKU-BLENDER": 2600, "SKU-FRYER": 4200}


def _records(dataset_id: str, rows: list[dict]) -> list[NormalizedRecord]:
    return [NormalizedRecord(dataset_id=dataset_id, row_index=i, values=row) for i, row in enumerate(rows)]


def build_demo_context() -> DetectionContext:
    rng = random.Random(42)
    orders, invoices, contracts = [], [], []

    order_id_counter = 1
    invoice_id_counter = 1

    # --- Orders: mostly clean, some completed-but-unbilled, some underpriced, some over-discounted ---
    for i in range(220):
        product = rng.choice(_PRODUCTS)
        list_price = _LIST_PRICES[product]
        qty = rng.choice([1, 1, 1, 2, 3])
        customer_id = f"CUST-{rng.randint(1, 40):03d}"
        order_id = f"ORDER-{order_id_counter:04d}"
        order_id_counter += 1
        order_date = _TODAY - timedelta(days=rng.randint(1, 180))
        status = rng.choices(
            ["completed", "completed", "completed", "pending", "cancelled"], weights=[70, 10, 10, 5, 5]
        )[0]

        unit_price = Decimal(list_price)
        discount_percent = None
        # ~8% of orders get a recurring, undocumented steep discount for a handful of repeat customers
        if customer_id in ("CUST-007", "CUST-013", "CUST-021") and rng.random() < 0.6:
            unit_price = unit_price * Decimal("0.6")  # 40% below list, no discount field set
        elif rng.random() < 0.1:
            discount_percent = Decimal(rng.choice([10, 15, 45, 50]))  # occasional steep *documented* discount

        total_amount = unit_price * qty
        if discount_percent:
            total_amount = total_amount * (Decimal("100") - discount_percent) / Decimal("100")

        row = {
            "order_id": order_id,
            "customer_id": customer_id,
            "product_id": product,
            "unit_price": str(unit_price),
            "list_price": str(list_price),
            "quantity": str(qty),
            "total_amount": str(total_amount.quantize(Decimal("0.01"))),
            "status": status,
            "order_date": order_date.isoformat(),
            "currency": DEMO_CURRENCY,
        }
        if discount_percent:
            row["discount_percent"] = str(discount_percent)
        orders.append(row)

        # Most completed orders get invoiced; ~6% of completed orders are never invoiced (the unbilled leak)
        if status == "completed" and rng.random() > 0.06:
            invoice_id = f"INV-{invoice_id_counter:04d}"
            invoice_id_counter += 1
            invoice_amount = total_amount
            # ~4% of invoiced completed orders are undercharged relative to the order (invoice mismatch)
            if rng.random() < 0.04:
                invoice_amount = invoice_amount * Decimal("0.8")
            invoices.append({
                "invoice_id": invoice_id,
                "order_id": order_id,
                "customer_id": customer_id,
                "total_amount": str(invoice_amount.quantize(Decimal("0.01"))),
                "invoice_date": (order_date + timedelta(days=rng.randint(0, 3))).isoformat(),
                "currency": DEMO_CURRENCY,
            })

    # One deliberate duplicate invoice record (same invoice_id billed twice)
    if invoices:
        dup = dict(invoices[10])
        invoices.insert(11, dup)

    # --- Contracts: a mix of healthy, expiring-soon, and already-expired ---
    for i in range(18):
        contract_id = f"CTR-{i+1:03d}"
        customer_id = f"CUST-{rng.randint(1, 40):03d}"
        annual_value = Decimal(rng.choice([48000, 96000, 144000, 240000]))
        if i < 5:
            end_date = _TODAY + timedelta(days=rng.randint(1, 29))   # expiring soon
        elif i < 8:
            end_date = _TODAY - timedelta(days=rng.randint(1, 60))   # already expired
        else:
            end_date = _TODAY + timedelta(days=rng.randint(60, 400))  # healthy
        contracts.append({
            "contract_id": contract_id,
            "customer_id": customer_id,
            "total_amount": str(annual_value),
            "contract_end_date": end_date.isoformat(),
            "currency": DEMO_CURRENCY,
        })

    return DetectionContext(
        scan_id=DEMO_SCAN_ID,
        business_id=DEMO_BUSINESS_ID,
        default_currency=DEMO_CURRENCY,
        datasets=[
            DatasetBundle("demo-orders", DatasetKind.ORDERS, _records("demo-orders", orders)),
            DatasetBundle("demo-invoices", DatasetKind.INVOICES, _records("demo-invoices", invoices)),
            DatasetBundle("demo-contracts", DatasetKind.CONTRACTS, _records("demo-contracts", contracts)),
        ],
    )
