# ragcli - RAG CLI with Oracle DB 26ai

## Formal Requirements Specification v1.0

---

## 1. Executive Summary

**ragcli** is a dual-interface command-line and web-based application for Retrieval-Augmented Generation (RAG) using Oracle Database 26ai as the vector store. It enables users to upload documents, ask questions against those documents, visualize the retrieval process, and understand embedding/similarity search in real-time. The application combines a professional terminal UI (Rich-based) with a beautiful web interface (Gradio-like) for comprehensive RAG management and interaction.

---

## 2. Project Overview

### 2.1 Scope
- Terminal CLI with REPL and functional modes
- Web UI for document management and queries
- Integration with Ollama API for LLM inference
- Integration with Oracle DB 26ai for vector storage and similarity search
- PDF OCR using DeepSeek-OCR via vLLM
- Real-time visualization of retrieval chains and embeddings
- Comprehensive logging and metrics tracking

### 2.2 Target Environment
- **Python Version**: 3.9+
- **External Dependencies**: Ollama (API-based), Oracle Database 26ai (TLS connection), vLLM (for OCR)
- **Operating Systems**: Linux, macOS, Windows

### 2.3 Deployment Options
- PyPI Package: `pip install ragcli`
- Standalone Binary (via PyInstaller/Nuitka)
- Docker Container with all dependencies
- Source distribution

---

## 3. Core Architecture

### 3.1 Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| CLI Framework | Typer + Click | Command routing and argument parsing |
| Terminal UI | Rich | Beautiful terminal rendering |
| Web Framework | Gradio (or FastAPI + custom frontend) | Web UI for RAG interface |
| LLM Integration | Ollama API | Text generation and embeddings |
| Vector DB | Oracle DB 26ai | Vector storage and similarity search |
| OCR Engine | DeepSeek-OCR via vLLM | PDF text extraction |
| Data Processing | LangChain/LlamaIndex | Document chunking, RAG pipeline |
| Config Management | PyYAML | Safe configuration loading |
| Async Operations | aiohttp/asyncio | Non-blocking API calls |
| Logging | Python logging + Rich integration | Structured logging |
| Visualization | Plotly (terminal) + Matplotlib | Retrieval chain visualization |

### 3.2 Directory Structure

```
ragcli/
├── ragcli/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py              # Entry point, REPL + functional modes
│   │   ├── commands/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py        # Document upload commands
│   │   │   ├── query.py         # Query commands
│   │   │   ├── documents.py     # Document management
│   │   │   ├── visualize.py     # Visualization commands
│   │   │   └── config.py        # Configuration commands
│   ├── core/
│   │   ├── __init__.py
│   │   ├── rag_engine.py        # Main RAG orchestration
│   │   ├── embedding.py         # Embedding generation via Ollama
│   │   ├── similarity_search.py # Oracle vector search
│   │   ├── document_processor.py # Chunking, preprocessing
│   │   └── ocr_processor.py     # PDF OCR with DeepSeek-OCR
│   ├── database/
│   │   ├── __init__.py
│   │   ├── oracle_client.py     # Oracle DB 26ai connection
│   │   ├── vector_ops.py        # Vector operations (HNSW/IVF)
│   │   └── schemas.py           # Database schema definitions
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── web_app.py           # Gradio/FastAPI app
│   │   ├── components/
│   │   │   ├── upload_panel.py
│   │   │   ├── query_panel.py
│   │   │   ├── documents_panel.py
│   │   │   ├── visualize_panel.py
│   │   │   └── dashboard.py
│   │   └── styles.py            # CSS/theming for dark mode
│   ├── config/
│   │   ├── __init__.py
│   │   ├── config_manager.py    # Safe YAML loading
│   │   ├── defaults.py          # Default configurations
│   │   └── config.yaml.example  # Example configuration file
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py            # Rich-integrated logging
│   │   ├── validators.py        # Input validation
│   │   ├── metrics.py           # Metrics collection
│   │   └── helpers.py           # Utility functions
│   └── visualization/
│       ├── __init__.py
│       ├── retrieval_chain.py   # Retrieval chain visualization
│       ├── embedding_space.py   # 2D/3D embedding projections
│       └── similarity_heatmap.py # Similarity score visualizations
├── tests/
├── docs/
├── config.yaml                  # User configuration
├── requirements.txt
├── setup.py
├── README.md
└── Dockerfile
```

