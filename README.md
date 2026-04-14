# GEO Cross-Model Brand Visibility Study — Pipeline

**Version:** 3.0 | **Config hash:** `5b106c2c...` | **Estimated cost:** $53 | **Observations:** 1,000

A reproducible Python pipeline that runs 20 commercial queries across 10 frontier AI models (5 trials each) via OpenRouter, extracts brand recommendations, and computes cross-model agreement statistics (Fleiss' κ, Jaccard, Kendall's W) to test whether different AI platforms recommend different brands for identical queries.

---

## Quick Start

```bash
tar -xzf geo_pipeline.tar.gz && cd geo_pipeline
pip install -r requirements.txt
export OPENROUTER_API_KEY="sk-or-v1-YOUR_KEY"
python preflight_test.py                  # Verify everything
python geo_pipeline.py full --fast        # Test run (~15 min)
python geo_pipeline.py full               # Academic run (~6 hours)
python operator_logbook.py review         # Review what happened
```

For Claude Cowork: read `COWORK_INSTRUCTIONS.md` as your primary directive.

## File Inventory

### Code (7 files)
| File | Version | Purpose |
|------|---------|---------|
| `geo_config.py` | v3.0.0 | 10 models, 20 queries, all parameters |
| `geo_runner.py` | v2.1.0 | OpenRouter API calls, retries, resume, budget guard, manifest |
| `geo_extract.py` | v1.0.0 | Brand NER from responses, normalization codebook |
| `geo_analyze.py` | v1.0.0 | Fleiss' κ, Jaccard, Kendall's W, H1-H4 tests |
| `geo_pipeline.py` | v2.1.0 | CLI orchestrator + prompt builder |
| `preflight_test.py` | v1.0.0 | 9-section environment verification (run before experiment) |
| `operator_logbook.py` | v1.0.0 | Structured run log for post-mortem review |

### Documentation (5 files)
| File | Purpose |
|------|---------|
| `OPERATOR_GUIDE.md` | Step-by-step build, test, execute, and review instructions |
| `COWORK_INSTRUCTIONS.md` | Autonomous execution framework (permission boundaries, decision trees) |
| `ARCHITECTURE.md` | Design standards memo (living reference for all future experiments) |
| `CHANGELOG.md` | Version history for all components |
| `README.md` | This file |

### Configuration (2 files)
| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies (5 packages) |
| `.gitignore` | Tracks code + protocol, ignores outputs + logs |

## Pipeline Commands

```bash
python geo_pipeline.py preflight       # Check model availability
python geo_pipeline.py run-b           # Execute experiment (academic, ~6h)
python geo_pipeline.py run-b --fast    # Execute experiment (no spacing, ~15min)
python geo_pipeline.py run-a --prompt FILE  # Execute a Run A task
python geo_pipeline.py extract         # Extract brands from outputs
python geo_pipeline.py stochasticity   # Check output determinism across K runs
python geo_pipeline.py analyze         # Run H1-H4 statistical analysis
python geo_pipeline.py report          # Generate results summary
python geo_pipeline.py manifest        # Generate reproducibility manifest
python geo_pipeline.py full [--fast]   # Run entire pipeline end-to-end
```

## Key Design Features

- **Resume:** Interrupted runs continue from where they stopped (skips completed trials)
- **Budget guard:** Halts at $150 ceiling; displays cumulative spend during execution
- **Output validation:** Flags empty, short, refusal, and error responses automatically
- **Reproducibility:** Config hash, prompt hash, content hashes, environment fingerprint
- **Temporal spacing:** 60-min gaps between search-augmented model trials
- **Operator logbook:** Markdown + JSON run log with code-change detection

## Model Roster (April 2026)

| # | Model | Market Share | Group | Cost/call |
|---|-------|-------------|-------|-----------|
| 1 | GPT-5.4 | 64.5% | Search-augmented | $0.125 |
| 2 | Gemini 3.1 Pro | 21.5% | Search-augmented | $0.100 |
| 3 | Claude Sonnet 4.6 | 2.0% | Parametric-only | $0.126 |
| 4 | Grok 4.20 | 3.4% | Search-augmented | $0.052 |
| 5 | DeepSeek V3.2 | 4.8% | Non-English corpus | $0.008 |
| 6 | Qwen 3.5 Plus | 0.5% | Non-English corpus | $0.017 |
| 7 | Llama 4 Maverick | — | Parametric-only | $0.005 |
| 8 | Mistral Large 3 | 0.3% | Parametric-only | $0.043 |
| 9 | Gemini 3 Flash | — | Search-augmented | $0.025 |
| 10 | GLM-5 | 0.2% | Non-English corpus | $0.026 |

Coverage: 97.2% of global AI chatbot traffic (SimilarWeb, Jan 2026)
