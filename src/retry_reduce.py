import os
import json
import modal
from .config import settings
from .summarize import synthesize_final_report
from .storage import JobStorage

app = modal.App("pdf-insight-retry")
image = modal.Image.debian_slim(python_version="3.10").pip_install("openai", "anthropic", "tenacity", "google-generativeai")
storage_vol = modal.Volume.from_name(settings.VOLUME_NAME, create_if_missing=True)

@app.function(
    image=image,
    volumes={settings.VOLUME_PATH: storage_vol},
    timeout=1800,
    secrets=[modal.Secret.from_name("pdf-insight-secrets")]
)
def retry_job(job_id: str):
    storage = JobStorage(base_path=settings.JOBS_DIR, volume=storage_vol)
    
    chunks_path = os.path.join(storage._job_dir(job_id), "chunks.json")
    if not os.path.exists(chunks_path):
        print(f"Chunks not found at {chunks_path}")
        return
        
    chunks_data = storage._read_json(chunks_path)
    if not chunks_data or "chunks" not in chunks_data:
        print("Invalid chunks format.")
        return
        
    chunk_summaries = chunks_data["chunks"]
    
    meta = storage.get_status(job_id)
    result_path = os.path.join(storage._job_dir(job_id), "result.json")
    existing_result = storage._read_json(result_path) or {}
    filename = existing_result.get("document_title", "document.pdf")
    
    params = {"translate_to": "ru", "max_summary_length": "medium", "extract_quotes": True}
    extraction_result = {"page_count": existing_result.get("page_count", 0), "used_ocr": False}
    
    storage.update_status(job_id, "summarizing: финальная сборка (retry)")
    print(f"Retrying final report synthesis for {job_id}...")
    final_result = synthesize_final_report(chunk_summaries, filename, params, extraction_result)
    
    storage.save_json(job_id, final_result)
    if "summary" in final_result and "full_markdown" in final_result["summary"]:
        storage.save_markdown(job_id, final_result["summary"]["full_markdown"])
        print("Success! Summary generated.")
    else:
        print("Warning: final_result did not contain full_markdown!")
        
    storage.update_status(job_id, "completed")

@app.local_entrypoint()
def main(job_id: str):
    retry_job.remote(job_id)
