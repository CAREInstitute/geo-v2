# Architectural Memo: Cross-Model AI Experimental Design

**Classification:** Internal Reference — Living Document
**Version:** 1.0.0
**Date:** 2026-04-15
**Origin:** GEO Cross-Model Brand Visibility Study (Pipeline v3.0)
**Maintainer:** Update this document whenever a new experiment is created or a design pattern is validated/invalidated by results.

---

## Purpose

This memo codifies the experimental design patterns, reproducibility infrastructure, and quality-control standards developed during the GEO Cross-Model Brand Visibility Study. It is intended as a binding reference for all future cross-model AI experiments — not aspirational guidance, but mandatory architecture that has been validated through adversarial review (JEC Protocol v9, Red Solo Pass, 4-cycle design panel).

Every section exists because a specific failure mode was identified. The rationale is documented so future experimenters understand *why* each requirement exists, not just *what* it is.

---

## 1. Pre-Registration Protocol

### Why This Exists

Post-hoc hypothesis selection inflates false-positive rates. A peer reviewer's first question will be: "Were these hypotheses specified before you saw the data?" Without pre-registration, the answer is indefensible.

### Required Steps

**Step 1 — Write the protocol document before any experimental execution.**

The protocol must contain, at minimum:

- Numbered hypotheses with directionality (e.g., "H1: κ < 0.6")
- Complete model roster with selection rationale
- Full query/prompt set (final text, not drafts)
- Analysis plan distinguishing primary (confirmatory) from secondary (exploratory) analyses
- Statistical tests to be used, including thresholds and effect-size metrics
- Threats to validity (internal, external, construct)
- Ethics statement

**Step 2 — Hash the prompt and config.**

```bash
# Prompt hash
sha256sum prompts/experiment_prompt.md > prompt_hash.txt

# Config hash (automated by pipeline)
python geo_pipeline.py manifest
# → data/manifest.json includes config_sha256
```

**Step 3 — Commit and tag.**

```bash
git init
git add .
git commit -m "Pre-registration: [experiment name] v1.0"
git tag -a "pre-reg-v1.0" -m "Pre-registered protocol — do not modify post-execution"
git remote add origin https://github.com/[handle]/[repo].git
git push -u origin main --tags
```

**Step 4 — Record the commit hash and timestamp in experiment metadata.**

The pre-registration commit hash becomes part of the experiment record. It is included in the paper's methodology section and in the data repository.

### Rules After Pre-Registration

- **The prompt file must not be modified.** The pipeline enforces this via SHA-256 hash comparison at execution time. If the hash doesn't match, execution halts.
- **The model roster must not be modified.** Any substitution (e.g., model unavailable) must use the pre-registered substitution list and must be documented in metadata.
- **New exploratory analyses may be added** but must be clearly labeled as "not pre-registered" in the results.
- **If the experimental design must change** (e.g., a model is permanently unavailable), re-register with a new version tag (`pre-reg-v2.0`) and document the change and rationale.

---

## 2. Model Roster Design

### Selection Criteria (Mandatory)

Every model in a cross-model experiment must satisfy all four:

1. **Current generation.** The model must be the provider's latest generally-available frontier offering. Using a superseded model (e.g., GPT-4o when GPT-5.4 exists) invalidates the study's relevance. Check the provider's model page and OpenRouter catalog before finalizing.

2. **Minimum context window ≥ 128K tokens.** This is the frontier floor as of Q1 2026. Models below this threshold are not competing at the frontier for recommendation/synthesis tasks.

3. **Available on the unified API surface** (e.g., OpenRouter) with published, stable pricing. The experiment must be executable through a single API endpoint for procedural consistency.

4. **Non-reasoning mode available.** Unless the experiment specifically studies reasoning behavior, models must support standard completion without mandatory chain-of-thought.

### Prioritization Criteria (Rank-Order)

5. **Consumer market share coverage.** The roster should collectively represent ≥95% of global AI chatbot traffic. Models powering platforms with ≥1% market share are prioritized because they are the surfaces where brand/information queries actually occur.

6. **Architecture diversity.** Include at least one model from each category:
   - Search-augmented (live web retrieval during inference)
   - Parametric-only (no retrieval; pure training-data knowledge)
   - Non-English-corpus (primarily trained on non-English data)
   - Open-weight (publicly available model weights)

