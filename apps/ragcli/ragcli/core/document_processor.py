"""Document processing utilities for chunking and preprocessing."""

import tiktoken
from pathlib import Path
from typing import List, Dict, Any, Optional
from .ocr_processor import pdf_to_markdown


def preprocess_document(file_path: str, config: dict, conn=None) -> tuple[str, bool]:
    """Preprocess document to extract text and metadata.

    Args:
        file_path: Path to the document file
        config: Configuration dictionary
        conn: Optional Oracle DB connection for OracleDocLoader

    Returns:
        tuple: (extracted_text, ocr_processed_flag)

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If format unsupported or file too large
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Check for Oracle Loader
    use_oracle_loader = config.get('documents', {}).get('use_oracle_loader', False)
    if conn and use_oracle_loader:
        try:
            from .oracle_integration import OracleIntegrationManager
            manager = OracleIntegrationManager(conn)
            # OracleDocLoader loading local file
            docs = manager.load_document(file_path)
            if docs:
                # Combine all pages/docs into one text
                text = "\n".join([doc.page_content for doc in docs])
                return text, False # Assuming Oracle Loader handles OCR if needed but returns text, or we set OCR flag to False/True based on what it did.
                # If Oracle Loader fails or is not appropriate, fallback.
        except Exception:
            pass  # Fallback to local processing

    file_format = path.suffix.lstrip('.').lower()
    if file_format not in config['documents']['supported_formats']:
        raise ValueError(f"Unsupported format: {file_format}")

    file_size = path.stat().st_size
    max_size = config['documents']['max_file_size_mb'] * 1024 * 1024
    if file_size > max_size:
        raise ValueError(f"File too large: {file_size} > {max_size} bytes")

    text = ""
    ocr_processed = False

    if file_format == 'pdf':
        ocr_processed = True
        text = pdf_to_markdown(str(path), config) or ""
    else:  # txt, md
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

    return text, ocr_processed


def chunk_text(text: str, config: dict, progress_callback=None, conn=None) -> List[Dict[str, Any]]:
    """Chunk text into smaller pieces with token-based splitting.

    Args:
        text: Full document text
        config: Configuration dictionary
        progress_callback: Optional callback function for progress updates
        conn: Optional Oracle DB connection for OracleTextSplitter

    Returns:
        List of chunks with metadata: [{'text': str, 'token_count': int, 'char_count': int}, ...]
    """
    # Check if we should use Oracle splitter
    use_oracle_splitter = config.get('documents', {}).get('use_oracle_splitter', False)
    
    if conn and use_oracle_splitter:
        try:
            from .oracle_integration import OracleIntegrationManager
            manager = OracleIntegrationManager(conn)
            
            # Oracle splitter params from config
            params = config.get('documents', {}).get('oracle_splitter_params', {"normalize": "all"})
            
            # Use Oracle splitter
            chunks_text = manager.split_text(text=text, params=params)
            
            # Post-process chunks to match expected format
            processed_chunks = []
            
            # We still need token counts for metadata
            try:
                enc = tiktoken.get_encoding("cl100k_base")
            except Exception:
                enc = None
                
            for chunk_str in chunks_text:
                tokens = len(enc.encode(chunk_str)) if enc else len(chunk_str.split())
                processed_chunks.append({
                    'text': chunk_str,
                    'token_count': tokens,
                    'char_count': len(chunk_str)
                })
                
            if progress_callback:
                progress_callback(len(text), len(text))
                
            return processed_chunks
            
        except Exception:
            pass  # Fallback to local chunking

    # Use tiktoken for accurate token counting (GPT-based)
    try:
        enc = tiktoken.get_encoding("cl100k_base")  # GPT-3.5/4 encoding
    except Exception:
        # Fallback to simple word count if tiktoken fails
        enc = None

    def token_count(text: str) -> int:
        if enc:
            return len(enc.encode(text))
        else:
            return len(text.split())  # Approx

    chunk_size = config['documents']['chunk_size']
    overlap_tokens = int(chunk_size * config['documents']['chunk_overlap_percentage'] / 100)

    # Custom chunking with token overlap
    chunks = []
    text_tokens = enc.encode(text) if enc else text.split()
    total_tokens = len(text_tokens)
    
    if total_tokens == 0:
        return []

    start = 0
    while start < total_tokens:
        end = min(start + chunk_size, total_tokens)
        chunk_tokens = text_tokens[start:end]
        chunk_text = enc.decode(chunk_tokens) if enc else ' '.join(chunk_tokens)

        chunks.append({
            'text': chunk_text,
            'token_count': len(chunk_tokens),
            'char_count': len(chunk_text)
        })

        if progress_callback:
            progress_callback(end, total_tokens)

        if end >= total_tokens:
            break
            
        start += (chunk_size - overlap_tokens)
        
        # Safety: ensure we always move forward at least 1 token
        if start <= (end - chunk_size + overlap_tokens): # This is always true if start was end - overlap
            # The simplified logic above 'start += (chunk_size - overlap_tokens)' is better
            pass
            
    return chunks


def calculate_total_tokens(chunks: List[Dict[str, Any]]) -> int:
    """Calculate total tokens across all chunks."""
    return sum(chunk['token_count'] for chunk in chunks)


def get_document_metadata(text: str, chunks: List[Dict[str, Any]], ocr_processed: bool) -> Dict[str, Any]:
    """Generate document metadata."""
    return {
        'extracted_text_size_bytes': len(text.encode('utf-8')),
        'chunk_count': len(chunks),
        'total_tokens': calculate_total_tokens(chunks),
        'ocr_processed': ocr_processed
    }
