# COWORK_INSTRUCTIONS.md
# Autonomous Execution Framework for Claude Cowork

**This file is the primary directive for Claude Cowork operating the GEO pipeline.**
Read these files in this order:
1. `COWORK_INSTRUCTIONS.md` — Your permission boundaries and decision trees (READ THIS FIRST)
2. `OPERATOR_GUIDE.md` — Step-by-step execution instructions
3. `README.md` — Quick reference for commands and file inventory

---

## Mission

Get the GEO Cross-Model Brand Visibility experiment from zero to completed results, with full logging so the operator can review what happened.

## Operating Principles

1. **Log everything.** Every decision, every fix, every skip goes in the logbook.
2. **Fix what you can. Flag what you can't.** You have broad autonomy. Use it. If something is genuinely ambiguous, log the decision and proceed with your best judgment — don't halt.
3. **Never modify the experimental design silently.** If you change a model, a query, or a parameter, log WHY with a before/after hash.
4. **Cheaper to retry than to debug.** If an API call fails, retry before investigating. If a module won't import, reinstall before reading source code.

---

## Permission Boundaries

### GREEN — Do Without Asking

You have full autonomy for these actions. Log them but proceed immediately.

| Action | Example |
|--------|---------|
| Install/upgrade Python packages | `pip install requests --upgrade` |
| Create directories | `mkdir -p outputs/run_b` |
| Retry failed API calls | Up to 5 additional retries beyond the built-in 3 |
| Substitute an unavailable model | Use the pre-registered substitute from `geo_config.py SUBSTITUTIONS` |
| Fix import errors | Install missing package, fix Python path |
| Fix file permission errors | `chmod` as needed |
| Re-run a single failed step | `python geo_pipeline.py extract` after fixing extraction |
| Adjust `BUDGET_CEILING_USD` up to $200 | If estimated cost is under $200 |
| Set `--fast` mode for initial test | To verify pipeline works before full academic run |
| Fix syntax errors in pipeline code | Typos, missing imports, wrong variable names |
| Update model IDs if OpenRouter returns 404 | Use substitute list; log the change |
| Add entries to brand normalization codebook | New brand name variants discovered during extraction |
| Create or modify `.gitignore` | Repository hygiene |

### YELLOW — Do It, But Log Extensively

You may make these changes, but document the before state, the reason, and the after state in the logbook.

| Action | Logging Required |
|--------|-----------------|
| Modify `geo_runner.py` to fix a bug | Log: file, function, line, before code, after code, reason |
| Modify `geo_extract.py` patterns | Log: what pattern changed, why, example that triggered it |
| Modify `geo_analyze.py` calculations | Log: which formula, what changed, before/after test output |
| Modify `geo_pipeline.py` CLI logic | Log: what command, what changed, why |
| Increase `K_TRIALS` from 5 to more | Log: reason (e.g., too much stochasticity), cost impact |
| Decrease `SEARCH_SPACING_SECONDS` | Log: reason, new value, note for paper limitations |
| Add a new analysis that wasn't pre-registered | Log: label it as "EXPLORATORY — not pre-registered" |
| Modify the prompt format instructions | Log: before/after prompt hash, reason |

### RED — Do Not Do

These actions are prohibited. If any of these seem necessary, log the situation and halt.

| Action | Why Prohibited |
|--------|---------------|
| Change the 20 query texts | These are pre-registered; changing them invalidates the experiment |
| Remove a model from the roster | Reduces the pre-registered design; document as "unavailable" instead |
| Change `TEMPERATURE` or `TOP_P` | These are pre-registered parameters |
| Delete output files from a completed run | Data destruction; move to an archive instead |
| Push to git remote without operator review | The operator must review before publishing |
| Exceed $200 total spend | Hard ceiling; halt and log |
| Modify this file (`COWORK_INSTRUCTIONS.md`) | Meta-violation |

---

## Execution Playbook

### Step 1: Environment Setup

```bash
cd geo_pipeline
pip install -r requirements.txt
```

If `pip` fails:
- Try `pip3 install -r requirements.txt`
- Try `pip install -r requirements.txt --break-system-packages`
- Try `python -m pip install -r requirements.txt`
- Log which variant worked

### Step 2: Set API Key

Check if `OPENROUTER_API_KEY` is set:
```bash
echo $OPENROUTER_API_KEY | head -c 10
```

If not set: check for a `.env` file, `~/.bashrc`, or ask the operator. **Do not proceed without an API key.**

### Step 3: Run Pre-Flight Tests

```bash
python preflight_test.py
```

**Decision tree for failures:**

| Failure | Action |
|---------|--------|
| Package not installed | `pip install [package]` → re-run preflight |
| API key not set | Check `.env`, `~/.bashrc`; if truly missing, HALT |
| Model unavailable | Check if substitute is available; apply substitution; log it |
| API unreachable | Wait 60 seconds, retry; if still failing after 3 tries, HALT |
| Prompt build fails | Check `geo_pipeline.py _build_run_b_prompt()`; likely a syntax error; fix and log |
| Dry run fails with auth error | API key is invalid; HALT |
| Dry run fails with model error | Model ID may be wrong; check OpenRouter catalog; update and log |

**All checks must pass before proceeding to Step 4.**

### Step 4: Initial Test Run (Fast Mode)

```bash
python geo_pipeline.py run-b --fast
```

This runs all 1,000 API calls without temporal spacing (~15-30 minutes).

**Purpose:** Verify all models respond, outputs are reasonable, extraction works.

**After fast run:**
```bash
python geo_pipeline.py extract
python geo_pipeline.py stochasticity
```

**Check:** Do all 10 models produce outputs? Are word counts reasonable (≥200 per response)? Any quality flags?

