from typing import Literal

from pydantic import BaseModel, Field


class VideoCandidate(BaseModel):
    video_id: str
    title: str
    channel_title: str
    published_at: str
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    engagement_rate: float = 0.0
    category: str = ""
    description: str = ""
    thumbnail_url: str = ""
    duration: str = ""
    has_captions: bool = Field(default=False)


class PaperMetadata(BaseModel):
    title: str
    abstract: str = ""
    citations: int = 0
    year: int = 0
    url: str = ""
    source: Literal["openalex", "arxiv"] = "openalex"
    authors: list[str] = []
    doi: str = ""


class EnhancedIdea(BaseModel):
    original_idea: str
    novel_features: list[str] = []
    scientific_backing: str = ""
    unexplored_angles: list[str] = []
    novelty_boost: float = 0.0


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str | None = None
    source: str
    confidence: Literal["normal", "high"] = "normal"


class MarketAnalysis(BaseModel):
    market_opportunity_score: int = 0
    competitors: list[str] = []
    gaps: list[str] = []
    differentiation: str = ""
    saturation_level: Literal["low", "medium", "high"] = "medium"
    search_confidence: Literal["llm_only", "normal", "high"] = "normal"


class EnhancedIdea(BaseModel):
    original_idea: str
    novel_features: list[str] = []
    scientific_backing: str = ""
    unexplored_angles: list[str] = []
    novelty_boost: float = Field(default=0.0, ge=0.0, le=0.3)


class Verdict(BaseModel):
    score: int
    decision: Literal["GO", "NO_GO"]
    reason: str
    reason_code: Literal[
        "high_potential",
        "market_saturated",
        "weak_differentiation",
        "low_confidence",
        "weak_paper_backing",
        "technical_risk",
    ]


class TranscriptArtifact(BaseModel):
    video_id: str
    text: str
    source: Literal["manual", "auto", "metadata_fallback", "error"]
    language: str | None = None
    token_count: int
