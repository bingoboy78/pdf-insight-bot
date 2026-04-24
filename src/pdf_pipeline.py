import traceback
import os
from .extract import extract_text_from_pdf
from .chunking import chunk_text
from .summarize import prepare_map_prompts, synthesize_final_report, generate_summary_and_insights
from .storage import JobStorage
from .config import settings

def process_pdf(job_id: str, filename: str, params: dict, volume=None, map_fn=None):
    """Orchestrates the PDF processing and insight extraction workflow."""
    storage = JobStorage(settings.JOBS_DIR, volume=volume)
    storage.update_status(job_id, "extracting")
    
    try:
        pdf_path = storage.get_input_pdf_path(job_id)
        
        # 1. Extraction Phase
        extraction_result = extract_text_from_pdf(pdf_path)
        storage.save_extracted_text(job_id, extraction_result["text"])
        
        storage.update_status(job_id, "chunking")
        
        # 2. Chunking Phase
        chunks = chunk_text(extraction_result["text"])
        
        # 3. LLM Insights & Synthesis Phase
        if map_fn:
            total_chunks = len(chunks)
            storage.update_status(job_id, f"summarizing: parallel (0/{total_chunks})")
            prompts = prepare_map_prompts(chunks)
            
            # Map prompts across Modal workers
            # We iterate through the results to update progress as they finish
            chunk_summaries = []
            
            for i, res in enumerate(map_fn(prompts, order_outputs=True)):
                if not res["success"]:
                    raise Exception(f"Ошибка в части {i+1}: {res['error']}")
                
                chunk_summaries.append(res["data"])
                storage.update_status(job_id, f"summarizing: parallel ({i+1}/{total_chunks})")
            
            # Save intermediate chunks in case synthesis fails
            try:
                storage._write_json(os.path.join(storage._job_dir(job_id), "chunks.json"), {"chunks": chunk_summaries})
            except Exception as e:
                print(f"Warning: Failed to save chunk summaries: {e}")
                
            storage.update_status(job_id, "summarizing: финальная сборка")
            final_result = synthesize_final_report(chunk_summaries, filename, params, extraction_result)
        else:
            def update_progress(msg):
                storage.update_status(job_id, msg)
                
            final_result = generate_summary_and_insights(
                chunks, filename, params, extraction_result, progress_cb=update_progress
            )
        
        # 4. Save Final Artifacts
        storage.save_json(job_id, final_result)
        if "summary" in final_result and "full_markdown" in final_result["summary"]:
            storage.save_markdown(job_id, final_result["summary"]["full_markdown"])
            
        storage.update_status(job_id, "completed")
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error in job {job_id}: {traceback.format_exc()}")
        storage.save_error(job_id, error_msg)
