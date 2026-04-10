FONT_PAIRINGS = [
    {
        "id": "editorial",
        "display": "Playfair_Display",
        "body": "Inter",
        "keywords": ["magazine", "news", "story"],
    },
    {
        "id": "modern_saas",
        "display": "Geist",
        "body": "Geist",
        "keywords": ["tech", "tool", "saas", "app"],
    },
    {
        "id": "elegant",
        "display": "Cormorant_Garamond",
        "body": "Montserrat",
        "keywords": ["luxury", "beauty", "fashion"],
    },
    {
        "id": "tech_dev",
        "display": "JetBrains_Mono",
        "body": "Inter",
        "keywords": ["developer", "code", "api"],
    },
    {
        "id": "friendly",
        "display": "Quicksand",
        "body": "Outfit",
        "keywords": ["community", "education", "kids"],
    },
    {
        "id": "business",
        "display": "Lora",
        "body": "Open_Sans",
        "keywords": ["finance", "legal", "corporate"],
    },
    {
        "id": "creative",
        "display": "Syne",
        "body": "Work_Sans",
        "keywords": ["design", "art", "creative"],
    },
    {
        "id": "minimal",
        "display": "Space_Grotesk",
        "body": "Inter",
        "keywords": ["portfolio", "minimal", "clean"],
    },
    {
        "id": "classic",
        "display": "Libre_Baskerville",
        "body": "Source_Sans_3",
        "keywords": ["archive", "history", "classic"],
    },
    {
        "id": "bold",
        "display": "Archivo_Black",
        "body": "Archivo",
        "keywords": ["sports", "entertainment", "bold"],
    },
]

_DEFAULT_PAIRING_ID = "modern_saas"


def select_font_pairing(typography_hint: str, design_system: dict | None = None) -> dict:
    """Select font pairing — prefer LLM-generated fonts, fall back to keyword matching."""
    import re

    # Use LLM-generated typography if available
    if design_system:
        generated = design_system.get("generated", {})
        typo = generated.get("typography") if generated else None
        if typo and typo.get("display_font"):
            return {
                "id": "llm_generated",
                "display": typo["display_font"].replace(" ", "_"),
                "body": (typo.get("body_font") or typo["display_font"]).replace(" ", "_"),
                "keywords": [],
            }

    hint_lower = typography_hint.lower()
    for pairing in FONT_PAIRINGS:
        for keyword in pairing["keywords"]:
            if re.search(r"\b" + re.escape(keyword) + r"\b", hint_lower):
                return pairing
    return next(p for p in FONT_PAIRINGS if p["id"] == _DEFAULT_PAIRING_ID)


def generate_layout_font_imports(pairing: dict) -> str:
    display_font = pairing["display"]
    body_font = pairing["body"]

    if display_font == body_font:
        lines = [
            f'import {{ {display_font} }} from "next/font/google";',
            "",
            f"const displayFont = {display_font}({{",
            '  subsets: ["latin"],',
            '  variable: "--font-display",',
            "});",
            "",
            f"const bodyFont = {display_font}({{",
            '  subsets: ["latin"],',
            '  variable: "--font-body",',
            "});",
        ]
    else:
        lines = [
            f'import {{ {display_font}, {body_font} }} from "next/font/google";',
            "",
            f"const displayFont = {display_font}({{",
            '  subsets: ["latin"],',
            '  variable: "--font-display",',
            "});",
            "",
            f"const bodyFont = {body_font}({{",
            '  subsets: ["latin"],',
            '  variable: "--font-body",',
            "});",
        ]

    return "\n".join(lines)


def generate_type_scale_css() -> str:
    scale_steps = [
        ("--type-xs", "0.64rem"),
        ("--type-sm", "0.80rem"),
        ("--type-base", "1rem"),
        ("--type-md", "1.25rem"),
        ("--type-lg", "1.563rem"),
        ("--type-xl", "1.953rem"),
        ("--type-2xl", "2.441rem"),
        ("--type-3xl", "3.052rem"),
        ("--type-4xl", "3.815rem"),
    ]

    lines = [":root {"]
    lines.append("  --font-display: var(--font-display, sans-serif);")
    lines.append("  --font-body: var(--font-body, sans-serif);")
    lines.append("")
    for name, value in scale_steps:
        lines.append(f"  {name}: {value};")
    lines.append("}")

    return "\n".join(lines)
