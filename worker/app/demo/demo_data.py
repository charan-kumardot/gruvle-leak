"""
Demo Mode datasets (spec section 64) — one synthetic business per industry
vertical, so a visitor can see Gruvle analyze something that looks like
their own business, not just one fixed retailer.

Every finding shown in demo mode is produced by running the REAL detector
engine against synthetic data — nothing here is a hand-typed fake finding.
The web app is responsible for labeling every screen that shows this data
as "DEMO DATA" and must never mix it with a real business's scan.

Generation is fully deterministic (seeded RNG, one fixed seed per industry)
so demo mode looks the same on every load and in every test run.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from app.detectors.base import DatasetBundle, DetectionContext
from app.schemas.domain import DatasetKind, NormalizedRecord

DEMO_CURRENCY = "INR"
_TODAY = date(2026, 8, 30)


@dataclass
class IndustryProfile:
    key: str
    label: str
    business_name: str
    tagline: str
    products: dict[str, int]  # product_id -> list price
    order_count: int = 220
    order_term: str = "order"  # what a line item is called, for copy purposes only
    # customer_ids that get a recurring, undocumented steep discount (the pricing leak)
    underpriced_customers: tuple[str, ...] = ("CUST-007", "CUST-013", "CUST-021")
    underpriced_discount: Decimal = field(default_factory=lambda: Decimal("0.6"))  # fraction of list price charged
    documented_discount_choices: tuple[int, ...] = (10, 15, 45, 50)
    documented_discount_rate: float = 0.1
    unbilled_rate: float = 0.06  # fraction of completed orders never invoiced
    undercharge_rate: float = 0.04  # fraction of invoiced orders undercharged
    has_contracts: bool = True
    contract_count: int = 18
    contract_values: tuple[int, ...] = (48000, 96000, 144000, 240000)
    seed: int = 42


PROFILES: dict[str, IndustryProfile] = {
    "retail": IndustryProfile(
        key="retail",
        label="Retail",
        business_name="Demo Retail Co.",
        tagline="an online retailer selling home appliances",
        products={"SKU-KETTLE": 1200, "SKU-MIXER": 3500, "SKU-TOASTER": 1800, "SKU-BLENDER": 2600, "SKU-FRYER": 4200},
        seed=42,
    ),
    "saas": IndustryProfile(
        key="saas",
        label="SaaS",
        business_name="Demo Cloudstack Inc.",
        tagline="a B2B SaaS company selling subscription plans",
        products={"PLAN-STARTER": 999, "PLAN-PRO": 2999, "PLAN-BUSINESS": 7999, "PLAN-ENTERPRISE": 19999},
        order_count=180,
        underpriced_customers=("CUST-004", "CUST-011", "CUST-019"),
        underpriced_discount=Decimal("0.55"),  # grandfathered legacy pricing
        unbilled_rate=0.03,  # billing is mostly automated
        undercharge_rate=0.05,  # proration errors
        has_contracts=True,
        contract_count=26,  # subscription renewals are the core of this business
        contract_values=(11988, 35988, 95988, 239988),  # annualized plan values
        seed=101,
    ),
    "agency": IndustryProfile(
        key="agency",
        label="Agency",
        business_name="Demo Northlight Studio",
        tagline="a creative agency billing for projects and retainers",
        products={
            "SVC-WEBSITE-SPRINT": 85000, "SVC-BRAND-PACKAGE": 140000,
            "SVC-AD-CAMPAIGN": 60000, "SVC-RETAINER-MONTH": 45000, "SVC-CONSULTING-BLOCK": 25000,
        },
        order_count=140,
        underpriced_customers=("CUST-002", "CUST-009"),
        underpriced_discount=Decimal("0.65"),
        unbilled_rate=0.11,  # unbilled hours are the classic agency leak
        undercharge_rate=0.05,  # scope creep not re-billed
        has_contracts=True,
        contract_count=14,  # retainer agreements
        contract_values=(180000, 360000, 540000),
        seed=202,
    ),
    "restaurant": IndustryProfile(
        key="restaurant",
        label="Restaurant",
        business_name="Demo Copper Kettle Kitchen",
        tagline="a restaurant group billing catering and private events",
        products={
            "EVT-CATERING-ORDER": 18000, "EVT-PRIVATE-EVENT": 65000,
            "EVT-BULK-SUPPLY": 22000, "EVT-DELIVERY-BATCH": 6000,
        },
        order_count=200,
        underpriced_customers=("CUST-005", "CUST-016", "CUST-023"),
        underpriced_discount=Decimal("0.5"),  # comps / staff discounts creeping into paid events
        documented_discount_rate=0.16,  # promos are common in hospitality
        unbilled_rate=0.07,
        undercharge_rate=0.03,
        has_contracts=False,  # no ongoing contracts for a restaurant — RenewalLeakDetector will cleanly skip
        seed=303,
    ),
    "logistics": IndustryProfile(
        key="logistics",
        label="Logistics",
        business_name="Demo Vantage Freight Co.",
        tagline="a logistics provider billing shipments and freight contracts",
        products={
            "SHIP-LOCAL-DELIVERY": 3500, "SHIP-INTERSTATE-FREIGHT": 28000,
            "SHIP-COLD-CHAIN": 42000, "SHIP-BULK-CARGO": 65000,
        },
        order_count=210,
        underpriced_customers=("CUST-008", "CUST-014"),
        underpriced_discount=Decimal("0.62"),
        unbilled_rate=0.09,  # shipments completed, billing lags operations
        undercharge_rate=0.06,  # freight billing discrepancies
        has_contracts=True,
        contract_count=16,  # shipping/logistics agreements
        contract_values=(220000, 480000, 720000),
        seed=404,
    ),
}

DEFAULT_INDUSTRY = "retail"


def list_industries() -> list[dict]:
    return [
        {"key": p.key, "label": p.label, "business_name": p.business_name, "tagline": p.tagline}
        for p in PROFILES.values()
    ]


def get_profile(industry: str) -> IndustryProfile:
    return PROFILES.get(industry, PROFILES[DEFAULT_INDUSTRY])


def _records(dataset_id: str, rows: list[dict]) -> list[NormalizedRecord]:
    return [NormalizedRecord(dataset_id=dataset_id, row_index=i, values=row) for i, row in enumerate(rows)]


def build_demo_context(industry: str = DEFAULT_INDUSTRY) -> DetectionContext:
    profile = get_profile(industry)
    rng = random.Random(profile.seed)
    products = list(profile.products.keys())

    orders, invoices, contracts = [], [], []
    order_id_counter = 1
    invoice_id_counter = 1

    for _ in range(profile.order_count):
        product = rng.choice(products)
        list_price = profile.products[product]
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
        if customer_id in profile.underpriced_customers and rng.random() < 0.6:
            unit_price = unit_price * profile.underpriced_discount  # undocumented, below list
        elif rng.random() < profile.documented_discount_rate:
            discount_percent = Decimal(rng.choice(profile.documented_discount_choices))

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

        if status == "completed" and rng.random() > profile.unbilled_rate:
            invoice_id = f"INV-{invoice_id_counter:04d}"
            invoice_id_counter += 1
            invoice_amount = total_amount
            if rng.random() < profile.undercharge_rate:
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
    if len(invoices) > 11:
        dup = dict(invoices[10])
        invoices.insert(11, dup)

    if profile.has_contracts:
        for i in range(profile.contract_count):
            contract_id = f"CTR-{i + 1:03d}"
            customer_id = f"CUST-{rng.randint(1, 40):03d}"
            annual_value = Decimal(rng.choice(profile.contract_values))
            if i < max(3, profile.contract_count // 4):
                end_date = _TODAY + timedelta(days=rng.randint(1, 29))   # expiring soon
            elif i < max(5, profile.contract_count // 3):
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

    datasets = [
        DatasetBundle(f"demo-{profile.key}-orders", DatasetKind.ORDERS, _records(f"demo-{profile.key}-orders", orders)),
        DatasetBundle(f"demo-{profile.key}-invoices", DatasetKind.INVOICES, _records(f"demo-{profile.key}-invoices", invoices)),
    ]
    if profile.has_contracts:
        datasets.append(
            DatasetBundle(f"demo-{profile.key}-contracts", DatasetKind.CONTRACTS, _records(f"demo-{profile.key}-contracts", contracts))
        )

    return DetectionContext(
        scan_id=f"demo-{profile.key}-scan",
        business_id=f"demo-{profile.key}-business",
        default_currency=DEMO_CURRENCY,
        datasets=datasets,
    )
