"""Exploratory data analysis on listing_master: figures to output/figures/, stats returned as dicts."""

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "output" / "figures"
FIGURE_DPI = 150

# Reference palette (see dataviz skill: references/palette.md) -- fixed hue
# order for categorical identity, one sequential hue for plain magnitude.
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
AXIS_LINE = "#c3c2b7"
CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
SEQUENTIAL = "#2a78d6"


def load_data() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "listing_master.parquet")


def load_calendar() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "calendar.parquet")


def _style_axes(ax, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=11, fontweight="bold", color=INK_PRIMARY, pad=8)
    ax.set_xlabel(xlabel, fontsize=9.5, color=INK_SECONDARY)
    ax.set_ylabel(ylabel, fontsize=9.5, color=INK_SECONDARY)
    ax.tick_params(colors=INK_MUTED, labelsize=8.5)
    ax.grid(True, color=GRIDLINE, linewidth=0.6, alpha=0.9, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("bottom", "left"):
        ax.spines[spine].set_color(AXIS_LINE)
    ax.set_facecolor(SURFACE)


def _save_fig(fig: plt.Figure, filename: str) -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / filename
    fig.patch.set_facecolor(SURFACE)
    fig.savefig(path, dpi=FIGURE_DPI, facecolor=SURFACE)
    plt.close(fig)
    return path


def _color_boxplot(bp: dict, colors: list) -> None:
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.85)
        patch.set_edgecolor(INK_SECONDARY)
        patch.set_linewidth(0.8)
    for element in ("whiskers", "caps"):
        for line in bp[element]:
            line.set_color(AXIS_LINE)
            line.set_linewidth(1)
    for line in bp["medians"]:
        line.set_color(INK_PRIMARY)
        line.set_linewidth(1.4)


def plot_price_distribution(df: pd.DataFrame) -> dict:
    price = df["price"].dropna().astype(float)
    log_price = np.log10(price[price > 0])

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))

    axes[0, 0].hist(price, bins=50, color=SEQUENTIAL, edgecolor=SURFACE, linewidth=0.3)
    _style_axes(axes[0, 0], "Price distribution (raw)", "Price (£/night)", "Listings")

    axes[0, 1].hist(log_price, bins=50, color=SEQUENTIAL, edgecolor=SURFACE, linewidth=0.3)
    _style_axes(axes[0, 1], "Price distribution (log10)", "log10(Price)", "Listings")

    # Room_type has only 4 values -- few enough to assign each its own
    # categorical hue (identity), fixed slot order per the palette.
    room_types = sorted(df["room_type"].dropna().unique())
    price_by_room = [df.loc[df["room_type"] == rt, "price"].dropna().astype(float) for rt in room_types]
    bp = axes[1, 0].boxplot(price_by_room, tick_labels=room_types, patch_artist=True, widths=0.6)
    _color_boxplot(bp, CATEGORICAL[: len(room_types)])
    _style_axes(axes[1, 0], "Price by room type (raw)", "", "Price (£/night)")
    axes[1, 0].tick_params(axis="x", rotation=15)

    price_by_room_log = [np.log10(p[p > 0]) for p in price_by_room]
    bp = axes[1, 1].boxplot(price_by_room_log, tick_labels=room_types, patch_artist=True, widths=0.6)
    _color_boxplot(bp, CATEGORICAL[: len(room_types)])
    _style_axes(axes[1, 1], "Price by room type (log10)", "", "log10(Price)")
    axes[1, 1].tick_params(axis="x", rotation=15)

    fig.suptitle("Price Distribution — Edinburgh Listings", fontsize=13, fontweight="bold", color=INK_PRIMARY)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    _save_fig(fig, "price_distribution.png")

    # property_type has 28 categories -- too many for distinguishable
    # categorical hues, so every box shares one neutral fill and identity is
    # carried by the (sorted) axis position/label instead of color.
    property_medians = df.groupby("property_type")["price"].median().sort_values()
    ordered_types = property_medians.index.tolist()
    price_by_property = [df.loc[df["property_type"] == pt, "price"].dropna().astype(float) for pt in ordered_types]

    fig2, axes2 = plt.subplots(1, 2, figsize=(14, max(6, 0.32 * len(ordered_types))))
    bp = axes2[0].boxplot(
        price_by_property, tick_labels=ordered_types, patch_artist=True, widths=0.6, orientation="horizontal"
    )
    _color_boxplot(bp, [SEQUENTIAL] * len(ordered_types))
    _style_axes(axes2[0], "Price by property type (raw)", "Price (£/night)", "")
    axes2[0].tick_params(axis="y", labelsize=7.5)

    price_by_property_log = [np.log10(p[p > 0]) for p in price_by_property]
    bp = axes2[1].boxplot(
        price_by_property_log, tick_labels=ordered_types, patch_artist=True, widths=0.6, orientation="horizontal"
    )
    _color_boxplot(bp, [SEQUENTIAL] * len(ordered_types))
    _style_axes(axes2[1], "Price by property type (log10)", "log10(Price)", "")
    axes2[1].tick_params(axis="y", labelsize=7.5)

    fig2.suptitle(
        "Price by Property Type — Edinburgh Listings (sorted by median)",
        fontsize=13,
        fontweight="bold",
        color=INK_PRIMARY,
    )
    fig2.tight_layout(rect=(0, 0, 1, 0.97))
    _save_fig(fig2, "price_distribution_by_property_type.png")

    return {
        "price_count": int(price.count()),
        "price_missing_pct": round(df["price"].isna().mean() * 100, 2),
        "price_mean": round(price.mean(), 2),
        "price_median": round(price.median(), 2),
        "price_std": round(price.std(), 2),
        "price_skew": round(price.skew(), 3),
        "price_p90": round(price.quantile(0.9), 2),
        "median_price_by_room_type": {rt: round(v, 2) for rt, v in df.groupby("room_type")["price"].median().items()},
        "median_price_top5_property_types": {
            k: round(v, 2) for k, v in property_medians.sort_values(ascending=False).head(5).items()
        },
    }


