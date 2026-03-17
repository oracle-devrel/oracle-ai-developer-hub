"""OCR processing for PDFs using DeepSeek-OCR via vLLM in ragcli."""

import requests
import base64
from typing import Optional
from pdfplumber import open as pdf_open
from PIL import Image
from io import BytesIO
from ..config.config_manager import load_config
from ..utils.helpers import retry_with_backoff
from ..utils.logger import get_logger

logger = get_logger(__name__)

def pdf_to_markdown(pdf_path: str, config: dict) -> Optional[str]:
    """Extract text from PDF using OCR via vLLM."""
    # Standard text extraction
    text = ""
    with pdf_open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
    return text.strip()

# TODO: Batch pages, error retries (2), post-process markdown, handle non-PDF
