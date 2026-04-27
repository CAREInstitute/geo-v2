# CHANGELOG — GEO Cross-Model Brand Visibility Pipeline

## [3.0.0] - 2026-04-27

### Added
- `geo_extract.py` v3.0.0 — EXTRACT-001 patch: slash-compound brand normalization. Bolded brand phrases of the form `**A/B**` (e.g., `**Apple Watch Series 10/Ultra 2**`) are rewritten to `**A**` before list and bold pattern extraction. Addresses 7 confirmed-affected patterns from the v1 bug report (Apple Watch family, Garmin Vivosmart/Forerunner/Venu lines, Home Assistant ecosystem, Amazon Echo).
- `geo_extract.py` v3.0.0 — EXTRACT-002 patch: 4 new false-positive entries in `FALSE_POSITIVE_BRANDS` covering citation-footer artifacts emitted by search-augmented models (`if web sources were consulted`, `web sources consulted briefly`, `sources consulted generally`, `web sources consulted`).
- `tests/test_extract_001.py` — 7 unit-test cases covering all bug-report slash-compound patterns + a no-leak assertion.
- `tests/test_extract_002.py` — 3 unit-test cases (filter-presence, list-context, realistic-citation-footer pattern).

### Changed
- `geo_extract.py` __version__ 2.0.1 → 3.0.0.
- `geo_runner.py` __version__ 2.2.0 → 3.0.0 (v2 line marker; paraphrase + temperature awareness features land in Stage 3.2 / 3.5c).
- `geo_config.py` __version__ 4.1.0 → 5.0.0 (v2 design parameters; 12-model panel per OIL-23, ~7290 obs target).
- `geo_analyze.py` __version__ 1.0.0 → 2.0.0 (paraphrase robustness + temperature sensitivity analyses land in Stage 3.7).
- `geo_pipeline.py` __version__ 2.1.0 → 3.0.0 (v2 stage orchestration).

### Known limitations (v3.0.0)
- `list_pattern` regex's brand character class does not include `()`. Brands with parenthetical qualifiers (e.g., `Amazon Echo (4th Gen)`) extract as the bare brand (`Amazon Echo`) — the parenthetical truncation is downstream-recoverable via the normalization codebook (collapses to canonical `Amazon`). Documented per test_extract_001.py case 7. Future v4.0 work could widen the character class.

### Reference
- `CRITICAL geo_extraction_bug_report.md` (v1 bug report)
- Phase 3 build file: `GEO_v2_Campaign_Package/3_Claude_GEO_v2_Build.md`

---

All notable changes to pipeline components are documented here.
Format: `[component] version — date — description`

---

## 2026-04-15 (Truncation Fix)

### geo_runner 2.2.0 — Query Batching
- **Root cause:** 4 of 10 models (DeepSeek V3.2, Qwen 3.5+, Llama 4 Maverick,
  Gemini 3 Flash) self-stopped after 5-15 of 40 queries. All showed
  `finish_reason=stop` (not `length`), confirming voluntary early termination —
  not token limit exhaustion. Models cannot handle 40-query prompts in one shot.
- **Fix:** Added `build_batch_prompts()` — splits 40 queries into 5 batches of 8.
  Added `run_batched_trial()` — sends batches sequentially, concatenates results
  into one output file matching single-prompt format. Extractor works unchanged.
- **Resume logic:** Checks for ≥80% Q-markers in existing file before skipping.
  Full-coverage models (6/10) are preserved; truncated models (4/10 + GLM-5 run1)
  are re-run with batching.
- **API calls:** 50 (single-prompt) → 250 (5 batches × 5 trials × 10 models).
  Estimated cost increase: $3.49 → $10-15 (still well under $150 ceiling).

### geo_config 4.1.0
- Added `QUERY_BATCH_SIZE = 8`
- Updated `estimate_total_cost()` for batched API calls

### geo_extract 2.0.1
- Fixed `_save_coverage_report()` hardcoded `f"Q{i:02d}"` format string.
  Now uses `cfg.QUERIES`-driven ID list for forward compatibility.

---

## 2026-04-15 (Post-Run Review)

### geo_extract 2.0.0 — CRITICAL FIX
- **`_find_query_section()` fallback contamination:** The v1.0 function returned the
  full response text when no query marker was found. 5 of 10 models only answered
  5-15 of 40 queries (output truncation), causing the fallback to attribute ALL
  brands from answered queries to ALL 40 queries. This created 14,222 phantom
  extractions (68.9% of all v1.0 data). Every cross-model metric was corrupted.
- **Fix:** `_find_query_section()` now returns `None` when no section is found.
  The caller skips unanswered queries instead of fabricating data.
