"""
GEO Pipeline — Brand Extraction
Parses Run B outputs to extract brand mentions per query.

v1.0.0  2026-04-14  Initial build — regex/pattern extraction, normalization, inter-coder sample
"""

__version__ = "1.0.0"
__component__ = "geo_extract"

import re
import json
import hashlib
from pathlib import Path
from collections import defaultdict

import pandas as pd
import geo_config as cfg


def extract_brands_from_response(text, query_id=None):
    """
    Extract brand names from a model response.

    Strategy: Look for proper nouns that appear in recommendation contexts.
    This is a heuristic extractor — the analysis plan requires dual-coder
    validation on a 20% sample.

    Returns a list of dicts: [{brand, position, context}, ...]
    """
    brands = []
    seen = set()

    # Common brand patterns in recommendation responses:
    # 1. Numbered lists: "1. BrandName — description"
    # 2. Bold headers: "**BrandName**"
    # 3. Inline mentions: "brands like BrandName, OtherBrand, and ThirdBrand"

    # Pattern 1: Numbered/bulleted list items with brand as first word(s)
    list_pattern = re.compile(
        r'(?:^|\n)\s*(?:\d+[\.\)]\s*|[-•*]\s*)'  # List marker
        r'(?:\*\*)?'                                # Optional bold
        r'([A-Z][A-Za-z0-9]*(?:\s+[A-Z][A-Za-z0-9]*){0,3})'  # Brand (1-4 capitalized words)
        r'(?:\*\*)?'                                # Optional bold close
        r'\s*(?:[—–\-:|\(])',                       # Separator after brand
        re.MULTILINE
    )

    for m in list_pattern.finditer(text):
        brand = m.group(1).strip()
        if brand and brand.lower() not in seen and len(brand) > 1:
            ctx_start = max(0, m.start() - 20)
            ctx_end = min(len(text), m.end() + 80)
            brands.append({
                "brand": brand,
                "position": len(brands) + 1,
                "context": text[ctx_start:ctx_end].replace("\n", " ").strip(),
                "method": "list_pattern",
            })
            seen.add(brand.lower())

    # Pattern 2: Bold brand names (common in markdown responses)
    bold_pattern = re.compile(r'\*\*([A-Z][A-Za-z0-9]*(?:\s+[A-Za-z0-9]*){0,3})\*\*')
    for m in bold_pattern.finditer(text):
        brand = m.group(1).strip()
        # Filter out common non-brand bold text
        skip_words = {"section", "note", "important", "key", "summary", "conclusion",
                      "pros", "cons", "features", "pricing", "overview", "recommendation",
                      "best", "top", "why", "how", "what", "when", "where", "the"}
        if (brand.lower() not in seen
            and brand.lower().split()[0] not in skip_words
            and len(brand) > 2):
            ctx_start = max(0, m.start() - 20)
            ctx_end = min(len(text), m.end() + 80)
            brands.append({
                "brand": brand,
                "position": len(brands) + 1,
                "context": text[ctx_start:ctx_end].replace("\n", " ").strip(),
                "method": "bold_pattern",
            })
            seen.add(brand.lower())

    return brands


def normalize_brand(brand_name, codebook=None):
    """
    Normalize a brand name to canonical form.
    Uses a codebook for known mappings, falls back to title case.
    """
    # Default codebook — extend as needed during extraction
    default_codebook = {
        "hubspot": "HubSpot", "hub spot": "HubSpot",
        "hubspot crm": "HubSpot",
        "salesforce": "Salesforce", "sfdc": "Salesforce",
        "salesforce crm": "Salesforce",
        "zoho": "Zoho", "zoho crm": "Zoho",
        "pipedrive": "Pipedrive",
        "freshsales": "Freshsales", "freshworks crm": "Freshsales",
        "monday": "Monday.com", "monday.com": "Monday.com",
        "asana": "Asana",
        "jira": "Jira", "atlassian jira": "Jira",
        "trello": "Trello",
        "notion": "Notion",
        "clickup": "ClickUp", "click up": "ClickUp",
        "mailchimp": "Mailchimp", "mail chimp": "Mailchimp",
        "klaviyo": "Klaviyo",
        "brevo": "Brevo", "sendinblue": "Brevo",
        "quickbooks": "QuickBooks", "quick books": "QuickBooks",
        "xero": "Xero",
        "freshbooks": "FreshBooks", "fresh books": "FreshBooks",
        "sony": "Sony", "sony wh": "Sony",
        "bose": "Bose",
        "apple": "Apple", "apple airpods": "Apple",
        "samsung": "Samsung",
        "google": "Google", "google pixel": "Google",
        "amazon": "Amazon", "amazon alexa": "Amazon",
    }

    cb = {**default_codebook, **(codebook or {})}
    key = brand_name.lower().strip()
    return cb.get(key, brand_name.strip())