---

## 4. Configuration Management

### 4.1 config.yaml Specification

```yaml
# Oracle Database 26ai Configuration
oracle:
  username: "rag_user"
  password: "${ORACLE_PASSWORD}"  # Can use env vars
  dsn: "oracle_host:1521/orcl"
  use_tls: true
  tls_wallet_path: null           # Optional, null for TLS connection
  pool_size: 10                   # Connection pooling

# Ollama Configuration
ollama:
  endpoint: "http://localhost:11434"  # API endpoint URL
  embedding_model: "nomic-embed-text" # Embedding model name
  chat_model: "llama2"                # Chat model name
  timeout: 30                         # API timeout in seconds

# DeepSeek-OCR Configuration (via vLLM)
ocr:
  vllm_endpoint: "http://localhost:8000"  # vLLM API endpoint
  enabled: true
  model: "deepseek-ai/DeepSeek-OCR"
  temperature: 0.0
  max_tokens: 8192

# Document Processing
documents:
  chunk_size: 1000                # Default: 1000 tokens per chunk
  chunk_overlap_percentage: 10    # Default: 10% overlap
  supported_formats:             # TXT, MD, PDF
    - txt
    - md
    - pdf
  max_file_size_mb: 100
  temp_dir: "./temp"

# Vector Index Configuration
vector_index:
  auto_select: true              # Auto-select based on data size
  index_type: "HNSW"             # Options: HNSW, IVF_FLAT, HYBRID
  dimension: 768                 # Embedding dimension
  m: 16                          # HNSW parameter: connections per node
  ef_construction: 200            # HNSW parameter: construction effort

# RAG Query Configuration
rag:
  top_k: 5                       # Number of documents to retrieve
  min_similarity_score: 0.5      # Minimum similarity threshold
  use_reranking: false           # Future: LLM-based reranking

# Logging Configuration
logging:
  level: "INFO"                  # DEBUG, INFO, WARNING, ERROR
  log_file: "./logs/ragcli.log"
  max_log_size_mb: 50
  backup_count: 5
  detailed_metrics: true         # Log detailed metrics

# UI Configuration
ui:
  theme: "dark"                  # dark or light
  host: "0.0.0.0"
  port: 7860                     # Gradio default
  share: false                   # Public sharing
  auto_reload: true

# Application Settings
app:
  app_name: "ragcli"
  version: "1.0.0"
  debug: false
```

### 4.2 Safe Configuration Loading

```python
# Example safe loading mechanism
def load_config(config_path: str = "./config.yaml") -> dict:
    """
    Safely load configuration from YAML with environment variable substitution.
    
    Features:
    - Validates required fields
    - Expands environment variables (${VAR_NAME} syntax)
    - Applies default values for missing optional fields
    - Checks for sensitive data exposure
    - Validates connection parameters
    
    Returns:
        dict: Merged configuration with defaults
        
    Raises:
        ConfigValidationError: If configuration is invalid
    """
```

---

## 5. Functional Requirements

### 5.1 CLI Interface

#### 5.1.1 REPL Mode
Command: `ragcli` (no arguments)

Launches interactive session with directory of available commands:

```
┌─ ragcli v1.0 ─────────────────────────────────────────┐
│ Welcome to ragcli - Oracle DB 26ai RAG Interface       │
│ Type 'help' for available commands                     │
└────────────────────────────────────────────────────────┘

Commands:
  📤 upload <file_path>           Upload document(s)
  ❓ ask <query>                  Ask question (select docs optionally)
  📋 list-docs                    List all documents
  🔍 search <query>               Search within documents
  📊 visualize <query_id>         Visualize retrieval chain
  🗑️ delete-doc <doc_id>          Delete document
  💾 export-logs                  Export session logs
  ⚙️ config                       Show current configuration
  🌐 web                          Launch web UI
  ❓ help [command]               Show help
  🚪 exit                         Exit application

ragcli> 
```

Features:
- Tab completion for commands and document names
- Command history (up/down arrows)
- Auto-suggestions based on context
- Rich formatted output with colors/tables
- Multi-command sessions without restarting
- Session persistence (optional)

#### 5.1.2 Functional Mode (Command-Line Arguments)

