"""Paper-based brainstorm enhancement — LLM-powered with rule-based fallback."""

import json
import logging
import re

from agent.llm import MODEL_GEMINI_3_1_FLASH, ainvoke_with_retry, get_llm

from .events import brainstorm_complete_event, brainstorm_start_event
from .schemas import EnhancedIdea

logger = logging.getLogger(__name__)

_MIN_SENTENCE_LEN = 15
_FEATURE_TRUNCATE_LEN = 150
_TITLE_TRUNCATE_LEN = 60
_GAP_TRUNCATE_LEN = 200
_CITATION_TITLE_LEN = 80
_MAX_NOVEL_FEATURES = 5
_MAX_UNEXPLORED_ANGLES = 3

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
    return [s.strip() for s in sentences if len(s.strip()) > _MIN_SENTENCE_LEN]


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
            summary = sent[:_FEATURE_TRUNCATE_LEN].rstrip(",;")
            return f"{summary} [from: {title[:_TITLE_TRUNCATE_LEN]}]"
    return None


def _extract_gap_angle(abstract: str) -> str | None:
    sentences = _split_sentences(abstract)
    for sent in sentences:
        lower = sent.lower()
        if any(marker in lower for marker in _GAP_MARKERS):
            return sent[:_GAP_TRUNCATE_LEN].rstrip(",;")
    return None


def _get_paper_attr(paper: object, key: str, default: object = "") -> object:
    """Extract an attribute from a paper dict or object."""
    if isinstance(paper, dict):
        return paper.get(key, default)
    return getattr(paper, key, default)


def _build_citation(paper: object) -> str:
    title = _get_paper_attr(paper, "title", "")
    year = _get_paper_attr(paper, "year", 0)
    authors = _get_paper_attr(paper, "authors", [])

    if not title:
        return ""

    first_author_last = ""
    if authors:
        parts = authors[0].split()
        first_author_last = parts[-1] if parts else ""

    year_str = str(year) if year else "n.d."
    author_part = f"{first_author_last} " if first_author_last else ""
    return f"{author_part}({year_str}): {title[:_CITATION_TITLE_LEN]}"


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
        abstract = _get_paper_attr(paper, "abstract", "")
        title = _get_paper_attr(paper, "title", "")

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

    novel_features = novel_features[:_MAX_NOVEL_FEATURES]
    unexplored_angles = unexplored_angles[:_MAX_UNEXPLORED_ANGLES]
    scientific_backing = "; ".join(citations)

    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    paper_presence_bonus = min(len(papers) * 0.04, 0.12)
    novelty_boost = round(min(avg_relevance * 0.6 + paper_presence_bonus, 0.3), 4)

    return EnhancedIdea(
        original_idea=idea,
        novel_features=novel_features,
        scientific_backing=scientific_backing,
        unexplored_angles=unexplored_angles,
        novelty_boost=novelty_boost,
    )


_LLM_BRAINSTORM_PROMPT = (
    "You are a novelty strategist. Given an app idea and academic paper abstracts, "
    "enhance the idea with research-backed insights.\n\n"
    "App Idea: {idea}\n\n"
    "Papers:\n{papers_text}\n\n"
    "Return ONLY valid JSON with these fields:\n"
    "- novel_features: list of up to 5 strings describing features directly inspired by the papers\n"
    "- scientific_backing: single string citing the papers (author, year, title)\n"
    "- unexplored_angles: list of up to 3 strings identifying research gaps to exploit\n"
    "- novelty_boost: float between 0.0 and 0.3 representing how much the papers improve novelty\n\n"
    "JSON only, no markdown, no explanation."
)

_MAX_ABSTRACT_CHARS = 400


def _build_papers_text(papers: list) -> str:
    lines = []
    for i, paper in enumerate(papers[:8], 1):
        title = _get_paper_attr(paper, "title", "")
        abstract = str(_get_paper_attr(paper, "abstract", ""))[:_MAX_ABSTRACT_CHARS]
        year = _get_paper_attr(paper, "year", "")
        lines.append(f"{i}. [{year}] {title}: {abstract}")
    return "\n".join(lines)


def _parse_llm_json(raw: str, idea: str) -> EnhancedIdea | None:
    try:
        data = json.loads(raw.strip())
        boost = float(data.get("novelty_boost", 0.0))
        boost = round(max(0.0, min(0.3, boost)), 4)
        return EnhancedIdea(
            original_idea=idea,
            novel_features=list(data.get("novel_features", []))[:_MAX_NOVEL_FEATURES],
            scientific_backing=str(data.get("scientific_backing", "")),
            unexplored_angles=list(data.get("unexplored_angles", []))[:_MAX_UNEXPLORED_ANGLES],
            novelty_boost=boost,
        )
    except Exception:
        return None


async def paper_brainstorm_llm(idea: str, papers: list) -> tuple[list[dict], EnhancedIdea]:
    start_event = brainstorm_start_event(idea, len(papers))
    enhanced: EnhancedIdea | None = None

    if papers:
        try:
            llm = get_llm(MODEL_GEMINI_3_1_FLASH, temperature=0.4, max_tokens=1024)
            papers_text = _build_papers_text(papers)
            prompt = _LLM_BRAINSTORM_PROMPT.format(idea=idea, papers_text=papers_text)
            response = await ainvoke_with_retry(llm, [{"role": "user", "content": prompt}], max_attempts=3)
            raw = response.content if hasattr(response, "content") else str(response)
            enhanced = _parse_llm_json(str(raw), idea)
            if enhanced is None:
                logger.warning("[paper_brainstorm_llm] JSON parse failed — falling back to rule-based")
        except Exception:
            logger.exception("[paper_brainstorm_llm] LLM call failed — falling back to rule-based")

    if enhanced is None:
        enhanced = enhance_idea_with_papers(idea, papers)

    complete_event = brainstorm_complete_event(
        novel_features=len(enhanced.novel_features),
        unexplored_angles=len(enhanced.unexplored_angles),
        novelty_boost=enhanced.novelty_boost,
    )
    return [start_event, complete_event], enhanced
