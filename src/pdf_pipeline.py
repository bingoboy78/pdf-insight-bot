import traceback
from .extract import extract_text_from_pdf
from .chunking import chunk_text
from .summarize import generate_summary_and_insights
from .storage import JobStorage
from .config import settings

def process_pdf(job_id: str, filename: str, params: dict, volume=None):
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
        
        storage.update_status(job_id, "summarizing")
        
        # 3. LLM Insights & Synthesis Phase
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
