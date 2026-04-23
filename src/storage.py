import os
import json

class JobStorage:
    """Handles persistence of artifacts across the Modal Volume for each job."""
    
    def __init__(self, base_path: str = "/data/jobs", volume=None):
        self.base_path = base_path
        self.volume = volume
        os.makedirs(self.base_path, exist_ok=True)
        
    def _sync_read(self):
        if self.volume and hasattr(self.volume, "reload"):
            self.volume.reload()

    def _sync_write(self):
        if self.volume and hasattr(self.volume, "commit"):
            self.volume.commit()
                
    def _job_dir(self, job_id: str):
        return os.path.join(self.base_path, job_id)
        
    def init_job(self, job_id: str):
        os.makedirs(self._job_dir(job_id), exist_ok=True)
        self.update_status(job_id, "initialized")
        
    def update_status(self, job_id: str, status: str):
        meta = self.get_status(job_id)
        if meta.get("status") == "not_found":
            meta = {}
        meta["status"] = status
        self._write_json(os.path.join(self._job_dir(job_id), "meta.json"), meta)
        
    def get_status(self, job_id: str):
        meta_path = os.path.join(self._job_dir(job_id), "meta.json")
        meta = self._read_json(meta_path)
        if not meta:
            return {"status": "not_found"}
        return {"job_id": job_id, "status": meta.get("status"), "error": meta.get("error")}
        
    def save_input_pdf(self, job_id: str, data: bytes):
        with open(os.path.join(self._job_dir(job_id), "input.pdf"), "wb") as f:
            f.write(data)
        self._sync_write()
            
    def get_input_pdf_path(self, job_id: str) -> str:
        self._sync_read()
        return os.path.join(self._job_dir(job_id), "input.pdf")
        
    def save_extracted_text(self, job_id: str, text: str):
        with open(os.path.join(self._job_dir(job_id), "extracted.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        self._sync_write()
            
    def save_json(self, job_id: str, data: dict):
        self._write_json(os.path.join(self._job_dir(job_id), "result.json"), data)
        
    def save_markdown(self, job_id: str, md: str):
        with open(os.path.join(self._job_dir(job_id), "summary.md"), "w", encoding="utf-8") as f:
            f.write(md)
        self._sync_write()
            
    def get_markdown(self, job_id: str) -> str:
        self._sync_read()
        path = os.path.join(self._job_dir(job_id), "summary.md")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
            
    def save_error(self, job_id: str, error: str):
        meta_path = os.path.join(self._job_dir(job_id), "meta.json")
        meta = self._read_json(meta_path) or {}
        meta["error"] = error
        meta["status"] = "failed"
        self._write_json(meta_path, meta)
        
    def get_result(self, job_id: str):
        res_path = os.path.join(self._job_dir(job_id), "result.json")
        return self._read_json(res_path)
        
    def _read_json(self, path: str):
        self._sync_read()
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
            
    def _write_json(self, path: str, data: dict):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._sync_write()