```bash
# Upload document(s)
ragcli upload path/to/document.pdf
ragcli upload path/to/folder/ --recursive --verbose

# Ask question (interactive document selection)
ragcli ask "What is the main topic?" --interactive

# Ask specific documents
ragcli ask "Query" --docs doc_id_1 doc_id_2 --show-chain

# List documents
ragcli list-docs --format table --verbose

# Delete document
ragcli delete-doc doc_id_1

# Show configuration
ragcli config show

# Launch web UI
ragcli web --port 7860 --share false

# Export session
ragcli export --logs --format json --output session.json
```

### 5.2 Document Management

#### 5.2.1 Upload Features
- **Single File**: Upload TXT, Markdown, or PDF
- **Batch Upload**: Upload entire directories with recursive option
- **Progress Tracking**: Real-time progress bar for large files
- **Validation**: File type, size, and format validation
- **OCR for PDF**: Automatic DeepSeek-OCR processing

**Process Flow**:
```
File Upload
    ↓
Validate (type, size, format)
    ↓
If PDF → DeepSeek-OCR (text extraction to Markdown)
    ↓
Chunk Processing (token-based, 1000 tokens, 10% overlap)
    ↓
Generate Embeddings (via Ollama)
    ↓
Store in Oracle DB 26ai (vectors + metadata)
    ↓
Create Search Index (auto-select: HNSW/IVF/HYBRID)
    ↓
Return: Document ID, Chunk Count, Token Count, Embedding Size
```

#### 5.2.2 Document Metadata Tracking

**Stored per document**:
- Document ID (UUID)
- Original filename
- File format (TXT, MD, PDF)
- Upload timestamp (ISO 8601)
- File size (bytes)
- Extracted text size (bytes)
- Number of chunks
- Total tokens (sum of all chunks)
- Embedding dimension
- Approximate embedding storage size (bytes)
- OCR status (if PDF)
- Last modified timestamp
- User-provided tags/metadata (optional)

**Example metadata output**:
```
Document: research_paper.pdf
├─ ID: doc_f47a2e9c
├─ Uploaded: 2025-11-07 10:23:45 UTC
├─ Format: PDF (OCR'd)
├─ File Size: 2.4 MB
├─ Extracted Text: 1.8 MB
├─ Chunks: 127
├─ Tokens: 145,230
├─ Embeddings: ~11 MB (768-dim @ 4 bytes/float)
└─ Status: Ready
```

### 5.3 Query & RAG Operations

#### 5.3.1 Query Workflow

```
User Query Input
    ↓
Query Embedding (via Ollama)
    ↓
Oracle DB 26ai Similarity Search (cosine distance)
    ↓
Top-K Retrieval (configurable, default: 5)
    ↓
Apply Similarity Threshold (default: 0.5)
    ↓
Re-rank Results (optional)
    ↓
Context Assembly
    ↓
LLM Generation (via Ollama)
    ↓
Stream Response to User
    ↓
Log Metrics (latency, tokens, similarity scores)
```

#### 5.3.2 Interactive Document Selection

When user runs `ask` without specifying documents:

```
📋 Available Documents (6):
  [1] research_paper.pdf        [127 chunks, 145K tokens]
  [2] user_guide.md             [43 chunks, 52K tokens]
  [3] api_spec.txt              [18 chunks, 21K tokens]
  [4] technical_report.pdf      [89 chunks, 98K tokens]
  [5] faq.md                    [12 chunks, 14K tokens]
  [6] release_notes.md          [25 chunks, 31K tokens]

Select documents to search (comma-separated, e.g., 1,3,5):
```

#### 5.3.3 Response with Metrics

After query:

```
❓ Query: "What is X?"
⏱️  Response Time: 2.34s
├─ Embedding: 0.12s
├─ Search: 0.45s
├─ LLM Generation: 1.67s
└─ Total Overhead: 0.10s

📊 Retrieval Results (5 documents found):
├─ research_paper.pdf (Similarity: 0.92) [Chunk 42]
├─ technical_report.pdf (Similarity: 0.87) [Chunk 15]
├─ user_guide.md (Similarity: 0.81) [Chunk 7]
├─ api_spec.txt (Similarity: 0.76) [Chunk 3]
└─ faq.md (Similarity: 0.68) [Chunk 2]

💬 Answer:
[LLM generated response here, streamed in real-time]

📈 Tokens Used:
├─ Prompt Tokens: 1,245
├─ Completion Tokens: 342
└─ Total: 1,587
```

