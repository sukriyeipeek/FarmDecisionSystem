from pathlib import Path
import logging
import re
from datetime import date

import pandas as pd
import pulp

from app.services.profit_service import kar_hesaplama_son
from app.services.risk import risk_hesapla
from app.services.product_catalog import URUN_MEVSIMLERI

logger = logging.getLogger(__name__)


ROOT_DIR = Path(__file__).resolve().parent.parent.parent

DATAPATH = ROOT_DIR / "data" / "processed" / "data_files" / "final_optimization.csv"
QUOTAPATH = ROOT_DIR / "data" / "processed" / "data_files" / "cleaned_quota.csv"

PROFIT_WEIGHT = 0.70
RISK_WEIGHT = 0.30

# Hangi kar degeri puanlanir: "dengeli" beklenen kari, "temkinli" fiyat araliginin alt
# ucundaki (kotu senaryo) kari kullanir. Temkinli plan, fiyati cokse de en az zarar eden
# urunlere yonelir.
STRATEJILER = {
    "dengeli": "profit_per_decare",
    "temkinli": "profit_low_per_decare",
}

PRODUCT_SEASONS = URUN_MEVSIMLERI

EN_TO_TR_SEASON = {
    "Spring": "İlkbahar",
    "Summer": "Yaz",
    "Fall": "Sonbahar",
    "Winter": "Kış",
}


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9_]", "_", str(value))


def load_optimization_data():
    df = pd.read_csv(DATAPATH)
    quota = pd.read_csv(QUOTAPATH)

    quota["quota"] = pd.to_numeric(quota["quota"], errors="coerce")
    quota = quota.drop_duplicates(subset=["district", "product_name"])

    return df.merge(
        quota[["district", "product_name", "quota"]],
        on=["district", "product_name"],
        how="left",
    )


def get_suitable_products(df, district, season=None):
    data = df.copy()

    data["planted_area"] = pd.to_numeric(data["planted_area"], errors="coerce")
    data["production_amount"] = pd.to_numeric(data["production_amount"], errors="coerce")

    mask = (
        (data["district"] == district)
        & (data["planted_area"] > 0)
        & (data["production_amount"] > 0)
    )

    if season:
        data["suitable_seasons"] = data["product_name"].map(PRODUCT_SEASONS)
        season_mask = data["suitable_seasons"].apply(
            lambda seasons: season in seasons if isinstance(seasons, list) else False
        )
        mask = mask & season_mask

    return (
        data[mask]
        .drop(columns=["suitable_seasons"], errors="ignore")
        .reset_index(drop=True)
    )


def get_target_year(season):
    season_order = {
        "Winter": 1,
        "Spring": 2,
        "Summer": 3,
        "Fall": 4,
    }

    month_to_season = {
        12: "Winter",
        1: "Winter",
        2: "Winter",
        3: "Spring",
        4: "Spring",
        5: "Spring",
        6: "Summer",
        7: "Summer",
        8: "Summer",
        9: "Fall",
        10: "Fall",
        11: "Fall",
    }

    if season not in season_order:
        raise ValueError(f"Gecersiz sezon: {season}")

    today = date.today()
    current_season = month_to_season[today.month]

    if season_order[season] > season_order[current_season]:
        return today.year

    return today.year + 1


def filter_selected_products(data, selected_products):
    if not selected_products:
        return data

    return data[data["product_name"].isin(selected_products)].reset_index(drop=True)


def add_profit(db, product_name, district, target_season, area, gecmis_verimler=None, ek_maliyet_donum=0):
    profit_season = EN_TO_TR_SEASON.get(target_season, target_season)

    return kar_hesaplama_son(
        db=db,
        ilce=district,
        urun=product_name,
        sezon=profit_season,
        donum=area,
        gecmis_verimler=(gecmis_verimler or {}).get(product_name),
        donum_basi_ek_maliyet=ek_maliyet_donum or 0,
    )


def add_risk(db, product_name, district, season, area):
    risk_season = EN_TO_TR_SEASON.get(season, season)

    return risk_hesapla(
        db=db,
        ilce=district,
        urun=product_name,
        sezon=risk_season,
        donum=area,
    )


def build_profit_data(db, suitable_products, district, season, gecmis_verimler=None, ek_maliyet_donum=0):
    product_rows = (
        suitable_products[["district", "product_name", "quota"]]
        .drop_duplicates(subset=["district", "product_name"])
        .reset_index(drop=True)
    )

    rows = []
    for _, row in product_rows.iterrows():
        product_name = row["product_name"]

        try:
            profit_result = add_profit(
                db=db,
                product_name=product_name,
                district=district,
                target_season=season,
                area=1,
                gecmis_verimler=gecmis_verimler,
                ek_maliyet_donum=ek_maliyet_donum,
            )
        except Exception as error:
            logger.warning(
                "Kar hesabi basarisiz oldu, urun planin disinda birakildi: "
                "district=%s product=%s season=%s error=%s",
                district, product_name, season, error,
            )
            continue

        rows.append(
            {
                "district": district,
                "product_name": product_name,
                "quota": row.get("quota"),
                "profit_per_decare": float(profit_result["net_kar"]),
                # aralik yoksa temkinli strateji beklenen kara geri duser
                "profit_low_per_decare": float(
                    profit_result["net_kar"] if profit_result["net_kar_dusuk"] is None
                    else profit_result["net_kar_dusuk"]
                ),
                "revenue_per_decare": float(profit_result["tahmini_gelir"]),
                "cost_per_decare": float(profit_result["toplam_gider"]),
                "predicted_price": float(profit_result["tahmini_fiyat"]),
            }
        )

    return pd.DataFrame(rows)