7. **One flagship per provider.** Including multiple models from the same lab (e.g., both GPT-5.4 and GPT-5.4 Pro) adds within-provider variance but reduces cross-provider coverage. Exceptions are justified only when the two models serve structurally different roles (e.g., budget-tier vs. flagship for tier-comparison analysis).

8. **Cost ceiling.** Total experiment cost must remain feasible for a solo researcher. Exclude models where a single trial exceeds $5 unless they represent a uniquely important platform.

### Roster Size Guidance

| Size | When to Use | Tradeoffs |
|------|------------|-----------|
| 5 models | Pilot studies, rapid prototyping | Low statistical power for Fleiss' κ; misses market tail |
| 10 models | Standard academic study | Covers ≥95% market; adequate power; manageable cost |
| 15–25 models | Large-scale or funded studies | Marginal info gain per model decreases; cost scales linearly |

**Default: 10 models.** This is the empirically validated sweet spot for cross-model agreement studies.

### Model Substitution Protocol

Pre-register a substitution list for each model. If the primary model is unavailable at execution time:

1. Use the pre-registered substitute
2. Document the substitution in per-run metadata
3. Note as a limitation in the paper
4. Do not substitute with a model from a different architecture group

### Staleness Check (Mandatory Before Execution)

Before any experiment begins, verify every model ID against the provider's current catalog. Model IDs that were valid during design may be deprecated by execution day. Run `python geo_pipeline.py preflight` and review the output.

---

## 3. Query / Prompt Engineering

### Prompt Design Principles

1. **Ecological validity over experimental control.** The prompt should simulate how a real user would phrase the query. Do not announce that the model is being studied — this activates hedging behavior in alignment-trained models and produces artificially cautious outputs.

2. **Unconstrained response format.** Do not specify "recommend exactly N items" unless the constraint is the experimental variable. Constraining the output measures prompt compliance, not natural model behavior.

3. **Explicit language instruction.** If the roster includes models trained primarily on non-English data, the prompt must include "Respond entirely in English" (or the target language). Without this, mixed-language outputs will break downstream extraction.

4. **Lightweight format specification.** Provide a format example (e.g., "1. **Brand** — Justification") to aid automated extraction, but do not over-specify. The format instruction should be clearly separable from the query content.

5. **Response-length anchor.** Include a soft word-count target (e.g., "Aim for 200-400 words per query") to control token cost. This is a cost-management mechanism, not a scientific constraint.

6. **Separate primary from meta-analytical prompts.** Source attribution ("What sources did you use?") and self-analysis ("Are you biased?") are interesting but are not part of the primary outcome variable. Run them as a separate, optional follow-up prompt after primary data is collected. This avoids: (a) wasting tokens, (b) triggering refusals, (c) contaminating the primary response with meta-reflection.

### Query Set Design

1. **Systematic, not ad hoc.** Document the query construction methodology: category taxonomy, selection criteria, pilot testing.

2. **Span the relevant spectrum.** If the experiment tests a category-dependent variable (e.g., AI Overview trigger rates), the query set should span the full range of that variable.

3. **Inter-rater validation.** Have 2+ independent raters classify queries by category and intent. Report Cohen's κ (require ≥ 0.7). This prevents the objection that queries were selected to produce the desired result.

4. **5 queries per category minimum.** Fewer than 5 makes category-level subgroup analysis statistically meaningless.

### Prompt Versioning

- The prompt is hashed (SHA-256) before execution and the hash is stored in experiment metadata
- Any modification after hashing requires a new experiment version
- The pipeline enforces hash integrity at runtime — mismatches halt execution
- The raw prompt text is committed to the pre-registration repository

---

## 4. Execution Architecture

### Unified API Surface

All models must be accessed through a single API gateway (e.g., OpenRouter). This ensures:

- Identical request format across models
- Consistent metadata capture (tokens, timestamps, model versions)
- Single billing surface for cost tracking
- Reproducible API call structure

### Repeated Trials (K ≥ 5)

A single observation per cell (one query × one model) provides no within-cell variance estimate. This makes statistical inference impossible and is the primary disqualifier for peer review.

**Minimum: K = 5 independent runs per model per query.**