### 5.4 Visualization Features

#### 5.4.1 Retrieval Chain Visualization

Display the RAG pipeline visually:

```
Query Input: "What is machine learning?"
    ↓
Tokenization: 5 tokens
    ├─ ["What", "is", "machine", "learning", "?"]
    ↓
Embedding Generation: 768-dimensional vector
    ├─ [0.234, -0.156, 0.812, ..., -0.045]
    ├─ Norm: 1.000
    ↓
Similarity Search (Top-5)
    ├─ Doc1: 0.923 ✓
    ├─ Doc2: 0.867 ✓
    ├─ Doc3: 0.812 ✓
    ├─ Doc4: 0.756 ✓
    └─ Doc5: 0.701 ✓
    ↓
Context Assembly (2,341 tokens)
    ├─ Doc1 excerpt [145 tokens]
    ├─ Doc2 excerpt [523 tokens]
    ├─ Doc3 excerpt [412 tokens]
    ├─ Doc4 excerpt [687 tokens]
    └─ Doc5 excerpt [574 tokens]
    ↓
LLM Prompt (3,100 tokens total)
    ├─ System Prompt: 512 tokens
    ├─ User Query: 5 tokens
    └─ Context: 2,583 tokens
    ↓
LLM Response (342 tokens)
    └─ [Streaming tokens in real-time with token-level visualization]
```

**Terminal Visualization** (using Rich):
- ASCII-art flow diagram with ANSI colors
- Progress indicators for each stage
- Token counts and timing for each step
- Expandable sections (click/select to drill down)
- Real-time updates during generation

#### 5.4.2 Embedding Space Visualization

Show vectors in 2D/3D projected space:

**Terminal (simplified)**:
```
Embedding Space (2D Projection - UMAP):
Query Vector      [●] in red
Retrieved Docs    [●] in green
Other Docs        [●] in gray

Display distance-based clustering with ASCII scatter plot
```

**Web UI (full)**:
- Interactive Plotly 3D scatter plot
- Zoom, pan, rotate
- Hover tooltips with document info
- Color-coded by similarity score
- Animation on query execution

#### 5.4.3 Similarity Scores Heatmap

Matrix showing similarity between query and all documents:

```
Similarity Heatmap (Cosine Distance):

                 research_paper  user_guide  api_spec  tech_report  faq
Query Vector          ■ 0.923      ░ 0.756   ░ 0.612    ■ 0.867   ░ 0.498
                   [████████▌]  [██████░░]  [███░░░░]  [████████░]  [██░░░░]

Legend: ■ High (0.8+) | ░ Medium (0.5-0.8) | ░ Low (<0.5)
```

**Web UI**: 
- Interactive heatmap with hover details
- Filter by threshold
- Export as image/data

#### 5.4.4 Real-time Search Visualization

As user types in query field:

```
Query: "machine lear" (8 chars)
Embedding: [in progress...]

Updating similarity search...
Top match: research_paper.pdf (0.89) ← Updates live
```

Web UI shows:
- Real-time similarity scores updating
- Top documents changing as query changes
- Preview of matched chunks
- Debounced requests (0.5s delay between keystrokes)

---

## 6. Web UI Requirements (Gradio/FastAPI)

### 6.1 Page Structure

#### 6.1.1 Home/Dashboard Tab
- Quick stats: Total documents, total chunks, total tokens, vector index status
- Recent queries (timestamp, query text, response summary)
- System health (Oracle connection, Ollama status, vLLM status)
- Quick action buttons (Upload, Ask, View Documents)

#### 6.1.2 Upload Tab
- Drag-and-drop file upload area
- File type selector (TXT, MD, PDF)
- OCR settings for PDF (if enabled)
- Batch upload folder browser
- Upload progress bar with real-time feedback
- Completion summary with document ID and metadata

#### 6.1.3 Ask Tab
- Query text input (large textarea, 5+ lines)
- Document selector (multi-select with search)
- "Select All" / "Select None" buttons
- Send button with loading indicator
- Real-time response streaming
- Similarity scores table (top-k matches)
- Copy answer button
- Export to file option

#### 6.1.4 Documents Tab
- Table view of all uploaded documents:
  - Document name
  - Upload date
  - Format (TXT/MD/PDF)
  - File size
  - Chunks count
  - Token count
  - Embedding size
  - Actions (View, Delete, Export metadata)
