import json
import re

from ..llm import MODEL_CONFIG, ainvoke_with_retry, get_llm, get_rate_limit_fallback_models
from ..state import VibeDeployState

EXPERIENCE_AGENT_PROMPT = (
    "You are the Experience Agent. You convert a product idea plus inspiration pack into a concrete "
    "first-screen experience contract that a blueprint and code generator can follow.\n\n"
    "Return a JSON object with:\n"
    "- must_have_surfaces: list of 4-6 specific first-screen sections or surfaces\n"
    "- primary_action_label: concise CTA label\n"
    "- input_labels: object with query_label and preferences_label\n"
    "- output_entities: list of 3-5 concrete result object names\n"
    "- trust_surfaces: list of 2-4 credibility surfaces\n"
    "- proof_points: list of 2-4 trust or proof elements\n"
    "- experience_non_negotiables: list of 4-6 UX guardrails\n"
    "- design_direction: object with visual_tone, color_strategy, typography_strategy, layout_strategy, motion_strategy, anti_patterns\n"
    "- ui_copy_tone: short phrase\n\n"
    "The answer must be domain-specific. Avoid generic labels like dashboard, analytics, metrics, or feature panel "
    "unless the product genuinely requires them."
)


async def experience_agent(state: VibeDeployState) -> dict:
    idea = state.get("idea", {}) or {}
    inspiration_pack = state.get("inspiration_pack", {}) or {}

    context = json.dumps(
        {
            "idea": idea,
            "inspiration_pack": inspiration_pack,
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
                {"role": "system", "content": EXPERIENCE_AGENT_PROMPT},
                {"role": "user", "content": f"Create an experience contract from this context:\n\n{context}"},
            ],
            fallback_models=get_rate_limit_fallback_models(model),
        )
        spec = _parse_json(response.content)
    except Exception:
        spec = {}

    if not isinstance(spec, dict) or not spec.get("must_have_surfaces"):
        spec = _fallback_experience_spec(idea, inspiration_pack)

    merged_idea = _merge_experience_spec(idea, spec)
    return {
        "idea": merged_idea,
        "experience_spec": spec,
        "phase": "experience_specialized",
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


def _fallback_experience_spec(idea: dict, inspiration_pack: dict) -> dict:
    domain = str(idea.get("domain") or inspiration_pack.get("domain") or "").strip().lower()

    if domain == "creator":
        return {
            "must_have_surfaces": [
                "hook card board",
                "shot list lane",
                "repurpose lane",
                "publish queue",
                "saved content batches",
            ],
            "primary_action_label": "Generate content batch",
            "input_labels": {
                "query_label": "Content angle, audience, or campaign brief",
                "preferences_label": "Platforms, tone, cadence, and recording constraints",
            },
            "output_entities": ["hook card", "shot list", "repurpose lane", "publish queue"],
            "trust_surfaces": ["saved content batches", "platform variations", "shoot-day readiness"],
            "proof_points": ["multi-post content batch", "platform-specific hook variations", "shoot-day checklist"],
            "experience_non_negotiables": [
                "no generic dashboard shell",
                "show creator workflow objects above the fold",
                "use creator-native language instead of enterprise copy",
                "keep publish sequencing visible from first load",
            ],
            "design_direction": {
                "visual_tone": "editorial, punchy, and creator-native",
                "color_strategy": "paper-light neutrals with bold production accents",
                "typography_strategy": "magazine-style display with sharp sans body",
                "layout_strategy": "storyboard board with workflow lanes and saved queue",
                "motion_strategy": "card reveals and sequence transitions",
                "anti_patterns": ["generic SaaS dashboard", "KPI tile shell", "empty input-first screen"],
            },
            "ui_copy_tone": "creator-native and decisive",
        }

    if domain == "travel":
        return {
            "must_have_surfaces": [
                "destination brief",
                "day-by-day route board",
                "moodboard highlights",
                "saved itineraries",
                "budget and timing rail",
            ],
            "primary_action_label": "Build trip route",
            "input_labels": {
                "query_label": "Trip brief, mood, or city goal",
                "preferences_label": "Style, budget, season, and must-see cues",
            },
            "output_entities": ["route day", "stop card", "highlight", "backup option"],
            "trust_surfaces": ["saved trip shelf", "time and budget cues", "signature moments"],
            "proof_points": ["saved itinerary snapshots", "route-ready day cards", "visible mood and budget alignment"],
            "experience_non_negotiables": [
                "no blank hero plus plain form",
                "show one trip shape above the fold",
                "use travel nouns instead of generic ai labels",
                "keep visual rhythm and place imagery cues visible",
            ],
            "design_direction": {
                "visual_tone": "editorial, cinematic, and warm",
                "color_strategy": "sunset accents over paper-like neutrals",
                "typography_strategy": "high-contrast display serif with humane sans body",
                "layout_strategy": "story-led spread with route board and supporting rail",
                "motion_strategy": "soft reveal and route-building transitions",
                "anti_patterns": ["generic SaaS dashboard", "banking app shell", "empty admin cards"],
            },
            "ui_copy_tone": "aspirational but practical",
        }

    if domain == "event_ops":
        return {
            "must_have_surfaces": [
                "live cue timeline",
                "stage readiness board",
                "incident lane",
                "speaker handoff panel",
                "saved show plans",
            ],
            "primary_action_label": "Draft run of show",
            "input_labels": {
                "query_label": "Event scenario or show brief",
                "preferences_label": "Crew limits, stage constraints, pacing notes",
            },
            "output_entities": ["cue block", "handoff", "incident response", "status lane"],
            "trust_surfaces": ["readiness states", "live timeline", "rehearsal snapshots"],
            "proof_points": ["visible handoff timing", "issue escalation lane", "operator-friendly sequencing"],
            "experience_non_negotiables": [
                "dark, high-signal console instead of neutral cards",
                "timeline must dominate the first screen",
                "avoid generic metric tiles as the main story",
                "surface show objects, not generic ai copy",
            ],
            "design_direction": {
                "visual_tone": "high-contrast, urgent, and command-center driven",
                "color_strategy": "dark graphite base with signal-light accents",
                "typography_strategy": "condensed display with compact UI sans",
                "layout_strategy": "operations console with large timeline spine",
                "motion_strategy": "status flips, cue pulses, and live-sequence movement",
                "anti_patterns": [
                    "beige productivity template",
                    "marketing hero-first landing page",
                    "generic dashboard cards",
                ],
            },
            "ui_copy_tone": "confident and operational",
        }

    if domain == "learning":
        return {
            "must_have_surfaces": [
                "study sprint builder",
                "syllabus board",
                "review cadence rail",
                "saved plans",
                "confidence checkpoints",
            ],
            "primary_action_label": "Generate study sprint",
            "input_labels": {
                "query_label": "Learning goal or interview target",
                "preferences_label": "Available time, topics, and pressure points",
            },
            "output_entities": ["module", "sprint lane", "review block", "checkpoint"],
            "trust_surfaces": ["syllabus depth", "time allocation", "review schedule"],
            "proof_points": ["visible sprint calendar", "concrete drill blocks", "saved milestones"],
            "experience_non_negotiables": [
                "no generic chatbot wrapper",
                "put syllabus structure on first load",
                "use academic nouns and progress cues",
                "show a schedule, not only prose",
            ],
            "design_direction": {
                "visual_tone": "energetic, optimistic, and structured",
                "color_strategy": "bright study accents over clean workshop neutrals",
                "typography_strategy": "sharp grotesk headline with readable companion sans",
                "layout_strategy": "studio board with plan lanes and review rail",
                "motion_strategy": "staggered plan reveal and progress highlighting",
                "anti_patterns": ["plain textarea landing page", "corporate analytics shell", "static brochure"],
            },
            "ui_copy_tone": "encouraging and exact",
        }

    if domain == "finance":
        return {
            "must_have_surfaces": [
                "money runway summary",
                "bucket planner",
                "scenario cards",
                "safety ladder",
                "saved plans",
            ],
            "primary_action_label": "Shape money plan",
            "input_labels": {
                "query_label": "Financial reset goal or planning scenario",
                "preferences_label": "Income pattern, stressors, targets, and tradeoffs",
            },
            "output_entities": ["bucket", "scenario", "runway band", "safety step"],
            "trust_surfaces": ["runway estimate", "tax visibility", "stress-reduction scenarios"],
            "proof_points": ["visible money buckets", "scenario comparison", "saved plan history"],
            "experience_non_negotiables": [
                "avoid spreadsheet skin",
                "show actual money objects immediately",
                "no generic insight dashboard",
                "make tradeoffs visible in the first screen",
            ],
            "design_direction": {
                "visual_tone": "strategic, grounded, and high-clarity",
                "color_strategy": "ink base with sharp citrus and mint highlights",
                "typography_strategy": "editorial numerals with precise sans text",
                "layout_strategy": "atlas-style summary with runway ladder and scenarios",
                "motion_strategy": "scenario morphing and value emphasis transitions",
                "anti_patterns": ["bank account clone", "generic analytics dashboard", "neutral admin board"],
            },
            "ui_copy_tone": "calm and directive",
        }

    if domain == "meal_prep":
        return {
            "must_have_surfaces": [
                "prep block planner",
                "meal board",
                "grocery lane",
                "container checklist",
                "saved meal boards",
            ],
            "primary_action_label": "Generate meal prep board",
            "input_labels": {
                "query_label": "Weekly cooking goal, diet, or meal prep brief",
                "preferences_label": "Household size, prep time, budget, and ingredients to use",
            },
            "output_entities": ["prep block", "grocery lane", "meal board", "container checklist"],
            "trust_surfaces": ["saved meal boards", "grocery grouping", "cook-from-this practicality"],
            "proof_points": ["weekly prep plan", "organized grocery groups", "saved meal board"],
            "experience_non_negotiables": [
                "no generic productivity dashboard",
                "show prep objects above the fold",
                "make grocery and meal sequencing practical",
                "avoid recipe-blog-only framing",
            ],
            "design_direction": {
                "visual_tone": "practical, warm, and kitchen-ready",
                "color_strategy": "fresh produce accents over clean prep neutrals",
                "typography_strategy": "friendly display with crisp kitchen note text",
                "layout_strategy": "atlas board with prep and grocery lanes",
                "motion_strategy": "prep-step reveals and board transitions",
                "anti_patterns": ["productivity dashboard shell", "empty hero", "generic ai assistant framing"],
            },
            "ui_copy_tone": "practical and encouraging",
        }

    if domain == "coaching":
        return {
            "must_have_surfaces": [
                "growth roadmap",
                "mentor note lane",
                "ritual tracker",
                "proof artifact shelf",
                "saved coaching paths",
            ],
            "primary_action_label": "Map coaching path",
            "input_labels": {
                "query_label": "Growth goal, role change, or coaching challenge",
                "preferences_label": "Habits, feedback style, milestones, and constraints",
            },
            "output_entities": ["milestone", "ritual", "artifact", "reflection"],
            "trust_surfaces": ["visible milestones", "proof artifacts", "coach note framing"],
            "proof_points": ["roadmap structure", "proof artifact prompts", "saved path snapshots"],
            "experience_non_negotiables": [
                "avoid generic AI assistant framing",
                "use roadmap and milestone language",
                "make progress artifacts visible above the fold",
                "do not lead with empty stats",
            ],
            "design_direction": {
                "visual_tone": "reflective, premium, and directional",
                "color_strategy": "warm neutrals with grounded green and copper accents",
                "typography_strategy": "literary headline with disciplined sans support",
                "layout_strategy": "notebook dossier with roadmap spine and artifact shelf",
                "motion_strategy": "annotation reveals and milestone emphasis",
                "anti_patterns": ["generic dashboard", "form-only hero", "plain chatbot surface"],
            },
            "ui_copy_tone": "measured and mentor-like",
        }

    return {
        "must_have_surfaces": [
            "idea brief",
            "primary generator",
            "result canvas",
            "saved outputs",
            "supporting evidence rail",
        ],
        "primary_action_label": "Generate concept",
        "input_labels": {
            "query_label": "Core product brief",
            "preferences_label": "Constraints, style cues, or priorities",
        },
        "output_entities": ["artifact", "result", "highlight"],
        "trust_surfaces": ["saved outputs", "evidence rail", "visible next steps"],
        "proof_points": ["saved sessions", "visible results", "first-run clarity"],
        "experience_non_negotiables": [
            "avoid generic SaaS shells",
            "avoid blank form-only first screens",
            "use domain nouns in the UI",
            "surface one result object immediately",
        ],
        "design_direction": {
            "visual_tone": "intentional and domain-specific",
            "color_strategy": "non-flat background with one strong accent family",
            "typography_strategy": "purposeful display + readable body contrast",
            "layout_strategy": "clear hero-to-workbench-to-result progression",
            "motion_strategy": "focused reveal and state transition motion",
            "anti_patterns": ["generic dashboard", "empty analytics tiles", "chatbot wrapper"],
        },
        "ui_copy_tone": "specific and product-led",
    }


def _merge_experience_spec(idea: dict, spec: dict) -> dict:
    merged = dict(idea)
    for field in ("must_have_surfaces", "proof_points", "experience_non_negotiables"):
        if spec.get(field):
            merged[field] = _merge_unique_strings(merged.get(field), spec[field])

    if spec.get("design_direction"):
        merged["design_direction"] = spec["design_direction"]
    if spec.get("primary_action_label"):
        merged["primary_action_label"] = spec["primary_action_label"]
    if spec.get("input_labels"):
        merged["input_labels"] = dict(spec["input_labels"])
    if spec.get("output_entities"):
        merged["output_entities"] = _merge_unique_strings(merged.get("output_entities"), spec["output_entities"])
    if spec.get("trust_surfaces"):
        merged["trust_surfaces"] = _merge_unique_strings(merged.get("trust_surfaces"), spec["trust_surfaces"])
    if spec.get("ui_copy_tone"):
        merged["ui_copy_tone"] = spec["ui_copy_tone"]

    design_direction = spec.get("design_direction") or {}
    if isinstance(design_direction, dict):
        tone_bits = [
            design_direction.get("visual_tone", ""),
            design_direction.get("layout_strategy", ""),
            design_direction.get("color_strategy", ""),
        ]
        merged["visual_style_hints"] = _merge_unique_strings(merged.get("visual_style_hints"), tone_bits)

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