def extract_all_brands(base_dir, codebook=None):
    """
    Extract brands from all Run B output files.
    Returns a DataFrame with one row per brand mention per query per model per run.
    """
    out_dir = Path(base_dir) / "outputs" / "run_b"
    rows = []

    for model in cfg.MODELS:
        short = model["short"]
        for k in range(1, cfg.K_TRIALS + 1):
            fpath = out_dir / f"{short}_run{k}.md"
            if not fpath.exists():
                continue

            text = fpath.read_text(encoding="utf-8")

            # Try to split by query — look for query markers
            # The prompt should produce responses with clear query separators
            # Attempt to find sections per query
            for query in cfg.QUERIES:
                qid = query["id"]
                qtext = query["text"]

                # Find the section of the response relevant to this query
                # Look for the query text or query ID in the response
                section = _find_query_section(text, qid, qtext)

                if section:
                    brands = extract_brands_from_response(section, qid)
                    for b in brands:
                        rows.append({
                            "query_id": qid,
                            "query_text": qtext,
                            "query_category": query["category"],
                            "model_id": model["id"],
                            "model_short": short,
                            "model_group": model["group"],
                            "run_number": k,
                            "brand_raw": b["brand"],
                            "brand_normalized": normalize_brand(b["brand"], codebook),
                            "position": b["position"],
                            "context": b["context"],
                            "extraction_method": b["method"],
                        })

    df = pd.DataFrame(rows)

    # Save raw extraction
    csv_path = Path(base_dir) / "data" / "brand_visibility_raw.csv"
    df.to_csv(csv_path, index=False)

    return df


def _find_query_section(text, qid, qtext):
    """Find the section of a response that corresponds to a specific query."""
    # Strategy: look for query ID markers, query text fragments, or numbered sections
    patterns = [
        re.compile(rf'{re.escape(qid)}[:\s]', re.IGNORECASE),
        re.compile(re.escape(qtext[:50]), re.IGNORECASE),
    ]

    for pat in patterns:
        m = pat.search(text)
        if m:
            start = m.start()
            # Find the next query marker or end of text
            end = len(text)
            for next_q in cfg.QUERIES:
                if next_q["id"] <= qid:
                    continue
                for npat in [re.compile(rf'{re.escape(next_q["id"])}[:\s]', re.IGNORECASE)]:
                    nm = npat.search(text, start + 50)
                    if nm and nm.start() < end:
                        end = nm.start()
            return text[start:end]

    # Fallback: return full text (single-query responses or unstructured output)
    return text


def build_brand_matrix(df, base_dir):
    """
    Build the brand visibility matrix: for each query × model,
    aggregate brands across K runs using majority vote.
    """
    if df.empty:
        return pd.DataFrame()

    # For each (query_id, model_short, brand_normalized), count appearances across runs
    counts = df.groupby(["query_id", "query_category", "model_short", "model_group", "brand_normalized"]).agg(
        appearances=("run_number", "nunique"),
        total_runs=("run_number", lambda x: cfg.K_TRIALS),
        avg_position=("position", "mean"),
    ).reset_index()

    # Majority rule: brand "included" if appears in >50% of K runs
    counts["majority_included"] = counts["appearances"] >= (cfg.K_TRIALS / 2)

    # Save
    csv_path = Path(base_dir) / "data" / "brand_visibility_matrix.csv"
    counts.to_csv(csv_path, index=False)

    return counts


