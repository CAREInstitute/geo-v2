"""
GEO Cross-Model Brand Visibility Study — Configuration
Version: 2026.4.15-r4 (Expanded 8-Category Study)

CHANGELOG:
  r4: Added 4 new categories (Financial Services, CPG, Enterprise Software, Travel)
      20 new queries (Q21-Q40), total now 40 queries across 8 categories
      Fixed Mistral model ID: mistral-large-3 → mistral-large-2512
      Fixed 7 imperative queries to question form for consistency
      Revised cost estimate: output_tokens 8000 → 4000 (based on actual run data)
  r3: 8 of 10 models replaced with current-generation equivalents
  r2: K=5 trials, 20 queries, temporal spacing
v5.0.0  2026-04-27  v2 design parameters (12-model panel per OIL-23, ~7290 obs target).
"""

__version__ = "5.0.0"
__component__ = "geo_config"

EXPERIMENT_NAME = "Cross-Model GEO Brand Visibility Study"
VERSION = "4.0-expanded"
TEMPERATURE = 0.3
TOP_P = 0.95
MAX_TOKENS = 16384
K_TRIALS = 5
SEARCH_SPACING_SECONDS = 3600
QUERY_BATCH_SIZE = 8  # v4.1: Send queries in batches of 8 to prevent output truncation

MODELS = [
    {"id": "openai/gpt-5.4", "short": "b01_gpt54", "name": "GPT-5.4", "group": "search_augmented", "arch": "proprietary/RLHF/Bing/computer-use", "corpus": "Western", "market_share": 64.5, "max_tokens": MAX_TOKENS, "cost_input_per_m": 2.50, "cost_output_per_m": 15.00, "context_window": 1_000_000, "released": "2026-03-05"},
    {"id": "google/gemini-3.1-pro-preview", "short": "b02_gemini31_pro", "name": "Gemini 3.1 Pro", "group": "search_augmented", "arch": "proprietary/Google-search/multimodal", "corpus": "Western", "market_share": 21.5, "max_tokens": MAX_TOKENS, "cost_input_per_m": 2.00, "cost_output_per_m": 12.00, "context_window": 1_000_000, "released": "2026-02-19"},
    {"id": "anthropic/claude-sonnet-4.6", "short": "b03_claude_sonnet", "name": "Claude Sonnet 4.6", "group": "parametric_only", "arch": "constitutional-AI", "corpus": "Western", "market_share": 2.0, "max_tokens": MAX_TOKENS, "cost_input_per_m": 3.00, "cost_output_per_m": 15.00, "context_window": 1_000_000, "released": "2026-02-17"},
    {"id": "x-ai/grok-4.20", "short": "b04_grok420", "name": "Grok 4.20", "group": "search_augmented", "arch": "proprietary/multi-agent/X-social", "corpus": "Western+X", "market_share": 3.4, "max_tokens": MAX_TOKENS, "cost_input_per_m": 2.00, "cost_output_per_m": 6.00, "context_window": 2_000_000, "released": "2026-03-31"},
    {"id": "deepseek/deepseek-chat-v3-0324", "short": "b05_deepseek_v32", "name": "DeepSeek V3.2", "group": "non_english_corpus", "arch": "MoE/sparse-attention/MIT-license", "corpus": "Chinese-primary", "market_share": 4.8, "max_tokens": MAX_TOKENS, "cost_input_per_m": 0.25, "cost_output_per_m": 0.89, "context_window": 164_000, "released": "2026-03-24"},
    {"id": "qwen/qwen3.5-plus", "short": "b06_qwen35_plus", "name": "Qwen 3.5 Plus", "group": "non_english_corpus", "arch": "proprietary/Alibaba-ecosystem", "corpus": "Chinese-primary", "market_share": 0.5, "max_tokens": MAX_TOKENS, "cost_input_per_m": 0.40, "cost_output_per_m": 2.00, "context_window": 1_000_000, "released": "2026-03"},
    {"id": "meta-llama/llama-4-maverick", "short": "b07_llama4_maverick", "name": "Llama 4 Maverick", "group": "parametric_only", "arch": "open-weight-MoE/17B-active/128-experts", "corpus": "Western", "market_share": 0.0, "max_tokens": MAX_TOKENS, "cost_input_per_m": 0.20, "cost_output_per_m": 0.60, "context_window": 128_000, "released": "2025-04"},
    {"id": "mistralai/mistral-large-2512", "short": "b08_mistral_large3", "name": "Mistral Large 3", "group": "parametric_only", "arch": "proprietary/EU-headquartered/multimodal", "corpus": "European", "market_share": 0.3, "max_tokens": MAX_TOKENS, "cost_input_per_m": 1.60, "cost_output_per_m": 5.00, "context_window": 256_000, "released": "2026-03"},
    {"id": "google/gemini-3-flash-preview", "short": "b09_gemini3_flash", "name": "Gemini 3 Flash", "group": "search_augmented", "arch": "proprietary/Google-search/budget-tier", "corpus": "Western", "market_share": 0.0, "max_tokens": MAX_TOKENS, "cost_input_per_m": 0.50, "cost_output_per_m": 3.00, "context_window": 1_000_000, "released": "2025-12-17"},
    {"id": "z-ai/glm-5", "short": "b10_glm5", "name": "GLM-5", "group": "non_english_corpus", "arch": "open-weight/sparse-attention/Chinese-independent", "corpus": "Chinese-primary", "market_share": 0.2, "max_tokens": MAX_TOKENS, "cost_input_per_m": 0.95, "cost_output_per_m": 3.00, "context_window": 204_000, "released": "2026-02"},
]