- **Fix:** `_find_next_query_boundary()` extracted as helper — builds fresh patterns
  for each subsequent query ID. v1.0 reused the current query's patterns for
  boundary detection, which also caused sections to extend to end-of-file.
- **Added:** `_save_coverage_report()` — produces `data/extraction_coverage.json`
  showing which queries each model answered per run. Exposes output truncation.
- **Added:** `FALSE_POSITIVE_BRANDS` set — filters "Sources", "Note", "Source",
  "Renovation", "Sources consulted", and 20+ other non-brand extractions.
- **Expanded:** Normalization codebook from 38 to 85+ entries. Consolidates
  HubSpot (9 variants → 1), QuickBooks (6 → 1), Microsoft Dynamics (2 → 1),
  Jira (3 → 1), Tealium (2 → 1), and others.
- **Added:** Validation gate check #4 (query coverage per model, warns at <50%)
- **Added:** Validation gate check #9 (cross-category contamination detection)
- **Result:** Extractions: 20,650 → 4,607. Contamination: 68.9% → 0%.
  False positives (Sources/Note/etc): 631 → 0.

---

## 2026-04-15

### geo_config 3.0.0
- **BREAKING:** 8 of 10 models replaced with current-generation equivalents
- GPT-4o → GPT-5.4, Gemini 2.5 Flash → Gemini 3.1 Pro, Grok 2 → Grok 4.20
- DeepSeek Chat → DeepSeek V3.2, Qwen3 235B → Qwen 3.5 Plus
- Removed Command R+ (no market share) and Gemma 3 27B (not frontier)
- Added GLM-5 (third Chinese-corpus model for H3 triangulation)
- Added Gemini 3 Flash (within-Google tier comparison for practitioners)
- Added per-model cost_input_per_m, cost_output_per_m, context_window, released fields
- Added estimate_total_cost() helper
- Added __version__ and __component__ front matter

### geo_runner 2.1.0
- Added generate_manifest() — single-file reproducibility manifest with all hashes
- Added hash_config() — SHA-256 of experimental design (models + queries + params)
- Added get_environment_fingerprint() — Python version, OS, package versions
- Added ExperimentLogger class — persistent append-only log file
- Added __version__ and __component__ front matter

### geo_pipeline 2.1.0
- Added `manifest` CLI command
- Added _get_version_info() — collects __version__ from all 5 modules
- Added _build_run_b_meta_prompt() — optional follow-up for attribution data
- Added component versions to experiment_metadata.json
- Added config_sha256 to experiment_metadata.json
- Added manifest step to `full` pipeline command
- Added __version__ and __component__ front matter
- **Revised Run B prompt (v2.0):**
  - Removed "You are participating in a research study" (ecologically invalid)
  - Changed "recommend 3-7 brands" → unconstrained ("brands you think best fit")
  - Added "Respond entirely in English" instruction
  - Added standardized output format spec for extraction consistency
  - Moved Sections B/C (attribution + self-analysis) to optional follow-up prompt
  - Added 200-400 word per query anchor

### geo_extract 1.0.0
- Added __version__ and __component__ front matter
- No functional changes

### geo_analyze 1.0.0
- Added __version__ and __component__ front matter
- No functional changes

## 2026-04-14

### geo_config 2.0.0
- Expanded from 10 to 20 queries across 4 AIO-trigger-rate categories
- Added K_TRIALS = 5 and SEARCH_SPACING_SECONDS = 3600
- Added model group classifications (search_augmented, parametric_only, non_english_corpus)

### geo_runner 2.0.0
- K=5 repeated trials with temporal spacing for search-augmented models
- Per-run metadata JSON with timestamps, token counts, model versions
- Prompt SHA-256 integrity checking
- Content SHA-256 per response
- Retry logic (3 attempts, exponential backoff on 429)

### geo_pipeline 2.0.0
- Full CLI orchestrator: preflight, run-b, run-a, extract, stochasticity, analyze, report, full
- --fast flag for skipping temporal spacing

### geo_extract 1.0.0
- Brand extraction via regex/pattern matching
- Normalization codebook
- Inter-coder reliability sample generation (20%)

### geo_analyze 1.0.0
- Fleiss' kappa (H1), pairwise Jaccard (H2), Kendall's W (exploratory)
- Intra- vs. inter-model consistency (H4)
- Architecture effect with Cohen's d and Mann-Whitney U (H2)
- Category-level subgroup analysis
- Brand frequency analysis

## 2026-04-14 (Initial)

### geo_config 1.0.0
- 10 models, 10 queries, single-run design (N=100)

### All components 1.0.0
- Initial pipeline build
