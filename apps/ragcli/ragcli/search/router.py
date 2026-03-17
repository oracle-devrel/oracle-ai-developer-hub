"""Query router: decide which search signals to activate."""

from typing import Set


RELATIONSHIP_WORDS = {"how", "relate", "between", "connect", "compare", "affect", "impact", "cause", "depend", "link"}


class QueryRouter:
    def route(self, query: str) -> Set[str]:
        signals = {"vector"}
        words = set(query.lower().split())

        if len(query.split()) <= 8 or any(c in query for c in ['"', "'", ":", ".", "_"]):
            signals.add("bm25")

        if words & RELATIONSHIP_WORDS:
            signals.add("graph")

        return signals
