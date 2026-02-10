# Oracle Database with AWS Bedrock for RAG Search

Integrate Oracle Database with Amazon Bedrock to build powerful Retrieval-Augmented Generation (RAG) applications. This guide demonstrates how to leverage Oracle's vector storage capabilities with AWS Bedrock's foundation models for intelligent, context-aware applications.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Setup Instructions](#setup-instructions)
- [Implementation Guide](#implementation-guide)
- [Code Examples](#code-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

This integration combines:
- **Oracle AI Database 26ai**: A powerful vector database for storing and searching embeddings
- **Amazon Bedrock**: Serverless foundation models for text embeddings and LLM inference
- **RAG Pattern**: Ground LLM responses with relevant context from your Oracle database

### Key Benefits
- **Low-Latency Access**: Use Oracle Database@AWS for direct connectivity
- **Secure Vector Storage**: Native AI vector search in Oracle AI Database 26ai
- **Scalable Embeddings**: Leverage Amazon Titan or other Bedrock models for embedding generation
- **Intelligent Responses**: Ground Claude or other LLMs with your proprietary data

## Prerequisites

### AWS Resources Required
- AWS Account with Bedrock access enabled
- EC2 instance or Lambda function in same VPC region
- IAM role with bedrock:InvokeModel permissions
- Amazon Bedrock models enabled:
  - `amazon.titan-embed-text-v1` or `amazon.titan-embed-text-v2` (embeddings)
  - `anthropic.claude-3-5-sonnet-20241022` or similar (LLM)

### Oracle Database Requirements
- Oracle AI Database 26ai or Autonomous Database@AWS
- Network connectivity from compute resource to database
- APEX 24.1+ or ORDS for REST API access (optional)

### Python Dependencies
```bash
pip install python-oracledb boto3 langchain-aws langchain-oracle langchain-text-splitters
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│              (Python/Streamlit/FastAPI)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────────┐      ┌──────▼──────────────┐
│  Oracle Vector   │      │ Amazon Bedrock     │
│  Store (AI DB)   │      │  - Embeddings      │
│  - Store vectors │      │  - LLM Inference   │
│  - Similarity    │      │  - Model Selection │
│    search        │      │                    │
└──────────────────┘      └────────────────────┘
```

### Data Flow
1. **Ingestion**: Documents → Split into chunks → Generate embeddings (Bedrock) → Store in Oracle
2. **Query**: User query → Generate embedding (Bedrock) → Search Oracle → Retrieve context
3. **Generation**: Context + Query → Send to LLM (Bedrock) → Generate response

## Setup Instructions

### 1. Prepare Oracle Database

Connect to your Oracle Database and create vector storage:

```sql
-- Create table for document chunks and vectors
CREATE TABLE documents (
    doc_id VARCHAR2(256) PRIMARY KEY,
    content CLOB,
    embedding VECTOR(1536),
    metadata JSON,
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- Create index for vector similarity search
CREATE INDEX doc_vector_idx ON documents(embedding) 
    INDEXTYPE IS VECTOR_INDEX;

-- Create table for RAG session history (optional)
CREATE TABLE rag_sessions (
    session_id VARCHAR2(256) PRIMARY KEY,
    query VARCHAR2(4000),
    response CLOB,
    context CLOB,
    model_id VARCHAR2(256),
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);
```

### 2. Configure AWS Credentials

Set up your AWS credentials for Bedrock access:

```bash
# Option 1: Environment variables
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_REGION="us-east-1"

# Option 2: AWS CLI configuration
aws configure
```

Verify Bedrock access:
```bash
aws bedrock list-foundation-models --region us-east-1
```

### 3. Set Up Network Connectivity

For Oracle Database@AWS:
```bash
# Create ODB Network peering to your VPC
# Document the database hostname, port, and credentials
# Test connectivity:
nc -zv <db-hostname> 1522
```

## Implementation Guide

### Step 1: Document Ingestion Pipeline

Load documents, chunk them, and generate embeddings:

```python
import boto3
import oracledb
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Initialize Bedrock client for embeddings
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

# Initialize Oracle connection
connection = oracledb.connect(
    user="admin",
    password="your_password",
    dsn="your_db_host:1522/FREEPDB1"
)

def generate_embedding(text: str) -> list:
    """Generate embedding using Amazon Titan"""
    response = bedrock_client.invoke_model(
        modelId='amazon.titan-embed-text-v2:0',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            "inputText": text,
            "dimensions": 1536,
            "normalize": True
        })
    )
    return json.loads(response['body'].read())['embedding']

def ingest_documents(file_path: str):
    """Ingest documents into Oracle vector store"""
    # Read documents
    with open(file_path, 'r') as f:
        text = f.read()
    
    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = splitter.split_text(text)
    
    # Generate embeddings and store
    cursor = connection.cursor()
    for i, chunk in enumerate(chunks):
        embedding = generate_embedding(chunk)
        doc_id = f"doc_{i}_{hash(chunk) % 10000}"
        
        cursor.execute(
            """
            INSERT INTO documents (doc_id, content, embedding, metadata)
            VALUES (:1, :2, :3, :4)
            """,
            [doc_id, chunk, embedding, json.dumps({"chunk_index": i})]
        )
    
    connection.commit()
    cursor.close()
    print(f"Ingested {len(chunks)} document chunks")

# Run ingestion
ingest_documents("sample_documents.txt")
```

### Step 2: RAG Retrieval

Retrieve relevant context from Oracle:

```python
def retrieve_context(query: str, top_k: int = 3) -> list:
    """Retrieve relevant documents from Oracle vector store"""
    # Generate query embedding
    query_embedding = generate_embedding(query)
    
    # Perform similarity search in Oracle
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT doc_id, content, VECTOR_DISTANCE(embedding, :1) AS distance
        FROM documents
        ORDER BY distance
        FETCH FIRST :2 ROWS ONLY
        """,
        [query_embedding, top_k]
    )
    
    results = cursor.fetchall()
    cursor.close()
    
    return [{"id": r[0], "content": r[1], "score": float(r[2])} for r in results]

# Test retrieval
context = retrieve_context("How do I configure Oracle with AWS?")
for doc in context:
    print(f"Doc: {doc['id']} (Score: {doc['score']:.4f})")
    print(f"Content: {doc['content'][:200]}...\n")
```

### Step 3: LLM Response Generation

Use Bedrock to generate responses grounded in retrieved context:

```python
def generate_rag_response(query: str, context_docs: list) -> str:
    """Generate response using Bedrock LLM with context"""
    # Prepare context string
    context_str = "\n\n".join([f"[{doc['id']}]\n{doc['content']}" 
                               for doc in context_docs])
    
    # Prepare prompt
    system_prompt = """You are a helpful assistant that answers questions based on the provided context. 
    Always reference the source document when applicable.
    If the context doesn't contain relevant information, say so clearly."""
    
    user_message = f"""Context:
{context_str}

Question: {query}

Please provide a comprehensive answer based on the context above."""
    
    # Invoke Bedrock LLM
    response = bedrock_client.invoke_model(
        modelId='anthropic.claude-3-5-sonnet-20241022',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            "anthropic_version": "bedrock-2023-06-01",
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        })
    )
    
    response_text = json.loads(response['body'].read())['content'][0]['text']
    return response_text

# Test RAG pipeline
query = "What are best practices for Oracle and AWS integration?"
context = retrieve_context(query)
response = generate_rag_response(query, context)
print(f"Query: {query}\n\nResponse:\n{response}")
```

### Step 4: Complete RAG Application

Integrate all components:

```python
def rag_pipeline(query: str, top_k: int = 3) -> dict:
    """Complete RAG pipeline"""
    # Retrieve context
    context_docs = retrieve_context(query, top_k)
    
    if not context_docs:
        return {
            "query": query,
            "response": "No relevant context found in the knowledge base.",
            "context": []
        }
    
    # Generate response
    response = generate_rag_response(query, context_docs)
    
    # Store in session history
    session_id = f"session_{int(time.time())}"
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO rag_sessions 
        (session_id, query, response, context, model_id)
        VALUES (:1, :2, :3, :4, :5)
        """,
        [
            session_id,
            query,
            response,
            json.dumps([{"id": d["id"], "score": d["score"]} for d in context_docs]),
            "anthropic.claude-3-5-sonnet-20241022"
        ]
    )
    connection.commit()
    cursor.close()
    
    return {
        "session_id": session_id,
        "query": query,
        "response": response,
        "context": context_docs
    }

# Test complete pipeline
result = rag_pipeline("How do I optimize vector search in Oracle?")
print(json.dumps(result, indent=2))
```

## Code Examples

### Using LangChain for RAG

```python
from langchain_oracle import OracleVectorStore
from langchain_aws import BedrockEmbeddings, BedrockLLM
from langchain.chains import RetrievalQA

# Initialize components
embeddings = BedrockEmbeddings(
    region_name="us-east-1",
    model_id="amazon.titan-embed-text-v2:0"
)

llm = BedrockLLM(
    region_name="us-east-1",
    model_id="anthropic.claude-3-5-sonnet-20241022"
)

vector_store = OracleVectorStore(
    client=connection,
    table_name="documents",
    embedding_function=embeddings
)

# Create RAG chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vector_store.as_retriever(search_kwargs={"k": 3})
)

# Query
response = qa_chain.run("How to integrate Oracle with AWS Bedrock?")
print(response)
```

### Streaming Responses

```python
def stream_rag_response(query: str):
    """Stream response for real-time user feedback"""
    context_docs = retrieve_context(query)
    context_str = "\n\n".join([f"[{doc['id']}]\n{doc['content']}" 
                               for doc in context_docs])
    
    user_message = f"""Context:
{context_str}

Question: {query}"""
    
    # Stream response
    with bedrock_client.invoke_model_with_response_stream(
        modelId='anthropic.claude-3-5-sonnet-20241022',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            "anthropic_version": "bedrock-2023-06-01",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": user_message}]
        })
    ) as response:
        for event in response['body']:
            if 'contentBlockDelta' in event:
                print(event['contentBlockDelta']['delta']['text'], end='', flush=True)
```

## Best Practices

### 1. Vector Quality
- Use consistent embedding model throughout pipeline
- Normalize embeddings for accurate similarity search
- Test embedding quality with known good vs. bad examples

### 2. Chunk Management
- Optimal chunk size: 512-1000 tokens
- Overlap chunks by 20-30% for context continuity
- Store chunk metadata for result filtering

### 3. Performance Optimization
- Create appropriate indexes on vector columns
- Use `VECTOR_DISTANCE` with batch operations
- Cache frequently accessed embeddings
- Monitor Bedrock token usage for cost optimization

### 4. Security
- Use IAM roles instead of access keys
- Encrypt Oracle database connections (SSL/TLS)
- Implement VPC endpoints for Bedrock access
- Audit and log all RAG queries

### 5. Quality Control
- Implement feedback loops to improve retrieval
- Monitor retrieval relevance scores
- A/B test different embedding models
- Track response latency and accuracy metrics

## Troubleshooting

### Connection Issues
```python
# Test database connectivity
try:
    cursor = connection.cursor()
    cursor.execute("SELECT 1 FROM DUAL")
    print("Database connected")
except Exception as e:
    print(f"Connection error: {e}")

# Test Bedrock access
try:
    bedrock_client.list_foundation_models()
    print("Bedrock accessible")
except Exception as e:
    print(f"Bedrock error: {e}")
```

### Vector Dimension Mismatch
```python
# Verify embedding dimensions
def check_embedding_dimensions():
    embedding = generate_embedding("test")
    print(f"Embedding dimensions: {len(embedding)}")
    # Should match vector column definition (usually 1536 for Titan)
```

### Slow Retrieval
```sql
-- Check index usage
SELECT * FROM user_indexes WHERE table_name = 'DOCUMENTS';

-- Analyze vector column statistics
ANALYZE TABLE documents COMPUTE STATISTICS;

-- Monitor query performance
EXPLAIN PLAN FOR
SELECT doc_id FROM documents
ORDER BY VECTOR_DISTANCE(embedding, :1)
FETCH FIRST 10 ROWS ONLY;
```

### High Bedrock Costs
- Batch embeddings when possible
- Cache embeddings for repeated queries
- Use smaller models for testing
- Monitor token usage with CloudWatch

## Next Steps

1. **Deploy to Production**: Use EC2/Lambda with Auto Scaling
2. **Build UI**: Create Streamlit or FastAPI application
3. **Monitor**: Set up CloudWatch endpoints and alarms
4. **Iterate**: Collect user feedback and improve retrieval quality
5. **Scale**: Implement caching and load balancing for high volume

## References
- [Oracle AI Database 26ai Documentation](https://docs.oracle.com/en/database/oracle/oracle-database/26/)
- [Amazon Bedrock User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/)
- [Oracle Vector Database](https://docs.oracle.com/en/database/oracle/oracle-database/26/arpls/DBMS_VECTOR.html)

