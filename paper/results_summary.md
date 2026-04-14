# GEO Cross-Model Brand Visibility Study — Results Summary

Generated: 2026-04-14 23:04 UTC

---

## H1: Cross-Model Agreement (Fleiss' κ)

- **Mean κ = 0.0331** (±0.1223)
- Interpretation: substantial_disagreement
- H1 supported (κ < 0.6): **YES**

| Query | Category | κ | Brands |
|-------|----------|---|--------|
| Q01 | b2b_saas | 0.2222 | 10 |
| Q02 | b2b_saas | 0.2437 | 9 |
| Q03 | b2b_saas | 0.2317 | 13 |
| Q04 | b2b_saas | 0.2104 | 21 |
| Q05 | b2b_saas | 0.0913 | 26 |
| Q06 | healthcare_wellness | -0.0493 | 25 |
| Q07 | healthcare_wellness | 0.1491 | 25 |
| Q08 | healthcare_wellness | -0.0421 | 26 |
| Q09 | healthcare_wellness | -0.09 | 28 |
| Q10 | healthcare_wellness | 0.1051 | 25 |
| Q11 | consumer_electronics | 0.0755 | 26 |
| Q12 | consumer_electronics | -0.0027 | 25 |
| Q13 | consumer_electronics | -0.0589 | 27 |
| Q14 | consumer_electronics | 0.0291 | 27 |
| Q15 | consumer_electronics | -0.0624 | 30 |
| Q16 | local_services | -0.071 | 40 |
| Q17 | local_services | -0.07 | 36 |
| Q18 | local_services | -0.0702 | 37 |
| Q19 | local_services | -0.0675 | 40 |
| Q20 | local_services | -0.1111 | 13 |

## H2: Retrieval Architecture Effect

- Within search-augmented Jaccard: **0.3629**
- Between groups Jaccard: **0.1705**
- Cohen's d: **0.7032**
- p-value: **3.599098436976481e-07**

## H4: Intra vs. Inter Consistency

- Intra-model Jaccard: **0.5261**
- Inter-model Jaccard: **0.2115**
- H4 supported: **YES**

## Brand Frequency (Exploratory)

- Total unique brands: 165
- Universal brands (≥8 models): Klaviyo, Segment, Pipedrive, Headspace, Pure Encapsulations, HubSpot, Jira, Sony, Fujifilm X, Calm
- Model-specific brands (≤2 models): 110

## Stochasticity Report

| Model | Group | Unique/Total | Deterministic |
|-------|-------|-------------|---------------|
| GPT-5.4 | search_augmented | 5/5 | No |
| Gemini 3.1 Pro | search_augmented | 5/5 | No |
| Claude Sonnet 4.6 | parametric_only | 5/5 | No |
| Grok 4.20 | search_augmented | 5/5 | No |
| DeepSeek V3.2 | non_english_corpus | 5/5 | No |
| Qwen 3.5 Plus | non_english_corpus | 5/5 | No |
| Llama 4 Maverick | parametric_only | 5/5 | No |
| Mistral Large 3 | parametric_only | 5/5 | No |
| Gemini 3 Flash | search_augmented | 5/5 | No |
| GLM-5 | non_english_corpus | 5/5 | No |
