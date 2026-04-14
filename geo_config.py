"""
GEO Cross-Model Brand Visibility Study — Configuration
Version: 2026.4.15-r3 (Post Red Team Roster Revision)

CHANGELOG from r2:
  - 8 of 10 models replaced with current-generation equivalents
  - GPT-4o → GPT-5.4, Gemini 2.5 Flash → Gemini 3.1 Pro, Grok 2 → Grok 4.20
  - Command R+ and Gemma 3 27B removed (no market share / not frontier)
  - Added GLM-5 (third Chinese-corpus model for H3 triangulation)
  - Added Gemini 3 Flash (within-Google tier comparison)
  - All OpenRouter model IDs verified against April 2026 catalog
"""

__version__ = "3.0.0"
__component__ = "geo_config"

EXPERIMENT_NAME = "Cross-Model GEO Brand Visibility Study"
VERSION = "3.0-academic"
TEMPERATURE = 0.3
TOP_P = 0.95
MAX_TOKENS = 16384
K_TRIALS = 5
SEARCH_SPACING_SECONDS = 3600

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
    {"id": "Q01", "category": "b2b_saas", "text": "What is the best CRM software for a B2B company with 50 to 200 employees?"},
    {"id": "Q02", "category": "b2b_saas", "text": "What project management tools do you recommend for a remote software development team of about 30 people?"},
    {"id": "Q03", "category": "b2b_saas", "text": "Compare the top enterprise email marketing platforms for a mid-market e-commerce company."},
    {"id": "Q04", "category": "b2b_saas", "text": "Which cloud-based accounting software is best for a growing SaaS startup with 10 million in annual revenue?"},
    {"id": "Q05", "category": "b2b_saas", "text": "What are the leading customer data platforms for B2B companies that need to unify sales and marketing data?"},
    {"id": "Q06", "category": "healthcare_wellness", "text": "What are the best telemedicine platforms for a small medical practice with five physicians?"},
    {"id": "Q07", "category": "healthcare_wellness", "text": "Which mental health apps are most effective for managing anxiety, based on clinical evidence?"},
    {"id": "Q08", "category": "healthcare_wellness", "text": "What are the top electronic health record systems for independent clinics in the United States?"},
    {"id": "Q09", "category": "healthcare_wellness", "text": "Compare the leading fitness tracking wearables for heart rate monitoring accuracy and sleep tracking."},
    {"id": "Q10", "category": "healthcare_wellness", "text": "Which supplement brands are most trusted for quality and third-party testing transparency?"},
    {"id": "Q11", "category": "consumer_electronics", "text": "What are the best noise-cancelling headphones under 400 dollars in 2026?"},
    {"id": "Q12", "category": "consumer_electronics", "text": "Which laptop is best for a college student who needs it for both coursework and light gaming?"},
    {"id": "Q13", "category": "consumer_electronics", "text": "Compare the top robot vacuum cleaners for a home with pets and hardwood floors."},
    {"id": "Q14", "category": "consumer_electronics", "text": "What are the best mirrorless cameras for a beginner photographer with a budget of 1500 dollars?"},
    {"id": "Q15", "category": "consumer_electronics", "text": "Which smart home hub integrates best with the widest range of devices in 2026?"},
    {"id": "Q16", "category": "local_services", "text": "What should I look for when choosing a local plumber for a kitchen renovation?"},
    {"id": "Q17", "category": "local_services", "text": "How do I find a reliable house cleaning service in a mid-sized city?"},
    {"id": "Q18", "category": "local_services", "text": "What are the most important factors when selecting a local daycare center for a toddler?"},
    {"id": "Q19", "category": "local_services", "text": "How do I evaluate and choose a good local auto mechanic for regular car maintenance?"},
    {"id": "Q20", "category": "local_services", "text": "What questions should I ask when hiring a local landscaping company for yard design?"},
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
    """Estimate total experiment cost for 20 queries x 10 models x 5 trials."""
    total = 0
    input_tokens, output_tokens = 2000, 8000
    calls_per_model = len(QUERIES) * K_TRIALS
    for m in MODELS:
        cost_per_call = (input_tokens / 1e6) * m["cost_input_per_m"] + (output_tokens / 1e6) * m["cost_output_per_m"]
        total += cost_per_call * calls_per_model
    return round(total, 2)
