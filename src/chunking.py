def chunk_text(text: str, max_chunk_chars: int = 15000) -> list:
    """
    Intelligently chunk text by paragraphs to ensure we don't break sentences.
    Default max_chunk_chars of 15000 is roughly 3500-4000 tokens.
    """
    chunks = []
    # Split by double newline to preserve paragraph structure
    paragraphs = text.split("\n\n")
    current_chunk = ""
    
    for p in paragraphs:
        if len(current_chunk) + len(p) > max_chunk_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = p + "\n\n"
        else:
            current_chunk += p + "\n\n"
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks
