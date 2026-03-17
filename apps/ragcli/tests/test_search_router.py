"""Test query router."""
from ragcli.search.router import QueryRouter


def test_always_includes_vector():
    router = QueryRouter()
    signals = router.route("anything at all")
    assert "vector" in signals


def test_relationship_adds_graph():
    router = QueryRouter()
    signals = router.route("How does authentication relate to the login module?")
    assert "graph" in signals


def test_short_query_adds_bm25():
    router = QueryRouter()
    signals = router.route("ORA-12154 error")
    assert "bm25" in signals


def test_technical_term_adds_bm25():
    router = QueryRouter()
    signals = router.route("config.yaml settings")
    assert "bm25" in signals


def test_compare_adds_graph():
    router = QueryRouter()
    signals = router.route("Compare the auth module with the payment system")
    assert "graph" in signals


def test_long_natural_query_vector_only():
    router = QueryRouter()
    signals = router.route("Can you explain the general architecture of the application and how components communicate with each other")
    # Long natural query without relationship words or special chars
    assert "vector" in signals
