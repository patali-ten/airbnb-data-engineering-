"""Two-group and multi-group hypothesis tests with automatic test selection and plain-language summaries."""

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd

ALPHA = 0.05
SHAPIRO_MAX_N = 5000
BOOTSTRAP_ITERATIONS = 2000
BOOTSTRAP_SEED = 42

COHENS_D_THRESHOLDS = (0.2, 0.5, 0.8)
RANK_BISERIAL_THRESHOLDS = (0.1, 0.3, 0.5)
ETA_SQUARED_THRESHOLDS = (0.01, 0.06, 0.14)
TUKEY_SUMMARY_GROUP_THRESHOLD = 10


def _check_normality(sample: np.ndarray) -> dict:
    n = len(sample)
    if n <= SHAPIRO_MAX_N:
        stat, p_value = stats.shapiro(sample)
        return {
            "method": "shapiro",
            "statistic": round(float(stat), 4),
            "p_value": round(float(p_value), 4),
            "is_normal": bool(p_value > ALPHA),
            "n": n,
        }

    # Shapiro-Wilk grows too sensitive at large n -- with thousands of points
    # it rejects normality for even trivial deviations, so it stops being a
    # useful decision rule. Skewness/excess-kurtosis close to 0 is used
    # instead as a practical-significance check.
    skewness = float(stats.skew(sample))
    excess_kurtosis = float(stats.kurtosis(sample))
    is_normal = abs(skewness) < 0.5 and abs(excess_kurtosis) < 1.0
    return {
        "method": "skew_kurtosis",
        "skewness": round(skewness, 4),
        "excess_kurtosis": round(excess_kurtosis, 4),
        "is_normal": is_normal,
        "n": n,
        "note": f"Shapiro-Wilk skipped (n={n} > {SHAPIRO_MAX_N}); used skewness/kurtosis heuristic instead.",
    }


def _cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    n1, n2 = len(a), len(b)
    pooled_std = np.sqrt(((n1 - 1) * np.var(a, ddof=1) + (n2 - 1) * np.var(b, ddof=1)) / (n1 + n2 - 2))
    return float((np.mean(a) - np.mean(b)) / pooled_std)


def _rank_biserial(u_statistic: float, n1: int, n2: int) -> float:
    # Oriented so positive means group_a tends to rank higher than group_b,
    # matching Cohen's d's sign convention (positive = a > b).
    return float((2 * u_statistic) / (n1 * n2) - 1)


def _bootstrap_median_diff_ci(
    a: np.ndarray, b: np.ndarray, n_iterations: int = BOOTSTRAP_ITERATIONS, ci: float = 0.95
) -> tuple[float, float]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    boot_a = rng.choice(a, size=(n_iterations, len(a)), replace=True)
    boot_b = rng.choice(b, size=(n_iterations, len(b)), replace=True)
    diffs = np.median(boot_a, axis=1) - np.median(boot_b, axis=1)
    tail = (1 - ci) / 2 * 100
    lower, upper = np.percentile(diffs, [tail, 100 - tail])
    return float(lower), float(upper)


def _effect_size_label(abs_effect: float, thresholds: tuple[float, float, float]) -> str:
    small, medium, large = thresholds
    if abs_effect < small:
        return "negligible"
    if abs_effect < medium:
        return "small"
    if abs_effect < large:
        return "medium"
    return "large"


