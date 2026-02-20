# Commonly Used Libraries for Agent Memory

## High-Level Frameworks

### LangChain Memory
- **Most popular** choice for agent implementations
- Multiple memory types available:
  - `ConversationMemory` - Basic conversation history
  - `EntityMemory` - Tracks entities across conversations
  - `VectorStoreMemory` - Semantic memory using embeddings
  - `BufferMemory` - Simple token-windowed memory
  - `SummaryMemory` - LLM-based conversation summarization
- Easy integration with LangChain agents and tools
- [LangChain Memory Documentation](https://python.langchain.com/docs/modules/memory/)

### LlamaIndex
- Document-focused memory and RAG patterns
- Built-in conversation memory for chat applications
- Strong for retrieval-augmented generation (RAG)
- Memory nodes and storage backends

### Semantic Kernel (Microsoft)
- Memory API for kernel-based agents
- Plugin architecture for memory extensions
- Strong for enterprise applications

## Vector Databases (Semantic Memory)

### Cloud-Managed Solutions
- **Pinecone** - Fully managed, serverless vector DB
- **Weaviate** - Open-source with GraphQL API
- **Milvus** - High-performance open-source vector database
- **Qdrant** - Vector similarity search engine

### Lightweight/Embedded Solutions
- **Chroma (ChromaDB)** - Lightweight, embeddable vector store, great for local development
- **FAISS** - Facebook's efficient similarity search library
- **Annoy** - Approximate nearest neighbors

### Database Extensions
- **pgvector** - PostgreSQL extension for vector operations
- **Redis Stack** - Redis with vector capabilities
  
## Traditional Databases

- **Redis** - Fast in-memory caching and session memory
- **SQLAlchemy** - ORM for structured conversation history
- **SQLite** - Lightweight local database storage
- **PostgreSQL** - Scalable structured memory with pgvector
- **MongoDB** - Document-based conversation storage
- **Oracle Database**  

## Specialized Agent Memory Libraries

### MemGPT
- Virtual context manager with external memory
- Handles long-term memory for extended interactions
- Persistent memory across sessions

### AutoGPT Memory
- Memory management optimized for autonomous agents
- Hierarchical memory structures
- Priority-based memory management

### ReAct (Reasoning + Acting)
- Memory patterns for reasoning and acting agent loops
- Thought-action-observation chains

### Haystack
- Semantic search and retrieval pipeline
- Integration with multiple backends
- RAG pipeline support

## Memory Pattern Comparison

| Type | Best For | Pros | Cons |
|------|----------|------|------|
| **Vector DB** | Semantic search, RAG | Semantic matching, scalable | Cost, latency |
| **SQLite** | Dev/local testing | No setup, lightweight | No scaling |
| **Redis** | Real-time access, caching | Ultra-fast, TTL support | Expensive, limited persistence |
| **PostgreSQL** | Production, complex queries | Powerful, reliable | More setup required |
| **LangChain Memory** | Quick agent prototyping | Simple integration, flexible | Limited for production scale |

## Selection Criteria

- **Single-turn conversations** → LangChain BufferMemory
- **Long-term semantic search** → Vector DB (Pinecone/Weaviate)
- **Cost-conscious local dev** → SQLite + Chroma
- **Production RAG applications** → PostgreSQL + pgvector or Pinecone
- **Real-time access patterns** → Redis + SQLite backup
- **Multi-session autonomous agents** → MemGPT or Redis with structured schema

## Example Usage Patterns

```python
# LangChain with conversation memory
from langchain.memory import ConversationBufferMemory
memory = ConversationBufferMemory()

# Vector-based semantic memory
from langchain.memory import VectorStoreMemory
vector_memory = VectorStoreMemory(vectorstore=vectorstore)

# Hybrid approach
from langchain.agents import AgentType, initialize_agent
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    memory=memory
)
```