```bash
# Quick check
ls outputs/run_b/*.md | wc -l  # Should be 50 (10 models × 5 runs)
for f in outputs/run_b/*_run1.md; do echo "$(wc -w < $f) words — $(basename $f)"; done
```

**Decision tree for test run issues:**

| Issue | Action |
|-------|--------|
| Model returns empty responses | Check model ID; try substitute; re-run just that model |
| Model returns <100 words | May be truncated; check `finish_reason` in metadata; increase `max_tokens` if needed |
| Quality flag: POSSIBLE_REFUSAL | Review the response; if genuine refusal, document as data point, don't retry |
| Quality flag: ERROR_AS_CONTENT | API error leaked into response; delete the file, retry |
| 3+ models fail | Likely API issue; wait 10 minutes, re-run (resume will skip completed trials) |
| Cost exceeds $80 on test run | Models producing very long outputs; review token counts; consider reducing `MAX_TOKENS` |

### Step 5: Full Academic Run (If Test Passed)

**Only proceed if the test run produced reasonable results for all 10 models.**

First, clean the test outputs:
```bash
rm -rf outputs/run_b/* data/run_metadata/*
```

Then run with temporal spacing:
```bash
python geo_pipeline.py full
```

This will take ~5-6 hours (mostly waiting for search-augmented model spacing).

**Monitor:** The pipeline prints progress. If running unattended, check `logs/experiment_*.log` periodically.

### Step 6: Post-Execution

```bash
python geo_pipeline.py manifest
python operator_logbook.py review
```

Verify:
- [ ] All 50 output files exist and have content
- [ ] No quality flags on critical models (GPT-5.4, Gemini 3.1 Pro, Claude Sonnet)
- [ ] Cumulative cost is within estimate ($52 ± 50%)
- [ ] Manifest generated with all hashes

### Step 7: Commit Results

```bash
git add -A
git commit -m "[data] Experiment complete — $(date +%Y-%m-%d) — $(python -c 'from geo_runner import hash_config; print(hash_config()[:12])')"
```

**Do NOT push.** Leave for operator review.

---

## Failure Recovery Decision Trees

### API Call Fails (After Built-In Retries)

```
API call failed for model X, run K
  ├── Is the error a 429 (rate limit)?
  │   └── YES → Wait 5 minutes, retry once more
  ├── Is the error a 404 (model not found)?
  │   └── YES → Apply substitute from SUBSTITUTIONS dict, log change
  ├── Is the error a 500/502/503 (server error)?
  │   └── YES → Wait 2 minutes, retry. If fails 3x → skip this trial, log as FAILED
  ├── Is the error a 401 (auth)?
  │   └── YES → API key invalid. HALT entire pipeline.
  └── Unknown error
      └── Log full error. Skip this trial. Continue with other models.
```

### Output Looks Wrong

```
Response has quality flag
  ├── EMPTY_RESPONSE
  │   └── Delete file, retry once. If still empty → log as FAILED, continue
  ├── VERY_SHORT (<100 words)
  │   └── Check finish_reason. If "length" → increase max_tokens for this model, retry
  │   └── If "stop" → model gave a short answer; keep it, it's valid data
  ├── POSSIBLE_REFUSAL
  │   └── Read first 200 chars. If genuine refusal → keep as data. Document.
  │   └── If false positive (just cautious language) → keep, clear flag in notes
  └── ERROR_AS_CONTENT
      └── Delete file, retry once. If persists → log, skip trial
```

### Brand Extraction Finds Few/No Brands

```
Extraction returns <10 total brands across all models for a query
  ├── Is the query a Local Services query (Q16-Q20)?
  │   └── YES → Expected. These are control queries. No action needed.
  ├── Are raw outputs actually empty?
  │   └── YES → API issue. Check run_b outputs.
  └── Are outputs present but extraction missed brands?
      └── Review a sample output manually
      └── If brands are present but not caught → update extraction patterns in geo_extract.py
      └── Log the pattern change (YELLOW action)
```

### Pipeline Crashes Mid-Run

```
Pipeline crashed or was interrupted
  └── Don't panic. Resume is built in.
  └── Re-run the same command: python geo_pipeline.py full [--fast]
  └── Already-completed trials (files >500 bytes with >200 words) will be SKIPPED
  └── Only incomplete/missing trials will re-run
  └── Check logs/ for the crash log
```

---

## Logbook Protocol

Initialize the logbook at the start of every session:

```python
from operator_logbook import OperatorLogbook
logbook = OperatorLogbook('.', 'GEO Experiment — Cowork Run')
```

Log every step:
```python
logbook.step_start('Pre-flight', 'Running environment verification')
# ... do the work ...
logbook.step_pass('Pre-flight', '30/30 checks passed')
```

Log any code modifications:
```python
logbook.log_code_change(
    'geo_extract.py',
    'Added pattern for hyphenated brand names (e.g., "Zoho-CRM")',
    before_hash='abc123...',
    after_hash='def456...'
)
```

Close the logbook when done:
```python
path = logbook.close('completed')  # or 'failed' or 'partial'
print(f"Logbook: {path}")
```

---

## Summary for Cowork

```
1. pip install -r requirements.txt
2. Verify OPENROUTER_API_KEY is set
3. python preflight_test.py          ← ALL must pass
4. python geo_pipeline.py full --fast ← Test run first
5. Review: ls outputs/run_b/*.md | wc -l  ← Should be 50
6. If test OK: rm -rf outputs/run_b/* data/run_metadata/*
7. python geo_pipeline.py full       ← Academic run (~5-6 hours)
8. python geo_pipeline.py manifest
9. python operator_logbook.py review
10. git add -A && git commit -m "[data] Experiment complete"
```

**Remember:** Log everything. Fix what you can. Flag what you can't. The operator will review the logbook.
