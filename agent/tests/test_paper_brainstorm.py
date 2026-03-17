from agent.zero_prompt.events import (
    ZP_BRAINSTORM_COMPLETE,
    ZP_BRAINSTORM_START,
    brainstorm_complete_event,
    brainstorm_start_event,
)
from agent.zero_prompt.paper_brainstorm import enhance_idea_with_papers
from agent.zero_prompt.schemas import EnhancedIdea, PaperMetadata

_IDEA_ML = "build a machine learning model for image classification"

_ABSTRACT_ML = (
    "We propose a novel convolutional neural network architecture for real-time image recognition. "
    "Our framework introduces adaptive pooling layers that improve accuracy on small datasets. "
    "The algorithm achieves state-of-the-art results on benchmark classification tasks. "
    "Future work remains to explore transfer learning on medical imaging datasets."
)

_ABSTRACT_GAPS = (
    "This paper presents a new approach to natural language processing with neural networks. "
    "Limitations include lack of multi-lingual support and unexplored cross-domain generalisation. "
    "Further investigation is needed into low-resource language settings."
)


def _paper(title: str, abstract: str = "", year: int = 2023, citations: int = 10, authors: list | None = None) -> dict:
    return {
        "title": title,
        "abstract": abstract,
        "year": year,
        "citations": citations,
        "authors": authors or [],
    }


def test_enhanced_idea_defaults():
    idea = EnhancedIdea(original_idea="test idea")
    assert idea.original_idea == "test idea"
    assert idea.novel_features == []
    assert idea.scientific_backing == ""
    assert idea.unexplored_angles == []
    assert idea.novelty_boost == 0.0


def test_empty_papers_returns_minimal():
    result = enhance_idea_with_papers("great idea", [])
    assert result.original_idea == "great idea"
    assert result.novel_features == []
    assert result.scientific_backing == ""
    assert result.unexplored_angles == []
    assert result.novelty_boost == 0.0


def test_novelty_boost_bounded_upper():
    papers = [_paper(f"Machine Learning Image Classification Paper {i}", _ABSTRACT_ML) for i in range(10)]
    result = enhance_idea_with_papers(_IDEA_ML, papers)
    assert result.novelty_boost <= 0.3


def test_novelty_boost_bounded_lower():
    papers = [_paper("Unrelated Biochemistry Paper", "Protein folding in cellular membrane structures.")]
    result = enhance_idea_with_papers(_IDEA_ML, papers)
    assert result.novelty_boost >= 0.0


def test_novel_features_extracted_from_relevant_paper():
    papers = [_paper("CNN Image Classifier", _ABSTRACT_ML)]
    result = enhance_idea_with_papers(_IDEA_ML, papers)
    assert len(result.novel_features) > 0


def test_novel_features_reference_paper_title():
    papers = [_paper("Adaptive Pooling CNN", _ABSTRACT_ML)]
    result = enhance_idea_with_papers(_IDEA_ML, papers)
    assert any("Adaptive Pooling CNN" in f for f in result.novel_features)


def test_scientific_backing_mentions_paper_title():
    papers = [_paper("Deep Learning for Vision Systems", _ABSTRACT_ML, authors=["John Smith"])]
    result = enhance_idea_with_papers(_IDEA_ML, papers)
    assert "Deep Learning for Vision Systems" in result.scientific_backing


def test_scientific_backing_multiple_papers():
    papers = [
        _paper("Paper Alpha", _ABSTRACT_ML),
        _paper("Paper Beta", _ABSTRACT_GAPS),
    ]
    result = enhance_idea_with_papers("idea", papers)
    assert "Paper Alpha" in result.scientific_backing
    assert "Paper Beta" in result.scientific_backing


def test_unexplored_angles_from_gap_keywords():
    papers = [_paper("NLP Research", _ABSTRACT_GAPS)]
    result = enhance_idea_with_papers("build a language model for text processing", papers)
    assert len(result.unexplored_angles) > 0


def test_brainstorm_start_event_structure():
    event = brainstorm_start_event("my idea", 3)
    assert event["type"] == ZP_BRAINSTORM_START
    assert event["idea"] == "my idea"
    assert event["paper_count"] == 3


def test_brainstorm_complete_event_structure():
    event = brainstorm_complete_event(novel_features=2, unexplored_angles=1, novelty_boost=0.15)
    assert event["type"] == ZP_BRAINSTORM_COMPLETE
    assert event["novel_features"] == 2
    assert event["unexplored_angles"] == 1
    assert event["novelty_boost"] == 0.15


def test_accepts_paper_metadata_objects():
    paper = PaperMetadata(
        title="Image Classification with Deep Neural Networks",
        abstract=_ABSTRACT_ML,
        year=2022,
        citations=50,
        authors=["Alice Lee"],
    )
    result = enhance_idea_with_papers(_IDEA_ML, [paper])
    assert isinstance(result, EnhancedIdea)
    assert 0.0 <= result.novelty_boost <= 0.3


def test_novel_features_capped_at_five():
    papers = [_paper(f"ML Paper {i}", _ABSTRACT_ML) for i in range(10)]
    result = enhance_idea_with_papers(_IDEA_ML, papers)
    assert len(result.novel_features) <= 5


def test_unexplored_angles_capped_at_three():
    papers = [_paper(f"Gap Paper {i}", _ABSTRACT_GAPS) for i in range(10)]
    result = enhance_idea_with_papers("language model for text", papers)
    assert len(result.unexplored_angles) <= 3