def build_risk_data(db, profit_data, district, season):
    risk_rows = []

    for _, row in profit_data.iterrows():
        product_name = row["product_name"]

        try:
            risk_result = add_risk(
                db=db,
                product_name=product_name,
                district=district,
                season=season,
                area=1,
            )
        except Exception as error:
            logger.warning(
                "Risk hesabi basarisiz oldu, urun planin disinda birakildi: "
                "district=%s product=%s season=%s error=%s",
                district, product_name, season, error,
            )
            continue

        risk_rows.append(
            {
                "district": district,
                "product_name": product_name,
                "risk_score": float(risk_result["genel_risk"]),
                "risk_level": risk_result.get("risk_seviyesi"),
                "risk_color": risk_result.get("risk_emoji"),
            }
        )

    return pd.DataFrame(risk_rows)


def add_final_score(data, strateji="dengeli"):
    if strateji not in STRATEJILER:
        raise ValueError(f"Gecersiz strateji: {strateji}")

    data = data.copy()
    profit_column = STRATEJILER[strateji]

    min_profit = data[profit_column].min()
    max_profit = data[profit_column].max()

    if max_profit == min_profit:
        data["profit_score"] = 100
    else:
        data["profit_score"] = (
            (data[profit_column] - min_profit)
            / (max_profit - min_profit)
            * 100
        )

    data["safety_score"] = 100 - data["risk_score"]
    data["final_score"] = (
        data["profit_score"] * PROFIT_WEIGHT
        + data["safety_score"] * RISK_WEIGHT
    ).round(2)

    return data


def build_decision_data(db, suitable_products, district, season, strateji="dengeli", gecmis_verimler=None,
                        ek_maliyet_donum=0):
    profit_data = build_profit_data(
        db=db,
        suitable_products=suitable_products,
        district=district,
        season=season,
        gecmis_verimler=gecmis_verimler,
        ek_maliyet_donum=ek_maliyet_donum,
    )

    if profit_data.empty:
        raise ValueError("Uygun urunler icin kar hesabi yapilamadi.")

    risk_data = build_risk_data(
        db=db,
        profit_data=profit_data,
        district=district,
        season=season,
    )

    if risk_data.empty:
        raise ValueError("Uygun urunler icin risk hesabi yapilamadi.")

    data = profit_data.merge(
        risk_data[["product_name", "risk_score", "risk_level", "risk_color"]],
        on="product_name",
        how="inner",
    )

    if data.empty:
        raise ValueError("Kar ve risk hesabi ortak olan urun bulunamadi.")

    return add_final_score(data, strateji=strateji)


def drop_unprofitable(decision_data):
    """Beklenen kari sifir ya da negatif olan urune alan ayrilmaz; o alanin bos kalmasi daha iyidir.
    Skor (0-100) her zaman pozitif oldugu icin bu filtre olmadan model araziyi zarar eden
    urunlerle de doldururdu."""
    return decision_data[decision_data["profit_per_decare"] > 0].reset_index(drop=True)