SUBSTITUTIONS = {
    "openai/gpt-5.4": "openai/gpt-5",
    "google/gemini-3.1-pro-preview": "google/gemini-3-pro-preview",
    "x-ai/grok-4.20": "x-ai/grok-4-fast",
    "qwen/qwen3.5-plus": "qwen/qwen3-235b-a22b",
    "z-ai/glm-5": "z-ai/glm-4.7",
}

QUERIES = [
    # ── Original 4 Categories (Q01-Q20) ──

    # B2B SaaS (AIO trigger ~70%)
    {"id": "Q01", "category": "b2b_saas", "text": "What is the best CRM software for a B2B company with 50 to 200 employees?"},
    {"id": "Q02", "category": "b2b_saas", "text": "What project management tools do you recommend for a remote software development team of about 30 people?"},
    {"id": "Q03", "category": "b2b_saas", "text": "What are the top enterprise email marketing platforms for a mid-market e-commerce company?"},
    {"id": "Q04", "category": "b2b_saas", "text": "Which cloud-based accounting software is best for a growing SaaS startup with 10 million in annual revenue?"},
    {"id": "Q05", "category": "b2b_saas", "text": "What are the leading customer data platforms for B2B companies that need to unify sales and marketing data?"},

    # Healthcare / Wellness (AIO trigger ~43-88%)
    {"id": "Q06", "category": "healthcare_wellness", "text": "What are the best telemedicine platforms for a small medical practice with five physicians?"},
    {"id": "Q07", "category": "healthcare_wellness", "text": "Which mental health apps are most effective for managing anxiety, based on clinical evidence?"},
    {"id": "Q08", "category": "healthcare_wellness", "text": "What are the top electronic health record systems for independent clinics in the United States?"},
    {"id": "Q09", "category": "healthcare_wellness", "text": "What are the leading fitness tracking wearables for heart rate monitoring accuracy and sleep tracking?"},
    {"id": "Q10", "category": "healthcare_wellness", "text": "Which supplement brands are most trusted for quality and third-party testing transparency?"},

    # Consumer Electronics (AIO trigger ~18%)
    {"id": "Q11", "category": "consumer_electronics", "text": "What are the best noise-cancelling headphones under 400 dollars in 2026?"},
    {"id": "Q12", "category": "consumer_electronics", "text": "Which laptop is best for a college student who needs it for both coursework and light gaming?"},
    {"id": "Q13", "category": "consumer_electronics", "text": "What are the top robot vacuum cleaners for a home with pets and hardwood floors?"},
    {"id": "Q14", "category": "consumer_electronics", "text": "What are the best mirrorless cameras for a beginner photographer with a budget of 1500 dollars?"},
    {"id": "Q15", "category": "consumer_electronics", "text": "Which smart home hub integrates best with the widest range of devices in 2026?"},

    # Local Services (AIO trigger <8% — control)
    {"id": "Q16", "category": "local_services", "text": "What should I look for when choosing a local plumber for a kitchen renovation?"},
    {"id": "Q17", "category": "local_services", "text": "How do I find a reliable house cleaning service in a mid-sized city?"},
    {"id": "Q18", "category": "local_services", "text": "What are the most important factors when selecting a local daycare center for a toddler?"},
    {"id": "Q19", "category": "local_services", "text": "How do I evaluate and choose a good local auto mechanic for regular car maintenance?"},
    {"id": "Q20", "category": "local_services", "text": "What questions should I ask when hiring a local landscaping company for yard design?"},

    # ── NEW: 4 Expansion Categories (Q21-Q40) ──

    # Financial Services / Fintech (AIO trigger ~63%)
    {"id": "Q21", "category": "financial_services", "text": "What is the best business credit card for a startup spending 20,000 dollars per month on software and travel?"},
    {"id": "Q22", "category": "financial_services", "text": "Which payroll platforms are best for a company with 100 employees across multiple US states?"},
    {"id": "Q23", "category": "financial_services", "text": "What are the top robo-advisors for a mid-career professional looking to invest 200,000 dollars?"},
    {"id": "Q24", "category": "financial_services", "text": "What are the best invoicing and payment processing platforms for a freelance consulting business?"},
    {"id": "Q25", "category": "financial_services", "text": "Which business banking accounts offer the best combination of no fees, high APY, and integration with accounting software?"},

    # CPG / Consumer Packaged Goods (AIO trigger ~25%, fastest growing)
    {"id": "Q26", "category": "cpg", "text": "What are the best protein bars for someone focused on high protein and low sugar with clean ingredients?"},
    {"id": "Q27", "category": "cpg", "text": "Which laundry detergent brands are most effective while also being environmentally friendly?"},
    {"id": "Q28", "category": "cpg", "text": "What are the top premium coffee brands available for home brewing in terms of quality and value?"},
    {"id": "Q29", "category": "cpg", "text": "What are the best natural deodorant brands that actually work for heavy perspiration?"},
    {"id": "Q30", "category": "cpg", "text": "Which dog food brands are most recommended by veterinarians for adult medium-sized breeds?"},

    # Enterprise Software — Security / Cloud / Data (AIO trigger ~70%)
    {"id": "Q31", "category": "enterprise_software", "text": "What are the best SIEM platforms for a mid-market company with 500 endpoints and a small security team?"},
    {"id": "Q32", "category": "enterprise_software", "text": "What are the top cloud infrastructure providers for a company migrating from on-premises to a hybrid cloud setup?"},
    {"id": "Q33", "category": "enterprise_software", "text": "Which business intelligence and data visualization platforms are best for a non-technical executive team?"},
    {"id": "Q34", "category": "enterprise_software", "text": "What are the leading identity and access management solutions for a company with 2,000 employees using SSO?"},
    {"id": "Q35", "category": "enterprise_software", "text": "Which endpoint detection and response platforms provide the best protection for a fully remote workforce?"},

    # Travel & Hospitality (AIO trigger ~30%)
    {"id": "Q36", "category": "travel_hospitality", "text": "What are the best hotel loyalty programs for a frequent business traveler doing 50 nights per year?"},
    {"id": "Q37", "category": "travel_hospitality", "text": "Which airlines offer the best business class experience on transatlantic routes in 2026?"},
    {"id": "Q38", "category": "travel_hospitality", "text": "What are the top travel booking platforms for finding the best deals on international flights?"},
    {"id": "Q39", "category": "travel_hospitality", "text": "What are the best all-inclusive resort chains in the Caribbean for a family with young children?"},
    {"id": "Q40", "category": "travel_hospitality", "text": "Which travel credit cards offer the best combination of sign-up bonus, lounge access, and no foreign transaction fees?"},
]

