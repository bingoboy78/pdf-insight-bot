import json
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from .config import settings
from .prompts import SYSTEM_PROMPT, MAP_PROMPT, REDUCE_PROMPT
from openai import OpenAI, RateLimitError, APITimeoutError
from anthropic import Anthropic

def prepare_map_prompts(chunks: list) -> list:
    total = len(chunks)
    prompts = []
    for i, chunk in enumerate(chunks):
        prompt = MAP_PROMPT.format(text=chunk, chunk_index=i+1, total_chunks=total)
        prompts.append(prompt)
    return prompts

def synthesize_final_report(chunk_summaries: list, filename: str, params: dict, extraction: dict) -> dict:
    provider = settings.LLM_PROVIDER.lower()
    
    # Reduce phase: combine insights and write final markdown
    combined_summaries = json.dumps(chunk_summaries, ensure_ascii=False)
    reduce_prompt = REDUCE_PROMPT.format(
        summaries=combined_summaries, 
        filename=filename,
        max_length=params.get("max_summary_length", "medium"),
        extract_quotes=params.get("extract_quotes", True)
    )
    
    final_json = call_llm(reduce_prompt, provider, is_json=True)
    
    # Structure output
    output = {
        "document_title": final_json.get("document_title", filename),
        "source_language": "en",
        "output_language": params.get("translate_to", "ru"),
        "page_count": extraction.get("page_count", 0),
        "summary": {
            "short": final_json.get("short_summary", ""),
            "full_markdown": final_json.get("full_markdown", "")
        },
        "insights": final_json.get("insights", {}),
        "sections": final_json.get("sections", []),
        "processing": {
            "used_ocr": extraction.get("used_ocr", False),
            "chunk_count": len(chunk_summaries),
            "model": settings.LLM_MODEL,
            "provider": provider
        }
    }
    return output

def generate_summary_and_insights(chunks: list, filename: str, params: dict, extraction: dict, progress_cb=None) -> dict:
    # Legacy sequential version, or just a wrapper
    prompts = prepare_map_prompts(chunks)
    chunk_summaries = []
    total = len(prompts)
    for i, p in enumerate(prompts):
        if progress_cb:
            progress_cb(f"summarizing: {i+1}/{total}")
        res = call_llm(p, settings.LLM_PROVIDER.lower(), is_json=True)
        chunk_summaries.append(res)
    
    if progress_cb:
        progress_cb("summarizing: финальная сборка")
    return synthesize_final_report(chunk_summaries, filename, params, extraction)

def call_llm(prompt: str, provider: str, is_json: bool = False, max_retries: int = 5) -> dict:
    """Call LLM with manual retry logic that respects 429 rate limits."""
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            content = _call_llm_once(prompt, provider, is_json)
            
            if is_json:
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                try:
                    return json.loads(content.strip())
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON. Raw output:\n{content}")
                    return {"error": "JSON parse error", "raw": content}
            
            return {"text": content}
            
        except RateLimitError as e:
            last_error = e
            wait_time = 60  # Wait 60s on rate limit
            print(f"[call_llm] Attempt {attempt}/{max_retries}: Rate limited (429). Waiting {wait_time}s...")
            time.sleep(wait_time)
            
        except APITimeoutError as e:
            last_error = e
            wait_time = min(10 * attempt, 30)
            print(f"[call_llm] Attempt {attempt}/{max_retries}: Timeout. Waiting {wait_time}s...")
            time.sleep(wait_time)
            
        except Exception as e:
            last_error = e
            wait_time = min(5 * attempt, 20)
            print(f"[call_llm] Attempt {attempt}/{max_retries}: {type(e).__name__}: {e}. Waiting {wait_time}s...")
            time.sleep(wait_time)
    
    raise last_error


def _call_llm_once(prompt: str, provider: str, is_json: bool) -> str:
    """Single LLM call without retry logic."""
    system_msg = SYSTEM_PROMPT
    if is_json:
        system_msg += "\n\nYou MUST return valid JSON. Do NOT wrap it in markdown codeblocks like ```json."
        
    if provider == "openai":
        client = OpenAI(api_key=settings.LLM_API_KEY, timeout=120.0)
        response = client.chat.completions.create(
            model=settings.LLM_MODEL or "gpt-4o",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"} if is_json else None
        )
        return response.choices[0].message.content
        
    elif provider == "openrouter":
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.LLM_API_KEY,
            timeout=120.0
        )
        response = client.chat.completions.create(
            model=settings.LLM_MODEL or "google/gemini-2.0-flash-lite-preview-02-05:free",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    elif provider == "nvidia":
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.LLM_API_KEY,
            timeout=120.0
        )
        response = client.chat.completions.create(
            model=settings.LLM_MODEL or "meta/llama-3.1-70b-instruct",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    elif provider == "anthropic":
        client = Anthropic(api_key=settings.LLM_API_KEY, timeout=120.0)
        prompt_with_formatting = f"{prompt}\n\nReturn ONLY valid JSON." if is_json else prompt
        response = client.messages.create(
            model=settings.LLM_MODEL or "claude-3-5-sonnet-20241022",
            max_tokens=8192,
            system=system_msg,
            messages=[
                {"role": "user", "content": prompt_with_formatting}
            ]
        )
        return response.content[0].text
    else:
        raise ValueError(f"Unsupported provider: {provider}")

