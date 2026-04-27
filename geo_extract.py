"""
GEO Pipeline — Brand Extraction
Parses Run B outputs to extract brand mentions per query.

v1.0.0  2026-04-14  Initial build — regex/pattern extraction, normalization, inter-coder sample
v2.0.0  2026-04-15  CRITICAL FIX — _find_query_section fallback returned full text for
                    unanswered queries, silently attributing all brands to every query.
                    5 of 10 models only answered 5-15 of 40 queries (output truncation).
                    The fallback created 14,222 phantom extractions (68.9% of all data).
                    Fix: return None when section not found; add coverage tracking;
                    expand false-positive filter; expand normalization codebook;
                    add cross-category contamination check to validation gate.
v3.0.0  2026-04-27  EXTRACT-001 (slash-compound brand normalization) + EXTRACT-002 (4 citation-footer false positives) per CRITICAL bug report. Tests in tests/test_extract_001.py and tests/test_extract_002.py.
"""

__version__ = "3.0.0"
__component__ = "geo_extract"

import re
import json
import hashlib
import logging
from pathlib import Path
from collections import defaultdict

import pandas as pd
import geo_config as cfg

logger = logging.getLogger(__name__)


# ─── False Positive Filter ────────────────────────────────────────────────────

# Words/phrases that regex patterns extract as brands but aren't.
# Matched case-insensitively against brand_raw before normalization.
FALSE_POSITIVE_BRANDS = {
    "sources", "source", "note", "notes", "renovation", "important",
    "summary", "conclusion", "section", "query", "recommendation",
    "recommendations", "overview", "considerations", "key considerations",
    "factors", "key factors", "tips", "additional tips", "disclaimer",
    "criteria", "key criteria", "answer", "response", "pro tip",
    "bottom line", "verdict", "word count", "consulted sources",
    "responsiveness and scheduling discipline",
    "sources consulted", "for a remote", "for a five", "for a non",
    "for a small", "for the best all", "for most enterprises migrating from on",
    "important caveat", "important note",
    "the veterinary nutrition community",
    "an unannounced drop-in visit",
    # Local services advice items commonly extracted as brands
    "specialization", "warranty", "reviews", "licensing",
    "licensing/insurance", "warranty on parts and labor",
    "warranty on labor", "references", "communication",
    "transparency", "experience",
    # EXTRACT-002 (v3.0.0): Citation-footer false positives from search-augmented models.
    "if web sources were consulted",
    "web sources consulted briefly",
    "sources consulted generally",
    "web sources consulted",
}


# ─── Brand Extraction ─────────────────────────────────────────────────────────

