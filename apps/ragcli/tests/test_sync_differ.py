"""Tests for DiffChunker incremental re-indexing logic."""

import pytest
from ragcli.sync.differ import DiffChunker, DiffResult


@pytest.fixture
def chunker():
    return DiffChunker(similarity_threshold=0.6)


def _chunk(chunk_id, content):
    """Helper to create chunk dicts."""
    return {"chunk_id": chunk_id, "content": content}


class TestDiffChunkerDiff:
    def test_identical_chunks(self, chunker):
        """Same content in old and new should all be unchanged."""
        old = [_chunk("a", "Hello world this is a test")]
        new = [_chunk("b", "Hello world this is a test")]
        result = chunker.diff(old, new)
        assert len(result.unchanged) == 1
        assert len(result.added) == 0
        assert len(result.removed) == 0
        assert len(result.modified) == 0

    def test_all_new(self, chunker):
        """Empty old list means everything is added."""
        new = [_chunk("a", "Brand new content")]
        result = chunker.diff([], new)
        assert len(result.added) == 1
        assert len(result.removed) == 0
        assert len(result.unchanged) == 0
        assert len(result.modified) == 0

    def test_all_removed(self, chunker):
        """Empty new list means everything is removed."""
        old = [_chunk("a", "Old content that is gone")]
        result = chunker.diff(old, [])
        assert len(result.removed) == 1
        assert len(result.added) == 0
        assert len(result.unchanged) == 0
        assert len(result.modified) == 0

    def test_modified_chunk(self, chunker):
        """Slightly changed text should be detected as modified."""
        old = [_chunk("a", "The quick brown fox jumps over the lazy dog")]
        new = [_chunk("b", "The quick brown fox leaps over the lazy dog")]
        result = chunker.diff(old, new)
        assert len(result.modified) == 1
        assert len(result.unchanged) == 0
        # Modified entries should contain both old and new
        mod = result.modified[0]
        assert "old" in mod
        assert "new" in mod

    def test_mixed_changes(self, chunker):
        """Some added, some removed, some unchanged."""
        old = [
            _chunk("a", "This chunk stays the same forever and ever"),
            _chunk("b", "This chunk will be removed entirely from the set"),
        ]
        new = [
            _chunk("c", "This chunk stays the same forever and ever"),
            _chunk("d", "This is a completely brand new chunk with unique text xyz"),
        ]
        result = chunker.diff(old, new)
        assert len(result.unchanged) == 1
        assert len(result.removed) == 1
        assert len(result.added) == 1
        assert len(result.modified) == 0


class TestSimilarity:
    def test_similarity_exact(self, chunker):
        """Identical strings should have similarity of 1.0."""
        assert chunker._similarity("abc", "abc") == 1.0

    def test_similarity_different(self, chunker):
        """Completely different strings should have low similarity."""
        score = chunker._similarity("abc", "xyz")
        assert score < 0.5

    def test_similarity_empty(self, chunker):
        """Two empty strings should have similarity of 1.0."""
        assert chunker._similarity("", "") == 1.0

    def test_similarity_one_empty(self, chunker):
        """One empty and one non-empty should have similarity of 0.0."""
        assert chunker._similarity("abc", "") == 0.0


class TestSummarize:
    def test_summarize(self, chunker):
        """Verify summarize returns correct counts."""
        diff_result = DiffResult(
            added=[{"chunk_id": "1"}, {"chunk_id": "2"}],
            removed=[{"chunk_id": "3"}],
            modified=[{"old": {}, "new": {}}],
            unchanged=[{"chunk_id": "4"}, {"chunk_id": "5"}, {"chunk_id": "6"}],
        )
        summary = chunker.summarize(diff_result)
        assert summary == {
            "added": 2,
            "removed": 1,
            "modified": 1,
            "unchanged": 3,
        }

    def test_summarize_empty(self, chunker):
        """Empty DiffResult should have all zeros."""
        diff_result = DiffResult()
        summary = chunker.summarize(diff_result)
        assert summary == {
            "added": 0,
            "removed": 0,
            "modified": 0,
            "unchanged": 0,
        }