def generate_intercoder_sample(df, sample_frac=0.2, seed=42):
    """
    Generate a random sample of responses for inter-coder reliability checking.
    Returns file paths and query IDs for manual coding.
    """
    if df.empty:
        return pd.DataFrame()

    # Get unique (model, run) combinations
    combos = df[["model_short", "run_number"]].drop_duplicates()
    sample = combos.sample(frac=sample_frac, random_state=seed)

    return sample


# ─── Data Validation Gate ─────────────────────────────────────────────────────

def validate_extraction(df, brand_matrix, base_dir):
    """
    Sanity-check extracted data before it reaches analysis.
    Returns a report dict with pass/warn/fail for each check.

    This is the gate between Layer 2 (extraction) and Layer 3 (analysis).
    If critical checks fail, analysis should not proceed.
    """
    from pathlib import Path
    import json

    report = {"checks": [], "pass": 0, "warn": 0, "fail": 0}

    def check(name, passed, detail="", severity="fail"):
        status = "pass" if passed else severity
        report["checks"].append({"name": name, "status": status, "detail": detail})
        report[status] += 1

    # 1. Do we have data at all?
    check("Extraction produced data",
          not df.empty,
          f"{len(df)} brand mentions extracted" if not df.empty else "NO DATA")

    if df.empty:
        # Save and return early — nothing else to check
        report_path = Path(base_dir) / "data" / "extraction_validation.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    # 2. Coverage: do all models have data?
    models_with_data = df["model_short"].nunique()
    expected_models = len(cfg.MODELS)
    check("All models have extracted brands",
          models_with_data == expected_models,
          f"{models_with_data}/{expected_models} models have data",
          severity="warn" if models_with_data >= expected_models * 0.7 else "fail")

    # 3. Coverage: do all queries have data?
    queries_with_data = df["query_id"].nunique()
    expected_queries = len(cfg.QUERIES)
    # Local services queries (Q16-Q20) may legitimately have no brands
    non_local = df[df["query_category"] != "local_services"]["query_id"].nunique()
    non_local_expected = len([q for q in cfg.QUERIES if q["category"] != "local_services"])
    check("Non-local queries have brands",
          non_local >= non_local_expected * 0.8,
          f"{non_local}/{non_local_expected} non-local queries have brands",
          severity="warn")

    # 4. Reasonable brand count per query-model cell
    cell_counts = df.groupby(["query_id", "model_short"])["brand_normalized"].nunique()
    median_brands = cell_counts.median()
    check("Median brands per cell ≥ 2",
          median_brands >= 2,
          f"Median: {median_brands:.1f} brands per query-model cell",
          severity="warn")

    # 5. No single brand dominates >80% of all cells
    if not brand_matrix.empty:
        total_cells = len(cfg.MODELS) * len(cfg.QUERIES)
        brand_freq = brand_matrix[brand_matrix["majority_included"]].groupby("brand_normalized")["model_short"].nunique()
        if len(brand_freq) > 0:
            max_brand = brand_freq.idxmax()
            max_models = brand_freq.max()
            check("No brand appears in >80% of models for all queries",
                  True,  # This is informational
                  f"Most frequent: {max_brand} ({max_models}/{expected_models} models)",
                  severity="warn")

    # 6. Normalization codebook coverage
    raw_unique = df["brand_raw"].nunique()
    normalized_unique = df["brand_normalized"].nunique()
    reduction = 1 - (normalized_unique / raw_unique) if raw_unique > 0 else 0
    check("Normalization reduces brand variants",
          reduction > 0,
          f"{raw_unique} raw → {normalized_unique} normalized ({reduction:.0%} reduction)",
          severity="warn")

    # 7. Check for suspiciously common extraction artifacts
    suspicious = ["section", "query", "note", "recommendation", "summary", "conclusion"]
    artifacts = df[df["brand_normalized"].str.lower().isin(suspicious)]
    check("No extraction artifacts in brand list",
          len(artifacts) == 0,
          f"{len(artifacts)} suspicious entries found" if len(artifacts) > 0 else "Clean",
          severity="warn")

    # Save report
    report_path = Path(base_dir) / "data" / "extraction_validation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report