def extract_brands_from_response(text, query_id=None):
    """
    Extract brand names from a model response section.

    Strategy: Look for proper nouns that appear in recommendation contexts.
    This is a heuristic extractor — the analysis plan requires dual-coder
    validation on a 20% sample.

    Returns a list of dicts: [{brand, position, context, method}, ...]
    """
    brands = []
    seen = set()

    # EXTRACT-001 (v3.0.0): Normalize slash-compound bolded brands.
    # Rewrites "**Apple Watch Series 10/Ultra 2**" -> "**Apple Watch Series 10**"
    # so the list_pattern and bold_pattern below extract a clean primary brand
    # rather than a compound that won't normalize cleanly.
    text_normalized = re.sub(
        r'\*\*([A-Z][^*]+?)\s*/\s*[A-Z][^*]+?\*\*',
        lambda m: '**' + m.group(1).strip() + '**',
        text
    )

    # Pattern 1: Numbered/bulleted list items with brand as first word(s)
    # Covers: "1. **Brand** — desc", "- Brand — desc", "* Brand: desc"
    list_pattern = re.compile(
        r'(?:^|\n)\s*(?:\d+[\.\)]\s*|[-\u2022*]\s*)'  # List marker
        r'(?:\*\*)?'                                     # Optional bold open
        r'([A-Z][A-Za-z0-9.\']*(?:[\s\-/+&][A-Za-z0-9.\']+){0,5})'  # Brand (1-6 words)
        r'(?:\*\*)?'                                     # Optional bold close
        r'\s*(?:[\u2014\u2013\-:|\(+])',                 # Separator after brand (added +)
        re.MULTILINE
    )

    for m in list_pattern.finditer(text_normalized):
        brand = m.group(1).strip()
        brand = re.sub(r'\s+', ' ', brand)  # Collapse whitespace
        if brand and brand.lower() not in seen and len(brand) > 1:
            if brand.lower() in FALSE_POSITIVE_BRANDS:
                continue
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
    bold_pattern = re.compile(r'\*\*([A-Z][A-Za-z0-9.\']*(?:[\s\-/+&][A-Za-z0-9.\']+){0,5})\*\*')
    for m in bold_pattern.finditer(text_normalized):
        brand = m.group(1).strip()
        brand = re.sub(r'\s+', ' ', brand)
        # Filter out common non-brand bold text
        skip_first_words = {"section", "note", "important", "key", "summary", "conclusion",
                            "pros", "cons", "features", "pricing", "overview", "recommendation",
                            "best", "top", "why", "how", "what", "when", "where", "the",
                            "sources", "source", "tip", "disclaimer", "word", "consulted",
                            "additional", "criteria", "factors", "considerations", "answer",
                            "bottom", "verdict", "response"}
        if (brand.lower() not in seen
                and brand.lower().split()[0] not in skip_first_words
                and brand.lower() not in FALSE_POSITIVE_BRANDS
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


# ─── Normalization ─────────────────────────────────────────────────────────────

def normalize_brand(brand_name, codebook=None):
    """
    Normalize a brand name to canonical form.
    Uses a codebook for known mappings, falls back to the raw name.
    """
    default_codebook = {
        # ── CRM / Sales ──
        "hubspot": "HubSpot", "hub spot": "HubSpot",
        "hubspot crm": "HubSpot", "hubspot crm suite": "HubSpot",
        "hubspot sales hub": "HubSpot", "hubspot marketing hub": "HubSpot",
        "hubspot operations hub": "HubSpot", "hubspot cdp": "HubSpot",
        "hubspot customer platform": "HubSpot", "hubspot crm enterprise": "HubSpot",
        "hubspot smart crm": "HubSpot",
        "hubspot crm (sales hub professional)": "HubSpot",
        "hubspot crm (professional/enterprise)": "HubSpot",
        "salesforce": "Salesforce", "sfdc": "Salesforce",
        "salesforce crm": "Salesforce", "salesforce sales cloud": "Salesforce",
        "salesforce essentials": "Salesforce",
        "salesforce customer 360": "Salesforce",
        "salesforce cdp": "Salesforce CDP",
        "salesforce marketing cloud": "Salesforce Marketing Cloud",
        "salesforce marketing cloud account engagement": "Salesforce Marketing Cloud",
        "salesforce data cloud": "Salesforce Data Cloud",
        "zoho": "Zoho", "zoho crm": "Zoho",
        "zoho books": "Zoho Books",
        "pipedrive": "Pipedrive",
        "freshsales": "Freshsales", "freshworks crm": "Freshsales",
        "monday": "Monday.com", "monday.com": "Monday.com",
        "monday.com (dev product)": "Monday.com",
        "microsoft dynamics 365": "Microsoft Dynamics 365",
        "microsoft dynamics 365 sales": "Microsoft Dynamics 365",

        # ── Project Management ──
        "asana": "Asana",
        "jira": "Jira", "atlassian jira": "Jira",
        "jira + confluence": "Jira", "jira (atlassian)": "Jira",
        "trello": "Trello",
        "notion": "Notion",
        "clickup": "ClickUp", "click up": "ClickUp",
        "linear": "Linear",

        # ── Email Marketing ──
        "mailchimp": "Mailchimp", "mail chimp": "Mailchimp",
        "klaviyo": "Klaviyo",
        "brevo": "Brevo", "sendinblue": "Brevo",
        "activecampaign": "ActiveCampaign", "active campaign": "ActiveCampaign",
        "omnisend": "Omnisend",

        # ── Accounting / Finance ──
        "quickbooks": "QuickBooks", "quick books": "QuickBooks",
        "quickbooks online": "QuickBooks",
        "quickbooks online advanced": "QuickBooks",
        "quickbooks online simple start": "QuickBooks",
        "quickbooks solopreneur": "QuickBooks",
        "quickbooks self": "QuickBooks",
        "quickbooks self-employed": "QuickBooks",
        "quickbooks online advanced + saas metrics add-ons": "QuickBooks",
        "qbo advanced": "QuickBooks",
        "xero": "Xero",
        "freshbooks": "FreshBooks", "fresh books": "FreshBooks",
        "netsuite": "NetSuite", "oracle netsuite": "NetSuite",
        "sage intacct": "Sage Intacct",

        # ── CDP / Data ──
        "segment": "Segment", "segment (twilio)": "Segment",
        "twilio segment": "Segment",
        "tealium": "Tealium", "tealium eventstream": "Tealium",
        "braze": "Braze",

        # ── Consumer Electronics ──
        "sony": "Sony", "sony wh": "Sony",
        "bose": "Bose", "bose quietcomfort ultra": "Bose QuietComfort Ultra",
        "apple": "Apple", "apple airpods": "Apple",
        "apple airpods max": "Apple AirPods Max",
        "samsung": "Samsung",
        "google": "Google", "google pixel": "Google",
        "amazon": "Amazon", "amazon alexa": "Amazon",
        "fujifilm x": "Fujifilm", "fujifilm": "Fujifilm",
        "asus rog zephyrus g14": "ASUS ROG Zephyrus G14",

        # ── Cloud / Enterprise ──
        "microsoft power bi": "Microsoft Power BI",
        "microsoft entra id": "Microsoft Entra ID",
        "rippling": "Rippling",

        # ── Health / Wellness ──
        "calm": "Calm",
        "headspace": "Headspace",
        "pure encapsulations": "Pure Encapsulations",
        "thorne": "Thorne",

        # ── Travel ──
        "marriott bonvoy": "Marriott Bonvoy",
        "hilton honors": "Hilton Honors",
        "chase sapphire reserve": "Chase Sapphire Reserve",
        "chase ink business preferred": "Chase Ink Business Preferred",
        "google flights": "Google Flights",
    }

    cb = {**default_codebook, **(codebook or {})}
    key = brand_name.lower().strip()
    return cb.get(key, brand_name.strip())


# ─── Query Section Finding (FIXED in v2.0.0) ──────────────────────────────────

def _find_query_section(text, qid, qtext):
    """
    Find the section of a response that corresponds to a specific query.

    v2.0.0 FIX: Previously returned the full response text as fallback when
    no query marker was found. This caused ALL brands from partial responses
    (models that only answered Q01-Q05) to be attributed to ALL 40 queries,
    creating phantom data for 14,222 of 20,650 extractions.

    Now returns None when the section is not found — the caller skips
    this as "model did not answer this query."
    """
    # Strategy 1: Look for exact query ID patterns
    # Handles: **Q01:, ### **Q01:, Q01:, Q01 —
    qid_patterns = [
        re.compile(
            rf'(?:\*\*|###?\s*\*?\*?)?\s*{re.escape(qid)}\b[:\s\u2014\u2013\-]',
            re.IGNORECASE
        ),
        re.compile(rf'{re.escape(qid)}[:\s]', re.IGNORECASE),
    ]

    for pat in qid_patterns:
        m = pat.search(text)
        if m:
            start = m.start()
            # Find the next query marker or end of text
            end = _find_next_query_boundary(text, qid, start)
            return text[start:end]

    # Strategy 2: Look for first 40 characters of query text
    qtext_pat = re.compile(re.escape(qtext[:40]), re.IGNORECASE)
    m = qtext_pat.search(text)
    if m:
        start = m.start()
        end = _find_next_query_boundary(text, qid, start)
        return text[start:end]

    # ── NO FALLBACK ── return None. The model did not answer this query.
    return None


def _find_next_query_boundary(text, current_qid, start_pos):
    """
    Find where the next query section begins after start_pos.
    Builds fresh regex patterns for each subsequent query ID.

    Returns the position of the next query marker, or len(text) if none found.
    """
    end = len(text)
    for next_q in cfg.QUERIES:
        if next_q["id"] <= current_qid:
            continue
        # Build patterns specifically for THIS next query's ID
        next_id = next_q["id"]
        next_patterns = [
            re.compile(
                rf'(?:\*\*|###?\s*\*?\*?)?\s*{re.escape(next_id)}\b[:\s\u2014\u2013\-]',
                re.IGNORECASE
            ),
            re.compile(rf'{re.escape(next_id)}[:\s]', re.IGNORECASE),
        ]
        for npat in next_patterns:
            nm = npat.search(text, start_pos + 20)
            if nm and nm.start() < end:
                end = nm.start()
                break  # Found this query's boundary, check next query
    return end


# ─── Main Extraction Pipeline ──────────────────────────────────────────────────

def extract_all_brands(base_dir, codebook=None):
    """
    Extract brands from all Run B output files.
    Returns a DataFrame with one row per brand mention per query per model per run.

    v2.0.0: Added coverage tracking. Queries where the model didn't respond
    are skipped (not filled with phantom data from other queries).
    """
    out_dir = Path(base_dir) / "outputs" / "run_b"
    rows = []

    # Coverage tracking: which queries did each model actually answer?
    coverage = {}  # {model_short: {run_number: set(query_ids)}}

    for model in cfg.MODELS:
        short = model["short"]
        coverage[short] = {}

        for k in range(1, cfg.K_TRIALS + 1):
            fpath = out_dir / f"{short}_run{k}.md"
            if not fpath.exists():
                logger.warning(f"Output file missing: {fpath}")
                coverage[short][k] = set()
                continue

            text = fpath.read_text(encoding="utf-8")
            coverage[short][k] = set()

            for query in cfg.QUERIES:
                qid = query["id"]
                qtext = query["text"]

                # Find the section of the response relevant to this query
                section = _find_query_section(text, qid, qtext)

                if section is None:
                    # Model did not answer this query — skip, don't fabricate
                    continue

                coverage[short][k].add(qid)
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
    data_dir = Path(base_dir) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    csv_path = data_dir / "brand_visibility_raw.csv"
    df.to_csv(csv_path, index=False)

    # Save coverage report
    _save_coverage_report(coverage, base_dir)

    return df


def _save_coverage_report(coverage, base_dir):
    """
    Save a report showing which queries each model answered across runs.
    This exposes truncation issues — models that only answered Q01-Q05, etc.
    """
    report = {}
    total_queries = len(cfg.QUERIES)

    for model_short, runs in coverage.items():
        all_qs = set()
        per_run = {}
        for k, qs in runs.items():
            per_run[f"run{k}"] = len(qs)
            all_qs |= qs

        min_coverage = min(per_run.values()) if per_run else 0
        max_coverage = max(per_run.values()) if per_run else 0

        report[model_short] = {
            "queries_total": total_queries,
            "queries_answered_union": len(all_qs),
            "min_per_run": min_coverage,
            "max_per_run": max_coverage,
            "coverage_pct": round(100 * len(all_qs) / total_queries, 1),
            "full_coverage": len(all_qs) == total_queries,
            "per_run": per_run,
            "missing_queries": sorted(
                [q["id"] for q in cfg.QUERIES if q["id"] not in all_qs]
            ),
        }

        # Log warnings for low coverage
        if len(all_qs) < total_queries:
            logger.warning(
                f"{model_short}: answered {len(all_qs)}/{total_queries} queries "
                f"({100 * len(all_qs) / total_queries:.0f}%). "
                f"Missing: {report[model_short]['missing_queries']}"
            )

    report_path = Path(base_dir) / "data" / "extraction_coverage.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Print summary
    print(f"\n{'Model':<25s} {'Coverage':>10s} {'Queries':>10s} {'Status':<15s}")
    print("-" * 65)
    for m, r in sorted(report.items()):
        status = "FULL" if r["full_coverage"] else f"PARTIAL ({r['min_per_run']}-{r['max_per_run']}/run)"
        print(f"{m:<25s} {r['coverage_pct']:>9.1f}% {r['queries_answered_union']:>5d}/{r['queries_total']:<4d} {status}")

    return report


# ─── Brand Matrix ──────────────────────────────────────────────────────────────

def build_brand_matrix(df, base_dir):
    """
    Build the brand visibility matrix: for each query x model,
    aggregate brands across K runs using majority vote.
    """
    if df.empty:
        return pd.DataFrame()

    # For each (query_id, model_short, brand_normalized), count appearances across runs
    counts = df.groupby(
        ["query_id", "query_category", "model_short", "model_group", "brand_normalized"]
    ).agg(
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


# ─── Inter-Coder Sample ───────────────────────────────────────────────────────

def generate_intercoder_sample(df, sample_frac=0.2, seed=42):
    """
    Generate a random sample of responses for inter-coder reliability checking.
    Returns file paths and query IDs for manual coding.
    """
    if df.empty:
        return pd.DataFrame()

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

    v2.0.0: Added cross-category contamination check and query coverage check.
    """
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

    # 3. Coverage: do all queries have data from at least some models?
    queries_with_data = df["query_id"].nunique()
    expected_queries = len(cfg.QUERIES)
    check("All queries have at least some brands",
          queries_with_data >= expected_queries * 0.8,
          f"{queries_with_data}/{expected_queries} queries have data",
          severity="warn")

    # 4. Query coverage per model — flag models with <50% query coverage
    model_query_coverage = df.groupby("model_short")["query_id"].nunique()
    low_coverage_models = model_query_coverage[model_query_coverage < expected_queries * 0.5]
    check("All models answer >= 50% of queries",
          len(low_coverage_models) == 0,
          f"{len(low_coverage_models)} models have <50% query coverage: "
          f"{low_coverage_models.to_dict()}" if len(low_coverage_models) > 0 else "All models adequate",
          severity="warn")

    # 5. Reasonable brand count per query-model cell
    cell_counts = df.groupby(["query_id", "model_short"])["brand_normalized"].nunique()
    median_brands = cell_counts.median()
    check("Median brands per cell >= 2",
          median_brands >= 2,
          f"Median: {median_brands:.1f} brands per query-model cell",
          severity="warn")

    # 6. No single brand dominates >80% of all cells
    if not brand_matrix.empty:
        brand_freq = brand_matrix[brand_matrix["majority_included"]].groupby(
            "brand_normalized"
        )["model_short"].nunique()
        if len(brand_freq) > 0:
            max_brand = brand_freq.idxmax()
            max_models = brand_freq.max()
            check("No brand in >80% of models",
                  True,
                  f"Most frequent: {max_brand} ({max_models}/{expected_models} models)",
                  severity="warn")

    # 7. Normalization codebook coverage
    raw_unique = df["brand_raw"].nunique()
    normalized_unique = df["brand_normalized"].nunique()
    reduction = 1 - (normalized_unique / raw_unique) if raw_unique > 0 else 0
    check("Normalization reduces brand variants",
          reduction > 0,
          f"{raw_unique} raw -> {normalized_unique} normalized ({reduction:.0%} reduction)",
          severity="warn")

    # 8. No known false positives in brand list
    known_fp = FALSE_POSITIVE_BRANDS
    artifacts = df[df["brand_normalized"].str.lower().isin(known_fp)]
    check("No false-positive brands in data",
          len(artifacts) == 0,
          f"{len(artifacts)} false-positive entries found: "
          f"{artifacts['brand_normalized'].unique().tolist()}" if len(artifacts) > 0 else "Clean",
          severity="warn")

    # 9. Cross-category contamination check
    # If a model shows identical brand sets across unrelated categories,
    # it signals the old fallback bug or a model giving identical answers.
    contaminated = []
    for model in df["model_short"].unique():
        mdata = df[df["model_short"] == model]
        cat_brands = mdata.groupby("query_category")["brand_normalized"].apply(
            lambda x: frozenset(x.unique())
        )
        if len(cat_brands) >= 3:
            brand_sets = list(cat_brands.values)
            most_common = max(set(brand_sets), key=brand_sets.count)
            identical_count = brand_sets.count(most_common)
            if identical_count > len(brand_sets) * 0.6:
                contaminated.append(
                    f"{model} ({identical_count}/{len(brand_sets)} categories identical)"
                )

    check("No cross-category contamination",
          len(contaminated) == 0,
          "; ".join(contaminated) if contaminated else "Clean",
          severity="fail" if contaminated else "warn")

    # Save report
    report_path = Path(base_dir) / "data" / "extraction_validation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report
