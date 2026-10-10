from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import Any


@dataclass(frozen=True)
class HomeAsset:
    asset_id: str
    product_name: str
    category: str
    manufacturer: str
    model_number: str
    purchase_date: str
    warranty_expiry: str
    retailer: str
    order_reference: str
    location: str


ASSETS = {
    "asset_ac_001": HomeAsset(
        asset_id="asset_ac_001",
        product_name="CoolBreeze Split AC",
        category="air_conditioner",
        manufacturer="CoolBreeze",
        model_number="CB-24X",
        purchase_date="2026-03-12",
        warranty_expiry="2027-03-12",
        retailer="Amazon",
        order_reference="ORDER-DEMO-AC-001",
        location="Bedroom",
    ),
    "asset_washer_001": HomeAsset(
        asset_id="asset_washer_001",
        product_name="AquaSpin Front Load Washer",
        category="washing_machine",
        manufacturer="AquaSpin",
        model_number="AS-WM8",
        purchase_date="2025-11-18",
        warranty_expiry="2026-11-18",
        retailer="Amazon",
        order_reference="ORDER-DEMO-WM-001",
        location="Utility Area",
    ),
}


SAFE_STEPS = {
    "air_conditioner": [
        "Check that the thermostat is set to cooling mode and below room temperature.",
        "Check whether the air filter is visibly clogged; clean it only if the unit is safely powered down.",
        "Confirm that indoor airflow is not blocked.",
        "If there is leakage near electrical parts, burning smell, sparking, exposed wiring, or repeated breaker trips, stop using the unit and request professional service.",
    ],
    "washing_machine": [
        "Pause the machine and check whether the load is visibly unbalanced.",
        "Confirm that the machine is standing level.",
        "Check that the drain hose is not visibly kinked.",
        "If there is active leaking near electrical parts, burning smell, sparking, or repeated breaker trips, stop using the machine and request professional service.",
    ],
}


def list_home_assets() -> list[dict[str, Any]]:
    return [asdict(asset) for asset in ASSETS.values()]


def get_home_asset(asset_id: str) -> dict[str, Any]:
    asset = ASSETS.get(asset_id)
    if asset is None:
        return {"found": False, "asset_id": asset_id, "message": "Unknown demo asset."}
    return {"found": True, "asset": asdict(asset)}


def check_asset_warranty(asset_id: str, as_of_date: str | None = None) -> dict[str, Any]:
    asset = ASSETS.get(asset_id)
    if asset is None:
        return {"found": False, "asset_id": asset_id, "message": "Unknown demo asset."}

    try:
        check_date = date.fromisoformat(as_of_date) if as_of_date else date.today()
        expiry = date.fromisoformat(asset.warranty_expiry)
    except ValueError:
        return {"found": True, "valid_input": False, "message": "Use YYYY-MM-DD."}

    active = check_date <= expiry
    return {
        "found": True,
        "asset_id": asset.asset_id,
        "product_name": asset.product_name,
        "as_of_date": check_date.isoformat(),
        "warranty_expiry": asset.warranty_expiry,
        "warranty_active": active,
        "recommended_path": "manufacturer_warranty_service" if active else "paid_service_search",
    }


def troubleshoot_asset(asset_id: str, symptoms: str) -> dict[str, Any]:
    asset = ASSETS.get(asset_id)
    if asset is None:
        return {"found": False, "asset_id": asset_id, "message": "Unknown demo asset."}

    normalized = symptoms.lower()
    danger_terms = ("smoke", "sparking", "spark", "burning", "shock", "exposed wire", "breaker", "fire")
    high_risk = any(term in normalized for term in danger_terms)

    if high_risk:
        steps = [
            "Stop using the device.",
            "Disconnect power only if it is safe to do so.",
            "Do not open or repair electrical components yourself.",
            "Request qualified professional service.",
        ]
    else:
        steps = SAFE_STEPS.get(
            asset.category,
            [
                "Power the device down if it appears unsafe.",
                "Check the manufacturer manual for basic non-invasive troubleshooting.",
                "Request professional service if the issue persists.",
            ],
        )

    return {
        "found": True,
        "asset_id": asset.asset_id,
        "product_name": asset.product_name,
        "symptoms": symptoms,
        "high_risk": high_risk,
        "can_continue_basic_troubleshooting": not high_risk,
        "steps": steps,
        "disclaimer": "Demo guidance only; follow manufacturer instructions and qualified technician advice.",
    }


def build_service_handoff(
    asset_id: str,
    symptoms: str,
    budget: float,
    deadline: str,
    excluded_days: list[str] | None = None,
) -> dict[str, Any]:
    asset = ASSETS.get(asset_id)
    if asset is None:
        return {"ready": False, "message": "Unknown demo asset."}
    if budget <= 0:
        return {"ready": False, "message": "Budget must be greater than zero."}
    if not deadline.strip():
        return {"ready": False, "message": "A deadline is required."}

    return {
        "ready": True,
        "asset": asdict(asset),
        "warranty": check_asset_warranty(asset_id),
        "service_contract": {
            "goal": f"Service {asset.product_name} ({asset.model_number}) for reported issue: {symptoms}",
            "budget": float(budget),
            "deadline": deadline.strip(),
            "excluded_days": excluded_days or [],
        },
        "next_tool": "create_errand",
        "message": "Pass service_contract into Relay's existing durable create_errand flow.",
    }
