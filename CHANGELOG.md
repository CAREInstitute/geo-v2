# CHANGELOG — GEO Cross-Model Brand Visibility Pipeline

All notable changes to pipeline components are documented here.
Format: `[component] version — date — description`

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