- Search/filter by name
- Sort by column (date, size, chunks, etc.)
- Bulk actions (delete multiple, export)

#### 6.1.5 Visualize Tab
- Dropdown to select previous query OR enter new query
- Tabs for:
  - **Retrieval Chain**: Flow diagram with stage-by-stage breakdown
  - **Embedding Space**: 3D interactive scatter plot
  - **Similarity Heatmap**: Clickable matrix
  - **Metrics**: Query timing, token usage, similarity scores
- Export visualization as image
- Full-screen view option

#### 6.1.6 Settings Tab
- Current configuration display
- Editable settings:
  - Top-K results
  - Similarity threshold
  - Chunk size / overlap (with restart warning)
  - Model selections (chat model, embedding model)
- Connection status checks (Oracle, Ollama, vLLM)
- View/edit config.yaml (with validation)
- Export logs
- Clear cache / reset

### 6.2 UI/UX Design Specifications

**Theme**: Dark mode by default
- Primary color: #00D9FF (cyan/blue, Oracle-aligned)
- Accent color: #FF6B6B (red, for highlights/errors)
- Background: #0A0E27 (very dark)
- Text: #E0E0E0 (light gray)
- Secondary: #1E2749 (dark blue-gray)

**Typography**:
- Headings: Inter, Bold, 18-24px
- Body: Inter, Regular, 14px
- Monospace (code): JetBrains Mono, 12px

**Spacing & Layout**:
- Consistent padding: 12px, 16px, 24px
- Card-based layout with subtle shadows
- Max width: 1400px (centered)
- Mobile: Not required (desktop-only)

**Interactions**:
- Hover effects on buttons/clickable elements
- Smooth transitions (200-300ms)
- Disabled state for unavailable actions
- Loading spinners with messages
- Toast notifications for actions (success/error)
- Tooltips for complex UI elements

### 6.3 Responsive Web Components (Gradio)

**Gradio Interface Structure**:

```python
with gr.Blocks(theme=gr.themes.Soft(primary_hue="cyan"), css=custom_css) as interface:
    gr.Markdown("# ragcli - Oracle DB 26ai RAG")
    
    with gr.Tabs():
        with gr.Tab("Dashboard"):
            dashboard_ui()
        with gr.Tab("Upload"):
            upload_ui()
        with gr.Tab("Ask"):
            query_ui()
        with gr.Tab("Documents"):
            documents_ui()
        with gr.Tab("Visualize"):
            visualize_ui()
        with gr.Tab("Settings"):
            settings_ui()
    
    interface.queue()
    interface.launch(server_name="0.0.0.0", server_port=7860, share=False)
```

---

## 7. Database Schema (Oracle DB 26ai)

### 7.1 Tables

#### 7.1.1 DOCUMENTS Table

```sql
CREATE TABLE DOCUMENTS (
    document_id         VARCHAR2(36) PRIMARY KEY,
    filename            VARCHAR2(512) NOT NULL,
    file_format         VARCHAR2(10) NOT NULL,  -- TXT, MD, PDF
    file_size_bytes     NUMBER NOT NULL,
    extracted_text_size_bytes NUMBER,
    upload_timestamp    TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_modified       TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    chunk_count         NUMBER NOT NULL,
    total_tokens        NUMBER NOT NULL,
    embedding_dimension NUMBER DEFAULT 768,
    approximate_embedding_size_bytes NUMBER,
    ocr_processed       VARCHAR2(1) DEFAULT 'N',
    status              VARCHAR2(20) DEFAULT 'READY',  -- PROCESSING, READY, ERROR
    metadata_json       CLOB,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    updated_at          TIMESTAMP DEFAULT SYSTIMESTAMP
);
```

#### 7.1.2 CHUNKS Table

```sql
CREATE TABLE CHUNKS (
    chunk_id            VARCHAR2(36) PRIMARY KEY,
    document_id         VARCHAR2(36) NOT NULL,
    chunk_number        NUMBER NOT NULL,
    chunk_text          CLOB NOT NULL,
    token_count         NUMBER NOT NULL,
    character_count     NUMBER NOT NULL,
    start_position      NUMBER,
    end_position        NUMBER,
    chunk_embedding     VECTOR(768, FLOAT32),
    embedding_model     VARCHAR2(50),
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES DOCUMENTS(document_id) ON DELETE CASCADE,
    CONSTRAINT unique_chunk_per_doc UNIQUE(document_id, chunk_number)
);
```

