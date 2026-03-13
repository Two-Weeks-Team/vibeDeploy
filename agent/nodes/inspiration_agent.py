import json
import re

from ..llm import MODEL_CONFIG, ainvoke_with_retry, get_llm, get_rate_limit_fallback_models
from ..state import VibeDeployState

INSPIRATION_AGENT_PROMPT = (
    "You are the Inspiration Agent. Your job is to translate raw idea text and any YouTube-derived "
    "reference material into a concrete product inspiration pack that downstream agents can implement.\n\n"
    "Return a JSON object with:\n"
    "- domain: short product domain label\n"
    "- layout_archetype: concrete screen archetype such as storyboard, operations_console, atlas, studio, notebook, lab, or marketplace\n"
    "- interface_metaphor: short phrase describing the interface metaphor\n"
    "- visual_motifs: list of 3-5 concrete aesthetic or composition cues\n"
    "- interaction_primitives: list of 3-5 domain-specific interaction patterns\n"
    "- reference_objects: list of 3-6 nouns that should visibly appear in the product\n"
    "- signature_demo_moments: list of 2-4 moments that should feel impressive live\n"
    "- anti_patterns: list of 3-5 patterns to avoid\n"
    "- sample_seed_data: list of 3-5 example entities the UI should be ready to show\n\n"
    "Avoid generic SaaS phrasing. Make the output specific enough that a designer and code generator "
    "would build a product that does not resemble an admin dashboard."
)


async def inspiration_agent(state: VibeDeployState) -> dict:
    idea = state.get("idea", {}) or {}
    raw_input = state.get("raw_input", "")
    transcript = state.get("transcript", "") or ""

    context = json.dumps(
        {
            "idea": idea,
            "raw_input": raw_input,
            "transcript_excerpt": transcript[:5000],
        },
        indent=2,
        ensure_ascii=False,
    )

    model = MODEL_CONFIG["brainstorm"]
    try:
        llm = get_llm(model=model, temperature=0.35, max_tokens=2500)
        response = await ainvoke_with_retry(
            llm,
            [
                {"role": "system", "content": INSPIRATION_AGENT_PROMPT},
                {"role": "user", "content": f"Build an inspiration pack from this context:\n\n{context}"},
            ],
            fallback_models=get_rate_limit_fallback_models(model),
        )
        pack = _parse_json(response.content)
    except Exception:
        pack = {}

    if not isinstance(pack, dict) or not pack.get("layout_archetype"):
        pack = _fallback_inspiration_pack(idea, raw_input, transcript)

    merged_idea = _merge_inspiration_pack(idea, pack)
    return {
        "idea": merged_idea,
        "inspiration_pack": pack,
        "phase": "inspiration_mapped",
    }


def _parse_json(content) -> dict:
    from ..llm import content_to_str

    text = content_to_str(content).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return {}
    return {}


