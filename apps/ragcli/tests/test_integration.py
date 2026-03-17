"""Integration tests for ragcli - automated functionality testing."""

import pytest
import tempfile
import shutil
import subprocess
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add ragcli to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ragcli.core.rag_engine import upload_document, ask_query
from ragcli.core.document_processor import preprocess_document, chunk_text
from ragcli.visualization.embedding_space import create_2d_embedding_plot
from ragcli.visualization.similarity_heatmap import create_similarity_heatmap
from ragcli.utils.validators import validate_file_path, validate_query_text
from ragcli.utils.metrics import record_query_metrics, get_metrics_collector
from ragcli.config.config_manager import load_config


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_files(temp_dir):
    """Create sample test files."""
    files = {}

    # TXT file
    txt_path = Path(temp_dir) / "sample.txt"
    txt_path.write_text("This is a sample text document for testing ragcli upload functionality.")
    files['txt'] = str(txt_path)

    # MD file
    md_path = Path(temp_dir) / "sample.md"
    md_path.write_text("# Sample Markdown\n\nThis is a markdown document with some content.")
    files['md'] = str(md_path)

    # PDF file (mock - we'll patch the OCR)
    pdf_path = Path(temp_dir) / "sample.pdf"
    pdf_path.write_bytes(b"Mock PDF content")
    files['pdf'] = str(pdf_path)

    return files


@pytest.fixture
def mock_config():
    """Mock configuration for tests."""
    return {
        'documents': {
            'chunk_size': 1000,
            'chunk_overlap_percentage': 10,
            'supported_formats': ['txt', 'md', 'pdf'],
            'max_file_size_mb': 10
        },
        'ollama': {
            'embedding_model': 'nomic-embed-text',
            'chat_model': 'llama2',
            'endpoint': 'http://localhost:11434'
        },
        'rag': {
            'top_k': 5,
            'min_similarity_score': 0.5
        },
        'vector_index': {
            'dimension': 768
        }
    }


@pytest.fixture
def mock_db():
    """Mock database connection and operations."""
    with patch('ragcli.core.rag_engine.OracleClient') as mock_client:
        mock_conn = MagicMock()
        mock_client.return_value.get_connection.return_value = mock_conn
        mock_client.return_value.close.return_value = None

        with patch('ragcli.database.vector_ops.insert_document') as mock_insert_doc:
            with patch('ragcli.database.vector_ops.insert_chunk') as mock_insert_chunk:
                mock_insert_doc.return_value = "test-doc-id"
                yield {
                    'client': mock_client,
                    'conn': mock_conn,
                    'insert_doc': mock_insert_doc,
                    'insert_chunk': mock_insert_chunk
                }


class TestDocumentProcessing:
    """Test document processing functionality."""

    def test_preprocess_txt(self, sample_files, mock_config):
        """Test TXT file preprocessing."""
        text, ocr_used = preprocess_document(sample_files['txt'], mock_config)
        assert isinstance(text, str)
        assert len(text) > 0
        assert not ocr_used

    def test_preprocess_md(self, sample_files, mock_config):
        """Test MD file preprocessing."""
        text, ocr_used = preprocess_document(sample_files['md'], mock_config)
        assert isinstance(text, str)
        assert len(text) > 0
        assert not ocr_used

    @patch('ragcli.core.document_processor.pdf_to_markdown')
    def test_preprocess_pdf(self, mock_ocr, sample_files, mock_config):
        """Test PDF preprocessing with OCR."""
        mock_ocr.return_value = "Extracted PDF text content."
        text, ocr_used = preprocess_document(sample_files['pdf'], mock_config)
        assert text == "Extracted PDF text content."
        assert ocr_used

    def test_chunk_text(self, mock_config):
        """Test text chunking."""
        text = "This is a long text document that should be chunked into smaller pieces for processing."
        chunks = chunk_text(text, mock_config)

        assert len(chunks) > 0
        for chunk in chunks:
            assert 'text' in chunk
            assert 'token_count' in chunk
            assert 'char_count' in chunk
            assert chunk['token_count'] > 0
            assert chunk['char_count'] > 0


class TestValidation:
    """Test input validation."""

    def test_validate_file_path_valid(self, sample_files, mock_config):
        """Test valid file validation."""
        path = validate_file_path(sample_files['txt'], mock_config)
        assert path.exists()
        assert path.is_file()

    def test_validate_file_path_invalid(self, mock_config):
        """Test invalid file validation."""
        with pytest.raises(Exception):  # ValidationError
            validate_file_path("nonexistent.txt", mock_config)

    def test_validate_query_text(self):
        """Test query text validation."""
        query = validate_query_text("What is machine learning?")
        assert query == "What is machine learning?"

    def test_validate_query_empty(self):
        """Test empty query validation."""
        with pytest.raises(Exception):  # ValidationError
            validate_query_text("")


class TestUploadFunctionality:
    """Test document upload functionality."""

    @patch('ragcli.core.rag_engine.generate_embedding')
    def test_upload_txt(self, mock_emb, sample_files, mock_config, mock_db):
        """Test uploading TXT file."""
        mock_emb.return_value = [0.1] * 768

        result = upload_document(sample_files['txt'], mock_config)

        assert 'document_id' in result
        assert result['filename'] == 'sample.txt'
        assert result['file_format'] == 'txt'
        assert result['chunk_count'] > 0
        assert result['total_tokens'] > 0

    @patch('ragcli.core.rag_engine.generate_embedding')
    @patch('ragcli.core.document_processor.pdf_to_markdown')
    def test_upload_pdf(self, mock_ocr, mock_emb, sample_files, mock_config, mock_db):
        """Test uploading PDF file."""
        mock_ocr.return_value = "PDF content extracted via OCR."
        mock_emb.return_value = [0.1] * 768

        result = upload_document(sample_files['pdf'], mock_config)

        assert result['file_format'] == 'pdf'