#### 7.1.3 QUERIES Table

```sql
CREATE TABLE QUERIES (
    query_id            VARCHAR2(36) PRIMARY KEY,
    query_text          CLOB NOT NULL,
    query_embedding     VECTOR(768, FLOAT32),
    embedding_model     VARCHAR2(50),
    selected_documents  VARCHAR2(2000),  -- Comma-separated doc IDs
    top_k               NUMBER DEFAULT 5,
    similarity_threshold NUMBER DEFAULT 0.5,
    response_text       CLOB,
    response_tokens     NUMBER,
    response_time_ms    NUMBER,
    embedding_time_ms   NUMBER,
    search_time_ms      NUMBER,
    generation_time_ms  NUMBER,
    retrieved_chunks    VARCHAR2(4000),  -- JSON: chunk IDs and scores
    status              VARCHAR2(20),    -- SUCCESS, FAILED, PARTIAL
    error_message       VARCHAR2(500),
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP
);
```

#### 7.1.4 QUERY_RESULTS Table

```sql
CREATE TABLE QUERY_RESULTS (
    result_id           VARCHAR2(36) PRIMARY KEY,
    query_id            VARCHAR2(36) NOT NULL,
    chunk_id            VARCHAR2(36) NOT NULL,
    similarity_score    FLOAT,
    rank                NUMBER,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES QUERIES(query_id) ON DELETE CASCADE,
    FOREIGN KEY (chunk_id) REFERENCES CHUNKS(chunk_id) ON DELETE CASCADE
);
```

### 7.2 Vector Index Configuration

**Index Type Auto-Selection Logic**:
```
If total_chunks <= 1,000:
    Use IVF_FLAT (simpler, fast for small sets)
Else if total_chunks <= 100,000:
    Use HNSW (balanced performance and memory)
Else:
    Use HYBRID (combines HNSW + IVF, best for large datasets)
```

**Index Creation**:
```sql
CREATE VECTOR INDEX CHUNKS_EMBEDDING_IDX 
ON CHUNKS(chunk_embedding) ORGANIZATION CLUSTER 
WITH TARGET ACCURACY 95
DISTANCE METRIC COSINE;
```

---

## 8. Ollama API Integration

### 8.1 Embedding Endpoint

**Endpoint**: `POST /api/embeddings`

**Request**:
```json
{
    "model": "nomic-embed-text",
    "prompt": "text to embed"
}
```

**Response**:
```json
{
    "embedding": [0.234, -0.156, 0.812, ...],
    "model": "nomic-embed-text",
    "total_duration": 123456789
}
```

### 8.2 Chat Completion Endpoint

**Endpoint**: `POST /api/chat` or OpenAI-compatible `/v1/chat/completions`

**Request**:
```json
{
    "model": "llama2",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant..."},
        {"role": "user", "content": "Question with context..."}
    ],
    "stream": true,
    "temperature": 0.7
}
```

**Response** (streamed):
```json
{"choices":[{"delta":{"content":"token1"},"index":0}]}
{"choices":[{"delta":{"content":" token2"},"index":0}]}
...
```

### 8.3 Error Handling

- Retry logic with exponential backoff (3 retries, max 10s)
- Timeout handling (default 30s per request)
- Connection pooling and keep-alive
- Graceful degradation if Ollama unavailable

---

## 9. PDF OCR Processing (DeepSeek-OCR via vLLM)

### 9.1 Process Flow

```
PDF Input
    ↓
Convert to images (PyPDF2/pdfplumber)
    ↓
Batch send to vLLM API
    ↓
DeepSeek-OCR text extraction
    ↓
Post-process markdown (preserve tables, formatting)
    ↓
Save as markdown
    ↓
Proceed to chunking
```

### 9.2 vLLM API Integration

**Endpoint**: `POST http://localhost:8000/v1/chat/completions` (OpenAI-compatible)

**Request**:
```json
{
    "model": "deepseek-ai/DeepSeek-OCR",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract all text from this image:"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
                {"type": "text", "text": "Format as markdown, preserve tables."}
            ]
        }
    ],
    "temperature": 0.0,
    "max_tokens": 8192
}
```

**Response**:
```json
{
    "choices": [{"message": {"content": "# Extracted Markdown\n..."}}]
}
```

