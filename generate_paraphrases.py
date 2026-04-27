"""
generate_paraphrases.py — Stage 3.2 paraphrase generation
Model: meta-llama/llama-3.3-70b-instruct via OpenRouter (held-out paraphraser)
Output: data/paraphrases.json (120 entries) + SHA-256 printed to stdout
"""

import json, os, hashlib, time, re, urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent
ENV_FILE = BASE.parent / ".env"
METADATA = BASE / "data" / "experiment_metadata.json"
OUTPUT = BASE / "data" / "paraphrases.json"
MODEL = "meta-llama/llama-3.3-70b-instruct"

def load_env(path):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

env = load_env(ENV_FILE)
KEY = env.get("OPENROUTER_API_KEY")
if not KEY:
    raise RuntimeError("OPENROUTER_API_KEY not found in .env")

def make_prompt(query_text):
    return (
        "Paraphrase the following search query in exactly 3 different ways. "
        "Output only valid JSON with no markdown fences: "
        '{"paraphrase_1": "...", "paraphrase_2": "...", "paraphrase_3": "..."}\n\n'
        "Rules:\n"
        "1. Preserve semantic intent (same brands should be valid answers)\n"
        "2. Vary surface phrasing meaningfully\n"
        "3. Stay natural, like a real user typed it\n"
        "4. Keep similar length (+-30%)\n\n"
        "Query: " + query_text
    )

def call_openrouter(query_text, retries=3):
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": make_prompt(query_text)}],
        "temperature": 0.7,
        "max_tokens": 400,
    }).encode()
    headers = {
        "Authorization": "Bearer " + KEY,
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/CAREInstitute/geo-v2",
        "X-Title": "GEO v2 paraphrase generation",
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=payload, headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise

def parse_paraphrases(content):
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()
    return json.loads(content)

with open(METADATA) as f:
    metadata = json.load(f)

queries = metadata["queries"]
results = []
errors = []

print(f"Starting paraphrase generation: {len(queries)} queries x 3 paraphrases")
print(f"Model: {MODEL}")
print(f"Output: {OUTPUT}\n")

for i, q in enumerate(queries):
    qid = q["id"]
    qtext = q["text"]
    qcat = q["category"]
    print(f"[{i+1:02d}/40] {qid} ({qcat}): {qtext[:60]}...")
    try:
        content = call_openrouter(qtext)
        parsed = parse_paraphrases(content)
        ts = datetime.now(timezone.utc).isoformat()
        for pidx in range(1, 4):
            key2 = f"paraphrase_{pidx}"
            results.append({
                "original_id": qid,
                "paraphrase_id": f"{qid}_P{pidx}",
                "original_text": qtext,
                "paraphrase_text": parsed[key2],
                "category": qcat,
                "generator_model": MODEL,
                "generation_timestamp": ts,
                "review_flag": False,
            })
        print(f"  v 3 paraphrases generated")
    except Exception as e:
        print(f"  x ERROR: {e}")
        errors.append({"query_id": qid, "error": str(e)})
    time.sleep(0.5)

with open(OUTPUT, "w") as f:
    json.dump(results, f, indent=2)

sha = hashlib.sha256(open(OUTPUT, "rb").read()).hexdigest()
print(f"\nDone. {len(results)} paraphrases written.")
print(f"SHA-256: {sha}")
if errors:
    print(f"ERRORS ({len(errors)}): {errors}")
else:
    print("No errors.")