def _fallback_inspiration_pack(idea: dict, raw_input: str, transcript: str) -> dict:
    selected_flagship = str(idea.get("selected_flagship") or "").strip().lower()
    existing_domain = str(idea.get("flagship_domain") or idea.get("domain") or "").strip().lower()
    text = " ".join(
        [
            json.dumps(idea, ensure_ascii=False),
            raw_input,
            transcript[:5000],
        ]
    ).lower()

    if (
        selected_flagship == "creator-batch-studio"
        or "creator" in existing_domain
        or (
            any(token in text for token in ("creator", "content", "short-form", "hook", "publish", "repurpose"))
            and not any(
                token in text
                for token in (
                    "travel",
                    "trip",
                    "itinerary",
                    "destination",
                    "vacation",
                    "journey",
                    "meal",
                    "grocery",
                    "prep",
                    "cook",
                    "recipe",
                    "kitchen",
                    "budget",
                    "finance",
                    "cash",
                    "income",
                    "study",
                    "learning",
                    "exam",
                    "interview",
                )
            )
        )
    ):
        return {
            "domain": "creator",
            "layout_archetype": "storyboard",
            "interface_metaphor": "editorial production board",
            "visual_motifs": ["story cards", "production tape", "editorial markers", "shoot-day lanes"],
            "interaction_primitives": ["batch planning", "hook drafting", "repurpose mapping", "publish sequencing"],
            "reference_objects": ["hook card", "shot list", "repurpose lane", "publish queue", "content batch"],
            "signature_demo_moments": [
                "assembling a multi-post creator batch live",
                "turning a rough angle into a publish-ready workflow",
            ],
            "anti_patterns": [
                "no generic SaaS dashboard",
                "no enterprise KPI framing",
                "no blank textarea-plus-card shell",
            ],
            "sample_seed_data": ["Hook variant", "Shoot-day checklist", "Repurpose lane", "Publish queue"],
        }

    if (
        selected_flagship == "meal-prep-atlas"
        or "meal prep" in existing_domain
        or "grocery" in existing_domain
        or any(token in text for token in ("meal", "grocery", "prep", "cook", "recipe", "kitchen"))
    ):
        return {
            "domain": "meal_prep",
            "layout_archetype": "atlas",
            "interface_metaphor": "kitchen prep atlas",
            "visual_motifs": ["recipe tabs", "container labels", "prep maps", "kitchen blocks"],
            "interaction_primitives": ["prep sequencing", "grocery grouping", "meal slotting", "container planning"],
            "reference_objects": ["prep block", "grocery lane", "meal board", "container checklist", "recipe slot"],
            "signature_demo_moments": [
                "turning grocery inspiration into a prep board",
                "mapping a week of meals in one pass",
            ],
            "anti_patterns": [
                "no productivity dashboard shell",
                "no empty recipe blog clone",
                "no generic AI assistant framing",
            ],
            "sample_seed_data": ["Sunday prep block", "Protein lane", "Lunch board", "Container checklist"],
        }

    if (
        selected_flagship == "weekender-route-postcards"
        or "travel" in existing_domain
        or any(token in text for token in ("travel", "trip", "itinerary", "destination", "vacation", "journey"))
    ):
        return {
            "domain": "travel",
            "layout_archetype": "storyboard",
            "interface_metaphor": "postcard route studio",
            "visual_motifs": ["editorial travel spreads", "map traces", "polaroid stacks", "sunset gradients"],
            "interaction_primitives": ["route building", "day sequencing", "moodboard curation", "quick budget swap"],
            "reference_objects": ["district", "cafe", "stop", "route", "day plan"],
            "signature_demo_moments": ["assembling a day-by-day route live", "turning a mood into a trip board"],
            "anti_patterns": [
                "no generic KPI tiles",
                "no sterile enterprise dashboard",
                "no blank form-only first screen",
            ],
            "sample_seed_data": ["Day 1 route", "Night-view cafe", "Market stop", "Rain backup plan"],
        }

    if (
        selected_flagship == "interview-sprint-forge"
        or "learning" in existing_domain
        or any(
            token in text for token in ("study", "learning", "exam", "interview", "course", "syllabus", "curriculum")
        )
    ):
        return {
            "domain": "learning",
            "layout_archetype": "studio",
            "interface_metaphor": "curriculum workshop",
            "visual_motifs": ["sticky-note syllabus", "progress tracks", "annotation layers", "bright study accents"],
            "interaction_primitives": [
                "sprint planning",
                "topic sequencing",
                "review scheduling",
                "confidence tagging",
            ],
            "reference_objects": ["module", "drill", "review block", "milestone", "syllabus"],
            "signature_demo_moments": [
                "turning a vague goal into a syllabus instantly",
                "showing a smart study sprint populate",
            ],
            "anti_patterns": [
                "no empty dashboard shell",
                "no generic analytics homepage",
                "no plain textarea-only app",
            ],
            "sample_seed_data": ["SQL drill", "Case prompt", "Revision block", "Mock interview"],
        }

    if any(
        token in text for token in ("event", "stage", "speaker", "rehearsal", "demo day", "conference", "run of show")
    ):
        return {
            "domain": "event_ops",
            "layout_archetype": "operations_console",
            "interface_metaphor": "live show command center",
            "visual_motifs": ["signal lights", "cue sheets", "timeline rails", "dark glass panels"],
            "interaction_primitives": ["cue locking", "timeline scrubbing", "readiness checks", "incident escalation"],
            "reference_objects": ["cue", "speaker", "sponsor", "stage lane", "incident"],
            "signature_demo_moments": ["seeing readiness flip live", "reordering the show without losing timing"],
            "anti_patterns": [
                "no beige productivity shell",
                "no card zoo without hierarchy",
                "no generic chatbot framing",
            ],
            "sample_seed_data": ["Opening cue", "Sponsor break", "Speaker handoff", "Volunteer issue"],
        }

    if (
        selected_flagship == "runway-reset-ledger"
        or "cash runway" in existing_domain
        or "budget" in existing_domain
        or any(token in text for token in ("budget", "finance", "cash", "tax", "income", "money", "expense"))
    ):
        return {
            "domain": "finance",
            "layout_archetype": "atlas",
            "interface_metaphor": "money runway atlas",
            "visual_motifs": ["radial budget rings", "runway ladders", "ledger cards", "ink-and-neon contrast"],
            "interaction_primitives": ["scenario switching", "runway adjustment", "bucket planning", "risk comparison"],
            "reference_objects": ["bucket", "runway", "bill", "ladder", "scenario"],
            "signature_demo_moments": [
                "watching runway scenarios recalc live",
                "turning income chaos into a visible plan",
            ],
            "anti_patterns": [
                "no bank clone dashboard",
                "no spreadsheet skin",
                "no generic insight cards without money objects",
            ],
            "sample_seed_data": ["Tax bucket", "Safety runway", "Lean month", "Stretch month"],
        }

    if any(token in text for token in ("mentor", "coaching", "career", "growth", "roadmap", "portfolio")):
        return {
            "domain": "coaching",
            "layout_archetype": "notebook",
            "interface_metaphor": "growth notebook",
            "visual_motifs": ["annotated dossiers", "milestone ribbons", "coach notes", "paper-over-canvas layers"],
            "interaction_primitives": [
                "milestone framing",
                "feedback loops",
                "habit tracking",
                "proof artifact capture",
            ],
            "reference_objects": ["milestone", "artifact", "ritual", "reflection", "path"],
            "signature_demo_moments": [
                "turning a vague career goal into a roadmap",
                "pinning proof artifacts to milestones",
            ],
            "anti_patterns": [
                "no generic ai assistant shell",
                "no neutral admin board",
                "no metric strip as primary story",
            ],
            "sample_seed_data": ["Stakeholder ritual", "Portfolio proof", "Month-one milestone", "Feedback checkpoint"],
        }

    return {
        "domain": "productivity",
        "layout_archetype": "lab",
        "interface_metaphor": "interactive concept lab",
        "visual_motifs": ["split surfaces", "bold typography", "modular cards", "ambient gradients"],
        "interaction_primitives": ["brief creation", "result shaping", "saved sessions", "rapid iteration"],
        "reference_objects": ["brief", "result", "artifact", "session", "variation"],
        "signature_demo_moments": ["turning a prompt into a visible artifact", "saving and comparing generated runs"],
        "anti_patterns": ["no generic dashboard", "no blank centered form", "no interchangeable saas shell"],
        "sample_seed_data": ["Primary brief", "Saved artifact", "Best variation", "Judge-ready outcome"],
    }