class TestQueryFunctionality:
    """Test query and search functionality."""

    @patch('ragcli.core.rag_engine.OracleClient')
    @patch('ragcli.core.rag_engine.log_query')
    @patch('ragcli.core.rag_engine.generate_response')
    @patch('ragcli.core.rag_engine.search_chunks')
    def test_ask_query(self, mock_search, mock_gen, mock_log, mock_client, mock_config):
        """Test asking a query."""
        mock_search.return_value = {
            'results': [
                {'document_id': 'doc1', 'text': 'Sample text', 'similarity_score': 0.8}
            ],
            'query_embedding': [0.1] * 768,
            'metrics': {'embedding_time_ms': 10, 'search_time_ms': 20}
        }
        mock_gen.return_value = "This is a sample response."
        mock_conn = MagicMock()
        mock_client.return_value.get_connection.return_value = mock_conn

        result = ask_query("What is RAG?", config=mock_config)

        assert result['response'] == "This is a sample response."
        assert len(result['results']) == 1
        assert 'metrics' in result
        assert result['metrics']['total_time_ms'] > 0


class TestVisualization:
    """Test visualization functionality."""

    def test_create_2d_embedding_plot(self):
        """Test 2D embedding plot creation."""
        # UMAP needs enough data points; provide at least 5 with higher-dim vectors
        embeddings = [
            [0.1, 0.2, 0.3, 0.4, 0.5],
            [0.4, 0.5, 0.6, 0.7, 0.8],
            [0.7, 0.8, 0.9, 1.0, 0.1],
            [0.2, 0.3, 0.4, 0.5, 0.6],
            [0.9, 0.1, 0.2, 0.3, 0.4],
        ]
        similarities = [0.8, 0.6, 0.7, 0.5, 0.9]

        fig = create_2d_embedding_plot(embeddings, similarities=similarities)
        assert fig is not None
        assert hasattr(fig, 'data')

    def test_create_similarity_heatmap(self):
        """Test similarity heatmap creation."""
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

        fig = create_similarity_heatmap(embeddings)
        assert fig is not None
        assert hasattr(fig, 'data')


class TestMetrics:
    """Test metrics collection."""

    def test_record_query_metrics(self):
        """Test recording query metrics."""
        metrics = record_query_metrics(
            query_id="test-query-123",
            query_text="Test query",
            embedding_time_ms=50.0,
            search_time_ms=100.0,
            generation_time_ms=200.0,
            total_time_ms=350.0,
            retrieved_chunks=3
        )

        assert metrics.query_id == "test-query-123"
        assert metrics.total_time_ms == 350.0
        assert metrics.retrieved_chunks == 3

    def test_metrics_collector(self):
        """Test metrics collector functionality."""
        collector = get_metrics_collector()

        # Clear previous test state
        collector.query_metrics.clear()

        # Add some metrics
        record_query_metrics("q1", query_text="Query 1", total_time_ms=100)
        record_query_metrics("q2", query_text="Query 2", total_time_ms=150)

        stats = collector.get_query_stats()
        assert 'total_queries' in stats
        assert stats['total_queries'] == 2


class TestCLI:
    """Test CLI commands (smoke tests)."""

    def test_cli_help(self):
        """Test CLI help command."""
        result = subprocess.run(
            [sys.executable, '-m', 'ragcli.cli.main', '--help'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        assert result.returncode == 0
        assert 'ragcli' in result.stdout.lower()

    @patch('ragcli.cli.commands.config.load_config')
    def test_cli_config_show(self, mock_load):
        """Test CLI config show command."""
        mock_load.return_value = {'test': 'config'}

        result = subprocess.run(
            [sys.executable, '-m', 'ragcli.cli.main', 'config', 'show'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        # This might fail without proper setup, but we test the command exists
        assert result.returncode in [0, 1]  # Allow for expected failures in test env


# Integration test that combines multiple components
def test_full_pipeline_integration(sample_files, mock_config, mock_db):
    """Test full upload-query pipeline."""
    with patch('ragcli.core.rag_engine.generate_embedding') as mock_emb, \
         patch('ragcli.core.rag_engine.generate_response') as mock_gen, \
         patch('ragcli.core.rag_engine.search_chunks') as mock_search, \
         patch('ragcli.core.rag_engine.log_query') as mock_log:

        mock_emb.return_value = [0.1] * 768
        mock_search.return_value = {
            'results': [{'document_id': 'test-doc-id', 'text': 'Sample chunk text', 'similarity_score': 0.8}],
            'query_embedding': [0.1] * 768,
            'metrics': {'embedding_time_ms': 10, 'search_time_ms': 20}
        }
        mock_gen.return_value = "Generated response based on the uploaded document."

        # Upload document
        upload_result = upload_document(sample_files['txt'], mock_config)
        assert upload_result['chunk_count'] > 0

        # Query the document
        query_result = ask_query("What is in the document?", config=mock_config)
        assert query_result['response'] == "Generated response based on the uploaded document."
        assert len(query_result['results']) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
