import modal
from fastapi import FastAPI, UploadFile, Form, File, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse
import uuid
import os

from .config import settings
from .storage import JobStorage

# Define the image and other resources
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("tesseract-ocr", "tesseract-ocr-rus", "libtesseract-dev", "poppler-utils")
    .pip_install(
        "fastapi[standard]",
        "pymupdf",
        "pytesseract",
        "pdf2image",
        "openai",
        "anthropic",
        "tenacity"
    )
)

app = modal.App("pdf-insight-bot")
volume = modal.Volume.from_name(settings.VOLUME_NAME, create_if_missing=True)

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("pdf-insight-secrets")],
    volumes={settings.VOLUME_PATH: volume},
    timeout=600, # 10 mins per chunk
    max_containers=5  # Google Gemini has generous rate limits
)
def summarize_chunk(prompt: str):
    from .summarize import call_llm
    from .config import settings
    try:
        return {"success": True, "data": call_llm(prompt, settings.LLM_PROVIDER.lower(), is_json=True)}
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        # Extract the real cause from RetryError
        real_error = str(e)
        if hasattr(e, '__cause__') and e.__cause__:
            real_error = f"{type(e.__cause__).__name__}: {e.__cause__}"
        elif hasattr(e, 'last_attempt'):
            try:
                real_error = str(e.last_attempt.exception())
            except:
                pass
        print(f"[summarize_chunk] FAILED: {real_error}\n{tb}")
        return {"success": False, "error": real_error, "traceback": tb}

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("pdf-insight-secrets")],
    volumes={settings.VOLUME_PATH: volume},
    timeout=1800  # 30 mins
)
def process_pdf_job(job_id: str, filename: str):
    from .pdf_pipeline import process_pdf
    process_pdf(job_id, filename, {}, volume=volume, map_fn=summarize_chunk.map)

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("pdf-insight-secrets")],
    volumes={settings.VOLUME_PATH: volume}
)
@modal.asgi_app()
def api():
    web_app = FastAPI(title="PDF Insight Bot API")
    storage = JobStorage(base_path=settings.JOBS_DIR, volume=volume)

    @web_app.get("/", response_class=HTMLResponse)
    async def index():
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>PDF Insight Bot 📚</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    background-color: #f4f7f6;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                    width: 100%;
                    max-width: 500px;
                }
                h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
                .upload-area {
                    border: 2px dashed #3498db;
                    padding: 30px;
                    text-align: center;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: background 0.3s;
                    display: block;
                }
                .upload-area:hover { background: #ebf5fb; }
                input[type="file"] { display: none; }
                .btn {
                    display: block;
                    width: 100%;
                    background: #3498db;
                    color: white;
                    border: none;
                    padding: 15px;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: bold;
                    cursor: pointer;
                    margin-top: 20px;
                    transition: background 0.3s;
                }
                .btn:hover { background: #2980b9; }
                .btn:disabled { background: #bdc3c7; cursor: not-allowed; }
                #status { 
                    margin-top: 30px; 
                    padding: 15px; 
                    border-radius: 6px; 
                    display: none; 
                    border: 1px solid #ddd;
                }
                .loading { color: #3498db; font-weight: bold; }
                .success { color: #27ae60; font-weight: bold; }
                .error { color: #e74c3c; font-weight: bold; }
                .links { margin-top: 15px; }
                .links a { 
                    display: block; 
                    margin: 10px 0; 
                    color: #3498db; 
                    text-decoration: none;
                    padding: 8px;
                    background: #f8f9fa;
                    border-radius: 4px;
                    text-align: center;
                }
                .links a:hover { background: #e9ecef; }
                #fileName { margin-top: 10px; color: #7f8c8d; font-size: 0.9em; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>PDF Insight Bot 📚</h1>
                <p style="text-align:center; color:#7f8c8d;">Загрузите PDF для создания русскоязычного конспекта.</p>
                
                <form id="uploadForm">
                    <label class="upload-area" id="dropZone">
                        <span id="uploadText">Нажмите для выбора PDF</span>
                        <input type="file" name="file" id="fileInput" accept=".pdf" required>
                        <div id="fileName"></div>
                    </label>
                    <button type="submit" class="btn" id="submitBtn">Запустить анализ</button>
                </form>

                <div id="status">
                    <div id="statusTitle">Статус:</div>
                    <div id="statusContent"></div>
                    <div id="links" class="links"></div>
                </div>
            </div>

            <script>
                const form = document.getElementById('uploadForm');
                const fileInput = document.getElementById('fileInput');
                const fileNameDisplay = document.getElementById('fileName');
                const submitBtn = document.getElementById('submitBtn');
                const statusDiv = document.getElementById('status');
                const statusContent = document.getElementById('statusContent');
                const linksDiv = document.getElementById('links');

                fileInput.onchange = () => {
                    if (fileInput.files.length > 0) {
                        fileNameDisplay.textContent = 'Выбран файл: ' + fileInput.files[0].name;
                        document.getElementById('uploadText').textContent = 'Файл выбран';
                    }
                };

                form.onsubmit = async (e) => {
                    e.preventDefault();
                    const formData = new FormData(form);
                    
                    submitBtn.disabled = true;
                    statusDiv.style.display = 'block';
                    statusContent.innerHTML = '<p class="loading">Загрузка файла на сервер...</p>';
                    linksDiv.innerHTML = '';
                    
                    try {
                        const response = await fetch('/submit', {
                            method: 'POST',
                            body: formData
                        });
                        const data = await response.json();
                        
                        if (data.job_id) {
                            checkStatus(data.job_id);
                        } else {
                            throw new Error(data.detail || 'Неизвестная ошибка');
                        }
                    } catch (err) {
                        statusContent.innerHTML = '<p class="error">Ошибка: ' + err.message + '</p>';
                        submitBtn.disabled = false;
                    }
                };

                async function checkStatus(jobId) {
                    const poll = async () => {
                        try {
                            const res = await fetch('/status/' + jobId);
                            const data = await res.json();
                            
                            if (data.status === 'completed') {
                                statusContent.innerHTML = '<p class="success">✅ Готово!</p>';
                                linksDiv.innerHTML = `
                                    <a href="/summary/${jobId}" target="_blank">📄 Открыть конспект (Markdown)</a>
                                    <a href="/result/${jobId}" target="_blank">⚙️ Посмотреть данные (JSON)</a>
                                `;
                                submitBtn.disabled = false;
                            } else if (data.status === 'error' || data.status === 'failed') {
                                statusContent.innerHTML = '<p class="error">❌ Ошибка: ' + (data.error || 'Неизвестная ошибка') + '</p>';
                                submitBtn.disabled = false;
                            } else {
                                const statusMap = {
                                    'processing': 'Инициализация...',
                                    'extracting': 'Извлечение текста...',
                                    'chunking': 'Разбиение на части...',
                                    'summarizing': 'Нейросеть пишет конспект...',
                                    'pending': 'В очереди...'
                                };
                                // Match starting string for progress like 'summarizing: 5/10'
                                let displayStatus = statusMap[data.status] || data.status;
                                if (data.status.startsWith('summarizing:')) {
                                    displayStatus = 'Анализ частей: ' + data.status.split(':')[1];
                                }
                                statusContent.innerHTML = '<p class="loading">⏳ ' + displayStatus + '</p>';
                                setTimeout(poll, 4000);
                            }
                        } catch (e) {
                            statusContent.innerHTML = '<p class="error">Ошибка проверки статуса</p>';
                        }
                    };
                    poll();
                }
            </script>
        </body>
        </html>
        """

    @web_app.post("/submit")
    async def submit_job(file: UploadFile = File(...)):
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        job_id = str(uuid.uuid4())
        content = await file.read()
        
        # Initialize and save to Volume
        storage.init_job(job_id)
        storage.save_input_pdf(job_id, content)
        storage.update_status(job_id, "pending")
        
        # Trigger background task
        process_pdf_job.spawn(job_id, file.filename)
        
        return {"job_id": job_id, "status": "processing"}

    @web_app.get("/status/{job_id}")
    async def get_status(job_id: str):
        job_data = storage.get_status(job_id)
        if not job_data or job_data.get("status") == "not_found":
            return {"error": "Job not found"}
        return {
            "job_id": job_id,
            "status": job_data.get("status"),
            "error": job_data.get("error")
        }

    @web_app.get("/result/{job_id}")
    async def get_result(job_id: str):
        result = storage.get_result(job_id)
        if not result:
            return {"error": "Result not found or job still processing"}
        return result

    @web_app.get("/summary/{job_id}", response_class=PlainTextResponse)
    async def get_summary(job_id: str):
        md = storage.get_markdown(job_id)
        if not md:
            return "Summary not found or still processing."
        return md

    return web_app
