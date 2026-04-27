# GEO Cross-Model Brand Visibility Study — Results Summary

Generated: 2026-04-15 04:53 UTC

---

## H1: Cross-Model Agreement (Fleiss' κ)

- **Mean κ = 0.165** (±0.177)
- Interpretation: substantial_disagreement
- H1 supported (κ < 0.6): **YES**

| Query | Category | κ | Brands |
|-------|----------|---|--------|
| Q01 | b2b_saas | 0.3407 | 6 |
| Q02 | b2b_saas | 0.2986 | 11 |
| Q03 | b2b_saas | 0.1711 | 12 |
| Q04 | b2b_saas | 0.4187 | 8 |
| Q05 | b2b_saas | 0.1435 | 17 |
| Q06 | healthcare_wellness | 0.2874 | 12 |
| Q07 | healthcare_wellness | 0.361 | 9 |
| Q08 | healthcare_wellness | 0.0024 | 10 |
| Q09 | healthcare_wellness | -0.0369 | 24 |
| Q10 | healthcare_wellness | 0.2725 | 11 |
| Q11 | consumer_electronics | 0.063 | 11 |
| Q12 | consumer_electronics | 0.1798 | 14 |
| Q13 | consumer_electronics | -0.04 | 12 |
| Q14 | consumer_electronics | 0.085 | 17 |
| Q15 | consumer_electronics | -0.0236 | 17 |
| Q16 | local_services | -0.0995 | 17 |
| Q17 | local_services | -0.0053 | 10 |
| Q18 | local_services | -0.0985 | 23 |
| Q19 | local_services | -0.0863 | 17 |
| Q20 | local_services | -0.1034 | 14 |
| Q21 | financial_services | 0.071 | 16 |
| Q22 | financial_services | 0.3718 | 8 |
| Q23 | financial_services | 0.1619 | 11 |
| Q24 | financial_services | 0.3695 | 10 |
| Q25 | financial_services | 0.0685 | 17 |
| Q26 | cpg | 0.0663 | 24 |
| Q27 | cpg | 0.008 | 13 |
| Q28 | cpg | 0.1429 | 9 |
| Q29 | cpg | 0.0313 | 17 |
| Q30 | cpg | 0.1163 | 11 |
| Q31 | enterprise_software | 0.0826 | 17 |
| Q32 | enterprise_software | 0.3167 | 12 |
| Q33 | enterprise_software | 0.4013 | 9 |
| Q34 | enterprise_software | 0.4193 | 12 |
| Q35 | enterprise_software | 0.291 | 14 |
| Q36 | travel_hospitality | 0.4571 | 7 |
| Q37 | travel_hospitality | 0.0074 | 14 |
| Q38 | travel_hospitality | 0.4515 | 10 |
| Q39 | travel_hospitality | 0.4027 | 16 |
| Q40 | travel_hospitality | 0.2325 | 10 |

## H2: Retrieval Architecture Effect

- Within search-augmented Jaccard: **0.3237**
- Between groups Jaccard: **0.2694**
- Cohen's d: **0.2012**
- p-value: **0.0010482625249713553**

## H4: Intra vs. Inter Consistency

- Intra-model Jaccard: **0.5772**
- Inter-model Jaccard: **0.2871**
- H4 supported: **YES**

## Brand Frequency (Exploratory)

- Total unique brands: 520
- Universal brands (≥8 models): FreshBooks, Tableau, Salesforce, Ping Identity, Google Flights, NOW Foods, Gusto, QuickBooks, Hilton Honors, Microsoft Azure, Beaches Resorts, HubSpot, Marriott Bonvoy, Headspace, Doxy.me
- Model-specific brands (≤2 models): 356

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