def _two_group_summary(
    value_col: str, group_a, group_b, a: np.ndarray, b: np.ndarray, test_used: str, p_value: float,
    effect_size: float, effect_size_type: str, magnitude: str, significant: bool,
    ci_low: float, ci_high: float,
) -> str:
    p_str = "p<0.001" if p_value < 0.001 else f"p={p_value:.3f}"

    if not significant:
        return (
            f"No statistically significant difference in {value_col} was found between "
            f"'{group_a}' and '{group_b}' ({test_used}, {p_str}); the observed gap could "
            f"plausibly be due to chance."
        )

    higher, lower = (group_a, group_b) if np.median(a) > np.median(b) else (group_b, group_a)
    effect_name = "Cohen's d" if effect_size_type == "cohens_d" else "rank-biserial correlation"
    practicality = "substantial" if magnitude in ("medium", "large") else "modest"

    # Direction is already stated in words ("higher than"); showing the signed
    # effect size alongside that would read as contradictory whenever group_b
    # is the higher one (a negative number next to a "higher" claim), so the
    # plain-language sentence reports magnitude only. The signed value is
    # still available in the returned dict's "effect_size" field.
    # The CI was computed as group_a minus group_b; re-orient it to
    # "higher minus lower" so it's a positive range consistent with the
    # sentence's wording, rather than flipping sign depending on argument order.
    higher_ci = (ci_low, ci_high) if higher == group_a else (-ci_high, -ci_low)

    return (
        f"'{higher}' listings have significantly higher {value_col} than '{lower}' ({test_used}, {p_str}), "
        f"with a {magnitude} effect size ({effect_name}={abs(effect_size):.2f}), meaning this is both a "
        f"statistically real and practically {practicality} difference. Bootstrap 95% CI for the "
        f"difference in medians ({higher} minus {lower}): [{higher_ci[0]:.2f}, {higher_ci[1]:.2f}]."
    )


def run_two_group_test(df: pd.DataFrame, group_col: str, value_col: str, group_a, group_b) -> dict:
    a = df.loc[df[group_col] == group_a, value_col].dropna().to_numpy(dtype=float)
    b = df.loc[df[group_col] == group_b, value_col].dropna().to_numpy(dtype=float)

    if len(a) < 3 or len(b) < 3:
        raise ValueError(
            f"Need at least 3 observations per group; got {len(a)} for {group_a!r} and {len(b)} for {group_b!r}"
        )

    normality_a = _check_normality(a)
    normality_b = _check_normality(b)
    both_normal = normality_a["is_normal"] and normality_b["is_normal"]

    levene_stat, levene_p = stats.levene(a, b)
    equal_variance = bool(levene_p > ALPHA)

    if both_normal:
        test_used = "Student's t-test" if equal_variance else "Welch's t-test"
        test_statistic, p_value = stats.ttest_ind(a, b, equal_var=equal_variance)
        effect_size = _cohens_d(a, b)
        effect_size_type = "cohens_d"
        thresholds = COHENS_D_THRESHOLDS
    else:
        test_used = "Mann-Whitney U"
        test_statistic, p_value = stats.mannwhitneyu(a, b, alternative="two-sided")
        effect_size = _rank_biserial(test_statistic, len(a), len(b))
        effect_size_type = "rank_biserial_correlation"
        thresholds = RANK_BISERIAL_THRESHOLDS

    significant = bool(p_value < ALPHA)
    magnitude = _effect_size_label(abs(effect_size), thresholds)
    ci_low, ci_high = _bootstrap_median_diff_ci(a, b)

    summary = _two_group_summary(
        value_col, group_a, group_b, a, b, test_used, p_value, effect_size, effect_size_type,
        magnitude, significant, ci_low, ci_high,
    )

    return {
        "test_used": test_used,
        "test_statistic": round(float(test_statistic), 4),
        "p_value": float(p_value),
        "significant": significant,
        "effect_size_type": effect_size_type,
        "effect_size": round(effect_size, 4),
        "effect_size_magnitude": magnitude,
        "median_diff_95ci": (round(ci_low, 4), round(ci_high, 4)),
        "group_a": {"name": group_a, "n": len(a), "mean": round(float(np.mean(a)), 4), "median": round(float(np.median(a)), 4)},
        "group_b": {"name": group_b, "n": len(b), "mean": round(float(np.mean(b)), 4), "median": round(float(np.median(b)), 4)},
        "normality": {str(group_a): normality_a, str(group_b): normality_b},
        "levene_test": {
            "statistic": round(float(levene_stat), 4), "p_value": round(float(levene_p), 4), "equal_variance": equal_variance,
        },
        "summary": summary,
    }


def _format_tukey_pair(row: dict) -> str:
    return f"{row['group1']} vs {row['group2']} (mean diff={row['meandiff']:.2f}, p-adj={row['p-adj']:.3f})"