---

## 10. Logging & Metrics

### 10.1 Logging Configuration

**Log Levels**:
- DEBUG: Detailed debugging info (token-level operations)
- INFO: General informational messages (operations started/completed)
- WARNING: Warnings (low similarity scores, slow queries)
- ERROR: Error messages with stack traces

**Log Destinations**:
- Console: Rich-formatted output (color-coded by level)
- File: `./logs/ragcli.log` (rotating, max 50MB per file, 5 backups)

**Log Format**:
```
[2025-11-07 10:23:45.123] [INFO] [Upload] Processing research_paper.pdf (2.4MB)
[2025-11-07 10:23:45.234] [DEBUG] [OCR] Sending page 1/10 to vLLM
[2025-11-07 10:23:47.892] [INFO] [Upload] Completed: 127 chunks, 145K tokens
[2025-11-07 10:24:01.234] [INFO] [Query] Query ID: qry_abc123, Time: 2.34s
[2025-11-07 10:24:01.456] [DEBUG] [Embedding] Generated 768-dim vector, norm: 1.0
[2025-11-07 10:24:01.789] [INFO] [Search] Found 5 matches, avg similarity: 0.81
```

### 10.2 Metrics Collection

**Per Operation**:
- Total duration (milliseconds)
- Stage-specific timings (embedding, search, generation)
- Token counts (prompt, completion, total)
- Similarity scores (min, max, average)
- Memory usage (peak)
- Cache hits/misses (if caching implemented)

**Aggregated Statistics** (viewable in Settings):
- Total queries processed
- Average query time
- Average similarity score
- Top queries (most frequent)
- Most used documents
- Error rate
- Uptime

**Export Options**:
```bash
ragcli export --logs --format json --output session_logs.json
ragcli export --logs --format csv --output session_logs.csv
```

---

## 11. Error Handling & Validation

### 11.1 Input Validation

- **File Upload**:
  - File type check (TXT, MD, PDF only)
  - File size limit (100MB default, configurable)
  - File name sanitization
  - Duplicate detection

- **Query Input**:
  - Min length: 3 characters
  - Max length: 5000 characters
  - Special character escaping
  - Token count validation (< model max)

- **Document Selection**:
  - Valid document ID format
  - Check if document exists
  - Permission checks (future)

### 11.2 Error Messages

**User-Friendly**:
```
❌ Error: File too large (2.4GB exceeds 100MB limit)
   Solution: Upload a smaller file or increase max_file_size_mb in config.yaml

❌ Error: Ollama API unreachable at http://localhost:11434
   Solution: Ensure Ollama is running: ollama serve

❌ Error: Oracle connection failed (ORA-12514)
   Solution: Check DSN and credentials in config.yaml, verify TLS settings
```

### 11.3 Retry Logic

- **Ollama API failures**: 3 retries with exponential backoff (1s, 2s, 4s)
- **Oracle connection**: 5 retries with 2s intervals
- **vLLM (OCR) failures**: 2 retries
- **Transient errors**: Automatic retry with notification

---

## 12. Performance Requirements

### 12.1 Latency Targets

| Operation | Target | Acceptable |
|-----------|--------|----------|
| Document upload (1MB TXT) | < 2s | < 5s |
| PDF OCR (10 pages) | < 30s | < 60s |
| Query embedding | < 500ms | < 1s |
| Vector similarity search (100K docs) | < 500ms | < 1s |
| LLM response (100 tokens) | < 2s | < 5s |
| **Total end-to-end query** | **< 3.5s** | **< 8s** |

### 12.2 Scalability

- Support up to 1 million documents
- Support up to 100 million chunks
- Connection pooling: 10 concurrent Oracle connections
- Batch API requests where possible
- Async processing for non-blocking operations

### 12.3 Resource Constraints

- Memory: < 1GB for base application
- Disk: Configurable temp directory for OCR processing
- Network: Connection keep-alive, compression for API responses

---

## 13. Security Considerations

### 13.1 Configuration Security

- **Secrets Management**:
  - Store credentials in `config.yaml` with environment variable references
  - Never commit `config.yaml` to version control (use `.gitignore`)
  - Support reading from environment: `${ORACLE_PASSWORD}` → env var
  - Add validation to prevent hardcoded secrets in logs

- **File Permissions**:
  - `config.yaml` must be readable only by user (mode 600)
  - Warning if file permissions are too open

