# Living Memo: Rapid Cross-Model AI Experiment Framework

**Classification:** Internal Reference — Living Document
**Version:** 1.0.0
**Date:** 2026-04-15
**Origin:** Engineering patterns validated during GEO Cross-Model Brand Visibility Study
**Companion document:** `ARCHITECTURE.md` (experimental design standards)

---

## What This Document Is

ARCHITECTURE.md tells you how to *design* a cross-model AI experiment. This document tells you how to *build the machine that runs it* — and how to do it in hours instead of weeks.

The GEO pipeline took approximately 8 hours of active development to go from "I want to compare brand recommendations across AI models" to a fully automated, reproducible, Cowork-operable experiment with pre-flight testing, budget guards, resume logic, statistical analysis, and a complete audit trail. The patterns documented here are what made that speed possible. They are not theoretical — every pattern was validated by building and debugging a working pipeline.

Update this document when a pattern proves wrong, when a new pattern emerges, or when a framework component is reused in a new experiment.

---

## 1. The Seven-Layer Architecture

Every cross-model experiment has the same seven layers. Build them in order. Do not skip layers.

```
Layer 6: Feedback Loop       Post-mortem → Framework updates → Next experiment
Layer 5: Operational Docs    RUNBOOK, COWORK_INSTRUCTIONS, OPERATOR_GUIDE
Layer 4: Quality & Audit     preflight_test, operator_logbook, manifest
Layer 3: Analysis            Statistical tests, report generation
Layer 2b: Data Validation    Sanity checks, coverage verification, artifact detection
Layer 2a: Data Processing    Extraction, normalization, codebook
Layer 1: Execution Engine    API calls, retry logic, metadata capture, resume, budget
Layer 0: Configuration       Models, queries/stimuli, parameters, hypotheses
```

**Build bottom-up** (Layer 0 → 6). Each layer depends only on layers below it. This means you can test each layer independently and swap implementations without breaking higher layers.

**Layer 2b (Data Validation) is a gate, not a processor.** It sits between extraction and analysis and verifies that extracted data is sane before statistical tests run on it. Checks include: all models have data, non-control queries have brands, median brands per cell ≥ 2, no extraction artifacts in the brand list, normalization codebook is reducing variants. If critical checks fail, analysis should not proceed.

**Layer 6 (Feedback Loop) closes the system.** Without it, each experiment is an isolated event. With it, operational lessons from Run N improve the framework for Run N+1. The operator logbook auto-generates framework feedback items — failure patterns, code modifications, quality flag trends, cost overruns — and prompts the operator to update `FRAMEWORK.md` Section 6 (Lessons Learned). The structured JSON logbook (`logs/logbook_*.json`) contains a `framework_feedback` array that can be programmatically aggregated across experiments.

**Lesson learned:** The GEO pipeline was initially built as Layers 0-1-3 (config, runner, analysis) without Layers 2b, 4, and 6. The validation gate was added after the Red Solo Pass identified that bad API responses could propagate silently into analysis. The feedback loop was added after recognizing that the logbook captured what happened but nothing converted that into framework improvements. Build all seven layers from the start.

### Layer 0: Configuration (`geo_config.py` pattern)

The configuration module is the single source of truth for the experiment. Everything flows from it.

**What it must contain:**
- Model roster with all metadata (IDs, groups, pricing, context windows)
- Stimulus set (queries, prompts, scenarios — whatever the experiment sends to models)
- Parameters (temperature, top_p, max_tokens, K trials, spacing)
- Group assignments (for hypothesis testing)
- Helper functions (get models by group, estimate cost)
- Version string

**Design principle:** The config is a Python module, not a YAML/JSON file. This allows helper functions, computed properties, and type safety. It also means the config can be imported by every other module without a parser.

**Forking for a new experiment:** Copy `geo_config.py`. Replace the MODELS list, QUERIES list, and group logic. Everything downstream (runner, extractor, analyzer) reads from the config — if the config is correct, the pipeline works.

### Layer 1: Execution Engine (`geo_runner.py` pattern)

The runner handles all API communication. It is the only module that makes network calls.

