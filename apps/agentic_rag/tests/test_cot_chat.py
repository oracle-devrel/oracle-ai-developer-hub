import sys
import logging
import json
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from src.gradio_app import chat
from src.store import VectorStore
from src.local_rag_agent import LocalRAGAgent

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def debug_response_structure(response, prefix=""):
    """Helper function to debug response structure"""
    logger.debug(f"{prefix}Response type: {type(response)}")
    if isinstance(response, dict):
        logger.debug(f"{prefix}Response keys: {list(response.keys())}")
        for key, value in response.items():
            logger.debug(f"{prefix}Key '{key}' type: {type(value)}")
            if isinstance(value, list):
                logger.debug(f"{prefix}List length: {len(value)}")
                if value and isinstance(value[0], dict):
                    logger.debug(f"{prefix}First item keys: {list(value[0].keys())}")
    elif isinstance(response, str):
        logger.debug(f"{prefix}String length: {len(response)}")
        logger.debug(f"{prefix}First 100 chars: {response[:100]}")

def test_cot_chat():
    """Test the CoT chat interface with detailed logging"""
    try:
        # Initialize components
        logger.info("Initializing vector store...")
        try:
            from src.OraDBVectorStore import OraDBVectorStore
            vector_store = OraDBVectorStore()
            logger.info("Using Oracle DB Vector Store")
        except ImportError:
            vector_store = VectorStore()
            logger.info("Using ChromaDB Vector Store")
        
        logger.info("Initializing local agent...")
        agent = LocalRAGAgent(vector_store, model_name="gemma3:270m", use_cot=True)
        
        # Test message
        test_message = "What is self-instruct in AI?"
        logger.info(f"Test message: {test_message}")
        
        # Initialize empty chat history
        history = []
        
        # Log initial state
        logger.info("Initial state:")
        logger.info(f"History type: {type(history)}")
        logger.info(f"History length: {len(history)}")
        
        # Process the chat
        logger.info("Processing chat...")
        try:
            # Get raw response from agent
            logger.info("Getting raw response from agent...")
            raw_response = agent.process_query(test_message)
            logger.info("Raw response received")
            debug_response_structure(raw_response, "Raw response: ")
            
            # Verify response structure
            if not isinstance(raw_response, dict):
                logger.error(f"Unexpected response type: {type(raw_response)}")
                raise TypeError(f"Expected dict response, got {type(raw_response)}")
            
            required_keys = ["answer", "reasoning_steps", "context"]
            missing_keys = [key for key in required_keys if key not in raw_response]
            if missing_keys:
                logger.error(f"Missing required keys in response: {missing_keys}")
                raise KeyError(f"Response missing required keys: {missing_keys}")
            
            # Process through chat function
            logger.info("Processing through chat function...")
            result = chat(
                message=test_message,
                history=history,
                agent_type="gemma3:270m",
                use_cot=True,
                collection="PDF Collection"
            )
            logger.info("Chat processing completed")
            debug_response_structure(result, "Final result: ")
            
        except Exception as e:
            logger.error(f"Error during processing: {str(e)}", exc_info=True)
            raise
        
        # Log final state
        logger.info("Final state:")
        logger.info(f"Result type: {type(result)}")
        logger.info(f"Result length: {len(result)}")
        
        # Save debug information to file
        debug_info = {
            "test_message": test_message,
            "raw_response": {
                "type": str(type(raw_response)),
                "keys": list(raw_response.keys()) if isinstance(raw_response, dict) else None,
                "content": str(raw_response)
            },
            "final_result": {
                "type": str(type(result)),
                "length": len(result) if isinstance(result, list) else None,
                "content": str(result)
            },
            "history": {
                "type": str(type(history)),
                "length": len(history),
                "content": str(history)
            }
        }
        
        with open("cot_chat_debug.json", "w") as f:
            json.dump(debug_info, f, indent=2)
        
        logger.info("Debug information saved to cot_chat_debug.json")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    test_cot_chat() 