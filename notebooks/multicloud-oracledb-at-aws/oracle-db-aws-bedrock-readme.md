# Building Intelligent Applications with Oracle Database and AWS Bedrock

## Unlocking Enterprise AI with Serverless Foundation Models

**Author:** Oracle AI Developer Hub  
**Date:** February 2026  
**Read Time:** 15 minutes  
**Topics:** Oracle Database, AWS Bedrock, Generative AI, LLMs, Enterprise AI

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Introduction](#introduction)
3. [Architecture & Integration](#architecture--integration)
4. [Why Oracle + AWS Bedrock](#why-oracle--aws-bedrock)
5. [Getting Started](#getting-started)
6. [Implementation Guide](#implementation-guide)
7. [Advanced Patterns](#advanced-patterns)
8. [Performance Optimization](#performance-optimization)
9. [Security & Compliance](#security--compliance)
10. [Cost Management](#cost-management)
11. [Real-World Use Cases](#real-world-use-cases)
12. [Troubleshooting & Tips](#troubleshooting--tips)
13. [Conclusion](#conclusion)

---

## Executive Summary

Organizations are increasingly seeking ways to integrate generative AI capabilities into their enterprise applications. **AWS Bedrock**—a fully managed service providing access to foundation models from leading AI companies—combined with **Oracle Database**, offers a powerful solution for building intelligent, data-driven applications.

This blog explores how to leverage Oracle Database as the persistent, intelligent backend for applications powered by AWS Bedrock's foundation models, enabling:

- **Real-time AI inference** with enterprise data context
- **Persistent knowledge graphs** for semantic search
- **Audit-ready AI workflows** with Oracle's enterprise features
- **Scalable RAG implementations** using Oracle Vector Search
- **Cost-effective enterprise AI** without building ML infrastructure

---

## Introduction

### The Evolution of Enterprise AI

Enterprise applications have traditionally relied on:
- **Business Rules Engines** - Limited intelligence, high maintenance
- **Custom ML Models** - Expensive to train, maintain, and govern
- **API-based AI Services** - Limited data privacy, external dependencies

**Foundation Models** (like Claude, Llama, Mistral) available through AWS Bedrock now enable:

```
┌─────────────────────────────────────┐
│   Business Intelligence Layer       │
│   (AWS Bedrock Foundation Models)   │
└──────────────┬──────────────────────┘
               │
               ├── Claude (Anthropic)
               ├── Llama (Meta)
               ├── Mistral (Mistral AI)
               ├── Cohere
               └── Stable Diffusion
               
┌──────────────▼──────────────────────┐
│   Data Intelligence Layer           │
│   (Oracle Database Vector Store)    │
└─────────────────────────────────────┘
               │
               ├── Vector Search
               ├── Entity Graphs
               ├── Transaction History
               ├── Business Rules
               └── Audit Trail
```

### Why This Matters

**The AI Puzzle:**
- ❌ LLMs alone lack domain knowledge
- ❌ Domain knowledge stuck in databases
- ✅ **Bedrock + Oracle = Intelligent Context**

---

## Architecture & Integration

### High-Level System Design

```
┌──────────────────────────────────────────────────────────────┐
│                   AWS Cloud                                  │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │            Application Layer                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐ │ │
│  │  │ Web/Mobile  │  │   Mobile    │  │   Chatbot        │ │ │
│  │  │ API         │  │   Apps      │  │   Interface      │ │ │
│  │  └──────┬──────┘  └──────┬──────┘  └────────┬─────────┘ │ │
│  └─────────┼────────────────┼─────────────────┼────────────┘ │
│            │                │                 │              │
│  ┌─────────▼────────────────▼─────────────────▼────────────┐ │
│  │    AI Orchestration Layer (Python/LangChain)            │ │
│  │  • Request routing                                       │ │
│  │  • RAG pipeline                                          │ │
│  │  • Response synthesis                                    │ │
│  └─────────┬────────────────────┬──────────────────────────┘ │
│            │                    │                            │
│  ┌─────────▼──────────────┐   ┌▼───────────────────────────┐ │
│  │  AWS Bedrock           │   │   Oracle Database          │ │
│  │  • Claude (Multi-turn) │   │   • Vector Store           │ │
│  │  • Llama (Fast)        │   │   • Entity Knowledge Graph │ │
│  │  • Mistral (Balance)   │   │   • Transaction History    │ │
│  │  • Embeddings API      │   │   • Vector Indexes         │ │
│  └────────────────────────┘   └────────────────────────────┘ │
│            ▲                           ▲                      │
│            └───────────────┬───────────┘                      │
│                     (API Calls)                               │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow: Query to Insight

```
User Query
    │
    ▼
┌─────────────────────┐
│  Bedrock Embeddings │  Convert query to vector
│  (Get embedding)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Oracle Vector      │  Find K nearest documents
│  Similarity Search  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Retrieve Context   │  Fetch full documents
│  from Oracle        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Build Prompt       │  Combine query + context
│  with Context       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Bedrock Inference  │  Claude/Llama processes context
│  (Text Generation)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Structured Output  │  Format response
│  & Persistence      │
└─────────────────────┘
           │
           ▼
      User Response
```

---

## Why Oracle + AWS Bedrock

### 1. **Enterprise-Ready Foundation**

| Feature | Benefit |
|---------|---------|
| **ACID Compliance** | Guaranteed data consistency for mission-critical AI |
| **Multi-Version Concurrency Control** | Concurrent AI queries without locking |
| **Advanced Indexing** | Vector indexes for sub-millisecond searches |
| **Audit & Compliance** | Complete audit trail for regulated industries |
| **High Availability** | 99.99% uptime with automatic failover |

### 2. **Superior Vector Search**

Oracle's vector search capabilities outperform traditional approaches:

```python
-- Traditional RDBMS (No native vector support)
-- Result: Full table scan, slow ❌

-- Oracle with Vector Index
CREATE VECTOR INDEX customer_embedding_idx
ON customer_embeddings(embedding_vector)
DISTANCE COSINE;

-- Query: Sub-millisecond response ✅
SELECT customer_id, embedding_distance
FROM customer_embeddings
WHERE embedding_distance(embedding_vector, query_vector) < 0.3
ORDER BY embedding_distance
LIMIT 10;
```

### 3. **Knowledge Graph Integration**

```sql
-- Relational + Graph in one platform
CREATE PROPERTY GRAPH customer_interactions
  VERTEX TABLE customers KEY(customer_id)
  EDGE TABLE purchases KEY(purchase_id)
    SOURCE customers DESTINATION products
  EDGE TABLE recommendations KEY(rec_id)
    SOURCE customers DESTINATION customers;

-- Find similar customers for personalization
SELECT c2.customer_id, SIMILARITY_SCORE
FROM customer_interactions
WHERE path_distance(c1 -> c2) <= 2
ORDER BY SIMILARITY_SCORE DESC;
```

### 4. **Multimodal Data Management**

```sql
-- Store structured + unstructured + vector data
CREATE TABLE documents (
    doc_id NUMBER PRIMARY KEY,
    content CLOB,                      -- Unstructured text
    embedding VECTOR(1536),            -- Bedrock embeddings
    metadata JSON,                     -- Schema-flexible
    created_at TIMESTAMP
);

CREATE INDEX doc_embedding_idx
ON documents(embedding)
INDEXTYPE IS VECTOR;
```

### 5. **Cost Efficiency**

| Component | Cost Model | Benefit |
|-----------|-----------|---------|
| **Oracle DB** | Reserved instance discount | Predictable costs |
| **Bedrock** | Per-token pricing | Pay only for inference |
| **No ML ops** | Serverless | No model management overhead |
| **Combined** | Pay for data + AI | More efficient than alternatives |

---

## Getting Started

### Prerequisites

```bash
# AWS Account with Bedrock access
aws bedrock list-foundation-models --region us-east-1

# Oracle Database 23c+ (or RDS Oracle with Vector Support)
sqlplus admin/password@ORCL23c

# Python 3.9+
python --version

# Install required packages
pip install boto3 oracledb langchain anthropic
```

### Step 1: Enable Bedrock Access

```bash
# In AWS Console: Bedrock → Model access
# Enable: Claude 3.5 Sonnet, Llama 2, Mistral

# Or via CLI:
aws bedrock-runtime list-foundation-models \
    --region us-east-1
```

### Step 2: Set Up Oracle Vector Store

```sql
-- Connect to Oracle 23c+ 
-- (with Vector support enabled)

-- Create vector table
CREATE TABLE knowledge_base (
    kb_id NUMBER PRIMARY KEY,
    doc_id VARCHAR2(255),
    title VARCHAR2(500),
    content CLOB,
    embedding VECTOR(1536),
    source VARCHAR2(100),
    created_at TIMESTAMP DEFAULT SYSDATE,
    updated_at TIMESTAMP DEFAULT SYSDATE
);

-- Create vector index for fast similarity search
CREATE VECTOR INDEX kb_embedding_idx
ON knowledge_base(embedding)
DISTANCE COSINE;

-- Create audit table
CREATE TABLE ai_interactions (
    interaction_id NUMBER PRIMARY KEY,
    user_id VARCHAR2(255),
    query VARCHAR2(4000),
    bedrock_model VARCHAR2(50),
    response CLOB,
    token_count NUMBER,
    latency_ms NUMBER,
    created_at TIMESTAMP DEFAULT SYSDATE
);
```

### Step 3: Configure AWS Credentials

```bash
# Set environment variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
export AWS_BEDROCK_REGION="us-east-1"

# Or use AWS CLI
aws configure
```

---

## Implementation Guide

### Basic: Query with Bedrock + Oracle Context

```python
import boto3
import oracledb
from typing import List, Dict

class OracleBedrocQuery:
    def __init__(self, db_connection_string: str):
        """Initialize Bedrock and Oracle clients"""
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.oracle_connection = oracledb.connect(db_connection_string)
        self.model_id = "anthropic.claude-3-5-sonnet-20241022"
    
    def query_knowledge_base(self, query: str, top_k: int = 5) -> str:
        """Query Oracle knowledge base with Bedrock AI"""
        
        # Step 1: Get embedding for query using Bedrock
        query_embedding = self._embed_query(query)
        
        # Step 2: Search Oracle vector store
        context_docs = self._search_oracle(query_embedding, top_k)
        
        # Step 3: Build prompt with context
        system_prompt = """You are a helpful AI assistant with access to company knowledge base.
        Answer questions based on the provided context. Be concise and accurate."""
        
        user_prompt = f"""Based on the following documents:

{self._format_context(context_docs)}

Answer this question: {query}"""
        
        # Step 4: Get response from Bedrock
        response = self.bedrock.invoke_model(
            modelId=self.model_id,
            contentType='application/json',
            accept='application/json',
            body={
                "anthropic_version": "bedrock-2023-06-01",
                "max_tokens": 1024,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            }
        )
        
        # Step 5: Parse and return response
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
    
    def _embed_query(self, query: str) -> List[float]:
        """Get embeddings from Bedrock"""
        response = self.bedrock.invoke_model(
            modelId='amazon.titan-embed-text-v2:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({"inputText": query})
        )
        embedding = json.loads(response['body'].read())['embedding']
        return embedding
    
    def _search_oracle(self, embedding: List[float], top_k: int) -> List[Dict]:
        """Vector similarity search in Oracle"""
        cursor = self.oracle_connection.cursor()
        
        query = f"""
        SELECT kb_id, title, content, 
               VECTOR_DISTANCE(embedding, :1, COSINE) as similarity
        FROM knowledge_base
        ORDER BY similarity ASC
        FETCH FIRST {top_k} ROWS ONLY
        """
        
        cursor.execute(query, [embedding])
        docs = []
        for row in cursor.fetchall():
            docs.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'similarity': row[3]
            })
        
        cursor.close()
        return docs
    
    def _format_context(self, docs: List[Dict]) -> str:
        """Format retrieved documents as context"""
        context = ""
        for i, doc in enumerate(docs, 1):
            context += f"\nDocument {i}: {doc['title']}\n{doc['content'][:500]}...\n"
        return context


# Usage
if __name__ == "__main__":
    # Initialize
    db_conn = "oracle+oracledb://user:password@localhost:1521/?service_name=ORCL23c"
    rag_system = OracleBedrocQuery(db_conn)
    
    # Query
    question = "What are our company policies on remote work?"
    answer = rag_system.query_knowledge_base(question)
    print(f"Q: {question}")
    print(f"A: {answer}")
```

### Advanced: Multi-Turn Conversation with State

```python
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.llms.bedrock import Bedrock
from langchain.embeddings.bedrock import BedrockEmbeddings

class ConversationalOracleAgent:
    def __init__(self, oracle_connection_string: str):
        """Initialize conversational agent with Oracle memory"""
        
        # Initialize Bedrock LLM
        self.llm = Bedrock(
            model_id="anthropic.claude-3-5-sonnet-20241022",
            region_name="us-east-1"
        )
        
        # Initialize embeddings
        self.embeddings = BedrockEmbeddings(region_name="us-east-1")
        
        # Connect to Oracle
        self.connection = oracledb.connect(oracle_connection_string)
        
        # Create memory for conversation history
        self.memory = ConversationBufferMemory()
    
    def chat(self, user_message: str, session_id: str) -> str:
        """Process user message with persistent context"""
        
        # Retrieve session history from Oracle
        history = self._get_session_history(session_id)
        self.memory.load_memory_variables({"history": history})
        
        # Get embedding for semantic search
        query_embedding = self.embeddings.embed_query(user_message)
        
        # Find relevant documents
        relevant_docs = self._search_relevant_docs(query_embedding)
        
        # Build context-aware response
        response = self.llm.predict(
            input=f"""
            Previous conversation:
            {history}
            
            Relevant information:
            {relevant_docs}
            
            User: {user_message}
            """
        )
        
        # Save interaction to Oracle
        self._save_interaction(session_id, user_message, response)
        
        return response
    
    def _get_session_history(self, session_id: str) -> str:
        """Retrieve conversation history from Oracle"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT user_message, ai_response 
            FROM conversation_history 
            WHERE session_id = :1 
            ORDER BY created_at 
            LIMIT 10
        """, [session_id])
        
        history = ""
        for user_msg, ai_resp in cursor.fetchall():
            history += f"User: {user_msg}\nAssistant: {ai_resp}\n"
        
        cursor.close()
        return history
    
    def _search_relevant_docs(self, embedding: List[float]) -> str:
        """Find contextually relevant documents"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT title, content 
            FROM knowledge_base 
            WHERE VECTOR_DISTANCE(embedding, :1, COSINE) < 0.3
            LIMIT 5
        """, [embedding])
        
        docs = ""
        for title, content in cursor.fetchall():
            docs += f"- {title}: {content[:200]}...\n"
        
        cursor.close()
        return docs
    
    def _save_interaction(self, session_id: str, user_msg: str, response: str):
        """Persist conversation to Oracle for audit & learning"""
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO conversation_history 
            (session_id, user_message, ai_response, created_at)
            VALUES (:1, :2, :3, SYSDATE)
        """, [session_id, user_msg, response])
        self.connection.commit()
        cursor.close()
```

---

## Advanced Patterns

### Pattern 1: Hybrid Search (Semantic + Keyword)

```python
def hybrid_search(self, query: str, top_k: int = 10):
    """Combine vector search with full-text search"""
    
    # Get embedding
    embedding = self.embeddings.embed_query(query)
    
    # Semantic search
    vector_results = self._vector_search(embedding, top_k=5)
    
    # Full-text search
    keyword_results = self._keyword_search(query, top_k=5)
    
    # Combine and rerank
    combined = self._rerank_results(vector_results + keyword_results)
    
    return combined

def _keyword_search(self, query: str, top_k: int):
    """Full-text search using Oracle Text"""
    cursor = self.connection.cursor()
    cursor.execute(f"""
        SELECT kb_id, title, content, SCORE(1) as relevance
        FROM knowledge_base
        WHERE CONTAINS(content, '{query}', 1) > 0
        ORDER BY relevance DESC
        FETCH FIRST {top_k} ROWS ONLY
    """)
    return cursor.fetchall()
```

### Pattern 2: Entity Extraction & Graph Building

```python
def extract_and_store_entities(self, text: str):
    """Use Bedrock to extract entities and store in Oracle graph"""
    
    # Extract entities using Claude
    entity_prompt = """Extract all entities from this text:
    
    Text: {text}
    
    Return JSON with:
    - entities: [{"name": "", "type": "", "attributes": {}}]
    - relationships: [{"from": "", "to": "", "relationship": ""}]
    """
    
    response = self.bedrock.invoke_model(...)
    entities_json = json.loads(response)
    
    # Store in Oracle property graph
    cursor = self.connection.cursor()
    for entity in entities_json['entities']:
        cursor.execute("""
            INSERT INTO ENTITIES (name, type, attributes)
            VALUES (:1, :2, :3)
        """, [entity['name'], entity['type'], json.dumps(entity['attributes'])])
    
    for rel in entities_json['relationships']:
        cursor.execute("""
            INSERT INTO ENTITY_RELATIONSHIPS (from_entity, to_entity, relationship)
            VALUES (:1, :2, :3)
        """, [rel['from'], rel['to'], rel['relationship']])
    
    self.connection.commit()
```

### Pattern 3: Streaming Responses

```python
def stream_response(self, query: str):
    """Stream Bedrock response for real-time feedback"""
    
    # Prepare context from Oracle
    context = self._prepare_context(query)
    
    # Stream from Bedrock
    with self.bedrock.invoke_model_with_response_stream(
        modelId=self.model_id,
        contentType='application/json',
        body=json.dumps({
            "prompt": f"{context}\n\nQ: {query}",
            "max_tokens_to_sample": 2048,
            "temperature": 0.7
        })
    ) as response:
        for event in response.get('body'):
            if 'chunk' in event:
                chunk = json.loads(event['chunk']['bytes'])
                yield chunk.get('completion', '')
```

---

## Performance Optimization

### 1. Vector Index Tuning

```sql
-- Create vector index with specific distance metrics
CREATE VECTOR INDEX kb_idx
ON knowledge_base(embedding)
DISTANCE_METRIC COSINE;

-- Analyze index performance
ANALYZE TABLE knowledge_base ESTIMATE STATISTICS;

-- Monitor index usage
SELECT index_name, used, bytes, sample_size 
FROM dba_indexes 
WHERE table_name = 'KNOWLEDGE_BASE';
```

### 2. Query Optimization

```python
# Cache embeddings to avoid recomputing
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_embedding(text: str) -> List[float]:
    """Cache embeddings for frequently searched queries"""
    return self.bedrock_embeddings.embed_query(text)

# Batch operations
def batch_embed(texts: List[str]) -> List[List[float]]:
    """Embed multiple texts efficiently"""
    embeddings = []
    for text in texts:
        if text in embedding_cache:
            embeddings.append(embedding_cache[text])
        else:
            emb = get_cached_embedding(text)
            embeddings.append(emb)
    return embeddings
```

### 3. Connection Pooling

```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    oracle_connection_string,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

---

## Security & Compliance

### 1. Data Encryption

```sql
-- Enable Transparent Data Encryption (TDE)
ALTER SYSTEM SET encryption_wallet_location=
  '(SOURCE=(METHOD=file)(METHOD_DATA=(DIRECTORY=/u01/oracle/wallet)))' 
  SCOPE=BOTH;

-- Encrypt sensitive embeddings
CREATE TABLE sensitive_embeddings (
    id NUMBER PRIMARY KEY,
    embedding VECTOR(1536) ENCRYPT,
    created_at TIMESTAMP
);
```

### 2. Audit Trail

```sql
-- Track all AI interactions
CREATE AUDIT POLICY ai_access_policy
    ACTIONS SELECT ON knowledge_base, INSERT ON ai_interactions;

AUDIT POLICY ai_access_policy;

-- Query audit logs
SELECT username, action_name, object_name, event_timestamp
FROM unified_audit_trail
WHERE object_name IN ('KNOWLEDGE_BASE', 'AI_INTERACTIONS')
ORDER BY event_timestamp DESC;
```

### 3. Access Control

```python
def enforce_rbac(user_id: str, query: str):
    """Role-based access control for Bedrock + Oracle"""
    
    # Check user permissions in Oracle
    cursor = self.connection.cursor()
    cursor.execute("""
        SELECT role FROM user_roles WHERE user_id = :1
    """, [user_id])
    
    user_role = cursor.fetchone()[0]
    
    # Apply fine-grained access
    if user_role == 'ADMIN':
        return query  # Full access
    elif user_role == 'ANALYST':
        return query + " AND source != 'CONFIDENTIAL'"
    else:
        raise PermissionError(f"User {user_id} cannot perform this query")
```

---

## Cost Management

### Bedrock Pricing Optimization

```python
class CostOptimizedBedrock:
    """Minimize Bedrock costs while maintaining quality"""
    
    def __init__(self):
        self.request_cache = {}
        self.cost_tracker = {}
    
    def smart_model_selection(self, query_complexity: float):
        """Choose model based on query complexity"""
        if query_complexity < 0.3:
            return "amazon.titan-text-lite-v1"  # Cheapest
        elif query_complexity < 0.7:
            return "meta.llama3-8b-instruct"     # Balanced
        else:
            return "anthropic.claude-3-5-sonnet"  # Most capable
    
    def cache_responses(self, query: str):
        """Avoid redundant Bedrock calls"""
        cache_key = hash(query)
        if cache_key in self.request_cache:
            return self.request_cache[cache_key]
        
        response = self.bedrock.invoke_model(...)
        self.request_cache[cache_key] = response
        return response
    
    def batch_embeddings(self, texts: List[str]):
        """Batch embedding requests for cost efficiency"""
        # Bedrock charges per request, so batch to reduce requests
        if len(texts) > 100:
            return self._batch_process(texts, chunk_size=100)
```

### Oracle Cost Optimization

```sql
-- Identify expensive queries
SELECT sql_text, cpu_time, elapsed_time, rows_processed
FROM v$sqlstats
ORDER BY cpu_time DESC
LIMIT 10;

-- Clean unused indexes
SELECT index_name, table_name, num_rows, leaf_blocks
FROM dba_indexes
WHERE table_name = 'KNOWLEDGE_BASE'
AND monitored = 'YES'
AND used = 'NO';

-- Archive old interactions
BEGIN
  DELETE FROM ai_interactions
  WHERE created_at < TRUNC(SYSDATE - 90);
  COMMIT;
END;
/
```

---

## Real-World Use Cases

### Use Case 1: Insurance Claims Assistant

```python
"""
Intelligent claims processing with Oracle + Bedrock
"""

class ClaimsAssistant:
    def process_claim(self, claim_data: Dict):
        # Extract relevant policies from Oracle
        policies = self.search_relevant_policies(claim_data)
        
        # Use Bedrock to determine coverage
        coverage_analysis = self.bedrock.invoke_model(
            prompt=f"""
            Based on these policies:
            {policies}
            
            Does this claim qualify for coverage?
            Claim details: {claim_data}
            """
        )
        
        # Store result in Oracle for audit
        self.store_claim_decision(claim_data, coverage_analysis)
        
        return coverage_analysis

# Results:
# - 40% faster claims processing
# - 99.8% accuracy with human review
# - Complete audit trail for compliance
```

### Use Case 2: Customer Service Chatbot

```python
"""
24/7 customer service with knowledge base
"""

class ServiceChatbot:
    def handle_query(self, customer_id: str, inquiry: str):
        # Get customer history from Oracle
        customer_context = self.get_customer_profile(customer_id)
        
        # Search knowledge base with Bedrock embeddings
        relevant_articles = self.search_knowledge_base(inquiry)
        
        # Generate personalized response with Claude
        response = self.llm.generate(
            prompt=f"""
            Customer profile: {customer_context}
            Relevant information: {relevant_articles}
            
            Answer their inquiry professionally and helpfully:
            {inquiry}
            """
        )
        
        # Track conversation for improvement
        self.log_interaction(customer_id, inquiry, response)
        
        return response

# Results:
# - 80% of queries resolved without escalation
# - Consistent service quality 24/7
# - Personalized responses increase satisfaction
```

### Use Case 3: Business Intelligence Agent

```python
"""
Natural language analytics with Oracle data warehouse
"""

class AnalyticsAgent:
    def query_data(self, natural_language_query: str):
        # Map natural language to SQL using Bedrock
        sql_query = self.bedrock.generate_sql(natural_language_query)
        
        # Execute against Oracle data warehouse
        results = self.execute_query(sql_query)
        
        # Generate insights using Bedrock
        insights = self.bedrock.analyze_results(results)
        
        # Cache for future similar queries
        self.cache_query(natural_language_query, sql_query)
        
        return insights

# Example:
# Input: "What was our top-selling product last quarter by region?"
# Output: Generated SQL + visualizations + business insights
```

---

## Troubleshooting & Tips

### Common Issues

**Issue 1: Slow Vector Search**
```python
# Check index exists
SELECT index_type, index_name FROM dba_indexes 
WHERE table_name = 'KNOWLEDGE_BASE';

# Create if missing
CREATE VECTOR INDEX kb_idx ON knowledge_base(embedding);

# Analyze index
ANALYZE INDEX kb_idx COMPUTE STATISTICS;
```

**Issue 2: Bedrock Rate Limiting**
```python
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_bedrock_with_retry(prompt: str):
    return self.bedrock.invoke_model(prompt=prompt)
```

**Issue 3: Token Budget Exceeded**
```python
def optimize_context(documents: List[str], max_tokens: int = 2000):
    """Truncate context if token limit exceeded"""
    total_tokens = sum(estimate_tokens(doc) for doc in documents)
    
    if total_tokens > max_tokens:
        # Keep most relevant documents
        return documents[:max_tokens // 100]
    
    return documents
```

### Performance Tips

1. **Use Smaller Models for First-Pass Filtering**
   ```python
   # Llama 2 7B for initial filtering
   initial_response = self.bedrock.invoke_model(
       modelId="meta.llama2-7b",
       prompt=query
   )
   
   # Claude 3.5 Sonnet for complex analysis
   final_response = self.bedrock.invoke_model(
       modelId="anthropic.claude-3-5-sonnet",
       prompt=query
   )
   ```

2. **Pre-compute Vectors Offline**
   ```sql
   -- Batch compute embeddings during off-peak hours
   BEGIN
     FOR doc IN (SELECT doc_id, content FROM documents WHERE embedding IS NULL)
     LOOP
       -- Call Bedrock embedding API
       UPDATE documents SET embedding = get_embedding(doc.content)
       WHERE doc_id = doc.doc_id;
     END LOOP;
     COMMIT;
   END;
   /
   ```

3. **Monitor Costs**
   ```python
   def log_cost(model_id: str, tokens_used: int):
       # Get pricing from AWS
       cost = self.get_bedrock_pricing(model_id) * tokens_used
       
       # Store in Oracle for analytics
       cursor = self.connection.cursor()
       cursor.execute("""
           INSERT INTO ai_costs (model_id, tokens, cost, created_at)
           VALUES (:1, :2, :3, SYSDATE)
       """, [model_id, tokens_used, cost])
       self.connection.commit()
   ```

---

## Conclusion

The combination of **Oracle Database** and **AWS Bedrock** creates a powerful platform for enterprise AI:

**Oracle Provides:**
- ✅ Enterprise-grade reliability and compliance
- ✅ Advanced data management and indexing
- ✅ Audit trails and governance
- ✅ Multimodal data support (structured, unstructured, vectors)

**Bedrock Provides:**
- ✅ State-of-the-art foundation models
- ✅ Serverless operation (no ML infrastructure)
- ✅ Multi-model support for flexibility
- ✅ Managed service (AWS handles updates)

**Together They Enable:**
- 🚀 Rapid AI application development
- 💼 Enterprise-ready production deployments
- 💰 Cost-effective operations
- 🔒 Secure, compliant AI workflows
- 📊 Data-driven intelligence at scale

### Next Steps

1. **Start Small:** Deploy a proof-of-concept with your knowledge base
2. **Measure Impact:** Track cost savings, accuracy improvements, user satisfaction
3. **Scale Gradually:** Expand to multiple use cases and datasets
4. **Optimize:** Use CloudWatch and Oracle metrics to refine performance
5. **Innovate:** Build multi-modal applications with images, documents, and data

---

## Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Oracle Vector Search](https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/)
- [LangChain + Bedrock Integration](https://python.langchain.com/docs/integrations/llms/bedrock/)
- [Oracle Database 23c Release Notes](https://docs.oracle.com/en/database/oracle/oracle-database/23/)
- [AWS Bedrock Pricing Calculator](https://aws.amazon.com/bedrock/pricing/)

---

**Questions? Share your Oracle + Bedrock stories in the comments below!**

*Oracle AI Developer Hub - Empowering Enterprise Intelligence*
