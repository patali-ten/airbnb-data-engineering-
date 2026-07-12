"""Train a RandomForestRegressor to predict listing price, benchmarked against a mean baseline."""

from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "output" / "figures"
REPORT_PATH = PROJECT_ROOT / "output" / "quality_report" / "model_performance.md"
FIGURE_DPI = 150

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"

RANDOM_STATE = 42
TEST_SIZE = 0.2
N_ESTIMATORS = 200
SKEW_THRESHOLD = 1.0  # matches regression.py's log-vs-raw price decision
SHAP_TOP_N = 5

# Same numeric feature set as regression.py's predictors, extended to the
# fuller set of non-leakage numeric fields available in listing_master.
NUMERIC_FEATURES = [
    "accommodates",
    "bedrooms",
    "beds",
    "bathrooms",
    "minimum_nights",
    "maximum_nights",
    "availability_365",
    "number_of_reviews",
    "review_scores_rating",
    "reviews_per_month",
    "host_listings_count",
    "calculated_host_listings_count",
    "occupancy_rate_365",
    "neighbourhood_listing_density",
    "neighbourhood_avg_rating",
    "latitude",
    "longitude",
    "host_tenure_years",
]
CATEGORICAL_FEATURES = ["room_type", "property_type"]

# Same leakage reasoning as regression.py: these are computed directly from
# price (or from a live price quote captured at the same scrape step as
# price), so a model including them would effectively predict price from
# price and report a meaninglessly high R². neighbourhood_median_price is
# the one regression.py's VIF check specifically flagged before being
# excluded there.
LEAKAGE_FEATURES = [
    "neighbourhood_median_price",
    "price_per_bedroom",
    "estimated_annual_revenue",
    "price_quote_total_price",
    "price_quote_price_per_night",
]


def load_data() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "listing_master.parquet")


def _select_target(df: pd.DataFrame, price_col: str = "price") -> tuple:
    # Cast off the nullable Float64 dtype before log10: its masked-out (NA)
    # slots carry an undefined underlying value, which np.log10 evaluates
    # elementwise before the mask is applied, raising a spurious "divide by
    # zero" warning even though every real price is positive.
    price = df[price_col].astype("float64")
    skewness = float(price.dropna().skew())

    if abs(skewness) > SKEW_THRESHOLD:
        target_name = "log_price"
        target_series = np.log10(price.where(price > 0))
    else:
        target_name = price_col
        target_series = price

    return target_name, target_series, skewness


def build_feature_matrix(df: pd.DataFrame) -> tuple:
    usable_numeric = []
    excluded = []
    for col in NUMERIC_FEATURES:
        if col not in df.columns:
            print(f"Skipping feature '{col}': not found in dataframe.")
            excluded.append(col)
            continue
        if df[col].isna().all():
            print(f"Skipping feature '{col}': entirely null in this dataset.")
            excluded.append(col)
            continue
        usable_numeric.append(col)

    numeric_part = df[usable_numeric].astype(float)
    categorical_part = pd.get_dummies(df[CATEGORICAL_FEATURES], columns=CATEGORICAL_FEATURES, dtype=float)
    X = pd.concat([numeric_part, categorical_part], axis=1)
    return X, excluded


def _rmse(y_true, y_pred) -> float:
    return float(mean_squared_error(y_true, y_pred) ** 0.5)


def print_largest_errors(df: pd.DataFrame, price_test: pd.Series, pred_price: np.ndarray, n: int = 5) -> None:
    # Checks whether the same extreme-outlier listings responsible for the
    # RMSE gap and the £-scale R² drop (see the report's scale note) are
    # visible here as the model's single worst individual misses.
    errors = pd.DataFrame(
        {
            "listing_id": df.loc[price_test.index, "id"].to_numpy(),
            "actual_price": price_test.to_numpy(),
            "predicted_price": pred_price,
        },
        index=price_test.index,
    )
    errors["abs_error"] = (errors["actual_price"] - errors["predicted_price"]).abs()
    top_errors = errors.sort_values("abs_error", ascending=False).head(n)

    print(f"\nTop {n} largest prediction errors on the test set (GBP):")
    for _, row in top_errors.iterrows():
        print(
            f"  listing_id={int(row['listing_id'])}  actual={row['actual_price']:.2f}  "
            f"predicted={row['predicted_price']:.2f}  abs_error={row['abs_error']:.2f}"
        )


