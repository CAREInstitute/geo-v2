# Operator Build Guide

**Purpose:** Step-by-step instructions to build, test, and execute the GEO Cross-Model Brand Visibility experiment. Written for both human operators and Claude Cowork autonomous execution.

**Important:** This guide produces a complete Operator Logbook at `logs/logbook_*.md`. After any run (manual or Cowork), review the logbook to understand what happened.

---

## Phase 0: Environment Setup

### 0.1 Extract the pipeline

```bash
tar -xzf geo_pipeline.tar.gz
cd geo_pipeline
```

### 0.2 Install dependencies

```bash
pip install -r requirements.txt
```

### 0.3 Set the API key

```bash
export OPENROUTER_API_KEY="sk-or-v1-YOUR_KEY_HERE"
```

To persist across sessions, add to `~/.bashrc` or `~/.zshrc`:
```bash
echo 'export OPENROUTER_API_KEY="sk-or-v1-YOUR_KEY_HERE"' >> ~/.bashrc
source ~/.bashrc
```

### 0.4 Verify setup

```bash
python preflight_test.py
```

**Decision gate:** ALL checks must pass before proceeding. If any check fails, resolve it before moving to Phase 1. The preflight report is saved to `data/preflight_report.json`.

Common failure resolutions:

| Failure | Fix |
|---------|-----|
| Package not installed | `pip install [package]` |
| API key not set | `export OPENROUTER_API_KEY="sk-or-v1-..."` |
| Model not available | Check OpenRouter status; pipeline will auto-substitute from pre-registered list |
| API unreachable | Check network; retry in 5 minutes |
| Dry run fails | Check API key validity at openrouter.ai/settings |

---

## Phase 1: Pre-Registration

### 1.1 Review the experimental design

Read these files to understand what you're about to run:

- `ARCHITECTURE.md` — Design standards and rationale
- `README.md` — Quick reference
- `geo_config.py` — Model roster, query set, parameters

### 1.2 Initialize the repository

```bash
git init
git add .
git commit -m "Initial commit: GEO pipeline v3.0"
```

### 1.3 Generate and record the config hash

```bash
python geo_pipeline.py manifest
# Note the config_sha256 from the output
```

### 1.4 Tag the pre-registration

```bash
git tag -a "pre-reg-v1.0" -m "Pre-registered experimental protocol"
```

### 1.5 Push to remote (if using GitHub/OSF)

```bash
git remote add origin https://github.com/[YOUR_HANDLE]/geo-cross-model-study.git
git push -u origin main --tags
```

**Decision gate:** After tagging, do NOT modify `geo_config.py` or the prompt builder in `geo_pipeline.py`. The pipeline enforces prompt hash integrity at runtime.

---

## Phase 2: Run the Experiment

### Option A: Full automated run (recommended)

```bash
# Academic mode (with temporal spacing — ~5-6 hours)
python geo_pipeline.py full

# Fast mode (no temporal spacing — ~15-30 minutes, NOT for publication)
python geo_pipeline.py full --fast
```

The `full` command executes these steps in order:
1. Pre-flight model check
2. Run B experiment (1,000 API calls)
3. Brand extraction
4. Stochasticity analysis
5. Statistical analysis (H1-H4)
6. Report generation
7. Manifest generation

### Option B: Step-by-step (for debugging or partial re-runs)

```bash
# Step 1: Verify models
python geo_pipeline.py preflight

# Step 2: Run the experiment
python geo_pipeline.py run-b           # academic (with spacing)
python geo_pipeline.py run-b --fast    # fast (no spacing)

# Step 3: Extract brands from outputs
python geo_pipeline.py extract

# Step 4: Check output determinism
python geo_pipeline.py stochasticity

# Step 5: Run statistical analysis
python geo_pipeline.py analyze

# Step 6: Generate report
python geo_pipeline.py report

# Step 7: Generate manifest
python geo_pipeline.py manifest
```

### Monitoring during execution

During Run B, the pipeline prints progress to stdout:
```
[phase2a_start] Parametric-only models: 6 models × 5 runs
  b03_claude_sonnet run 1: 4523 words [OK] (1/50)
  b07_llama4_maverick run 1: 3891 words [OK] (2/50)
  ...
[phase2b_start] Search-augmented models: 4 models × 5 runs (≥3600s spacing)
  Waiting 3600s before next search-augmented trial...
```

All events are also logged to `logs/experiment_*.log`.

---

## Phase 3: Post-Execution Review

### 3.1 Review the Operator Logbook

```bash
python operator_logbook.py review
```

