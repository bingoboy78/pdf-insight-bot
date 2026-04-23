import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path

def extract_text_from_pdf(pdf_path: str) -> dict:
    """
    Two-stage extraction:
    1. Try PyMuPDF for structural text.
    2. Fallback to OCR (Tesseract) if text is too sparse (scanned docs).
    """
    doc = fitz.open(pdf_path)
    text = ""
    page_count = len(doc)
    
    # Try text extraction first
    for page in doc:
        text += page.get_text("text") + "\n"
        
    used_ocr = False
    
    # Heuristic: if text length is tiny compared to page count, it's likely a scan.
    if len(text.strip()) < page_count * 50:
        used_ocr = True
        text = ""
        # Convert pages to images and run OCR in chunks to prevent OOM
        chunk_size = 10
        for i in range(0, page_count, chunk_size):
            images = convert_from_path(
                pdf_path, 
                dpi=200, 
                first_page=i+1, 
                last_page=min(i+chunk_size, page_count)
            )
            for j, img in enumerate(images):
                page_text = pytesseract.image_to_string(img, lang="eng+rus")
                text += f"\n--- Page {i+j+1} ---\n" + page_text
            
    return {
        "text": text,
        "page_count": page_count,
        "used_ocr": used_ocr
    }
