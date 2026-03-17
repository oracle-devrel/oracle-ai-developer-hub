"""Synthetic Q&A pair generator for RAG evaluation."""

import json
import re
from typing import Dict, List, Optional, Tuple

from ragcli.utils.helpers import generate_uuid
from ragcli.utils.logger import get_logger
from ragcli.core.embedding import generate_response

logger = get_logger(__name__)


class SyntheticQAGenerator:
    """Generates synthetic question-answer pairs from document chunks for evaluation."""

    GENERATION_PROMPT = """Generate {n} question-answer pairs from the following text.
Return ONLY valid JSON with this exact structure (no markdown, no explanation):

{{
  "pairs": [
    {{"question": "A specific question answerable from the text", "answer": "The answer based only on the text"}}
  ]
}}

Text:
{text}"""

    def __init__(self, conn, config: dict):
        self.conn = conn
        self.config = config
        eval_config = config.get("evaluation", {})
        self.pairs_per_chunk = eval_config.get("pairs_per_chunk", 2)
        self.max_chunks_per_doc = eval_config.get("max_chunks_per_doc", 20)

    def generate_for_chunk(self, chunk_text: str, n: int = 2) -> List[Dict[str, str]]:
        """Generate Q&A pairs from a single chunk of text.

        Args:
            chunk_text: The text content of the chunk.
            n: Number of Q&A pairs to generate.

        Returns:
            List of dicts with "question" and "answer" keys.
        """
        truncated = chunk_text[:3000]
        prompt = self.GENERATION_PROMPT.format(n=n, text=truncated)
        messages = [{"role": "user", "content": prompt}]

        try:
            model = self.config["ollama"]["chat_model"]
            response_text = generate_response(messages, model, self.config, stream=False)
            return self._parse_qa_response(response_text)
        except Exception:
            logger.exception("Failed to generate Q&A pairs from chunk")
            return []

    def _parse_qa_response(self, response_text: str) -> List[Dict[str, str]]:
        """Parse JSON Q&A pairs from LLM response.

        Handles raw JSON and JSON wrapped in ```json ... ``` code blocks.
        Filters out pairs missing "question" or "answer" keys.

        Args:
            response_text: Raw LLM response string.

        Returns:
            List of valid {"question": ..., "answer": ...} dicts.
        """
        # Try to extract JSON from code block first
        code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", response_text, re.DOTALL)
        if code_block_match:
            json_str = code_block_match.group(1).strip()
        else:
            json_str = response_text.strip()

        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to parse Q&A response as JSON")
            return []

        pairs = data.get("pairs", [])
        valid_pairs = [
            p for p in pairs
            if isinstance(p, dict) and "question" in p and "answer" in p
        ]
        return valid_pairs

    def get_chunks_for_document(self, document_id: str, limit: int = 20) -> List[Tuple[str, str]]:
        """Fetch chunks for a document from the CHUNKS table.

        Args:
            document_id: The document ID to fetch chunks for.
            limit: Maximum number of chunks to return.

        Returns:
            List of (chunk_id, content) tuples.
        """
        sql = """
            SELECT chunk_id, chunk_text
            FROM CHUNKS
            WHERE document_id = :doc_id
            ORDER BY chunk_number
            FETCH FIRST :limit ROWS ONLY
        """
        with self.conn.cursor() as cursor:
            cursor.execute(sql, {"doc_id": document_id, "limit": limit})
            rows = cursor.fetchall()
        return [(row[0], row[1]) for row in rows]

    def store_qa_pair(
        self,
        run_id: str,
        document_id: str,
        chunk_id: str,
        question: str,
        answer: str,
    ) -> None:
        """Store a generated Q&A pair in the EVAL_RESULTS table.

        Args:
            run_id: The evaluation run ID.
            document_id: The source document ID.
            chunk_id: The source chunk ID.
            question: The generated question.
            answer: The generated answer.
        """
        sql = """
            INSERT INTO EVAL_RESULTS (
                result_id, run_id, document_id, question, expected_answer,
                actual_answer, faithfulness, relevance, context_precision,
                context_recall, chunk_ids_json, duration_ms
            ) VALUES (
                :result_id, :run_id, :document_id, :question, :expected_answer,
                NULL, NULL, NULL, NULL,
                NULL, :chunk_ids_json, NULL
            )
        """
        result_id = generate_uuid()
        chunk_ids_json = json.dumps([chunk_id])

        with self.conn.cursor() as cursor:
            cursor.execute(sql, {
                "result_id": result_id,
                "run_id": run_id,
                "document_id": document_id,
                "question": question,
                "expected_answer": answer,
                "chunk_ids_json": chunk_ids_json,
            })
        self.conn.commit()

    def generate_for_document(self, document_id: str, run_id: str) -> int:
        """Generate Q&A pairs for all chunks in a document.

        Fetches chunks, generates pairs via LLM, and stores them in EVAL_RESULTS.

        Args:
            document_id: The document to generate pairs for.
            run_id: The evaluation run ID.

        Returns:
            Total number of Q&A pairs generated.
        """
        chunks = self.get_chunks_for_document(document_id, limit=self.max_chunks_per_doc)
        total_pairs = 0

        for chunk_id, content in chunks:
            pairs = self.generate_for_chunk(content, n=self.pairs_per_chunk)
            for pair in pairs:
                self.store_qa_pair(
                    run_id=run_id,
                    document_id=document_id,
                    chunk_id=chunk_id,
                    question=pair["question"],
                    answer=pair["answer"],
                )
                total_pairs += 1

        logger.info(
            "Generated %d Q&A pairs for document %s across %d chunks",
            total_pairs, document_id, len(chunks),
        )
        return total_pairs