This enables:
- Within-cell variance estimation
- Confidence intervals for agreement metrics
- Intra-model consistency measurement (H4-type hypotheses)
- Stochasticity characterization at the chosen temperature

### Temporal Spacing

**Search-augmented models:** Space runs ≥60 minutes apart. Models with live web retrieval may share retrieval cache state across rapid successive calls, artificially inflating consistency.

**Parametric-only models:** No spacing required. Outputs depend on model weights, not retrieval state. All K runs can execute in a single parallel batch.

**Document the classification.** Some models (e.g., Claude via API) have ambiguous search status. Default to parametric-only unless documentation confirms search activation, and note the classification decision.

### Temperature and Sampling

- **Default: T = 0.3, top_p = 0.95.** This balances reproducibility with natural variation.
- **T = 0 is not recommended** for brand recommendation tasks — it may produce degenerate outputs (e.g., always selecting the first token in a tie).
- **Report stochasticity:** After execution, compute the proportion of identical outputs across K runs per model. This characterizes the "variance floor" and is a finding in itself.

### Metadata Capture (Per-Run)

Every API call must log:

| Field | Purpose | Used For |
|-------|---------|----------|
| `model_requested` | What you asked for | Audit trail |
| `model_returned` | What the API actually served | Catches silent model updates |
| `prompt_sha256` | Hash of the prompt sent | Integrity verification |
| `content_sha256` | Hash of the response received | Replication comparison |
| `start_timestamp` / `end_timestamp` | Wall-clock timing | Temporal spacing verification |
| `prompt_tokens` / `completion_tokens` | Token counts | Cost accounting |
| `finish_reason` | Why the response ended | Truncation detection |
| `attempt` | Retry count | Error pattern analysis |
| `errors` | Any failures or retries | Debugging, limitation documentation |

### Error Handling

- **Retry with backoff:** 3 attempts, exponential delay, extra delay on 429 (rate limit).
- **Log all errors** including failed attempts that were retried successfully.
- **Document refusals as data.** If a model refuses to answer a query (e.g., declines to recommend brands in a regulated category), the refusal is itself a finding. Save the refusal text and note it in metadata.

---

## 5. Reproducibility Infrastructure

### The Three Hashes

| Hash | What It Covers | What Match Means |
|------|---------------|-----------------|
| **Config hash** | Model roster + query set + parameters (T, top_p, K) | Same experimental design |
| **Prompt hash** | The exact text sent to models | Same stimulus |
| **Content hash** (per response) | Each model's output | Identical output (full replication) |

A replicator who matches config + prompt hashes ran the same experiment. If they also match content hashes, they got identical outputs — which is unlikely at T > 0 but the *degree of divergence* is a meaningful measurement.

### Experiment Manifest

The manifest (`data/manifest.json`) is a single file containing:

- Config hash
- Prompt hash
- Environment fingerprint (Python version, OS, package versions)
- Component versions (all pipeline modules)
- Per-output content hashes with timestamps

**Generate after execution:** `python geo_pipeline.py manifest`

**Share with the pre-registration repository** so others can verify their replication against your manifest.

### Environment Fingerprint

Capture and log:
- Python version (exact, e.g., 3.12.3)
- OS / platform
- Key package versions (requests, pandas, numpy, scipy)
- Pipeline component versions (all `__version__` strings)

### Persistent Logging

All experiment events log to `logs/experiment_YYYYMMDD_HHMMSS.log`:
- Config hash at start
- Each trial: model, run number, word count, status
- Errors and retries
- Timing events (spacing waits)

Logs are append-only and never overwritten. Multiple experiment runs produce separate log files.

---

## 6. Version Control

### Component Versioning

Every pipeline module carries `__version__` and `__component__` in its front matter:

```python
__version__ = "3.0.0"
__component__ = "geo_config"
```

**Semantic versioning:**
- **Major** — Breaking change (model roster swap, new metric, API change)
- **Minor** — New feature (new CLI command, new analysis, new extraction pattern)
- **Patch** — Bugfix, display change, comment update

### CHANGELOG.md

Every change gets a dated entry:

```markdown
## 2026-04-15

### geo_config 3.0.0
- **BREAKING:** 8 of 10 models replaced with current-generation equivalents
- Added per-model cost fields
```

### Git Workflow

