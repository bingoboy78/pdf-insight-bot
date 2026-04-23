# PDF Insight Bot 📚

<div align="center">
  <h3>Serverless PDF parsing and LLM-powered summarization</h3>
  <p>Easily deployable to <a href="https://modal.com">Modal.com</a></p>
  <p>
    <a href="README_RU.md">🇷🇺 Читать на русском</a>
  </p>
</div>

---

## What is this?
**PDF Insight Bot** is a complete, serverless data pipeline that accepts PDF files via a Web UI (or API), extracts the text (with OCR fallback for images), splits it into manageable chunks, and feeds it into large language models (LLMs) to generate detailed insights, summaries, and structured JSON outputs.

Built on top of **Modal**, this application handles everything from heavy PDF processing (using Tesseract OCR) to API provisioning, with zero infrastructure management required.

## Key Features
- **Web UI & API Integration**: Upload files via a simple drag-and-drop web interface or programmatically via a REST API.
- **Robust OCR**: Automatically handles image-based PDFs using `PyMuPDF` and `tesseract-ocr`.
- **LLM Agnostic**: Supports OpenAI, Anthropic, OpenRouter, and NVIDIA NIM. Easily switch models without changing code.
- **Chunking Engine**: Breaks large PDFs into safe segments to prevent Context Window overflow.
- **Async & Serverless**: Long-running jobs run seamlessly in the background on Modal, storing persistent state in Modal Volumes.

## Architecture
1. **Upload**: User submits a PDF to the `/submit` endpoint (FastAPI).
2. **Persistence**: Job metadata and the raw PDF are written to a Modal Volume (`/data`).
3. **Background Job**: The FastAPI endpoint spawns a background Modal task (`process_pdf_job`).
4. **Processing**: 
   - Extract text using `PyMuPDF`.
   - Apply OCR via `pytesseract` for image-heavy pages.
   - Text is split into semantic chunks.
5. **Synthesis**: The chunks are sent to the configured LLM API using custom prompts to generate structured insights.
6. **Result**: Outputs are saved as `result.json` and `summary.md`. Status can be checked via the Web UI.

## Getting Started

### 1. Prerequisites
- Python 3.9+
- A [Modal.com](https://modal.com) account

### 2. Install Modal and Authenticate
```bash
pip install modal
modal setup
```

### 3. Configure Secrets
The application requires API keys for your chosen LLM provider. You must create a Modal Secret named `pdf-insight-secrets`.

Run the following command, replacing the values with your actual keys:
```bash
modal secret create pdf-insight-secrets \
  LLM_PROVIDER="nvidia" \
  LLM_API_KEY="nvapi-YOUR_API_KEY_HERE" \
  LLM_MODEL="meta/llama-3.1-70b-instruct"
```
*(Supported providers: `openai`, `anthropic`, `openrouter`, `nvidia`)*

### 4. Deploy to Modal
Deploying the application is a single command. Modal will automatically build the container image, install system dependencies (like Tesseract), and provision the endpoints.

```bash
modal deploy -m src.app
```

Once deployed, Modal will output a URL (e.g., `https://<your-username>--pdf-insight-bot-api.modal.run`). Open this URL in your browser to access the Web UI.

## API Reference

If you prefer to integrate the bot into an automation workflow (like n8n, Make, or a custom script), use the REST endpoints:

- `POST /submit` - Upload a PDF. Expects `multipart/form-data` with a `file` field. Returns `{"job_id": "...", "status": "processing"}`.
- `GET /status/{job_id}` - Check job status.
- `GET /result/{job_id}` - Get the final structured JSON output.
- `GET /summary/{job_id}` - Get the raw Markdown summary.

## Security Notice
- This project includes a `.gitignore` to prevent committing sensitive keys.
- **Never** commit your `.env` or API keys to GitHub.
- All secrets are managed securely within Modal's infrastructure via `modal.Secret`.

## License
MIT License. Feel free to fork and build upon this!
