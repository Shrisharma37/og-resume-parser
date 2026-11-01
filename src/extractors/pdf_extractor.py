import hashlib
import io
import pdfplumber

def extract_pdf_data(file_bytes: bytes, filename: str) -> dict:
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    file_size = len(file_bytes)
    
    extracted_text = ""
    hyperlinks = set()
    
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
            
            # Extract any embedded hyperlink annotations (e.g. icon links or linked text)
            for link in getattr(page, "hyperlinks", []) or []:
                uri = link.get("uri")
                if uri and uri.startswith(("http://", "https://", "mailto:")):
                    hyperlinks.add(uri)

    # Append embedded links so regex and AI models can parse them seamlessly
    if hyperlinks:
        extracted_text += "\n\nEmbedded Links:\n" + "\n".join(hyperlinks)

    is_scanned = len(extracted_text.strip()) < 50
    return {
        "text": extracted_text,
        "is_scanned": is_scanned,
        "file_hash": file_hash,
        "file_size": file_size,
        "file_name": filename
    }