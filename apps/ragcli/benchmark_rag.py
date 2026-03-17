
import os
import time
import json
import logging
import random
import string
from pathlib import Path
from ragcli.core.rag_engine import upload_document, ask_query
from ragcli.config.config_manager import load_config
import oracledb

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("benchmark")

def generate_text_file(filename, size_kb=10):
    """Generate a random text file of approx certain size."""
    logger.info(f"Generating {size_kb}KB text file: {filename}")
    words = ["lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit", "sed", "do", "eiusmod", "tempor", "incididunt", "ut", "labore", "et", "dolore", "magna", "aliqua", "Oracle", "Database", "Vector", "search", "AI", "Ollama", "Gemma"]
    
    with open(filename, 'w') as f:
        current_size = 0
        target_size = size_kb * 1024
        while current_size < target_size:
            line = " ".join(random.choices(words, k=20)) + ".\n"
            f.write(line)
            current_size += len(line)
    return filename

def run_benchmarks():
    results = {
        "system_info": {
            "model_chat": "gemma3:270m",
            "model_embedding": "nomic-embed-text",
            "db": "Oracle Database 26ai (Simulated/Real)"
        },
        "ingestion": {},
        "retrieval": {}
    }

    config = load_config()
    
    # Check dependencies
    try:
        import ragcli.database.oracle_client
        logger.info("Oracle Client module found.")
    except ImportError:
        logger.error("Oracle Client module not found.")
        return

    # Ingestion Benchmark
    # Create files of different sizes
    sizes = [10, 50] # KB
    inges_times = []
    
    for size in sizes:
        fname = f"bench_{size}bk.txt"
        generate_text_file(fname, size)
        
        try:
            logger.info(f"Benchmarking upload for {fname}...")
            start = time.perf_counter()
            meta = upload_document(fname, config)
            duration = time.perf_counter() - start
            
            inges_times.append({
                "size_kb": size,
                "time_sec": duration,
                "chunks": meta.get('chunk_count', 0),
                "tokens": meta.get('total_tokens', 0)
            })
            logger.info(f"Upload success: {duration:.2f}s")
        except Exception as e:
            logger.error(f"Upload failed for {fname}: {e}")
            inges_times.append({
                "size_kb": size,
                "error": str(e)
            })
        finally:
            if os.path.exists(fname):
                os.remove(fname)

    results['ingestion'] = inges_times

    # Retrieval Benchmark
    queries = [
        "What is Lorem Ipsum?",
        "Tell me about Oracle Database.",
        "How does vector search work?"
    ]
    
    query_metrics = []
    
    # Pre-warm (optional, maybe not needed for CLI)
    
    for q in queries:
        try:
            logger.info(f"Benchmarking query: {q}")
            start = time.perf_counter()
            # stream=False for easier timing
            res = ask_query(q, config=config, stream=False)
            total = time.perf_counter() - start
            
            metrics = res.get('metrics', {})
            token_count = metrics.get('completion_tokens', 0)
            
            gen_time = metrics.get('generation_time_ms', 0) / 1000.0
            search_time = metrics.get('search_time_ms', 0) / 1000.0
            
            tps = token_count / gen_time if gen_time > 0 else 0
            
            query_metrics.append({
                "query": q,
                "total_time_sec": total,
                "search_time_sec": search_time,
                "generation_time_sec": gen_time,
                "tokens_generated": token_count,
                "tokens_per_sec": tps
            })
            logger.info(f"Query success: {total:.2f}s, {tps:.2f} t/s")
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            query_metrics.append({
                "query": q,
                "error": str(e)
            })

    results['retrieval'] = query_metrics
    
    with open('benchmark_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info("Benchmarks completed. Results saved to benchmark_results.json")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    run_benchmarks()