def create_planting(
    db,
    district,
    season,
    total_area,
    selected_products=None,
    max_share=0.4,
    strateji="dengeli",
    gecmis_verimler=None,
    ek_maliyet_donum=0,
):
    target_year = get_target_year(season)

    df = load_optimization_data()
    suitable_products = get_suitable_products(df, district, season=season)
    suitable_products = filter_selected_products(suitable_products, selected_products)

    if suitable_products.empty:
        raise ValueError("Bu il/ilce icin uygun urun bulunamadi.")

    decision_data = build_decision_data(
        db=db,
        suitable_products=suitable_products,
        district=district,
        season=season,
        strateji=strateji,
        gecmis_verimler=gecmis_verimler,
        ek_maliyet_donum=ek_maliyet_donum,
    )

    decision_data = drop_unprofitable(decision_data)
    if decision_data.empty:
        raise ValueError(
            "Bu koşullarda beklenen kârı pozitif olan ürün yok. "
            "Alanı boş bırakmak ya da girilen giderleri gözden geçirmek önerilir."
        )

    model = pulp.LpProblem("optimal_ekim_plani", pulp.LpMaximize)

    area_vars = {}
    for _, row in decision_data.iterrows():
        product_name = row["product_name"]
        area_vars[product_name] = pulp.LpVariable(
            name=f"x_{safe_name(product_name)}",
            lowBound=0,
            cat="Continuous",
        )

    model += pulp.lpSum(
        area_vars[row["product_name"]] * row["final_score"]
        for _, row in decision_data.iterrows()
    )

    model += (
        pulp.lpSum(area_vars.values()) <= total_area,
        "total_area_constraint",
    )

    for _, row in decision_data.iterrows():
        product_name = row["product_name"]

        model += (
            area_vars[product_name] <= total_area * max_share,
            f"max_share_{safe_name(product_name)}",
        )

        if pd.notna(row.get("quota")):
            model += (
                area_vars[product_name] <= row["quota"],
                f"quota_{safe_name(product_name)}",
            )

    status = model.solve(pulp.PULP_CBC_CMD(msg=False))

    if pulp.LpStatus[status] != "Optimal":
        raise ValueError(f"Optimal ekim plani bulunamadi: {pulp.LpStatus[status]}")

    result_rows = []
    for _, row in decision_data.iterrows():
        product_name = row["product_name"]
        planted_area = area_vars[product_name].value()

        if planted_area is None or planted_area <= 0:
            continue

        profit_result = add_profit(
            db=db,
            product_name=product_name,
            district=district,
            target_season=season,
            area=planted_area,
            gecmis_verimler=gecmis_verimler,
            ek_maliyet_donum=ek_maliyet_donum,
        )
        risk_result = add_risk(
            db=db,
            product_name=product_name,
            district=district,
            season=season,
            area=planted_area,
        )

        result_rows.append(
            {
                "district": district,
                "target_year": target_year,
                "season": season,
                "product_name": product_name,
                "recommended_area": round(planted_area, 2),
                "quota": None if pd.isna(row.get("quota")) else float(row["quota"]),
                "predicted_price": round(float(profit_result["tahmini_fiyat"]), 2),
                "estimated_production": round(float(profit_result["tahmini_uretim"]), 2),
                "estimated_revenue": round(float(profit_result["tahmini_gelir"]), 2),
                "fertilizer_cost": round(float(profit_result["gubre_gideri"]), 2),
                "fuel_cost": round(float(profit_result["mazot_gideri"]), 2),
                "estimated_cost": round(float(profit_result["toplam_gider"]), 2),
                "estimated_profit": round(float(profit_result["net_kar"]), 2),
                "estimated_profit_low": profit_result["net_kar_dusuk"],
                "estimated_profit_high": profit_result["net_kar_yuksek"],
                "breakeven_price": profit_result["basabas_fiyati"],
                "loss_probability": profit_result["zarar_olasiligi"],
                "interval_coverage": profit_result["aralik_isabeti"],
                "own_yield_weight": profit_result["kendi_verim_agirligi"],
                "assumptions": profit_result["varsayimlar"],
                "costs_incomplete": profit_result["maliyetler_eksik"],
                "strategy": strateji,
                "profit_per_decare": round(float(row["profit_per_decare"]), 2),
                "profit_score": round(float(row["profit_score"]), 2),
                "risk_score": round(float(risk_result["genel_risk"]), 2),
                "risk_level": risk_result.get("risk_seviyesi"),
                "risk_color": risk_result.get("risk_emoji"),
                "safety_score": round(100 - float(risk_result["genel_risk"]), 2),
                "final_score": round(float(row["final_score"]), 2),
            }
        )

    result = pd.DataFrame(result_rows)
    result = result.sort_values(by="final_score", ascending=False).reset_index(drop=True)

    return result.to_dict(orient="records")


def create_plan_for_user_fields(
    db,
    fields,
    season,
    selected_products=None,
    strateji="dengeli",
    gecmis_verimler=None,
    ek_maliyet_donum=0,
):
    all_plans = []
    target_year = get_target_year(season)

    for field in fields:
        field_id = field["id"]
        district = field["district"]
        total_area = field["area"]

        try:
            plan = create_planting(
                db=db,
                district=district,
                season=season,
                total_area=total_area,
                selected_products=selected_products,
                strateji=strateji,
                gecmis_verimler=gecmis_verimler,
                ek_maliyet_donum=ek_maliyet_donum,
            )

            all_plans.append(
                {
                    "field_id": field_id,
                    "district": district,
                    "total_area": total_area,
                    "target_year": target_year,
                    "strategy": strateji,
                    "success": True,
                    # kota ve karlilik kisitlari yuzunden ekilmesi onerilmeyen alan
                    "unallocated_area": round(total_area - sum(row["recommended_area"] for row in plan), 2),
                    "plan": plan,
                }
            )

        except ValueError as error:
            all_plans.append(
                {
                    "field_id": field_id,
                    "district": district,
                    "total_area": total_area,
                    "target_year": target_year,
                    "success": False,
                    "error": str(error),
                    "plan": [],
                }
            )

    return all_plans


if __name__ == "__main__":
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        plan = create_planting(
            db=db,
            district="Tire",
            season="Summer",
            total_area=100,
        )
        print(plan)
    finally:
        db.close()