def _anova_summary(
    group_col: str, value_col: str, means: dict, p_value: float, eta_squared: float, magnitude: str,
    significant: bool, significant_tukey_rows: list,
) -> str:
    p_str = "p<0.001" if p_value < 0.001 else f"p={p_value:.3f}"

    if not significant:
        return f"No statistically significant difference in {value_col} was found across {group_col} groups ({p_str})."

    highest = max(means, key=means.get)
    lowest = min(means, key=means.get)

    summary = (
        f"{value_col} differs significantly across {group_col} groups (one-way ANOVA, {p_str}), with a "
        f"{magnitude} effect size (eta-squared={eta_squared:.3f}). '{highest}' has the highest average "
        f"{value_col} ({means[highest]:.2f}) and '{lowest}' has the lowest ({means[lowest]:.2f})."
    )

    n_groups = len(means)
    if not significant_tukey_rows:
        summary += " However, no individual pair reached significance in the Tukey HSD post-hoc test."
    elif n_groups > TUKEY_SUMMARY_GROUP_THRESHOLD:
        # Naming every significant pair stops being "plain language" once
        # there are many groups (e.g. 111 neighbourhoods can produce ~90
        # significant pairs) -- report the count and the single most extreme
        # pair, and point to the structured table for the rest.
        most_extreme = max(significant_tukey_rows, key=lambda row: abs(row["meandiff"]))
        summary += (
            f" Tukey HSD post-hoc found {len(significant_tukey_rows)} significant pairwise differences "
            f"across {n_groups} groups; the most extreme is {_format_tukey_pair(most_extreme)}. See the "
            "returned 'tukey_hsd' table for the full pairwise comparison."
        )
    else:
        lines = [_format_tukey_pair(row) for row in significant_tukey_rows]
        summary += " Tukey HSD post-hoc found significant pairwise differences: " + "; ".join(lines) + "."
    return summary


def run_anova(df: pd.DataFrame, group_col: str, value_col: str) -> dict:
    groups = {
        str(label): sub[value_col].dropna().to_numpy(dtype=float)
        for label, sub in df.groupby(group_col)
        if sub[value_col].dropna().shape[0] >= 2
    }
    if len(groups) < 2:
        raise ValueError(f"Need at least 2 groups with data in {group_col!r} to run ANOVA")

    labels = list(groups.keys())
    samples = list(groups.values())

    f_statistic, p_value = stats.f_oneway(*samples)
    levene_stat, levene_p = stats.levene(*samples)
    equal_variance = bool(levene_p > ALPHA)

    all_values = np.concatenate(samples)
    grand_mean = all_values.mean()
    ss_between = sum(len(s) * (s.mean() - grand_mean) ** 2 for s in samples)
    ss_total = float(((all_values - grand_mean) ** 2).sum())
    eta_squared = float(ss_between / ss_total) if ss_total > 0 else 0.0

    significant = bool(p_value < ALPHA)
    magnitude = _effect_size_label(eta_squared, ETA_SQUARED_THRESHOLDS)
    means = {label: float(s.mean()) for label, s in zip(labels, samples)}

    tukey_records = None
    significant_tukey_rows = []
    if significant:
        group_labels = np.concatenate([[label] * len(s) for label, s in zip(labels, samples)])
        tukey = pairwise_tukeyhsd(all_values, group_labels, alpha=ALPHA)
        table = tukey.summary().data
        tukey_records = [dict(zip(table[0], row)) for row in table[1:]]
        significant_tukey_rows = [row for row in tukey_records if row["reject"]]

    summary = _anova_summary(group_col, value_col, means, p_value, eta_squared, magnitude, significant, significant_tukey_rows)

    return {
        "test_used": "One-way ANOVA",
        "f_statistic": round(float(f_statistic), 4),
        "p_value": float(p_value),
        "significant": significant,
        "effect_size_type": "eta_squared",
        "eta_squared": round(eta_squared, 4),
        "effect_size_magnitude": magnitude,
        "levene_test": {
            "statistic": round(float(levene_stat), 4), "p_value": round(float(levene_p), 4), "equal_variance": equal_variance,
        },
        "group_summary": {
            label: {"n": len(s), "mean": round(float(s.mean()), 4), "median": round(float(np.median(s)), 4)}
            for label, s in zip(labels, samples)
        },
        "tukey_hsd": tukey_records,
        "summary": summary,
    }
