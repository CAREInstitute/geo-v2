"""
GEO Pipeline — Statistical Analysis
Implements the pre-registered analysis plan: Fleiss' κ, Jaccard, Kendall's W.

v1.0.0  2026-04-14  Initial build — H1-H4 tests, category subgroup, brand frequency
v2.0.0  2026-04-27  Paraphrase robustness + temperature sensitivity analyses (features land in Stage 3.7).
"""

__version__ = "2.0.0"
__component__ = "geo_analyze"

import json
import numpy as np
import pandas as pd
from itertools import combinations
from pathlib import Path
from scipy import stats

import geo_config as cfg


# ─── Jaccard Similarity ──────────────────────────────────────────────────────

def jaccard_similarity(set_a, set_b):
    """Compute Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0  # Both empty = perfect agreement on "nothing"
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def compute_pairwise_jaccard(brand_matrix, query_id):
    """
    Compute pairwise Jaccard similarity between all model pairs for a given query.
    Uses majority-included brands.
    """
    qdata = brand_matrix[
        (brand_matrix["query_id"] == query_id) & (brand_matrix["majority_included"])
    ]

    model_brands = {}
    for model in cfg.MODELS:
        short = model["short"]
        mdata = qdata[qdata["model_short"] == short]
        model_brands[short] = set(mdata["brand_normalized"].tolist())

    models = list(model_brands.keys())
    n = len(models)
    matrix = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            matrix[i][j] = jaccard_similarity(model_brands[models[i]], model_brands[models[j]])

    return pd.DataFrame(matrix, index=models, columns=models), model_brands


# ─── Fleiss' Kappa ────────────────────────────────────────────────────────────

def fleiss_kappa(ratings_matrix):
    """
    Compute Fleiss' kappa for multi-rater agreement.

    ratings_matrix: np.array of shape (n_subjects, n_categories)
                    Each row is a subject (brand), each cell is the count of
                    raters (models) assigning that category.
    """
    n_subjects, n_categories = ratings_matrix.shape
    n_raters = ratings_matrix[0].sum()  # Assumes all subjects rated by same # raters

    if n_raters <= 1 or n_subjects == 0:
        return 0.0

    # Proportion of rater pairs in agreement per subject
    P_i = np.zeros(n_subjects)
    for i in range(n_subjects):
        P_i[i] = (np.sum(ratings_matrix[i] ** 2) - n_raters) / (n_raters * (n_raters - 1))

    P_bar = np.mean(P_i)

    # Expected agreement by chance
    p_j = np.sum(ratings_matrix, axis=0) / (n_subjects * n_raters)
    P_e = np.sum(p_j ** 2)

    if P_e == 1.0:
        return 1.0  # Perfect agreement expected by chance = degenerate

    kappa = (P_bar - P_e) / (1.0 - P_e)
    return kappa


def compute_fleiss_kappa_per_query(brand_matrix, query_id):
    """
    Compute Fleiss' kappa for cross-model agreement on brand inclusion.

    Treats models as raters and brand inclusion (yes/no) as the rated variable.
    """
    qdata = brand_matrix[brand_matrix["query_id"] == query_id]

    # Get all brands mentioned by any model for this query
    all_brands = sorted(qdata[qdata["majority_included"]]["brand_normalized"].unique())

    if len(all_brands) < 2:
        return 0.0, len(all_brands)

    model_shorts = [m["short"] for m in cfg.MODELS]
    n_raters = len(model_shorts)

    # Build ratings matrix: rows = brands, cols = [included, not_included]
    ratings = np.zeros((len(all_brands), 2), dtype=int)

    for i, brand in enumerate(all_brands):
        included_count = 0
        for ms in model_shorts:
            mdata = qdata[(qdata["model_short"] == ms) & (qdata["brand_normalized"] == brand)]
            if not mdata.empty and mdata.iloc[0]["majority_included"]:
                included_count += 1
        ratings[i, 0] = included_count       # "yes" votes
        ratings[i, 1] = n_raters - included_count  # "no" votes

    kappa = fleiss_kappa(ratings)
    return kappa, len(all_brands)


# ─── Kendall's W ──────────────────────────────────────────────────────────────

def compute_kendalls_w(brand_matrix, query_id):
    """
    Compute Kendall's W (coefficient of concordance) for rank agreement.

    Only applicable when models produce ordered recommendation lists.
    Uses average position as the rank variable.
    """
    qdata = brand_matrix[
        (brand_matrix["query_id"] == query_id) & (brand_matrix["majority_included"])
    ]

    if qdata.empty:
        return 0.0, 0

    model_shorts = [m["short"] for m in cfg.MODELS]
    all_brands = sorted(qdata["brand_normalized"].unique())

    if len(all_brands) < 2:
        return 0.0, len(all_brands)

    # Build rank matrix: rows = brands, cols = models
    # Rank = average position (lower = higher recommendation)
    rank_data = []
    for brand in all_brands:
        row = []
        for ms in model_shorts:
            mdata = qdata[(qdata["model_short"] == ms) & (qdata["brand_normalized"] == brand)]
            if not mdata.empty:
                row.append(mdata.iloc[0]["avg_position"])
            else:
                row.append(len(all_brands) + 1)  # Not mentioned = worst rank
        rank_data.append(row)

    rank_array = np.array(rank_data).T  # shape: (n_models, n_brands)

    if rank_array.shape[1] < 2:
        return 0.0, rank_array.shape[1]

    # Scipy's Kendall's W via Friedman chi-square approximation
    try:
        k = rank_array.shape[0]  # raters (models)
        n = rank_array.shape[1]  # objects (brands)

        # Rank within each rater
        ranked = np.zeros_like(rank_array, dtype=float)
        for i in range(k):
            ranked[i] = stats.rankdata(rank_array[i])

        # Sum of ranks per brand
        R = ranked.sum(axis=0)
        R_bar = R.mean()

        S = np.sum((R - R_bar) ** 2)
        W = (12 * S) / (k ** 2 * (n ** 3 - n))

        return min(max(W, 0.0), 1.0), n
    except Exception:
        return 0.0, 0


# ─── Intra- vs Inter-Model Consistency (H4) ──────────────────────────────────

def compute_intra_inter_consistency(raw_df):
    """
    Compare intra-model consistency (across K runs) vs. inter-model consistency.

    Returns per-query intra and inter Jaccard means.
    """
    results = []

    for query in cfg.QUERIES:
        qid = query["id"]
        qdata = raw_df[raw_df["query_id"] == qid]

        if qdata.empty:
            continue

        # Intra-model: Jaccard across K runs within each model
        intra_jaccards = []
        for model in cfg.MODELS:
            short = model["short"]
            mdata = qdata[qdata["model_short"] == short]

            run_sets = {}
            for k in range(1, cfg.K_TRIALS + 1):
                rdata = mdata[mdata["run_number"] == k]
                run_sets[k] = set(rdata["brand_normalized"].tolist())

            # Pairwise Jaccard across runs for this model
            runs = list(run_sets.keys())
            for i, j in combinations(runs, 2):
                intra_jaccards.append(jaccard_similarity(run_sets[i], run_sets[j]))

        # Inter-model: Jaccard across models (using majority brands per model)
        inter_jaccards = []
        model_brand_sets = {}
        for model in cfg.MODELS:
            short = model["short"]
            mdata = qdata[qdata["model_short"] == short]
            # Majority: brands appearing in >50% of runs
            brand_counts = mdata.groupby("brand_normalized")["run_number"].nunique()
            majority_brands = set(brand_counts[brand_counts >= cfg.K_TRIALS / 2].index)
            model_brand_sets[short] = majority_brands

        shorts = list(model_brand_sets.keys())
        for i, j in combinations(shorts, 2):
            # i and j are string keys from combinations(shorts, 2), not indices
            inter_jaccards.append(jaccard_similarity(model_brand_sets[i], model_brand_sets[j]))

        results.append({
            "query_id": qid,
            "category": query["category"],
            "intra_jaccard_mean": np.mean(intra_jaccards) if intra_jaccards else 0,
            "intra_jaccard_std": np.std(intra_jaccards) if intra_jaccards else 0,
            "inter_jaccard_mean": np.mean(inter_jaccards) if inter_jaccards else 0,
            "inter_jaccard_std": np.std(inter_jaccards) if inter_jaccards else 0,
            "n_intra_pairs": len(intra_jaccards),
            "n_inter_pairs": len(inter_jaccards),
        })

    return pd.DataFrame(results)


# ─── H2: Retrieval Architecture Effect ────────────────────────────────────────

def compute_architecture_effect(brand_matrix):
    """
    Compare Jaccard overlap within search-augmented group vs.
    between search-augmented and parametric-only groups.
    """
    search_shorts = {m["short"] for m in cfg.get_search_augmented()}
    param_shorts = {m["short"] for m in cfg.get_parametric_only()}

    within_search = []
    between_groups = []

    for query in cfg.QUERIES:
        qid = query["id"]
        _, model_brands = compute_pairwise_jaccard(brand_matrix, qid)

        # Within search-augmented
        for a, b in combinations(search_shorts, 2):
            if a in model_brands and b in model_brands:
                within_search.append(jaccard_similarity(model_brands[a], model_brands[b]))

        # Between search-augmented and parametric-only
        for s in search_shorts:
            for p in param_shorts:
                if s in model_brands and p in model_brands:
                    between_groups.append(jaccard_similarity(model_brands[s], model_brands[p]))

    # Effect size: Cohen's d
    if within_search and between_groups:
        mean_within = np.mean(within_search)
        mean_between = np.mean(between_groups)
        pooled_std = np.sqrt(
            ((len(within_search) - 1) * np.var(within_search) +
             (len(between_groups) - 1) * np.var(between_groups)) /
            (len(within_search) + len(between_groups) - 2)
        )
        cohens_d = (mean_within - mean_between) / pooled_std if pooled_std > 0 else 0

        # Mann-Whitney U test (non-parametric)
        u_stat, p_value = stats.mannwhitneyu(within_search, between_groups, alternative="greater")
    else:
        mean_within = mean_between = cohens_d = 0
        u_stat = p_value = None

    return {
        "within_search_mean": mean_within,
        "within_search_n": len(within_search),
        "between_groups_mean": mean_between if between_groups else 0,
        "between_groups_n": len(between_groups),
        "cohens_d": cohens_d,
        "mann_whitney_u": u_stat,
        "p_value": p_value,
    }


# ─── Full Analysis Pipeline ──────────────────────────────────────────────────

def run_full_analysis(base_dir):
    """Execute all pre-registered analyses and save results."""
    data_dir = Path(base_dir) / "data"
    results_dir = Path(base_dir) / "paper" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    raw_csv = data_dir / "brand_visibility_raw.csv"
    matrix_csv = data_dir / "brand_visibility_matrix.csv"

    if not raw_csv.exists() or not matrix_csv.exists():
        return {"error": "Run brand extraction first (geo_extract.py)"}

    raw_df = pd.read_csv(raw_csv)
    brand_matrix = pd.read_csv(matrix_csv)

    analysis_results = {}

    # ── H1: Fleiss' kappa per query ──
    kappa_results = []
    for query in cfg.QUERIES:
        k, n_brands = compute_fleiss_kappa_per_query(brand_matrix, query["id"])
        kappa_results.append({
            "query_id": query["id"],
            "category": query["category"],
            "fleiss_kappa": round(k, 4),
            "n_brands": n_brands,
        })
    kappa_df = pd.DataFrame(kappa_results)
    kappa_df.to_csv(results_dir / "h1_fleiss_kappa.csv", index=False)

    mean_kappa = kappa_df["fleiss_kappa"].mean()
    analysis_results["H1"] = {
        "mean_kappa": round(mean_kappa, 4),
        "std_kappa": round(kappa_df["fleiss_kappa"].std(), 4),
        "hypothesis_supported": mean_kappa < 0.6,
        "interpretation": "substantial_disagreement" if mean_kappa < 0.4 else
                          "moderate_disagreement" if mean_kappa < 0.6 else
                          "substantial_agreement",
        "per_query": kappa_results,
    }

    # ── H2: Architecture effect ──
    h2 = compute_architecture_effect(brand_matrix)
    analysis_results["H2"] = h2
    pd.DataFrame([h2]).to_csv(results_dir / "h2_architecture_effect.csv", index=False)

    # ── H4: Intra vs. Inter consistency ──
    h4_df = compute_intra_inter_consistency(raw_df)
    h4_df.to_csv(results_dir / "h4_intra_inter.csv", index=False)

    mean_intra = h4_df["intra_jaccard_mean"].mean()
    mean_inter = h4_df["inter_jaccard_mean"].mean()
    analysis_results["H4"] = {
        "mean_intra_jaccard": round(mean_intra, 4),
        "mean_inter_jaccard": round(mean_inter, 4),
        "hypothesis_supported": mean_intra > mean_inter,
        "difference": round(mean_intra - mean_inter, 4),
    }

    # ── Exploratory: Kendall's W per query ──
    kendall_results = []
    for query in cfg.QUERIES:
        w, n = compute_kendalls_w(brand_matrix, query["id"])
        kendall_results.append({
            "query_id": query["id"],
            "category": query["category"],
            "kendalls_w": round(w, 4),
            "n_brands": n,
        })
    kendall_df = pd.DataFrame(kendall_results)
    kendall_df.to_csv(results_dir / "exploratory_kendalls_w.csv", index=False)
    analysis_results["Kendalls_W"] = {
        "mean": round(kendall_df["kendalls_w"].mean(), 4),
        "per_query": kendall_results,
    }

    # ── Exploratory: Category-level kappa ──
    category_kappa = kappa_df.groupby("category")["fleiss_kappa"].agg(["mean", "std", "count"]).round(4)
    category_kappa.to_csv(results_dir / "exploratory_category_kappa.csv")
    analysis_results["Category_Kappa"] = category_kappa.to_dict(orient="index")

    # ── Exploratory: Brand frequency ──
    if not brand_matrix.empty:
        brand_freq = brand_matrix[brand_matrix["majority_included"]].groupby("brand_normalized").agg(
            n_models=("model_short", "nunique"),
            n_queries=("query_id", "nunique"),
            mean_position=("avg_position", "mean"),
        ).sort_values("n_models", ascending=False)
        brand_freq.to_csv(results_dir / "exploratory_brand_frequency.csv")
        analysis_results["Brand_Frequency"] = {
            "universal_brands": brand_freq[brand_freq["n_models"] >= 8].index.tolist(),
            "model_specific_brands": brand_freq[brand_freq["n_models"] <= 2].index.tolist(),
            "total_unique_brands": len(brand_freq),
        }

    # Save combined results
    with open(results_dir / "analysis_results.json", "w") as f:
        json.dump(analysis_results, f, indent=2, default=str)

    return analysis_results
