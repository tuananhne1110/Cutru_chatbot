import os
import requests
import json
from config import embedding_model

CHUTES_API_KEY = os.getenv("CHUTES_API_KEY")
CHUTES_API_URL = "https://llm.chutes.ai/v1/chat/completions"


def call_llm_stream(prompt, model="deepseek-ai/DeepSeek-V3-0324", max_tokens=1000, temperature=0.3):
    headers = {
        "Authorization": f"Bearer {CHUTES_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True
    }
    # print("[call_llm_stream] Sending payload:", json.dumps(payload, ensure_ascii=False))
    with requests.post(CHUTES_API_URL, headers=headers, json=payload, stream=True, timeout=120) as r:
        for line in r.iter_lines():
            if line:
                try:
                    decoded = line.decode("utf-8")
                    if decoded.startswith("data:"):
                        decoded = decoded[len("data:"):].strip()
                    data = json.loads(decoded)
                    # print("[call_llm_stream] Received:", data)
                    if "choices" in data and data["choices"]:
                        chunk = data["choices"][0].get("delta", {}).get("content", None)
                        if chunk is not None and chunk != "":
                            yield f"data: {{\"choices\":[{{\"delta\":{{\"content\":{json.dumps(chunk, ensure_ascii=False)}}}}}]}}\n"
                except Exception as e:
                    print("[call_llm_stream] Exception parsing line:", line, e)
                    continue

def call_llm_full(prompt, model="deepseek-ai/DeepSeek-V3-0324", max_tokens=1000, temperature=0.3):
    headers = {
        "Authorization": f"Bearer {CHUTES_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    # print("[call_llm_full] Sending payload:", json.dumps(payload, ensure_ascii=False))
    response = requests.post(CHUTES_API_URL, headers=headers, json=payload, timeout=120)
    print("[call_llm_full] Status:", response.status_code)
    print("[call_llm_full] Response:", response.text)
    if response.status_code != 200:
        raise Exception(f"LLM API error: {response.status_code} - {response.text}")
    result = response.json()
    return result['choices'][0]['message']['content'] 