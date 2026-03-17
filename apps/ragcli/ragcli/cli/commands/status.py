"""Status monitoring commands for ragcli CLI."""

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from ragcli.utils.status import get_overall_status, print_status, get_vector_statistics, get_index_metadata
from ragcli.config.config_manager import load_config

app = typer.Typer()
console = Console()

@app.command()
def status(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed vector statistics"),
    format: str = typer.Option("rich", "--format", help="Output format (rich, json)")
):
    """Check system status: DB, APIs, documents, vectors."""
    config = load_config()
    overall = get_overall_status(config)
    
    if format == "json":
        import json
        if verbose:
            overall['vector_stats'] = get_vector_statistics(config)
            overall['index_metadata'] = get_index_metadata(config)
        rprint(json.dumps(overall, indent=2, default=str))
        return
    
    # Premium Rich format
    if not verbose:
        print_status(overall)
        return
    
    # Verbose mode with detailed statistics
    print_status(overall)
    
    console.print("\n   [bold #a855f7]V E C T O R   S T A T I S T I C S[/bold #a855f7]")
    
    # Get detailed stats
    vector_stats = get_vector_statistics(config)
    index_meta = get_index_metadata(config)
    
    # Vector Configuration Table
    config_table = Table(
        title="   Core Configuration", 
        show_header=True, 
        box=None, 
        header_style="bold #a855f7",
        title_style="bold white",
        padding=(0, 2)
    )
    config_table.add_column("Parameter", style="dim white")
    config_table.add_column("Value", style="#9333ea")
    
    config_table.add_row("      Embedding Dimension", str(vector_stats.get('dimension', 'N/A')))
    config_table.add_row("      Index Type", vector_stats.get('index_type', 'N/A'))
    config_table.add_row("      Embedding Model", config['ollama']['embedding_model'])
    config_table.add_row("      HNSW M Parameter", str(config.get('vector_index', {}).get('m', 'N/A')))
    config_table.add_row("      HNSW EF Construction", str(config.get('vector_index', {}).get('ef_construction', 'N/A')))
    
    console.print(config_table)
    
    # Storage Statistics
    storage_table = Table(
        title="   Resource Utilization", 
        show_header=True, 
        box=None, 
        header_style="bold #a855f7",
        title_style="bold white",
        padding=(0, 2)
    )
    storage_table.add_column("Metric", style="dim white")
    storage_table.add_column("Value", style="#9333ea")
    
    total_vectors = vector_stats.get('total_vectors', 0)
    dimension = vector_stats.get('dimension', 768)
    vector_size_mb = (total_vectors * dimension * 4) / (1024 * 1024)  # 4 bytes per float
    
    storage_table.add_row("      Total Vectors", f"{total_vectors:,}")
    storage_table.add_row("      Estimated Vector Size", f"{vector_size_mb:.2f} MB")
    storage_table.add_row("      Total Documents", f"{vector_stats.get('total_documents', 0):,}")
    storage_table.add_row("      Total Tokens", f"{vector_stats.get('total_tokens', 0):,}")
    storage_table.add_row("      Avg Chunks per Doc", f"{vector_stats.get('avg_chunks_per_doc', 0):.1f}")
    
    console.print(storage_table)
    
    # Index Metadata
    if index_meta.get('indexes'):
        index_table = Table(
            title="   Vector Indexes", 
            show_header=True, 
            box=None, 
            header_style="bold #a855f7",
            title_style="bold white",
            padding=(0, 2)
        )
        index_table.add_column("Index Name", style="dim white")
        index_table.add_column("Table", style="#9333ea")
        index_table.add_column("Column", style="#a855f7")
        index_table.add_column("Status", style="#4caf50")
        
        for idx in index_meta['indexes']:
            index_table.add_row(
                f"      {idx['index_name']}",
                idx['table_name'],
                idx['column_name'],
                idx['status']
            )
        
        console.print(index_table)
    
    # Performance Metrics
    perf_table = Table(
        title="   Operational Metrics", 
        show_header=True, 
        box=None, 
        header_style="bold #a855f7",
        title_style="bold white",
        padding=(0, 2)
    )
    perf_table.add_column("Metric", style="dim white")
    perf_table.add_column("Value", style="#9333ea")
    
    perf_table.add_row("      Avg Search Latency", f"{vector_stats.get('avg_search_latency_ms', 0):.2f} ms")
    perf_table.add_row("      Cache Hit Rate", f"{vector_stats.get('cache_hit_rate', 0):.1f}%")
    
    console.print(perf_table)
    
    # Recommendations
    recommendations = []
    if total_vectors > 100000 and vector_stats.get('index_type') != 'HYBRID':
        recommendations.append("Consider using HYBRID index for better performance")
    if vector_stats.get('avg_chunks_per_doc', 0) > 50:
        recommendations.append("High granularity detected - consider increasing chunk_size")
    
    if recommendations:
        console.print("\n   [bold #a855f7]💡 STRATEGIC ADVISORY[/bold #a855f7]")
        for rec in recommendations:
            console.print(f"      [dim white]•[/dim] [#a855f7]{rec}[/#a855f7]")

if __name__ == "__main__":
    app()
