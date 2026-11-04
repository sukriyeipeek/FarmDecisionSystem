import pandas as pd
import pytest

from app.schemas import OptimizationManuelRequest
from app.services import optimization_plan as optimizer


def _profit(product_name, area, **_kwargs):
    return {
        "net_kar": {"A": 1000.0, "B": 1800.0}[product_name] * area,
        "net_kar_dusuk": None,
        "tahmini_gelir": 3000.0 * area,
        "toplam_gider": 1000.0 * area,
        "tahmini_fiyat": 10.0,
        "tahmini_uretim": 100.0 * area,
        "gubre_gideri": 100.0 * area,
        "mazot_gideri": 100.0 * area,
        "net_kar_yuksek": 1200.0 * area,
        "basabas_fiyati": 4.0,
        "zarar_olasiligi": 0.1,
        "aralik_isabeti": 0.8,
        "kendi_verim_agirligi": 0.0,
        "varsayimlar": [],
        "maliyetler_eksik": False,
    }


def _risk(product_name, **_kwargs):
    return {"genel_risk": {"A": 20.0, "B": 40.0}[product_name], "risk_seviyesi": "Orta", "risk_emoji": ""}


@pytest.fixture(autouse=True)
def mocked_calculators(monkeypatch):
    def estimate_water(product_name, season, irrigation_method="damla"):
        base = {"A": 100.0, "B": 200.0}[product_name]
        multiplier = {"damla": 1.0, "yagmurlama": 1.2, "salma": 1.5}[irrigation_method]
        return {"water_m3_per_decare": base * multiplier, "assumptions": ["provisional test range"]}

    monkeypatch.setattr(optimizer, "estimate_water", estimate_water)
    monkeypatch.setattr(optimizer, "PRODUCT_SEASONS", {"A": ["Spring"], "B": ["Spring"]})
    monkeypatch.setattr(optimizer, "add_profit", _profit)
    monkeypatch.setattr(optimizer, "add_risk", _risk)
    monkeypatch.setattr(
        optimizer,
        "load_optimization_data",
        lambda: pd.DataFrame(
            [
                {"district": "Test", "product_name": "A", "planted_area": 1, "production_amount": 1, "quota": 1000},
                {"district": "Test", "product_name": "B", "planted_area": 1, "production_amount": 1, "quota": 1000},
            ]
        ),
    )


def test_water_budget_is_hard_constraint_and_rows_report_water():
    plan = optimizer.create_planting(
        db=None,
        district="Test",
        season="Spring",
        total_area=1,
        selected_products=["A", "B"],
        su_butcesi_m3=100,
    )

    assert sum(row["estimated_water_m3"] for row in plan) <= 100
    assert plan[0]["water_assumptions"] == ["provisional test range"]


def test_zero_budget_returns_empty_feasible_plan():
    plan = optimizer.create_planting(
        db=None,
        district="Test",
        season="Spring",
        total_area=1,
        selected_products=["A", "B"],
        su_butcesi_m3=0,
    )

    assert plan == []


def test_water_saving_mode_uses_water_efficiency_score():
    data = pd.DataFrame(
        [
            {"product_name": "A", "profit_per_decare": 1000, "profit_low_per_decare": 1000, "risk_score": 20, "water_per_decare_m3": 100},
            {"product_name": "B", "profit_per_decare": 1800, "profit_low_per_decare": 1800, "risk_score": 40, "water_per_decare_m3": 200},
        ]
    )
    scored = optimizer.add_final_score(data, optimizasyon_modu="su_tasarruflu")
    assert scored.loc[scored["product_name"] == "A", "profit_per_m3"].item() == 10
    assert scored["final_score"].notna().all()


def test_water_efficiency_is_area_invariant():
    one_decare = optimizer.create_planting(db=None, district="Test", season="Spring", total_area=1)
    two_decare = optimizer.create_planting(db=None, district="Test", season="Spring", total_area=2)
    efficiency_one = next(row for row in one_decare if row["product_name"] == "A")["water_efficiency_tl_m3"]
    efficiency_two = next(row for row in two_decare if row["product_name"] == "A")["water_efficiency_tl_m3"]
    assert efficiency_one == efficiency_two == 10.0


def test_schema_rejects_non_finite_budget_and_accepts_new_defaults():
    request = OptimizationManuelRequest(ilce_adi="Test", donum=1, sezon="Yaz")
    assert request.su_butcesi_m3 is None
    assert request.sulama_yontemi == "damla"
    assert request.optimizasyon_modu == "dengeli"

    with pytest.raises(ValueError):
        OptimizationManuelRequest(ilce_adi="Test", donum=1, sezon="Yaz", su_butcesi_m3=float("inf"))