**Mandatory capabilities:**
- Single API call with retry logic (3 attempts, exponential backoff, rate-limit awareness)
- Per-call metadata capture (timestamps, token counts, model version returned, errors)
- Content hashing (SHA-256 of every response)
- Prompt hashing (SHA-256, checked against pre-registration)
- Resume logic (skip completed trials based on file existence + content threshold)
- Budget tracking (cumulative cost from actual token counts, ceiling enforcement)
- Output validation (quality flags for empty, short, refusal, error-as-content)
- Temporal spacing (configurable delay between trials for retrieval-dependent models)
- Parallel execution (ThreadPoolExecutor for independent trials)
- Manifest generation (single-file reproducibility record)
- Environment fingerprinting (Python version, OS, package versions)
- Config hashing (deterministic hash of the experimental design)

**What NOT to put in the runner:** Analysis logic, extraction logic, CLI logic, display logic. The runner returns raw data + metadata. Other layers interpret it.

### Layer 2a: Data Processing (`geo_extract.py` pattern)

Transforms raw API responses into structured data for analysis.

**This layer is experiment-specific.** The GEO pipeline extracts brand names. A different experiment might extract sentiment scores, citation URLs, factual claims, code snippets, or structured JSON. The extraction module must be rewritten for each experiment.

**Reusable patterns:**
- Normalization codebook (canonical forms for equivalent entities)
- Per-response extraction with provenance (which model, which run, which query)
- Inter-coder reliability sample generation (random 20% for manual validation)
- Majority-rule aggregation across K trials

### Layer 2b: Data Validation (`validate_extraction()` pattern)

**The gate between extraction and analysis.** This layer does not transform data — it checks that transformed data is sane before statistical tests run on it.

**Standard checks (reusable across experiments):**
- All models have extracted data (coverage check)
- Non-control stimuli produced results (domain check)
- Reasonable entity count per cell (density check)
- No extraction artifacts in the entity list (artifact detection)
- Normalization codebook is reducing variants (codebook efficacy)

**Output:** `data/extraction_validation.json` with pass/warn/fail per check. If any check is "fail," the pipeline should halt and the operator should review the extraction before proceeding to analysis.