RUN_A_MODELS = {
    "a1_gemini": {"id": "google/gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro", "max_tokens": 65536},
    "a2_chatgpt": {"id": "openai/o3", "name": "o3", "max_tokens": 65536, "fallback": "openai/gpt-5.4"},
    "a3_claude": {"id": "anthropic/claude-opus-4-6", "name": "Claude Opus 4.6", "max_tokens": 32768},
}

def get_search_augmented():
    return [m for m in MODELS if m["group"] == "search_augmented"]

def get_parametric_only():
    return [m for m in MODELS if m["group"] == "parametric_only"]

def get_non_english():
    return [m for m in MODELS if m["group"] == "non_english_corpus"]

def get_model_by_short(short):
    return next((m for m in MODELS if m["short"] == short), None)

def estimate_total_cost():
    """Estimate total experiment cost (with query batching)."""
    total = 0
    n_batches = -(-len(QUERIES) // QUERY_BATCH_SIZE)  # ceil division
    prompt_tokens_per_batch = 400  # ~preamble + 8 queries
    output_tokens_per_batch = 2000  # ~8 queries × 250 words
    calls_per_model = n_batches * K_TRIALS
    for m in MODELS:
        cost_per_call = (prompt_tokens_per_batch / 1e6) * m["cost_input_per_m"] + \
                        (output_tokens_per_batch / 1e6) * m["cost_output_per_m"]
        total += cost_per_call * calls_per_model
    return round(total, 2)