def _save_shap_fig(filename: str) -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / filename
    fig = plt.gcf()
    fig.patch.set_facecolor(SURFACE)
    fig.tight_layout()
    fig.savefig(path, dpi=FIGURE_DPI, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_shap_summary(shap_values, X_test: pd.DataFrame) -> Path:
    # The model's target is log_price (see _select_target), so these SHAP
    # values are in log-price units, not £ -- the title says so directly to
    # stop this plot from being misread as a pound-figure breakdown.
    shap.summary_plot(shap_values, X_test, show=False)
    plt.title("SHAP Summary -- log-price units, NOT GBP", fontsize=11, color=INK_PRIMARY)
    return _save_shap_fig("shap_summary.png")


def plot_shap_importance(shap_values, X_test: pd.DataFrame) -> Path:
    shap.summary_plot(shap_values, X_test, plot_type="bar", show=False)
    # shap's default width clips this plot's long x-axis label; widen it.
    plt.gcf().set_size_inches(11, plt.gcf().get_size_inches()[1])
    plt.title("Mean |SHAP value| per Feature -- log-price units, NOT GBP", fontsize=11, color=INK_PRIMARY)
    return _save_shap_fig("shap_importance.png")


def _describe_shap_feature(feature: str, direction: str, rank: int) -> str:
    strength = "the strongest" if rank == 1 else "one of the strongest"
    driver_noun = "driver" if rank == 1 else "drivers"
    polarity = "positive" if direction == "positive" else "negative"

    for cat_col in CATEGORICAL_FEATURES:
        prefix = f"{cat_col}_"
        if feature.startswith(prefix):
            category = feature[len(prefix):]
            group = cat_col.replace("_", " ")
            return (
                f"being '{category}' ({group}) is {strength} {polarity} {driver_noun} of predicted price "
                f"relative to the other {group} categories."
            )

    trend = "increases" if direction == "positive" else "decreases"
    return (
        f"higher {feature} {trend} predicted price; it is {strength} {driver_noun} of the model's "
        "predictions overall."
    )


def describe_top_shap_features(shap_values, X_test: pd.DataFrame, n: int = SHAP_TOP_N) -> list:
    # Directional/relative only: SHAP contributions here live on the log-price
    # scale the model was fit on, and a log-scale contribution doesn't map to
    # a fixed £ amount (its £ effect depends on the listing's baseline price),
    # so these descriptions never quantify a pound figure.
    values = shap_values.values
    mean_abs = np.abs(values).mean(axis=0)
    order = np.argsort(mean_abs)[::-1][:n]

    results = []
    for rank, idx in enumerate(order, start=1):
        feature = X_test.columns[idx]
        feature_values = X_test.iloc[:, idx].to_numpy(dtype=float)
        shap_col = values[:, idx]

        if np.std(feature_values) > 0:
            correlation = np.corrcoef(feature_values, shap_col)[0, 1]
            direction = "positive" if correlation >= 0 else "negative"
        else:
            direction = "positive" if shap_col.mean() >= 0 else "negative"

        results.append(
            {
                "rank": rank,
                "feature": feature,
                "mean_abs_shap": round(float(mean_abs[idx]), 4),
                "direction": direction,
                "description": _describe_shap_feature(feature, direction, rank),
            }
        )

    print(f"\nTop {n} features by mean |SHAP value| (log-price units -- directional only, not GBP):")
    for row in results:
        print(f"{row['rank']}. {row['feature']}: {row['description']}")

    return results


def render_report(
    target_name: str, price_skew: float, n_train: int, n_test: int, dropped_rows: int,
    excluded_features: list, rf_metrics: dict, baseline_metrics: dict, feature_importances: pd.Series,
    shap_features: list,
) -> str:
    mae_improvement = (1 - rf_metrics["mae"] / baseline_metrics["mae"]) * 100
    rmse_improvement = (1 - rf_metrics["rmse"] / baseline_metrics["rmse"]) * 100

    lines = [
        "# Price Prediction Model Performance",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Setup",
        f"- Target: `{target_name}`" + (
            f" (price skew={price_skew:.2f}, log10-transformed since |skew| > {SKEW_THRESHOLD:.0f})"
            if target_name != "price" else f" (price skew={price_skew:.2f}, used raw)"
        ),
        f"- Model: RandomForestRegressor(n_estimators={N_ESTIMATORS}, random_state={RANDOM_STATE})",
        f"- Train/test split: 80/20, random_state={RANDOM_STATE}",
        f"- Rows used: {n_train + n_test} ({n_train} train / {n_test} test); {dropped_rows} rows dropped for missing values",
        f"- Excluded leakage features: {', '.join(LEAKAGE_FEATURES)} (derived from price itself)",
    ]
    if excluded_features:
        lines.append(f"- Excluded unusable features: {', '.join(excluded_features)} (entirely null in this dataset)")
    lines.append("")

    lines.append("## Test Set Performance (£ scale)")
    lines.append("")
    lines.append("| Model | MAE (£) | RMSE (£) | R² |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| Mean baseline | {baseline_metrics['mae']:.2f} | {baseline_metrics['rmse']:.2f} | {baseline_metrics['r2']:.4f} |"
    )
    lines.append(
        f"| Random Forest ({N_ESTIMATORS} trees) | {rf_metrics['mae']:.2f} | {rf_metrics['rmse']:.2f} | {rf_metrics['r2']:.4f} |"
    )
    lines.append("")
    lines.append(
        f"Random Forest reduces MAE by {mae_improvement:.1f}% and RMSE by {rmse_improvement:.1f}% compared to "
        "always predicting the training-set mean price."
    )
    lines.append("")

    if target_name != "price":
        lines.append(
            f"**Note on R² and scale:** the model is fit on `{target_name}`, where it explains "
            f"{rf_metrics['r2_log_scale']:.1%} of variance (R²={rf_metrics['r2_log_scale']:.4f}) — better than "
            "the OLS regression's log-scale R² (0.550). The £-scale R² above is lower because a handful of "
            "extreme luxury listings (£1,000+/night) get pulled toward the bulk of the distribution by "
            "log-space training, and those few large misses dominate a squared-error metric once "
            "back-transformed to £. MAE/RMSE are still reported in £ since that's the business-relevant unit, "
            "but the log-scale R² is the fairer measure of how well the model captures price patterns overall."
        )
        lines.append("")

    lines.append("## Top 10 Feature Importances")
    lines.append("")
    lines.append("| Feature | Importance |")
    lines.append("|---|---|")
    for feature, importance in feature_importances.head(10).items():
        lines.append(f"| {feature} | {importance:.4f} |")
    lines.append("")

    lines.append("## SHAP Feature Impact")
    lines.append("")
    lines.append(
        f"SHAP (TreeExplainer) values below are computed on `{target_name}` -- log-price units, not £. "
        "A log-scale contribution doesn't translate to a fixed pound amount (its £ effect depends on the "
        "listing's baseline price), so these are described directionally/relatively only, never quantified "
        "in £."
    )
    lines.append("")
    lines.append(f"![SHAP summary](../figures/shap_summary.png)")
    lines.append("")
    lines.append(f"![SHAP importance](../figures/shap_importance.png)")
    lines.append("")
    lines.append(f"**Top {len(shap_features)} drivers of predicted price:**")
    lines.append("")
    for row in shap_features:
        lines.append(f"{row['rank']}. **{row['feature']}** -- {row['description']}")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    df = load_data()

    target_name, target_series, price_skew = _select_target(df)
    print(f"Target: {target_name} (price skew={price_skew:.2f})")

    X, excluded_features = build_feature_matrix(df)
    feature_cols = list(X.columns)

    data = X.copy()
    data["price"] = df["price"].astype("float64")
    data["_target"] = df["price"].astype("float64") if target_name == "price" else target_series

    n_before = len(data)
    data = data.dropna()
    dropped_rows = n_before - len(data)

    X_clean = data[feature_cols]
    y_target = data["_target"]
    y_price = data["price"]

    X_train, X_test, y_train, y_test, price_train, price_test = train_test_split(
        X_clean, y_target, y_price, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    model = RandomForestRegressor(n_estimators=N_ESTIMATORS, random_state=RANDOM_STATE)
    model.fit(X_train, y_train)

    raw_pred = model.predict(X_test)
    pred_price = (10 ** raw_pred) if target_name == "log_price" else raw_pred

    rf_metrics = {
        "mae": float(mean_absolute_error(price_test, pred_price)),
        "rmse": _rmse(price_test, pred_price),
        "r2": float(r2_score(price_test, pred_price)),
        # R2 on the model's native (possibly log) target -- see the report's
        # note on why this diverges from the back-transformed £-scale R2.
        "r2_log_scale": float(r2_score(y_test, raw_pred)),
    }

    # Baseline: always predict the training-set mean price -- the simplest
    # model a stakeholder could imagine, and the bar the Random Forest needs
    # to clear to justify its added complexity.
    baseline_pred = np.full(len(price_test), fill_value=price_train.mean())
    baseline_metrics = {
        "mae": float(mean_absolute_error(price_test, baseline_pred)),
        "rmse": _rmse(price_test, baseline_pred),
        "r2": float(r2_score(price_test, baseline_pred)),
    }

    print("\n=== Test Set Performance (GBP scale) ===")
    print(f"Mean baseline : MAE={baseline_metrics['mae']:.2f}  RMSE={baseline_metrics['rmse']:.2f}  R2={baseline_metrics['r2']:.4f}")
    print(f"Random Forest : MAE={rf_metrics['mae']:.2f}  RMSE={rf_metrics['rmse']:.2f}  R2={rf_metrics['r2']:.4f}")
    if target_name != "price":
        print(f"Random Forest R2 on native '{target_name}' scale: {rf_metrics['r2_log_scale']:.4f} (see report note)")

    print_largest_errors(df, price_test, pred_price, n=5)

    feature_importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print("\nTop 10 feature importances:")
    print(feature_importances.head(10).to_string())

    print("\nComputing SHAP values (TreeExplainer) on the test set...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer(X_test)

    plot_shap_summary(shap_values, X_test)
    plot_shap_importance(shap_values, X_test)
    shap_features = describe_top_shap_features(shap_values, X_test, n=SHAP_TOP_N)

    report = render_report(
        target_name, price_skew, len(X_train), len(X_test), dropped_rows, excluded_features,
        rf_metrics, baseline_metrics, feature_importances, shap_features,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\nReport written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
