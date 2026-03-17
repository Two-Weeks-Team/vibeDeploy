"""Paper-based brainstorm enhancement — pure rule-based extraction, no LLM calls."""

import re

from .schemas import EnhancedIdea

_NOVELTY_MARKERS = [
    "propose",
    "introduce",
    "novel",
    "new approach",
    "we present",
    "framework",
    "algorithm",
    "technique",
    "architecture",
    "method",
    "we develop",
    "we design",
]

_GAP_MARKERS = [
    "future work",
    "future research",
    "remains",
    "open question",
    "limitation",
    "we did not",
    "not explored",
    "unexplored",
    "further investigation",
    "not yet",
    "has not been",
    "lack of",
    "open problem",
    "challenge",
    "unresolved",
]

_STOP_WORDS = frozenset(
    "a an the and or but in on at to for of with is are be was were "
    "this that it its they them their we our you your by from as have "
    "has had do does did not can will would could should may might".split()
)


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    return {t for t in tokens if t not in _STOP_WORDS}


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 15]


def _relevance_score(idea_tokens: set[str], text: str) -> float:
    if not idea_tokens:
        return 0.0
    text_tokens = _tokenize(text)
    overlap = idea_tokens & text_tokens
    return len(overlap) / len(idea_tokens)


def _extract_novel_feature(idea_tokens: set[str], abstract: str, title: str) -> str | None:
    sentences = _split_sentences(abstract)
    for sent in sentences:
        lower = sent.lower()
        has_novelty = any(marker in lower for marker in _NOVELTY_MARKERS)
        if not has_novelty:
            continue
        sent_tokens = _tokenize(sent)
        overlap = idea_tokens & sent_tokens
        if len(overlap) >= 1:
            summary = sent[:150].rstrip(",;")
            return f"{summary} [from: {title[:60]}]"
    return None


def _extract_gap_angle(abstract: str) -> str | None:
    sentences = _split_sentences(abstract)
    for sent in sentences:
        lower = sent.lower()
        if any(marker in lower for marker in _GAP_MARKERS):
            return sent[:200].rstrip(",;")
    return None


def _build_citation(paper: object) -> str:
    if isinstance(paper, dict):
        title = paper.get("title", "") or ""
        year = paper.get("year", 0) or 0
        authors = paper.get("authors", []) or []
    else:
        title = getattr(paper, "title", "") or ""
        year = getattr(paper, "year", 0) or 0
        authors = getattr(paper, "authors", []) or []

    if not title:
        return ""

    first_author_last = ""
    if authors:
        parts = str(authors[0]).split()
        first_author_last = parts[-1] if parts else ""

    year_str = str(year) if year else "n.d."
    author_part = f"{first_author_last} " if first_author_last else ""
    return f"{author_part}({year_str}): {title[:80]}"


def enhance_idea_with_papers(idea: str, papers: list) -> EnhancedIdea:
    """Enhance an idea using academic papers — pure rule-based, no LLM calls.

    Args:
        idea: The original idea string.
        papers: List of PaperMetadata objects or equivalent dicts.

    Returns:
        EnhancedIdea with extracted novel features, scientific backing,
        unexplored angles, and a novelty_boost score in [0.0, 0.3].
    """
    if not papers:
        return EnhancedIdea(
            original_idea=idea,
            novel_features=[],
            scientific_backing="",
            unexplored_angles=[],
            novelty_boost=0.0,
        )

    idea_tokens = _tokenize(idea)
    novel_features: list[str] = []
    unexplored_angles: list[str] = []
    citations: list[str] = []
    relevance_scores: list[float] = []

    for paper in papers:
        if isinstance(paper, dict):
            abstract = paper.get("abstract", "") or ""
            title = paper.get("title", "") or ""
        else:
            abstract = getattr(paper, "abstract", "") or ""
            title = getattr(paper, "title", "") or ""

        rel = _relevance_score(idea_tokens, f"{title} {abstract}")
        relevance_scores.append(rel)

        feature = _extract_novel_feature(idea_tokens, abstract, title)
        if feature:
            novel_features.append(feature)

        angle = _extract_gap_angle(abstract)
        if angle:
            unexplored_angles.append(angle)

        citation = _build_citation(paper)
        if citation:
            citations.append(citation)

    novel_features = novel_features[:5]
    unexplored_angles = unexplored_angles[:3]
    scientific_backing = "; ".join(citations)

    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    novelty_boost = round(min(avg_relevance * 0.6, 0.3), 4)

    return EnhancedIdea(
        original_idea=idea,
        novel_features=novel_features,
        scientific_backing=scientific_backing,
        unexplored_angles=unexplored_angles,
        novelty_boost=novelty_boost,
    )
