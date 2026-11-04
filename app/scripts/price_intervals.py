"""Empirical prediction intervals for the price forecast.

The intervals come from the model's own out-of-sample errors in the rolling-origin
backtest, run end-to-end with the inflation forecast (as in the app). For each
forecast horizon (1-4 seasons ahead) the log errors log(actual / predicted) are
collected and their 2.5th and 97.5th percentiles give the interval:

    low  = predicted x exp(q_low)      high = predicted x exp(q_high)

Products differ in how wrong the forecast tends to be (some prices swing far more
than others), so each product also gets its own band. A product has only ~15-17
errors, so its quantiles are shrunk toward the horizon's pooled ones:

    q = w x q_product + (1 - w) x q_horizon,      w = n_product / (n_product + SHRINK_K)

Coverage is checked by leaving one forecast origin out at a time: intervals built
from the other origins are tested on the held-out one. The nominal 95% band only
covers about 77% of held-out prices (a narrower 80% band covered 62%): price regimes
shift between years, so in-sample errors understate future ones. The app therefore
reports the measured coverage, not the nominal level. Re-run after new data arrives.

Run from the project root:  python -m app.scripts.price_intervals
"""

import json
from datetime import date

import numpy as np
import pandas as pd

from app.scripts.price_backtest import run_backtest
from app.services.price_prediction import INTERVALS_PATH

LOW_Q, HIGH_Q = 0.025, 0.975
# A horizon with fewer errors than this falls back to all horizons pooled.
MIN_SAMPLES = 30
# Weight of a product's own quantiles: n / (n + SHRINK_K); ~15 errors give about one half.
SHRINK_K = 15


def log_errors(frame: pd.DataFrame) -> pd.Series:
    return np.log(frame["actual"] / frame["model"])


def quantiles(errors) -> dict:
    errors = np.asarray(errors, dtype=float)
    return {
        "q_low": float(np.quantile(errors, LOW_Q)),
        "q_mid": float(np.quantile(errors, 0.5)),
        "q_high": float(np.quantile(errors, HIGH_Q)),
        "n": int(len(errors)),
    }


def build_intervals(frame: pd.DataFrame) -> dict:
    frame = frame.assign(log_error=log_errors(frame))
    pooled = frame["log_error"].to_numpy()

    by_horizon = {}
    for horizon, group in frame.groupby("horizon"):
        errors = group["log_error"].to_numpy()
        source = errors if len(errors) >= MIN_SAMPLES else pooled
        by_horizon[str(int(horizon))] = {
            **quantiles(source),
            "pooled": bool(len(errors) < MIN_SAMPLES),
            "errors": [round(float(e), 4) for e in source],
        }

    by_product = {}
    for product, group in frame.groupby("product"):
        errors = group["log_error"].to_numpy()
        by_product[product] = {
            **quantiles(errors),
            "weight": round(len(errors) / (len(errors) + SHRINK_K), 3),
            "errors": [round(float(e), 4) for e in errors],
        }

    return {"overall": quantiles(pooled), "by_horizon": by_horizon, "by_product": by_product}


def shrunk_bounds(horizon_q: tuple[float, float], product_errors, shrink_k: int = SHRINK_K):
    """Product quantiles pulled toward the horizon's; the app applies the same rule."""
    if product_errors is None or len(product_errors) == 0:
        return horizon_q
    weight = len(product_errors) / (len(product_errors) + shrink_k)
    product_q = np.quantile(product_errors, [LOW_Q, HIGH_Q])
    return tuple(weight * pq + (1 - weight) * hq for pq, hq in zip(product_q, horizon_q))


def leave_one_origin_out_coverage(frame: pd.DataFrame, per_product: bool = True) -> float:
    frame = frame.assign(log_error=log_errors(frame))
    hits = []
    for origin in frame["origin"].unique():
        train = frame[frame["origin"] != origin]
        test = frame[frame["origin"] == origin]
        for row in test.itertuples():
            reference = train.loc[train["horizon"] == row.horizon, "log_error"]
            if len(reference) < MIN_SAMPLES:
                reference = train["log_error"]
            bounds = tuple(np.quantile(reference, [LOW_Q, HIGH_Q]))
            if per_product:
                bounds = shrunk_bounds(bounds, train.loc[train["product"] == row.product, "log_error"].to_numpy())
            hits.append(bounds[0] <= row.log_error <= bounds[1])
    return float(np.mean(hits))


def main():
    frame = run_backtest(inflation_source="forecast")
    intervals = build_intervals(frame)
    coverage = leave_one_origin_out_coverage(frame)
    pooled_coverage = leave_one_origin_out_coverage(frame, per_product=False)

    payload = {
        "generated": date.today().isoformat(),
        "level": HIGH_Q - LOW_Q,
        "inflation_source": "forecast",
        "n_predictions": int(len(frame)),
        "loo_coverage": round(coverage, 3),
        "loo_coverage_pooled_only": round(pooled_coverage, 3),
        "shrink_k": SHRINK_K,
        "low_q": LOW_Q,
        "high_q": HIGH_Q,
        **intervals,
    }
    INTERVALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    INTERVALS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"{len(frame)} tahmin, nominal kapsama %{payload['level'] * 100:.0f}, "
          f"olculen (birini-disarida-birak) kapsama %{coverage * 100:.1f} "
          f"(urune ozel olmadan %{pooled_coverage * 100:.1f})")
    for horizon, row in intervals["by_horizon"].items():
        low, high = np.exp(row["q_low"]) * 100 - 100, np.exp(row["q_high"]) * 100 - 100
        print(f"  {horizon} sezon sonrasi: tahminin %{low:+.0f} / %{high:+.0f} arasi (n={row['n']})")
    for product, row in intervals["by_product"].items():
        low, high = np.exp(row["q_low"]) * 100 - 100, np.exp(row["q_high"]) * 100 - 100
        print(f"  {product:<16} kendi hatalari %{low:+.0f} / %{high:+.0f} (n={row['n']}, agirlik {row['weight']})")
    print(f"Kaydedildi: {INTERVALS_PATH}")


if __name__ == "__main__":
    main()