**Forking for a new experiment:** The validation checks are experiment-specific (what counts as "reasonable" depends on what you're extracting), but the pattern (gate between L2a and L3, machine-readable report, halt-on-fail) is universal.

### Layer 3: Analysis (`geo_analyze.py` pattern)

Statistical analysis of the processed data. Contains only math — no I/O, no display, no API calls.

**Reusable statistical functions (copy directly to new experiments):**
- `fleiss_kappa()` — multi-rater agreement
- `jaccard_similarity()` — pairwise set overlap
- `compute_kendalls_w()` — rank concordance
- `compute_architecture_effect()` — between-group comparison with Cohen's d and Mann-Whitney U
- `compute_intra_inter_consistency()` — within-model vs. between-model agreement

**Experiment-specific analysis:** The hypothesis tests, subgroup analyses, and result formatting are specific to each experiment's pre-registered analysis plan. These must be rewritten, but the statistical primitives above are reusable.

### Layer 4: Quality & Audit

Three components that catch problems before they reach analysis:

**preflight_test.py:** Run before any experiment execution. Validates environment, packages, API key, model availability, config integrity, prompt determinism, file system, and optionally makes a single cheap API call. Produces a machine-readable report. The experiment does not start unless preflight passes.

**operator_logbook.py:** Records what happened during execution. Steps (start/pass/fail), code modifications (with before/after hashes), output file locations, errors, warnings, and auto-generated next actions. Produces both markdown (human review) and JSON (programmatic analysis). Detects unauthorized code modifications by hashing all `.py` files at start and comparing at close.

**manifest generation (in runner):** Single JSON file containing config hash, prompt hash, environment fingerprint, component versions, and per-output content hashes. A replicator who matches config + prompt hashes ran the same experiment. If their content hashes also match, they got identical outputs.

### Layer 5: Operational Docs

Three documents that enable both human and autonomous (Cowork) execution:

**RUNBOOK.md:** The prompt you hand to an autonomous agent. Contains: mission brief, file reading order, 8-step execution sequence, rules of engagement, success criteria. This is the entry point for Cowork.

**COWORK_INSTRUCTIONS.md:** Permission boundaries (GREEN/YELLOW/RED) and failure recovery decision trees. Tells the agent what it can fix autonomously, what requires logging, and what it must never do.

**OPERATOR_GUIDE.md:** Step-by-step instructions for human execution. Covers setup, pre-registration, execution, monitoring, and post-execution review. Also serves as Cowork's detailed reference for each step.

### Layer 6: Feedback Loop (`operator_logbook.py` post-mortem pattern)

The logbook's `close()` method auto-generates a "Post-Mortem: Framework Feedback" section by analyzing the run's events:

- **Failure patterns** → Should a new decision tree entry be added to `COWORK_INSTRUCTIONS.md`?
- **Code modifications** → Were these workarounds for framework gaps? Should the fix be integrated into the base pipeline?
- **Unlogged code changes** → Do permission boundaries need tightening?
- **Warning patterns** → Should any warnings become preflight checks?
- **Quality flag trends** → Do extraction patterns need updating?
- **Cost overruns/underruns** → Does the cost estimation formula need revised assumptions?
- **Resume events** → Were there crashes? What caused them?

The structured JSON logbook (`logs/logbook_*.json`) includes a `framework_feedback` array that can be aggregated across experiments programmatically. After each run, the operator reviews these items and updates `FRAMEWORK.md` Section 6 (Lessons Learned).

**The feedback loop is what makes this a framework instead of a one-off pipeline.** Without it, you build the same workarounds repeatedly. With it, each experiment improves the next.

---

## 2. The Fork Protocol — New Experiment in 4 Hours

When starting a new cross-model experiment, follow this sequence:

### Hour 1: Design (Layer 0)

1. Copy `geo_config.py` → `[experiment]_config.py`
2. Define your research question and hypotheses
3. Build the model roster (apply ARCHITECTURE.md Section 2 criteria)
4. Write the stimulus set (queries, scenarios, prompts)
5. Set parameters (T, top_p, K, spacing)
6. Compute cost estimate
7. Write the pre-registration protocol

### Hour 2: Execution Engine (Layer 1)

1. Copy `geo_runner.py` — this is **almost entirely reusable**
2. Update the import to reference your new config module
3. Adjust `BUDGET_CEILING_USD` for your experiment's scale
4. Verify the prompt builder generates your stimulus correctly
5. Test with a single API call to the cheapest model

### Hour 3: Processing + Analysis (Layers 2-3)

1. Write the extraction module for your specific output format
2. Write the normalization codebook
3. Copy the statistical primitives from `geo_analyze.py`
4. Write your hypothesis-specific tests
5. Wire the extraction → analysis pipeline

### Hour 4: Quality + Ops (Layers 4-5)

1. Copy `preflight_test.py` — update the config import and any experiment-specific checks
2. Copy `operator_logbook.py` — fully reusable, no changes needed
3. Update `RUNBOOK.md` with your experiment's mission, steps, and success criteria
4. Update `COWORK_INSTRUCTIONS.md` RED list with your experiment's immutable elements
5. Run the full pipeline in `--fast` mode to verify end-to-end

### The Reuse Matrix

| Component | Reuse Level | Adaptation Needed |
|-----------|------------|-------------------|
| `geo_runner.py` | ~95% | Change import, adjust budget ceiling |
| `preflight_test.py` | ~90% | Change import, update experiment-specific checks |
| `operator_logbook.py` | 100% | No changes |
| `geo_pipeline.py` (CLI) | ~70% | New prompt builder, updated step names |
| `geo_config.py` | ~20% | New models, new stimuli, new parameters |
| `geo_extract.py` | ~10% | Almost entirely experiment-specific |
| `geo_analyze.py` | ~50% | Statistical primitives reusable; hypothesis tests new |
| `RUNBOOK.md` | ~60% | New mission, same structure |
| `COWORK_INSTRUCTIONS.md` | ~80% | Update RED list; decision trees mostly reusable |
| `ARCHITECTURE.md` | 100% | Reference document, no changes |

---

## 3. The OpenRouter-as-Unified-Surface Pattern

Using a single API gateway (OpenRouter) for all models provides:

1. **Identical request format** — same JSON structure for GPT-5.4 and DeepSeek V3.2
2. **Consistent metadata** — token counts, timestamps, and model versions in a standard format
3. **Single billing surface** — one API key, one credit balance, one spend dashboard
4. **Automatic fallback** — OpenRouter can route to alternative providers if one is down
5. **Model substitution at the config level** — changing a model is a one-line config change, not an API refactor

**Tradeoff:** Some provider-specific features (Google's Deep Research, Anthropic's Extended Thinking, OpenAI's reasoning effort) are not available through OpenRouter's generic API. The pipeline explicitly scopes results to "API-level model behavior" and acknowledges this as a limitation.

**When to break this pattern:** If the experiment specifically requires provider-native features (e.g., testing whether Extended Thinking changes Claude's recommendations), access those models through their native APIs and document the procedural difference.

---

## 4. The Reproducibility Stack

Four mechanisms work together to make experiments reproducible:

### Hashing (What was run?)

```
Config hash ──→ "Did we test the same models with the same parameters?"
Prompt hash ──→ "Did we send the same stimulus?"
Content hash ─→ "Did we get the same response?"
```

Config + prompt hashes matching = same experiment. Content hashes matching = identical outputs (full replication). The degree of content hash divergence across replications is itself a finding about model determinism.

### Versioning (What code ran?)

Every module carries `__version__` and `__component__`. The manifest captures all versions. If a replicator's module versions differ, any divergence in results could be attributed to code changes, not model behavior.

### Pre-Registration (Was this planned?)

Git tag `pre-reg-vN.0` locks the experimental design before execution. Post-hoc analyses are permitted but must be labeled "exploratory — not pre-registered." This prevents the reviewer objection: "You only tested the hypotheses that worked."

### Manifest (One file to verify everything)

`data/manifest.json` is the single artifact a replicator needs. It contains all three hashes, the environment fingerprint, component versions, and per-output metadata. Share this file alongside the paper.

---

## 5. The Autonomous Execution Model

The framework supports three execution modes:

### Manual (Human operator)
Follow `OPERATOR_GUIDE.md`. Run each step, review output, proceed.

### Semi-Autonomous (Cowork with oversight)
Provide `RUNBOOK.md` + `geo_pipeline.tar.gz`. Cowork executes the 8-step sequence. Operator reviews the logbook afterward. Cowork has GREEN/YELLOW/RED permission boundaries and decision trees for common failures.

### Fully Autonomous (Cowork, no oversight during execution)
Same as semi-autonomous, but Cowork operates for the full 6-8 hours without human monitoring. The logbook, quality flags, and budget guard provide the post-mortem audit trail. The operator reviews results once, after completion.

**Key design principle:** Maximum autonomy with maximum observability. Cowork can fix anything in the GREEN list without asking. Every action is logged. The operator's review happens once, after completion, not during execution.

### What Makes This Work

1. **Budget guard** — The pipeline halts at $150. Cowork cannot spend unlimited money.
2. **Resume logic** — Crashes are recoverable. Re-running the same command continues from where it stopped.
3. **Quality flags** — Bad responses are flagged but not silently accepted. The operator sees them in the logbook.
4. **Code-change detection** — The logbook hashes all `.py` files at start and compares at close. Any modification is flagged, even if Cowork didn't explicitly log it.
5. **No-push rule** — Cowork commits to local git but never pushes to remote. The operator reviews before publishing.

---

## 6. Lessons Learned (Update This Section)

These lessons emerged from building and debugging the GEO pipeline. Add new lessons as future experiments surface them.

### Lesson 1: Build all five layers from the start
The initial build skipped quality/audit (Layer 4) and operational docs (Layer 5). This created blindspots that required retrofitting. The retrofit took 40% of total development time. Building all five layers from the start is faster than adding them later.

### Lesson 2: The prompt matters more than the code
The Run B prompt was rewritten after the Red Solo Pass found that "You are participating in a research study" triggered hedging behavior in alignment-trained models. A single sentence in the prompt had more impact on data quality than any code change. Always run the prompt through adversarial review before execution.

### Lesson 3: Model IDs go stale fast
8 of 10 model IDs in the original roster were outdated by the time the pipeline was ready to run. The staleness check (preflight verifying model availability) is not optional — it's the difference between a working experiment and a 404.

### Lesson 4: The cheapest models dominate the budget conversation but don't dominate the cost
GPT-5.4 and Claude Sonnet 4.6 together account for ~48% of total experiment cost despite being only 2 of 10 models. Cost optimization should focus on the 2-3 most expensive models, not the 7-8 cheap ones.

### Lesson 5: Resume logic pays for itself immediately
The pipeline crashed once during development. Resume logic (skip files that already exist with sufficient content) saved ~30 minutes of re-execution. It was added in 15 minutes. Always build resume logic into the runner.

### Lesson 6: Cowork needs explicit permission boundaries, not just instructions
Early versions of the Cowork instructions said "fix errors as needed." This is too vague — Cowork might modify pre-registered parameters to "fix" a model that's producing unexpected results. The GREEN/YELLOW/RED permission system prevents this by explicitly listing what changes are autonomous, what require logging, and what are prohibited.

### Lesson 7: The config should be Python, not YAML
A Python config module allows helper functions (`get_search_augmented()`, `estimate_total_cost()`), computed properties, and type-checked access. YAML/JSON configs require a separate parser and can't contain logic. The config-as-module pattern eliminates an entire class of "config doesn't match code" bugs.

### Lesson 8: Version everything, even before you think you need to
Version strings were added to all modules in a single pass. If they had been added from the first commit, the CHANGELOG would have been more granular and the manifest would have captured version evolution from day one. Add `__version__` to every module in the first commit.

### Lesson 9: Silent fallbacks are the most dangerous bugs
The `_find_query_section()` function fell back to returning the entire response text when no query marker was found. This was designed for "single-query responses or unstructured output" but produced catastrophic data contamination when 5 of 10 models only answered 5-15 of 40 queries. The fallback silently attributed ALL brands to ALL queries, creating 14,222 phantom extractions (68.9% of data). Every metric was corrupted. The fix was trivial (return `None` instead of full text), but the bug was invisible because the pipeline produced plausible-looking output — just wrong output. **Rule: functions that parse structured data must fail explicitly (return None, raise, or log a warning) when the expected structure isn't found. Never silently fall back to "return everything."** The validation gate's new cross-category contamination check would have caught this before analysis.

### Lesson 10: Multi-query prompts require output truncation handling
Sending 40 queries in a single prompt caused 4 models (Gemini Flash, Qwen, Llama Maverick, DeepSeek) to truncate after 5-15 queries due to output token limits or self-imposed response length preferences. The pipeline must either: (a) detect truncation and re-prompt for remaining queries, (b) send queries individually (40× more API calls but guaranteed coverage), or (c) split into batches of 8-10 queries. For the temporal drift study (K=10), option (b) may be required. The coverage report (`data/extraction_coverage.json`) now exposes this automatically.

---

## 7. Template Experiment Ideas

Future experiments that can be built on this framework with minimal adaptation:

| Experiment | What Changes | Reuse % |
|-----------|-------------|---------|
| Cross-model **factual accuracy** (do models agree on facts?) | Queries → factual questions; Extraction → claim extraction; Analysis → agreement on specific claims | ~60% |
| Cross-model **citation behavior** (what sources do models cite?) | Queries → research questions; Extraction → URL/source extraction; Analysis → source overlap | ~65% |
| Cross-model **sentiment** (do models have the same opinion?) | Queries → opinion prompts; Extraction → sentiment scoring; Analysis → sentiment divergence | ~55% |
| **Prompt sensitivity** (does paraphrasing change recommendations?) | Models → same; Queries → same queries paraphrased 5 ways; Analysis → within-query variance | ~75% |
| **Temporal drift** (do recommendations change over time?) | Models → same; Queries → same; K_TRIALS → daily runs over 30 days; Analysis → temporal stability | ~80% |
| **Multilingual divergence** (same query in 5 languages) | Queries → translated; Models → same; Analysis → cross-language agreement | ~70% |

Each of these can be built in ~4 hours by following the Fork Protocol (Section 2).

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-04-15 | Initial version. Codified from GEO pipeline build (8 hours active development). |
| 1.1.0 | 2026-04-15 | Added Lessons 9-10 (silent fallback contamination, multi-query truncation). |

*This is a living document. Update it when a pattern is validated, invalidated, or extended by building a new experiment.*