def _merge_inspiration_pack(idea: dict, pack: dict) -> dict:
    merged = dict(idea)
    if pack.get("domain"):
        merged["domain"] = pack["domain"]
    if pack.get("layout_archetype"):
        merged["layout_archetype"] = pack["layout_archetype"]
    if pack.get("interface_metaphor"):
        merged["interface_metaphor"] = pack["interface_metaphor"]
    if pack.get("reference_objects"):
        merged["reference_objects"] = _merge_unique_strings(merged.get("reference_objects"), pack["reference_objects"])
    if pack.get("sample_seed_data"):
        merged["sample_seed_data"] = _merge_unique_strings(merged.get("sample_seed_data"), pack["sample_seed_data"])
    if pack.get("visual_motifs"):
        merged["visual_style_hints"] = _merge_unique_strings(merged.get("visual_style_hints"), pack["visual_motifs"])
    if pack.get("signature_demo_moments"):
        merged["signature_demo_moments"] = _merge_unique_strings(
            merged.get("signature_demo_moments"),
            pack["signature_demo_moments"],
        )
        existing_demo = str(merged.get("demo_story_hints") or "").strip()
        demo_bits = _merge_unique_strings(
            [existing_demo] if existing_demo else [],
            pack["signature_demo_moments"],
        )
        if demo_bits:
            merged["demo_story_hints"] = " / ".join(demo_bits[:3])
    if pack.get("anti_patterns"):
        merged["experience_non_negotiables"] = _merge_unique_strings(
            merged.get("experience_non_negotiables"),
            pack["anti_patterns"],
        )
    return merged


def _merge_unique_strings(*groups) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        if isinstance(group, str):
            group = [group]
        if not isinstance(group, list):
            continue
        for item in group:
            text = str(item).strip()
            key = text.lower()
            if not text or key in seen:
                continue
            seen.add(key)
            merged.append(text)
    return merged
