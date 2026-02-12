"""
Oracle Database Memory Store for AI Agents
Integrates with LangChain for agent memory management

This module provides a production-ready memory store using Oracle Database
for AI agents, supporting conversation history, entity tracking, and session management.

Features:
- LangChain SQLChatMessageHistory for conversation persistence
- LangChain SQL Database agent for querying
- Vector embeddings with Oracle Vector Store
- Full LangChain memory integration
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import sqlalchemy as sa
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Index, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from langchain.memory import BaseMemory, ConversationBufferMemory, ConversationSummaryMemory
from langchain.chat_history import BaseChatMessageHistory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.sql_database import SQLDatabase
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.llms.base import BaseLanguageModel
from langchain.embeddings.base import Embeddings

# ============================================================================
# 1. Oracle Database Models (SQLAlchemy ORM)
# ============================================================================

Base = declarative_base()


class ConversationMemory(Base):
    """Stores conversation history in Oracle database"""
    __tablename__ = "agent_conversation_memory"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    agent_id = Column(String(255), nullable=False, index=True)
    message_type = Column(String(50), nullable=False)  # 'human' or 'ai'
    content = Column(Text, nullable=False)
    metadata = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_session_agent_created', 'session_id', 'agent_id', 'created_at'),
    )
    
    def to_message(self) -> BaseMessage:
        """Convert DB record to LangChain message"""
        if self.message_type == "human":
            return HumanMessage(content=self.content)
        else:
            return AIMessage(content=self.content)


class EntityMemory(Base):
    """Stores extracted entities and facts for agent reasoning"""
    __tablename__ = "agent_entity_memory"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    agent_id = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False)  # 'person', 'location', etc.
    entity_name = Column(String(255), nullable=False)
    entity_value = Column(Text, nullable=False)  # JSON string for complex data
    last_mentioned = Column(DateTime, default=datetime.utcnow)
    mention_count = Column(Integer, default=1)
    
    __table_args__ = (
        Index('idx_session_entity_type', 'session_id', 'agent_id', 'entity_type'),
        Index('idx_entity_name', 'entity_name'),
    )


class AgentTask(Base):
    """Stores agent tasks and execution history"""
    __tablename__ = "agent_tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    agent_id = Column(String(255), nullable=False, index=True)
    task_description = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending, in_progress, completed, failed
    result = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_session_status', 'session_id', 'status'),
    )


class VectorEmbedding(Base):
    """Stores vector embeddings for semantic search"""
    __tablename__ = "agent_vector_embeddings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    agent_id = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Text, nullable=False)  # JSON array as string
    metadata = Column(Text)  # JSON string with source, type, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_session_vector', 'session_id', 'agent_id'),
    )


# ============================================================================
# 2. LangChain Chat Message History
# ============================================================================

class OracleSQLChatMessageHistory(BaseChatMessageHistory):
    """
    LangChain-compatible chat message history using Oracle database.
    Implements the BaseChatMessageHistory interface from LangChain.
    """
    
    def __init__(
        self,
        engine: sa.engine.Engine,
        session_id: str,
        agent_id: str = "default_agent",
    ):
        """Initialize Oracle chat message history"""
        self.engine = engine
        self.session_id = session_id
        self.agent_id = agent_id
        self.SessionLocal = sessionmaker(bind=engine)
    
    @property
    def messages(self) -> List[BaseMessage]:
        """Get all messages from Oracle"""
        session = self.SessionLocal()
        try:
            records = session.query(ConversationMemory).filter(
                ConversationMemory.session_id == self.session_id,
                ConversationMemory.agent_id == self.agent_id,
            ).order_by(ConversationMemory.created_at).all()
            
            return [msg.to_message() for msg in records]
        finally:
            session.close()
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to Oracle"""
        session = self.SessionLocal()
        try:
            if isinstance(message, HumanMessage):
                msg_type = "human"
            elif isinstance(message, AIMessage):
                msg_type = "ai"
            else:
                msg_type = "system"
            
            db_msg = ConversationMemory(
                session_id=self.session_id,
                agent_id=self.agent_id,
                message_type=msg_type,
                content=message.content,
            )
            session.add(db_msg)
            session.commit()
        finally:
            session.close()
    
    def clear(self) -> None:
        """Clear all messages for this session"""
        session = self.SessionLocal()
        try:
            session.query(ConversationMemory).filter(
                ConversationMemory.session_id == self.session_id,
                ConversationMemory.agent_id == self.agent_id,
            ).delete()
            session.commit()
        finally:
            session.close()