```
main
  ├── pre-reg-v1.0 (tag) ─── locked protocol
  ├── experiment execution commits
  ├── data/ commits (outputs, metadata)
  └── paper/ commits (analysis, drafts)
```

**Branch strategy:**
- `main` — the canonical experiment record
- `pre-reg-vN.0` tags — immutable protocol snapshots
- Feature branches for pipeline improvements (merge to main before next experiment)

**Commit conventions:**
- `[config]` — model roster, query set, parameter changes
- `[runner]` — API execution, retry logic, metadata capture
- `[extract]` — brand extraction, normalization codebook
- `[analyze]` — statistical analysis, new metrics
- `[pipeline]` — CLI, orchestration, prompt builder
- `[data]` — output files, metadata, manifests
- `[paper]` — analysis results, figures, drafts
- `[docs]` — README, CHANGELOG, this memo

---

## 7. Data Extraction Protocol

### Automated Extraction

- Use NER or regex patterns to extract entity names (brands, products, services) from each response
- Normalize to canonical forms using a pre-built codebook (e.g., "HubSpot" = "hubspot" = "Hub Spot")
- Output: one row per entity mention per query per model per run

### Inter-Coder Reliability

Automated extraction is a starting point, not ground truth.

1. Generate a 20% random sample of responses for manual coding
2. Two independent coders extract entities from the sample
3. Calculate Cohen's κ for extraction agreement
4. **Require κ ≥ 0.8.** If below threshold: reconcile disagreements, refine the codebook, re-code until met
5. Document the codebook, sample selection, and reliability score in the methods section

### Majority Rule for Repeated Trials

When K > 1, an entity is "included" for a given query-model cell if it appears in > 50% of the K runs. This stabilizes the data against stochastic noise while preserving genuine model preferences.

---

## 8. Statistical Analysis Framework

### Primary vs. Exploratory

Pre-register which analyses are **primary** (confirmatory — test specific hypotheses) and which are **exploratory** (hypothesis-generating — interesting patterns that emerged).

This distinction prevents p-hacking and significance inflation. A peer reviewer will accept exploratory findings labeled as such; they will reject exploratory findings presented as confirmatory.

### Standard Metrics for Cross-Model Agreement

| Metric | What It Measures | When to Use |
|--------|-----------------|-------------|
| **Fleiss' kappa (κ)** | Multi-rater agreement on categorical assignment | Models as raters, entity inclusion as the rated variable |
| **Pairwise Jaccard** | Set overlap between two models | Pairwise comparison; can be decomposed by architecture group |
| **Kendall's W** | Rank concordance across models | When models produce ordered lists |
| **Cohen's d** | Effect size between groups | Comparing agreement within vs. between architecture groups |
| **Mann-Whitney U** | Non-parametric group comparison | When normality assumptions don't hold |

### Interpretation Guide

| Fleiss' κ | Interpretation |
|-----------|---------------|
| < 0.00 | Less than chance agreement |
| 0.01 – 0.20 | Slight agreement |
| 0.21 – 0.40 | Fair agreement |
| 0.41 – 0.60 | Moderate agreement |
| 0.61 – 0.80 | Substantial agreement |
| 0.81 – 1.00 | Almost perfect agreement |

---

## 9. Threats to Validity

Every experiment must include an explicit threats-to-validity section. The following taxonomy is the minimum; experiment-specific threats should be added.

### Internal Validity

| Threat | Standard Mitigation |
|--------|-------------------|
| Stochastic variation | K ≥ 5 repeated trials; report stochasticity metrics |
| Temporal confounding (search models) | ≥ 60-minute spacing between trials |
| Query ordering effects | Fixed order, identical across models |
| Prompt sensitivity | Single prompt version (limitation); future work tests paraphrasing |

### External Validity

| Threat | Standard Mitigation |
|--------|-------------------|
| API vs. consumer interface | Explicit scope declaration; do not overclaim |
| Query representativeness | Systematic construction; inter-rater validation; acknowledge non-random |
| English-only | Acknowledge; do not generalize to multilingual |
| Point-in-time | Timestamp all runs; acknowledge model updates |
| Model roster | Document roster date; may not generalize to future models |

### Construct Validity