This prints the most recent logbook. Check:
- [ ] All steps passed
- [ ] No unexpected code modifications
- [ ] Output file count matches expectations (50 Run B files + analysis CSVs)

### 3.2 Review stochasticity

```bash
python geo_pipeline.py stochasticity
```

Check that search-augmented models show variation across runs (low identical %). If a model produced 5 identical outputs at T=0.3, it may not be using search, or the query may be too simple.

### 3.3 Review analysis results

```bash
cat paper/results_summary.md
```

Key numbers to check:
- **H1 (Fleiss' κ):** If κ > 0.6, the fragmentation thesis is weakened
- **H4 (intra > inter):** If intra-model Jaccard is NOT higher than inter-model, the experiment design may need revision

### 3.4 Review the manifest

```bash
cat data/manifest.json | python -m json.tool | head -30
```

Verify:
- `config_sha256` matches the pre-registration
- `prompt_sha256` matches the pre-registration
- Output count = expected (50 files for 10 models × 5 runs)

### 3.5 Commit results

```bash
git add data/ paper/ logs/
git commit -m "[data] Experiment results — $(date +%Y-%m-%d)"
git push
```

---

## Phase 4: Run A (Optional — Deep Research via OpenRouter)

Run A tasks use frontier models for deep research. These produce the literature review and measurement framework that inform the paper's background sections.

```bash
# Requires A-run prompt files in prompts/ directory
python geo_pipeline.py run-a --prompt prompts/run_a1_gemini.md
python geo_pipeline.py run-a --prompt prompts/run_a2_chatgpt.md
python geo_pipeline.py run-a --prompt prompts/run_a3_claude.md
```

**Note:** Run A via OpenRouter uses standard API access, not Deep Research or Extended Thinking modes. For maximum quality, use the platform-native interfaces (Google AI Studio, ChatGPT Pro, Claude.ai) as described in the Build Guide.

---

## Troubleshooting

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| `preflight_test.py` fails on API | Key expired or invalid | Regenerate at openrouter.ai/settings |
| Model returns empty response | Model may be overloaded | Retry; pipeline has 3-attempt retry logic |
| "Prompt hash mismatch" error | Prompt was modified after pre-registration | Restore from git: `git checkout pre-reg-v1.0 -- geo_pipeline.py` |
| Run B hangs on "Waiting 3600s" | Normal — temporal spacing for search models | Wait, or use `--fast` for testing |
| Brand extraction finds 0 brands | Model output format unexpected | Review raw outputs in `outputs/run_b/`; may need extraction pattern update |
| Fleiss' κ = 0 for all queries | Brand extraction may have failed | Check `data/brand_visibility_raw.csv` for data |
| Cost exceeds estimate | Models producing longer outputs | Check token counts in `data/run_metadata/*.json` |
| Cowork modified code unexpectedly | Review logbook code changes section | Diff against pre-reg: `git diff pre-reg-v1.0` |

---

## For Claude Cowork

If this pipeline is being operated by Claude Cowork:

1. **Start with:** `python preflight_test.py` — do not proceed if any check fails
2. **Use:** `python geo_pipeline.py full --fast` for initial test run
3. **If a step fails:** Log the error, attempt the documented fix from the troubleshooting table, retry once. If it fails again, log the failure and stop — do not attempt creative fixes without operator approval.
4. **Do not modify** `geo_config.py` or the prompt builder without logging the change and reason in the Operator Logbook.
5. **If modifying any `.py` file:** Record the file path, reason, and before/after hashes in the logbook.
6. **After completion:** Ensure the logbook is written to `logs/logbook_*.md` and the manifest is generated.
7. **Final step:** Print the logbook summary so the operator can review.

---

## File Quick Reference

| File | What It Is | When You Need It |
|------|-----------|-----------------|
| `preflight_test.py` | Automated environment verification | Before any experiment run |
| `geo_pipeline.py` | Main experiment orchestrator | Running the experiment |
| `operator_logbook.py` | Structured run log + review tool | After any run |
| `geo_config.py` | Models, queries, parameters | Understanding the experimental design |
| `ARCHITECTURE.md` | Design standards and rationale | Understanding WHY things are designed this way |
| `CHANGELOG.md` | Version history | Debugging, understanding what changed |
| `README.md` | Quick-start reference | Getting oriented |
| `data/manifest.json` | Reproducibility hashes | Sharing with replicators |
| `data/preflight_report.json` | Pre-flight test results | Diagnosing setup issues |
| `logs/logbook_*.md` | Operator logbook (human-readable) | Post-run review |
| `logs/logbook_*.json` | Operator logbook (machine-readable) | Programmatic analysis |
| `paper/results_summary.md` | Analysis results | Writing the paper |