def plot_listings_per_host(df: pd.DataFrame) -> dict:
    listings_per_host = df.groupby("host_id").size()

    # Degree-distribution view: for each listing count k, how many hosts have
    # exactly k listings. Plotting on log-log axes is the standard way to spot
    # the heavy-tailed, power-law-like concentration typical of Airbnb markets.
    degree_counts = listings_per_host.value_counts().sort_index()

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(
        degree_counts.index, degree_counts.values, s=32, color=CATEGORICAL[0], alpha=0.85,
        edgecolor=SURFACE, linewidth=0.4,
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    _style_axes(ax, "Listings per Host (log-log)", "Listings per host (log scale)", "Number of hosts (log scale)")
    fig.tight_layout()
    _save_fig(fig, "listings_per_host.png")

    sorted_desc = listings_per_host.sort_values(ascending=False)
    n_hosts = len(sorted_desc)
    top_n = max(1, math.ceil(n_hosts * 0.10))
    top_10pct_share = sorted_desc.iloc[:top_n].sum() / sorted_desc.sum() * 100

    return {
        "n_hosts": int(n_hosts),
        "n_listings": int(listings_per_host.sum()),
        "avg_listings_per_host": round(listings_per_host.mean(), 2),
        "median_listings_per_host": int(listings_per_host.median()),
        "max_listings_single_host": int(listings_per_host.max()),
        "top_10pct_host_count": int(top_n),
        "top_10pct_listing_share_pct": round(top_10pct_share, 2),
    }


def plot_review_score_distribution(df: pd.DataFrame) -> dict:
    scores = df["review_scores_rating"].dropna().astype(float)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.hist(scores, bins=np.arange(1, 5.05, 0.05), color=SEQUENTIAL, edgecolor=SURFACE, linewidth=0.3)
    # Reference line, not a data series -- uses the fixed "critical" status
    # step so it never gets mistaken for a categorical identity color.
    ax.axvline(4.8, color="#d03b3b", linewidth=1.5, linestyle="--", zorder=3)
    ax.text(4.8, ax.get_ylim()[1] * 0.97, " 4.8+", color=INK_SECONDARY, fontsize=9, va="top")
    _style_axes(ax, "Review Score Distribution", "Average review score", "Number of listings")
    fig.tight_layout()
    _save_fig(fig, "review_score_distribution.png")

    pct_high = (scores >= 4.8).mean() * 100

    return {
        "reviewed_listing_count": int(scores.count()),
        "no_review_score_pct": round(df["review_scores_rating"].isna().mean() * 100, 2),
        "avg_review_score": round(scores.mean(), 3),
        "median_review_score": round(scores.median(), 3),
        "pct_scoring_4_8_or_higher": round(pct_high, 2),
    }


def _annotate_bars(ax, bars, fmt) -> None:
    for bar in bars:
        height = bar.get_height()
        if pd.isna(height):
            continue
        ax.text(
            bar.get_x() + bar.get_width() / 2, height, fmt(height),
            ha="center", va="bottom", fontsize=8.5, color=INK_PRIMARY,
        )


def plot_host_segment_comparison(df: pd.DataFrame) -> dict:
    df = df.copy()
    listings_per_host = df.groupby("host_id")["id"].transform("count")
    df["_host_size_segment"] = np.where(listings_per_host >= 2, "Multi-listing (2+)", "Single-listing")
    df["_superhost_segment"] = df["host_is_superhost"].map({"t": "Superhost", "f": "Non-superhost"})

    metrics = [
        ("price", "Avg price (£/night)", lambda v: f"£{v:.0f}"),
        ("occupancy_rate_365", "Avg occupancy rate", lambda v: f"{v:.0%}"),
        ("review_scores_rating", "Avg review score", lambda v: f"{v:.2f}"),
    ]
    host_size_order = ["Single-listing", "Multi-listing (2+)"]
    superhost_order = ["Non-superhost", "Superhost"]

    host_size_means = df.groupby("_host_size_segment")[[m for m, _, _ in metrics]].mean().reindex(host_size_order)
    superhost_means = df.groupby("_superhost_segment")[[m for m, _, _ in metrics]].mean().reindex(superhost_order)

    fig, axes = plt.subplots(2, 3, figsize=(14, 8.5))

    for col, (metric, label, fmt) in enumerate(metrics):
        ax = axes[0, col]
        bars = ax.bar(
            host_size_order, host_size_means[metric].values, color=CATEGORICAL[0:2], width=0.55,
            edgecolor=SURFACE, linewidth=0.5,
        )
        _style_axes(ax, label, "", "")
        _annotate_bars(ax, bars, fmt)

        ax = axes[1, col]
        bars = ax.bar(
            superhost_order, superhost_means[metric].values, color=CATEGORICAL[2:4], width=0.55,
            edgecolor=SURFACE, linewidth=0.5,
        )
        _style_axes(ax, label, "", "")
        _annotate_bars(ax, bars, fmt)

    axes[0, 0].set_ylabel("By listings per host", fontsize=9.5, color=INK_SECONDARY)
    axes[1, 0].set_ylabel("By superhost status", fontsize=9.5, color=INK_SECONDARY)

    fig.suptitle("Host Segment Comparison — Edinburgh Listings", fontsize=13, fontweight="bold", color=INK_PRIMARY)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    _save_fig(fig, "host_segment_comparison.png")

    host_listing_counts = df.groupby("host_id").size()
    superhost_host_counts = df.drop_duplicates("host_id")["host_is_superhost"].value_counts(dropna=True)

    return {
        "n_single_listing_hosts": int((host_listing_counts == 1).sum()),
        "n_multi_listing_hosts": int((host_listing_counts >= 2).sum()),
        "n_superhosts": int(superhost_host_counts.get("t", 0)),
        "n_non_superhosts": int(superhost_host_counts.get("f", 0)),
        "by_host_size": host_size_means.round(3).to_dict(orient="index"),
        "by_superhost_status": superhost_means.round(3).to_dict(orient="index"),
    }


def plot_price_by_neighbourhood(df: pd.DataFrame) -> dict:
    medians = df.groupby("neighbourhood_cleansed")["price"].median().sort_values()
    ordered = medians.index.tolist()

    # One neutral fill, not per-neighbourhood hues: with 100+ categories,
    # color can't do identity work anyway -- the sorted axis position and
    # label already carry it (ascending order here plots highest at the top,
    # i.e. "sorted descending" reading top-to-bottom).
    fig, ax = plt.subplots(figsize=(10, max(6, 0.22 * len(ordered))))
    ax.barh(ordered, medians.values, color=SEQUENTIAL, edgecolor=SURFACE, linewidth=0.3, height=0.7)
    _style_axes(ax, "Median Price by Neighbourhood — Edinburgh", "Median price (£/night)", "")
    ax.tick_params(axis="y", labelsize=7.5)
    fig.tight_layout()
    _save_fig(fig, "price_by_neighbourhood.png")

    return {
        "n_neighbourhoods": int(len(ordered)),
        "highest_median_price_neighbourhood": ordered[-1],
        "highest_median_price": round(medians.iloc[-1], 2),
        "lowest_median_price_neighbourhood": ordered[0],
        "lowest_median_price": round(medians.iloc[0], 2),
        "citywide_median_price": round(df["price"].median(), 2),
    }


def plot_geographic_scatter(df: pd.DataFrame) -> dict:
    geo = df.dropna(subset=["latitude", "longitude", "price"])

    # Price is heavily right-skewed (see plot_price_distribution); a linear
    # color scale would saturate almost every point to one end and hide the
    # spatial gradient behind a handful of luxury outliers, so price maps to
    # color on a log scale here. viridis is perceptually uniform and
    # colorblind-safe, which is what a continuous spatial gradient needs.
    fig, ax = plt.subplots(figsize=(9, 8))
    scatter = ax.scatter(
        geo["longitude"], geo["latitude"], c=geo["price"], cmap="viridis",
        norm=LogNorm(vmin=geo["price"].min(), vmax=geo["price"].max()),
        s=14, alpha=0.75, linewidth=0,
    )
    _style_axes(ax, "Spatial Price Gradient — Edinburgh Listings", "Longitude", "Latitude")
    ax.set_aspect("equal", adjustable="datalim")
    cbar = fig.colorbar(scatter, ax=ax, pad=0.02)
    cbar.set_label("Price (£/night, log scale)", fontsize=9.5, color=INK_SECONDARY)
    cbar.ax.tick_params(colors=INK_MUTED, labelsize=8.5)
    fig.tight_layout()
    _save_fig(fig, "geographic_price_scatter.png")

    return {
        "n_listings_plotted": int(len(geo)),
        "n_listings_missing_coords_or_price": int(len(df) - len(geo)),
        "lat_range": (round(geo["latitude"].min(), 4), round(geo["latitude"].max(), 4)),
        "lon_range": (round(geo["longitude"].min(), 4), round(geo["longitude"].max(), 4)),
    }


def plot_seasonal_price_trend(calendar_df: pd.DataFrame) -> dict:
    # This extract's calendar.csv has no price column at all (see
    # cleaning.py/standardize_price_columns) -- there's no per-date price to
    # average by month, so this is surfaced clearly instead of silently
    # skipping or fabricating a chart from something else.
    if "price" not in calendar_df.columns:
        print("plot_seasonal_price_trend: calendar data has no 'price' column -- no figure generated.")
        return {
            "status": "unavailable",
            "reason": "calendar.csv has no price column in this extract",
        }

    monthly = calendar_df.dropna(subset=["price"]).groupby(calendar_df["date"].dt.month)["price"].mean()
    monthly = monthly.reindex(range(1, 13))
    month_labels = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    peak_month = int(monthly.idxmax())

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(range(1, 13), monthly.values, color=SEQUENTIAL, linewidth=2, marker="o", markersize=5)
    ax.scatter(
        [peak_month], [monthly.loc[peak_month]], color="#d03b3b", s=60, zorder=4,
        label=f"Peak: {month_labels[peak_month - 1]}",
    )
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(month_labels)
    _style_axes(ax, "Average Price by Month — Edinburgh Calendar", "Month", "Average price (£/night)")
    ax.legend(frameon=False, labelcolor=INK_SECONDARY, fontsize=9.5)
    fig.tight_layout()
    _save_fig(fig, "seasonal_price_trend.png")

    return {
        "status": "ok",
        "peak_month": month_labels[peak_month - 1],
        "peak_month_avg_price": round(monthly.loc[peak_month], 2),
        "lowest_month": month_labels[int(monthly.idxmin()) - 1],
        "lowest_month_avg_price": round(monthly.min(), 2),
    }


def main() -> None:
    df = load_data()
    calendar_df = load_calendar()

    results = {
        "price_distribution": plot_price_distribution(df),
        "listings_per_host": plot_listings_per_host(df),
        "review_score_distribution": plot_review_score_distribution(df),
        "host_segment_comparison": plot_host_segment_comparison(df),
        "price_by_neighbourhood": plot_price_by_neighbourhood(df),
        "geographic_scatter": plot_geographic_scatter(df),
        "seasonal_price_trend": plot_seasonal_price_trend(calendar_df),
    }

    for section, stats in results.items():
        print(f"\n--- {section} ---")
        for key, value in stats.items():
            print(f"{key}: {value}")

    print(f"\nFigures written to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
