"""Rolling-origin backtest for the inflation model.

The price forecast is built on top of the inflation forecast, so its error flows
straight into prices and profits. For every origin the model is trained only on
seasons up to that point and forecasts the next four seasons recursively, exactly
as the app does. It is compared with the naive forecast "inflation stays where it
is now"; the model is only worth using if it beats that. The app uses the blend
of the two (inflation_service.NAIVE_WEIGHT), which this script also reports.

Run from the project root:  python -m app.scripts.inflation_backtest
"""

import numpy as np
import pandas as pd

from app.services.inflation_service import (
    NAIVE_WEIGHT,
    SEASON_ORDER,
    blend_with_naive,
    TARGET_COLUMN,
    forecast_from_history,
    load_raw_inflation_data,
)

FIRST_ORIGIN = (2019, "Winter")
HORIZON = 4


def run_inflation_backtest(horizon: int = HORIZON) -> pd.DataFrame:
    raw = load_raw_inflation_data()
    keys = list(zip(raw["year"], raw["season_order"]))
    first = (FIRST_ORIGIN[0], SEASON_ORDER[FIRST_ORIGIN[1]])
    actual = {key: value for key, value in zip(keys, raw[TARGET_COLUMN])}

    records = []
    for index, key in enumerate(keys):
        if key < first or index == len(keys) - 1:
            continue

        history = raw.iloc[: index + 1]
        last_value = float(history[TARGET_COLUMN].iloc[-1])
        forecasts = forecast_from_history(history, horizon, naive_weight=0.0)

        for step, (year, season, predicted) in enumerate(forecasts, start=1):
            target = (year, SEASON_ORDER[season])
            if target not in actual:
                continue
            records.append(
                {
                    "origin": f"{key[0]}-{key[1]}",
                    "horizon": step,
                    "actual": actual[target],
                    "model": predicted,
                    "naive": last_value,
                    "blend": blend_with_naive(predicted, last_value, NAIVE_WEIGHT),
                }
            )

    return pd.DataFrame(records)


def error_by_horizon(frame: pd.DataFrame) -> pd.DataFrame:
    rows = {}
    for horizon, group in frame.groupby("horizon"):
        rows[horizon] = {
            "n": len(group),
            "model MAE (puan)": (group["model"] - group["actual"]).abs().mean(),
            "naive MAE (puan)": (group["naive"] - group["actual"]).abs().mean(),
            "karma MAE (puan)": (group["blend"] - group["actual"]).abs().mean(),
            "model bias (puan)": (group["model"] - group["actual"]).mean(),
        }
    return pd.DataFrame(rows).T.round(2)


def main():
    frame = run_inflation_backtest()
    print(f"Enflasyon backtest: {frame['origin'].nunique()} baslangic, {len(frame)} tahmin")
    print("Hata yillik enflasyon puani cinsindendir (ornegin 3.0 = 3 puan).\n")
    print(error_by_horizon(frame).to_string())

    mae = {name: (frame[name] - frame["actual"]).abs().mean() for name in ["model", "naive", "blend"]}
    best = min(mae, key=mae.get)
    print(f"\nGenel MAE: model {mae['model']:.2f}, naive {mae['naive']:.2f}, "
          f"karma {mae['blend']:.2f} -> en isabetlisi: {best}")


if __name__ == "__main__":
    main()
