"""Bounded request bodies: every string has a length limit, every number a range."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RecordType = Literal["fact", "preference", "guideline", "memory", "message"]
Id = Field(min_length=1, max_length=128)


class EmbedRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=4)

    def cleaned(self) -> list[str]:
        out = [t.strip()[:2000] for t in self.texts if t.strip()]
        if not out:
            raise ValueError("enter at least one sentence")
        return out


class ReportEventRequest(BaseModel):
    asset_id: str = Id
    inspector: str = Id
    narrative: str = Field(min_length=3, max_length=4000)
    thread_id: str = Id


class ExtractionDemoRequest(BaseModel):
    count: int = Field(default=4, ge=1, le=8)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    # None means "only records with no user scope": the SDK requires the key.
    user_id: str | None = Field(default=None, max_length=128)
    agent_id: str | None = Field(default=None, max_length=128)
    thread_id: str | None = Field(default=None, max_length=128)
    exact_thread_match: bool | None = None
    record_types: list[RecordType] = Field(default_factory=list, max_length=5)
    max_results: int = Field(default=10, ge=1, le=50)


class FindingSearchRequest(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    asset_id: str | None = Field(default=None, max_length=128)
    category: str | None = Field(default=None, max_length=32)
    k: int = Field(default=3, ge=1, le=20)


class LogFindingRequest(BaseModel):
    asset_id: str = Id
    inspector: str = Id
    category: str = Field(min_length=1, max_length=32)
    severity: Literal["low", "medium", "high", "critical"]
    description: str = Field(min_length=3, max_length=4000)
    recommendation: str = Field(default="", max_length=4000)
    overall_grade: Literal["A", "B", "C", "D", "F"] | None = None
    days_ago: int = Field(default=0, ge=0, le=36500)


class CopilotRequest(BaseModel):
    narrative: str = Field(min_length=3, max_length=4000)
    inspector_id: str = Id
    asset_id: str = Id


class StatelessRequest(BaseModel):
    narrative: str = Field(min_length=3, max_length=4000)
