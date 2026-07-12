"""Correlation matrix, OLS price regression, and VIF diagnostics for listing_master."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from matplotlib.colors import LinearSegmentedColormap
from statsmodels.stats.outliers_influence import variance_inflation_factor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "output" / "figures"
FIGURE_DPI = 150

# Reference palette (see dataviz skill: references/palette.md).
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
AXIS_LINE = "#c3c2b7"
# Diverging job (correlation has a meaningful zero midpoint): sequential-blue's
# darkest practical step <-> neutral gray midpoint <-> the categorical red slot.
DIVERGING_NEG = "#184f95"
DIVERGING_ZERO = "#f0efec"
DIVERGING_POS = "#e34948"

SKEW_THRESHOLD = 1.0
VIF_THRESHOLD = 5.0

# Conceptual name -> actual listing_master column. Lets callers (and the
# hardcoded correlation-matrix list below) use the business-friendly names
# from the spec while resolving to this dataset's real schema.
CORRELATION_COLUMNS = {
    "price": "price",
    "occupancy_rate_365": "occupancy_rate_365",
    "review_count": "number_of_reviews",
    "avg_review_score": "review_scores_rating",
    "bedrooms": "bedrooms",
    "host_tenure_years": "host_tenure_years",
}


def load_data() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "listing_master.parquet")


def _style_axes(ax, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=11, fontweight="bold", color=INK_PRIMARY, pad=8)
    ax.set_xlabel(xlabel, fontsize=9.5, color=INK_SECONDARY)
    ax.set_ylabel(ylabel, fontsize=9.5, color=INK_SECONDARY)
    ax.tick_params(colors=INK_MUTED, labelsize=8.5)
    ax.set_facecolor(SURFACE)


def _save_fig(fig: plt.Figure, filename: str) -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / filename
    fig.patch.set_facecolor(SURFACE)
    fig.savefig(path, dpi=FIGURE_DPI, facecolor=SURFACE)
    plt.close(fig)
    return path


def _usable_columns(df: pd.DataFrame, column_map: dict) -> dict:
    """Resolve conceptual -> real column names, dropping any missing or entirely-null ones."""
    usable = {}
    for label, col in column_map.items():
        if col not in df.columns:
            print(f"Skipping '{label}': column '{col}' not found in dataframe.")
            continue
        if df[col].isna().all():
            print(f"Skipping '{label}' ('{col}'): column is entirely null in this dataset.")
            continue
        usable[label] = col
    return usable


def plot_correlation_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    usable = _usable_columns(df, CORRELATION_COLUMNS)
    labels = list(usable.keys())
    corr = df[[usable[label] for label in labels]].corr()
    corr.index = labels
    corr.columns = labels

    cmap = LinearSegmentedColormap.from_list("diverging_blue_red", [DIVERGING_NEG, DIVERGING_ZERO, DIVERGING_POS])

    fig, ax = plt.subplots(figsize=(1.2 * len(labels) + 2, 1.2 * len(labels) + 1))
    im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1)

    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=9, color=INK_SECONDARY)
    ax.set_yticklabels(labels, fontsize=9, color=INK_SECONDARY)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Direct value labels -- a heatmap's precise numbers matter more than the
    # color alone, and text color flips for contrast against strong fills.
    for i in range(len(labels)):
        for j in range(len(labels)):
            value = corr.values[i, j]
            text_color = SURFACE if abs(value) > 0.5 else INK_PRIMARY
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", color=text_color, fontsize=8.5)

    ax.set_title("Correlation Matrix — Edinburgh Listings", fontsize=12, fontweight="bold", color=INK_PRIMARY, pad=10)

    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("Pearson correlation", fontsize=9.5, color=INK_SECONDARY)
    cbar.ax.tick_params(colors=INK_MUTED, labelsize=8.5)

    fig.tight_layout()
    _save_fig(fig, "correlation_heatmap.png")
    return corr


def _resolve_column(name: str, df: pd.DataFrame) -> str:
    resolved = CORRELATION_COLUMNS.get(name, name)
    if resolved not in df.columns:
        raise KeyError(f"Predictor '{name}' (resolved to '{resolved}') not found in dataframe columns")
    return resolved


def _build_design_matrix(df: pd.DataFrame, predictors: list) -> tuple:
    frames = []
    excluded = []

    for name in predictors:
        col = _resolve_column(name, df)
        series = df[col]

        if series.isna().all():
            print(f"Excluding predictor '{name}' ('{col}'): entirely null in this dataset.")
            excluded.append(name)
            continue

        if pd.api.types.is_numeric_dtype(series):
            frames.append(series.rename(col).astype(float))
        else:
            # Categorical predictor (e.g. room_type) -- dummy-encode with
            # drop_first to avoid the dummy-variable trap (perfect
            # collinearity with the intercept).
            dummies = pd.get_dummies(series, prefix=col, drop_first=True, dtype=float)
            frames.append(dummies)

    design = pd.concat(frames, axis=1)
    return design, excluded


def _select_target(df: pd.DataFrame, price_col: str = "price") -> tuple:
    # Cast off the nullable Float64 dtype before log10: its masked-out (NA)
    # slots carry an undefined underlying value, which np.log10 evaluates
    # elementwise before the mask is applied, raising a spurious "divide by
    # zero" warning even though every real price is positive.
    price = df[price_col].astype("float64")
    skewness = float(price.dropna().skew())

    if abs(skewness) > SKEW_THRESHOLD:
        # Price is heavily right-skewed here (a handful of luxury listings
        # pull the tail out to 10000+); OLS assumes roughly normal residuals,
        # so a log target is the standard fix instead of forcing a linear fit
        # onto a lognormal-shaped variable.
        target_name = "log_price"
        target_series = np.log10(price.where(price > 0))
    else:
        target_name = price_col
        target_series = price

    return target_name, target_series, skewness


def run_price_regression(df: pd.DataFrame, predictors: list) -> dict:
    target_name, target_series, price_skew = _select_target(df)

    design, excluded_predictors = _build_design_matrix(df, predictors)
    data = design.copy()
    data[target_name] = target_series

    n_before = len(data)
    data = data.dropna()
    dropped_rows = n_before - len(data)

    y = data[target_name]
    X = sm.add_constant(data.drop(columns=[target_name]))

    model = sm.OLS(y, X).fit()

    print(
        f"Target: {target_name} "
        f"(price skew={price_skew:.2f}, {'log10-transformed' if target_name != 'price' else 'raw'})"
    )
    print(f"Observations used: {int(model.nobs)} (dropped {dropped_rows} rows with missing values)")
    if excluded_predictors:
        print(f"Excluded predictors (entirely null): {excluded_predictors}")
    print()
    print(model.summary())

    vif_rows = []
    for i, col in enumerate(X.columns):
        if col == "const":
            continue
        vif = float(variance_inflation_factor(X.values, i))
        vif_rows.append({"predictor": col, "vif": round(vif, 3), "flagged": bool(vif > VIF_THRESHOLD)})

    print("\nVariance Inflation Factors:")
    for row in vif_rows:
        flag = f" <-- FLAGGED (VIF > {VIF_THRESHOLD:.0f})" if row["flagged"] else ""
        print(f"  {row['predictor']:30s} VIF={row['vif']:.3f}{flag}")

    return {
        "target": target_name,
        "price_skew": round(price_skew, 3),
        "n_obs": int(model.nobs),
        "dropped_rows": int(dropped_rows),
        "excluded_predictors": excluded_predictors,
        "r_squared": round(float(model.rsquared), 4),
        "r_squared_adj": round(float(model.rsquared_adj), 4),
        "f_pvalue": float(model.f_pvalue),
        "coefficients": {col: round(float(v), 4) for col, v in model.params.items()},
        "p_values": {col: round(float(v), 4) for col, v in model.pvalues.items()},
        "vif": vif_rows,
        "flagged_predictors": [row["predictor"] for row in vif_rows if row["flagged"]],
        "model": model,
    }


def main() -> None:
    df = load_data()

    plot_correlation_heatmap(df)
    run_price_regression(
        df,
        predictors=[
            "occupancy_rate_365",
            "review_count",
            "avg_review_score",
            "bedrooms",
            "host_tenure_years",
            "room_type",
        ],
    )

    print(f"\nFigures written to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