| Threat | Standard Mitigation |
|--------|-------------------|
| Entity mention ≠ endorsement | Acknowledge; "brand mention" is operationalized as name presence |
| Jaccard treats mentions equally | Acknowledge; does not capture sentiment or position weight |
| Self-reported attribution unreliable | Treat meta-analytical data as exploratory, not primary |

---

## 10. Cost Estimation

### Formula

```
Total cost = Σ (models) × queries × K_trials × cost_per_call

cost_per_call = (input_tokens / 1M) × input_price + (output_tokens / 1M) × output_price
```

### Standard Assumptions

- Input tokens per call: ~2,000 (prompt)
- Output tokens per call: ~8,000 (response)
- Add 20-30% buffer for retries and longer-than-expected outputs

### Cost-Tier Awareness

As of Q1 2026, models span a 100× cost range:

| Tier | Example Models | Output $/M tokens |
|------|---------------|-------------------|
| Ultra-low | DeepSeek V3.2, Llama 4 Maverick | $0.38 – $0.89 |
| Budget | Gemini 3 Flash, Qwen 3.5 Plus | $2 – $3 |
| Standard | GPT-5.4, Claude Sonnet 4.6 | $15 |
| Premium | Claude Opus 4.6, GPT-5.4 Pro | $25 – $180 |

The top 2-3 most expensive models typically account for >60% of total experiment cost. Consider whether the premium tier is justified by market share or architectural uniqueness.

---

## 11. Ethics

### Standard Ethics Statement

All experiments using this framework should include:

1. All models accessed via published API terms through a licensed aggregation service
2. No personal data collected
3. No human subjects involved
4. Model outputs may reflect training-data biases; the study documents but does not correct these
5. Entity recommendations in AI outputs do not constitute endorsements by the researchers or model providers

### API Terms Compliance

Before execution, verify that systematic API evaluation is permitted under each provider's terms of service. Document this verification.

### Bias Documentation

If the experiment reveals systematic biases (e.g., models consistently favoring certain brands), document these as findings, not as flaws to be corrected. The purpose of cross-model experiments is to *characterize* model behavior, not to optimize it.

---

## 12. Paper Structure (Reference Template)

For academic publication, the standard structure:

1. **Abstract** (250 words)
2. **Introduction** — Motivation, research questions, contribution
3. **Related Work** — Prior cross-model studies, relevant domain literature
4. **Methodology**
   - 4.1 Hypotheses (pre-registered)
   - 4.2 Model selection and grouping (with justification table)
   - 4.3 Query design and validation
   - 4.4 Execution protocol (K trials, temporal spacing)
   - 4.5 Data extraction and inter-coder reliability
   - 4.6 Analysis plan (primary vs. exploratory)
5. **Results**
   - 5.1 Stochasticity characterization
   - 5.2–5.N Primary hypotheses (in pre-registered order)
   - 5.N+1 Exploratory analyses (clearly labeled)
6. **Discussion** — Implications, comparison with prior work
7. **Threats to Validity** (per Section 9 taxonomy)
8. **Conclusion and Future Work**
9. **Ethics Statement**
10. **Data Availability** — Link to pre-registration repo with all code, prompts, outputs

---

## 13. Checklist: Before Any Experiment Executes

Use this as a gate. Every box must be checked before the first API call.

```
[ ] Hypotheses written and numbered
[ ] Model roster verified against current provider catalogs (preflight check passed)
[ ] Query set validated by 2+ independent raters (κ ≥ 0.7)
[ ] Prompt finalized and hashed (SHA-256)
[ ] Config hashed (automated by pipeline)
[ ] Analysis plan written with primary/exploratory distinction
[ ] Threats to validity documented
[ ] Ethics statement written
[ ] CHANGELOG.md updated with current component versions
[ ] All materials committed to public repository with pre-registration tag
[ ] Commit hash and timestamp recorded in experiment metadata
[ ] Cost estimate computed and budget confirmed
[ ] Substitution list pre-registered for each model
[ ] Pipeline preflight check passed (all models available)
[ ] Environment fingerprint captured
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-04-15 | — | Initial version. Codified from GEO Cross-Model Brand Visibility Study pipeline (v3.0), JEC Protocol v9, Red Solo Pass, and 4-cycle design panel. |

*This is a living document. Update it when a design pattern is validated, invalidated, or extended by experimental results.*