# ============================================================================
# 3. Oracle Connection Configuration
# ============================================================================

class OracleMemoryConfig:
    """Configuration for Oracle memory store and LangChain integration"""
    
    def __init__(
        self,
        username: str,
        password: str,
        host: str,
        port: int = 1521,
        service_name: Optional[str] = None,
        sid: Optional[str] = None,
    ):
        """
        Initialize Oracle connection configuration.
        
        Args:
            username: Oracle username
            password: Oracle password
            host: Oracle host address
            port: Oracle port (default 1521)
            service_name: Oracle service name (for Oracle Cloud/modern setup)
            sid: Oracle SID (for on-premise traditional setup)
            
        Example:
            config = OracleMemoryConfig(
                username="admin",
                password="password123",
                host="oracle.example.com",
                service_name="orcl"
            )
        """
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.service_name = service_name
        self.sid = sid
        
        if not service_name and not sid:
            raise ValueError("Either service_name or sid must be provided")
    
    def get_connection_string(self) -> str:
        """Generate Oracle connection string for SQLAlchemy"""
        if self.service_name:
            # Oracle Cloud or modern setup
            dsn = f"{self.host}:{self.port}/{self.service_name}"
            return f"oracle+oracledb://{self.username}:{self.password}@{dsn}"
        else:
            # Traditional setup with SID
            dsn = f"{self.host}:{self.port}:{self.sid}"
            return f"oracle+oracledb://{self.username}:{self.password}@{dsn}"


# ============================================================================
# 3. Oracle Memory Store Implementation
# ============================================================================