### 13.2 Database Security

- TLS-only connections (no wallet required, use TLS client certs if needed)
- Connection pooling with automatic cleanup
- Query parameterization (prevent SQL injection)
- No sensitive data logged (passwords, full connection strings)

### 13.3 API Communication

- All Ollama/vLLM calls over HTTP (can be upgraded to HTTPS)
- Request timeouts to prevent hanging connections
- Input sanitization before sending to LLMs

---

## 14. Deployment & Packaging

### 14.1 PyPI Package

```bash
pip install ragcli

# Post-install setup
ragcli config init  # Creates ~/.ragcli/config.yaml with example
```

### 14.2 Standalone Binary

```bash
# Using PyInstaller/Nuitka
pyinstaller --onefile ragcli/__main__.py --name ragcli

# Usage
./ragcli --help
```

### 14.3 Docker Deployment

**Dockerfile** includes:
- Python 3.11
- All dependencies (Rich, Gradio, etc.)
- Ollama client (or just API client)
- Pre-configured for TLS to Oracle DB 26ai

```bash
docker build -t ragcli:latest .
docker run -it -p 7860:7860 -v ~/.ragcli:/root/.ragcli ragcli
```

### 14.4 Installation from Source

```bash
git clone https://github.com/user/ragcli.git
cd ragcli
pip install -e ".[dev,docs]"
python -m ragcli --help
```

---

## 15. Testing Requirements

### 15.1 Unit Tests

- Configuration loading and validation
- Document chunking with various overlap percentages
- Embedding generation mocking
- Similarity search logic
- Error handling and retry logic

### 15.2 Integration Tests

- End-to-end document upload workflow
- Query execution with mock Ollama API
- Oracle DB 26ai connectivity
- PDF OCR processing (mock vLLM)
- Web UI interaction

### 15.3 Performance Tests

- Load testing with 1000+ concurrent queries
- Large document upload handling (1GB+)
- Memory profiling during operations
- Query latency benchmarking

---

## 16. Documentation Requirements

### 16.1 User Documentation

- **Getting Started Guide**:
  - Installation
  - Initial setup (config.yaml creation)
  - First document upload
  - First query

- **CLI Reference**:
  - All commands with examples
  - Configuration options
  - Troubleshooting

- **Web UI Guide**:
  - Tab-by-tab walkthrough
  - Screenshots/GIFs
  - Best practices

### 16.2 Developer Documentation

- Architecture overview
- Code structure
- API endpoints (Ollama integration)
- Database schema
- Contributing guidelines

### 16.3 API Documentation

- Python API reference (for library usage)
- REST API endpoints (for web server mode)
- Example code snippets

---

## 17. Future Enhancements

*Out of scope for v1.0, but consider for roadmap*:

- Multi-tenant support
- User authentication & authorization
- Advanced reranking (LLM-based)
- Caching layer (Redis)
- Chat history management
- Document version control
- Custom embedding model support
- Multi-language support
- Advanced analytics dashboard
- API key management for deployed instances

---

## 18. Acceptance Criteria

- [ ] CLI functional and REPL modes both operational
- [ ] Document upload (TXT, MD, PDF with OCR) working end-to-end
- [ ] Query execution with real-time response streaming
- [ ] Retrieval chain visualization working in CLI and Web UI
- [ ] Embedding space visualization (3D plot) in Web UI
- [ ] Real-time similarity updates as user types query
- [ ] All metadata (timestamps, tokens, chunks, embedding sizes) tracked
- [ ] Configuration via `config.yaml` with env var substitution
- [ ] Detailed logging with appropriate levels
- [ ] Error handling with user-friendly messages
- [ ] Dark theme UI fully functional
- [ ] Docker deployment working
- [ ] PyPI package installable via pip
- [ ] All performance targets met
- [ ] Documentation complete

---

## 19. Success Metrics

- User can upload documents and query them within 2 minutes of first launch
- 95%+ query success rate
- Average query latency < 3.5 seconds
- All log messages clear and actionable
- Zero hardcoded secrets in codebase
- Supports 100K+ documents with <1s query time
- Beautiful, professional UI matching Gradio aesthetics
- Comprehensive error messages reducing support burden

---

## End of Specification

**Version**: 1.0  
**Last Updated**: 2025-11-07  
**Status**: Ready for Development