class OracleAgentMemory(BaseMemory):
    """
    LangChain-compatible memory store using Oracle database.
    
    Provides persistent storage for:
    - Conversation history
    - Entity extraction and tracking
    - Task execution records
    - Agent state management
    """
    
    def __init__(
        self,
        engine: sa.engine.Engine,
        session_id: str,
        agent_id: str = "default_agent",
        max_context_length: int = 10,
    ):
        """
        Initialize Oracle agent memory.
        
        Args:
            engine: SQLAlchemy engine for Oracle
            session_id: Unique conversation session ID
            agent_id: Agent identifier
            max_context_length: Max messages to retrieve for context window
        """
        super().__init__()
        self.engine = engine
        self.session_id = session_id
        self.agent_id = agent_id
        self.max_context_length = max_context_length
        self.SessionLocal = sessionmaker(bind=engine)
    
    @property
    def memory_variables(self) -> List[str]:
        """Return memory variable names for LangChain"""
        return ["history"]
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve conversation history from Oracle.
        Called by LangChain agent before processing input.
        """
        session = self.SessionLocal()
        try:
            messages = session.query(ConversationMemory).filter(
                ConversationMemory.session_id == self.session_id,
                ConversationMemory.agent_id == self.agent_id,
            ).order_by(ConversationMemory.created_at).limit(
                self.max_context_length
            ).all()
            
            history = "\n".join([
                f"{msg.message_type.upper()}: {msg.content}" 
                for msg in messages
            ])
            return {"history": history}
        finally:
            session.close()
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """
        Save user input and AI response to Oracle.
        Called by LangChain agent after processing.
        """
        session = self.SessionLocal()
        try:
            # Save user message
            if "input" in inputs:
                user_msg = ConversationMemory(
                    session_id=self.session_id,
                    agent_id=self.agent_id,
                    message_type="human",
                    content=inputs["input"],
                    metadata=json.dumps({"type": "user_input"})
                )
                session.add(user_msg)
            
            # Save AI response
            if "output" in outputs:
                ai_msg = ConversationMemory(
                    session_id=self.session_id,
                    agent_id=self.agent_id,
                    message_type="ai",
                    content=outputs["output"],
                    metadata=json.dumps({"type": "agent_response"})
                )
                session.add(ai_msg)
            
            session.commit()
        except Exception as e:
            session.rollback()
            raise Exception(f"Error saving context to Oracle: {e}")
        finally:
            session.close()
    
    def clear(self) -> None:
        """Clear all conversation history for this session"""
        session = self.SessionLocal()
        try:
            session.query(ConversationMemory).filter(
                ConversationMemory.session_id == self.session_id,
                ConversationMemory.agent_id == self.agent_id,
            ).delete()
            session.commit()
        finally:
            session.close()
    
    def add_entity(self, entity_type: str, entity_name: str, entity_value: Dict) -> None:
        """
        Store extracted entity in Oracle.
        
        Args:
            entity_type: Type of entity (e.g., 'person', 'location', 'organization')
            entity_name: Name of the entity
            entity_value: Dictionary containing entity attributes
        """
        session = self.SessionLocal()
        try:
            existing = session.query(EntityMemory).filter(
                EntityMemory.session_id == self.session_id,
                EntityMemory.agent_id == self.agent_id,
                EntityMemory.entity_type == entity_type,
                EntityMemory.entity_name == entity_name,
            ).first()
            
            if existing:
                existing.entity_value = json.dumps(entity_value)
                existing.last_mentioned = datetime.utcnow()
                existing.mention_count += 1
            else:
                entity = EntityMemory(
                    session_id=self.session_id,
                    agent_id=self.agent_id,
                    entity_type=entity_type,
                    entity_name=entity_name,
                    entity_value=json.dumps(entity_value),
                )
                session.add(entity)
            
            session.commit()
        finally:
            session.close()
    
    def get_entities(self, entity_type: Optional[str] = None) -> List[Dict]:
        """
        Retrieve stored entities from Oracle.
        
        Args:
            entity_type: Optional filter by entity type
            
        Returns:
            List of entities with their metadata
        """
        session = self.SessionLocal()
        try:
            query = session.query(EntityMemory).filter(
                EntityMemory.session_id == self.session_id,
                EntityMemory.agent_id == self.agent_id,
            )
            
            if entity_type:
                query = query.filter(EntityMemory.entity_type == entity_type)
            
            entities = []
            for e in query.all():
                entities.append({
                    "type": e.entity_type,
                    "name": e.entity_name,
                    "value": json.loads(e.entity_value),
                    "mention_count": e.mention_count,
                    "last_mentioned": e.last_mentioned.isoformat(),
                })
            
            return entities
        finally:
            session.close()
    
    def add_task(self, task_description: str, result: Optional[Dict] = None) -> int:
        """
        Record a task or action taken by the agent.
        
        Args:
            task_description: Description of the task
            result: Optional result data as dictionary
            
        Returns:
            Task ID
        """
        session = self.SessionLocal()
        try:
            task = AgentTask(
                session_id=self.session_id,
                agent_id=self.agent_id,
                task_description=task_description,
                status="in_progress",
                result=json.dumps(result) if result else None,
            )
            session.add(task)
            session.commit()
            return task.id
        finally:
            session.close()
    
    def update_task_status(self, task_id: int, status: str, result: Optional[Dict] = None) -> None:
        """
        Update task status and result.
        
        Args:
            task_id: ID of task to update
            status: New status (pending, in_progress, completed, failed)
            result: Optional result data
        """
        session = self.SessionLocal()
        try:
            task = session.query(AgentTask).filter(AgentTask.id == task_id).first()
            if task:
                task.status = status
                if result:
                    task.result = json.dumps(result)
                if status == "completed":
                    task.completed_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()
    
    def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get complete conversation history for this session.
        
        Args:
            limit: Optional limit on number of messages
            
        Returns:
            List of conversation messages
        """
        session = self.SessionLocal()
        try:
            query = session.query(ConversationMemory).filter(
                ConversationMemory.session_id == self.session_id,
                ConversationMemory.agent_id == self.agent_id,
            ).order_by(ConversationMemory.created_at)
            
            if limit:
                query = query.limit(limit)
            
            history = []
            for msg in query.all():
                history.append({
                    "id": msg.id,
                    "type": msg.message_type,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "metadata": json.loads(msg.metadata) if msg.metadata else {},
                })
            
            return history
        finally:
            session.close()
    
    def get_chat_message_history(self) -> OracleSQLChatMessageHistory:
        """
        Get LangChain-compatible chat message history.
        Use this with LangChain's memory classes and chains.
        
        Returns:
            OracleSQLChatMessageHistory instance
        """
        return OracleSQLChatMessageHistory(
            engine=self.engine,
            session_id=self.session_id,
            agent_id=self.agent_id
        )
    
    def add_embedding(self, content: str, embedding: List[float], metadata: Optional[Dict] = None) -> None:
        """
        Store vector embedding for semantic search.
        
        Args:
            content: Original text content
            embedding: Vector embedding (list of floats)
            metadata: Optional metadata dictionary
        """
        session = self.SessionLocal()
        try:
            vector_record = VectorEmbedding(
                session_id=self.session_id,
                agent_id=self.agent_id,
                content=content,
                embedding=json.dumps(embedding),
                metadata=json.dumps(metadata) if metadata else None,
            )
            session.add(vector_record)
            session.commit()
        finally:
            session.close()
    
    def get_embeddings(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Retrieve stored embeddings for semantic search.
        
        Args:
            limit: Optional limit on results
            
        Returns:
            List of embeddings with content and metadata
        """
        session = self.SessionLocal()
        try:
            query = session.query(VectorEmbedding).filter(
                VectorEmbedding.session_id == self.session_id,
                VectorEmbedding.agent_id == self.agent_id,
            ).order_by(VectorEmbedding.created_at)
            
            if limit:
                query = query.limit(limit)
            
            embeddings = []
            for record in query.all():
                embeddings.append({
                    "id": record.id,
                    "content": record.content,
                    "embedding": json.loads(record.embedding),
                    "metadata": json.loads(record.metadata) if record.metadata else {},
                    "created_at": record.created_at.isoformat(),
                })
            
            return embeddings
        finally:
            session.close()


# ============================================================================
# 4. LangChain Agent Builders
# ============================================================================

class OracleSQLAgentBuilder:
    """Builder for creating LangChain SQL agents with Oracle database"""
    
    @staticmethod
    def create_sql_agent(
        oracle_config: OracleMemoryConfig,
        llm: BaseLanguageModel,
        verbose: bool = True,
    ):
        """
        Create a LangChain SQL agent for Oracle database queries.
        
        Args:
            oracle_config: OracleMemoryConfig instance
            llm: LangChain language model (e.g., OpenAI, Claude)
            verbose: Whether to show agent reasoning
            
        Returns:
            LangChain agent executor for SQL operations
            
        Example:
            from langchain.llms import OpenAI
            
            config = OracleMemoryConfig(...)
            llm = OpenAI(temperature=0)
            agent = OracleSQLAgentBuilder.create_sql_agent(config, llm)
            result = agent.run("How many records are in the customers table?")
        """
        # Create SQLAlchemy engine
        engine = create_engine(oracle_config.get_connection_string())
        
        # Create LangChain SQL database instance
        db = SQLDatabase(engine)
        
        # Create toolkit for SQL operations
        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        
        # Create agent with SQL tools
        agent = create_sql_agent(
            llm=llm,
            toolkit=toolkit,
            verbose=verbose,
            agent_type="openai-tools",
        )
        
        return agent


class OracleLangChainMemoryBuilder:
    """Builder for creating LangChain memory chains with Oracle"""
    
    @staticmethod
    def create_conversation_memory(
        oracle_config: OracleMemoryConfig,
        session_id: str,
        agent_id: str = "default_agent",
        llm: Optional[BaseLanguageModel] = None,
    ) -> ConversationBufferMemory:
        """
        Create LangChain ConversationBufferMemory with Oracle backend.
        
        Args:
            oracle_config: OracleMemoryConfig instance
            session_id: Conversation session ID
            agent_id: Agent identifier
            llm: Optional LLM for memory operations
            
        Returns:
            ConversationBufferMemory configured with Oracle
        """
        memory = create_oracle_agent_memory(
            oracle_config=oracle_config,
            session_id=session_id,
            agent_id=agent_id
        )
        
        return ConversationBufferMemory(
            chat_memory=memory.get_chat_message_history(),
            return_messages=True
        )
    
    @staticmethod
    def create_conversation_summary_memory(
        oracle_config: OracleMemoryConfig,
        session_id: str,
        llm: BaseLanguageModel,
        agent_id: str = "default_agent",
    ) -> ConversationSummaryMemory:
        """
        Create LangChain ConversationSummaryMemory with Oracle backend.
        Summarizes conversation over time to maintain context.
        
        Args:
            oracle_config: OracleMemoryConfig instance
            session_id: Conversation session ID
            llm: Language model for summarization
            agent_id: Agent identifier
            
        Returns:
            ConversationSummaryMemory configured with Oracle
        """
        memory = create_oracle_agent_memory(
            oracle_config=oracle_config,
            session_id=session_id,
            agent_id=agent_id
        )
        
        return ConversationSummaryMemory(
            llm=llm,
            chat_memory=memory.get_chat_message_history(),
            return_messages=True
        )


# ============================================================================
# 5. Factory and Utility Functions
# ============================================================================

def create_oracle_agent_memory(
    oracle_config: OracleMemoryConfig,
    session_id: str,
    agent_id: str = "default_agent",
    create_tables: bool = True
) -> OracleAgentMemory:
    """
    Factory function to create Oracle memory store.
    
    Args:
        oracle_config: OracleMemoryConfig instance
        session_id: Unique session identifier
        agent_id: Agent identifier
        create_tables: Whether to create tables if they don't exist
        
    Returns:
        OracleAgentMemory instance
    """
    engine = create_engine(oracle_config.get_connection_string())
    
    # Create tables if they don't exist
    if create_tables:
        Base.metadata.create_all(engine)
    
    return OracleAgentMemory(
        engine=engine,
        session_id=session_id,
        agent_id=agent_id
    )


def test_oracle_connection(oracle_config: OracleMemoryConfig) -> bool:
    """
    Test Oracle database connection.
    
    Args:
        oracle_config: OracleMemoryConfig instance
        
    Returns:
        True if connection successful
    """
    try:
        engine = create_engine(oracle_config.get_connection_string())
        with engine.connect() as conn:
            result = conn.execute(sa.text("SELECT 1 FROM DUAL"))
            return result.fetchone() is not None
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False


# ============================================================================
# 6. Complete Usage Examples
# ============================================================================

if __name__ == "__main__":
    """
    Example usage with LangChain Agent and Oracle Database
    """
    
    # ========================================================================
    # Example 1: Basic Memory Setup with LangChain
    # ========================================================================
    print("=" * 70)
    print("EXAMPLE 1: Basic Oracle Memory with LangChain")
    print("=" * 70)
    
    # Configure Oracle connection
    oracle_config = OracleMemoryConfig(
        username="your_username",
        password="your_password",
        host="your_oracle_host",
        port=1521,
        service_name="your_service_name"
        # OR use sid for traditional setup:
        # sid="orcl"
    )
    
    # Test connection
    if test_oracle_connection(oracle_config):
        print("✓ Oracle connection successful\n")
    else:
        print("✗ Oracle connection failed")
        exit(1)
    
    # Create memory store with Oracle backend
    memory = create_oracle_agent_memory(
        oracle_config=oracle_config,
        session_id="chat_session_001",
        agent_id="financial_advisor"
    )
    
    # ========================================================================
    # Example 2: LangChain Agent with SQL Capabilities
    # ========================================================================
    print("\n" + "=" * 70)
    print("EXAMPLE 2: SQL Agent with Oracle Database")
    print("=" * 70)
    
    try:
        from langchain.llms import OpenAI
        from langchain.agents import initialize_agent, AgentType, Tool
        from langchain.chains import ConversationChain
        
        # Initialize LLM
        llm = OpenAI(temperature=0, api_key="your_openai_key")
        
        # Example 2A: Create SQL agent for database queries
        print("\n2A. Creating SQL Agent...")
        sql_agent = OracleSQLAgentBuilder.create_sql_agent(
            oracle_config=oracle_config,
            llm=llm,
            verbose=False
        )
        print("✓ SQL Agent created successfully")
        # You can use: sql_agent.run("SELECT COUNT(*) FROM customers")
        
        # Example 2B: Create basic agent with tools
        print("\n2B. Creating General Agent with Tools...")
        tools = [
            Tool(
                name="Calculator",
                func=lambda x: str(eval(x)),
                description="Useful for mathematical calculations"
            ),
        ]
        
        agent = initialize_agent(
            tools,
            llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            memory=memory,
            verbose=True
        )
        
        # Example interaction
        print("\nAgent Conversation:")
        response1 = agent.run("What is 25 * 4?")
        print(f"Response: {response1}\n")
        
        response2 = agent.run("Multiply that by 2")
        print(f"Response: {response2}")
        
    except ImportError as e:
        print(f"Note: {e}")
        print("Install with: pip install langchain openai")
    except Exception as e:
        print(f"Error in agent setup: {e}")
    
    # ========================================================================
    # Example 3: Conversation Chain with Oracle Memory
    # ========================================================================
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Conversation Chain with Oracle Backend")
    print("=" * 70)
    
    try:
        from langchain.chains import ConversationChain
        from langchain.llms import OpenAI
        
        llm = OpenAI(temperature=0.7, api_key="your_openai_key")
        
        # Create conversation buffer memory with Oracle backend
        conversation_memory = OracleLangChainMemoryBuilder.create_conversation_memory(
            oracle_config=oracle_config,
            session_id="conversation_001",
            agent_id="chat_bot"
        )
        
        # Create conversation chain
        conversation = ConversationChain(
            llm=llm,
            memory=conversation_memory,
            verbose=True
        )
        
        print("\n✓ Conversation chain created with Oracle memory backend")
        # You can use: conversation.run("How are you?")
        
    except Exception as e:
        print(f"Note: Skipping conversation chain example - {e}")
    
    # ========================================================================
    # Example 4: Vector Embeddings for Semantic Search
    # ========================================================================
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Vector Embeddings with Oracle")
    print("=" * 70)
    
    try:
        from langchain.embeddings import OpenAIEmbeddings
        
        embeddings = OpenAIEmbeddings(api_key="your_openai_key")
        
        # Add sample embeddings
        sample_text = "Oracle database is a powerful enterprise database"
        embedding = embeddings.embed_query(sample_text)
        
        memory.add_embedding(
            content=sample_text,
            embedding=embedding,
            metadata={"source": "documentation", "type": "system_message"}
        )
        
        print(f"✓ Stored embedding for text: '{sample_text[:50]}...'")
        
        # Retrieve embeddings
        stored_embeddings = memory.get_embeddings(limit=5)
        print(f"  Retrieved {len(stored_embeddings)} embeddings from Oracle")
        
    except Exception as e:
        print(f"Note: Skipping embeddings example - {e}")
    
    # ========================================================================
    # Example 5: Verify Stored Data
    # ========================================================================
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Verify Stored Data in Oracle")
    print("=" * 70)
    
    print("\n=== Stored Conversation History ===")
    history = memory.get_conversation_history(limit=5)
    if history:
        for msg in history:
            content_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            print(f"[{msg['type'].upper()}] {content_preview}")
    else:
        print("No conversation history stored yet")
    
    print("\n=== Stored Entities ===")
    entities = memory.get_entities()
    if entities:
        for entity in entities:
            print(f"  {entity['type']}: {entity['name']} (mentioned {entity['mention_count']}x)")
    else:
        print("No entities stored yet")
    
    print("\n=== Session Information ===")
    print(f"Session ID: {memory.session_id}")
    print(f"Agent ID: {memory.agent_id}")
    print(f"Max Context Length: {memory.max_context_length} messages")
    
    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
