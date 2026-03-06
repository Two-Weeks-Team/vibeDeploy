from dataclasses import dataclass, field

PRICING_PER_MILLION = {
    "openai-gpt-oss-120b": (0.10, 0.70),
    "openai-gpt-oss-20b": (0.05, 0.45),
    "llama3.3-70b-instruct": (0.65, 0.65),
    "llama3-8b-instruct": (0.20, 0.20),
    "deepseek-r1-distill-llama-70b": (0.99, 0.99),
    "anthropic-claude-opus-4": (15.00, 75.00),
    "anthropic-claude-sonnet-4": (3.00, 15.00),
    "openai-gpt-5-nano": (0.05, 0.40),
    "openai-gpt-5-mini": (0.25, 2.00),
    "openai-gpt-5": (1.25, 10.00),
    "openai-gpt-4.1": (2.00, 8.00),
    "openai-o3": (2.00, 8.00),
    "openai-gpt-4o": (2.50, 10.00),
    "openai-gpt-4o-mini": (0.15, 0.60),
    "openai-o1": (15.00, 60.00),
    "openai-o3-mini": (1.10, 4.40),
    "alibaba-qwen3-32b": (0.25, 0.55),
    "mistral-nemo-instruct-2407": (0.30, 0.30),
    "anthropic-claude-4.1-opus": (15.00, 75.00),
    "anthropic-claude-4.5-sonnet": (3.00, 15.00),
    "anthropic-claude-opus-4.5": (5.00, 25.00),
    "openai-gpt-5.2": (1.75, 14.00),
    "openai-gpt-5.1-codex-max": (1.25, 10.00),
    "openai-gpt-5-2-pro": (21.00, 168.00),
    "anthropic-claude-4.5-haiku": (1.00, 5.00),
    "anthropic-claude-opus-4.6": (5.00, 25.00),
    "anthropic-claude-4.6-sonnet": (3.00, 15.00),
    "openai-gpt-5.3-codex": (1.75, 14.00),
    "openai-gpt-image-1": (5.00, 40.00),
    "fal-ai/flux/schnell": (3.00, 3.00),
    "fal-ai/fast-sdxl": (1.00, 1.00),
}

DB_MONTHLY_COST = 15.15


@dataclass
class CostTracker:
    entries: list[dict] = field(default_factory=list)

    def record(self, model: str, input_tokens: int, output_tokens: int, step: str = ""):
        input_price, output_price = PRICING_PER_MILLION.get(model, (0.0, 0.0))
        cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
        self.entries.append(
            {
                "model": model,
                "step": step,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": round(cost, 6),
            }
        )

    @property
    def total_cost(self) -> float:
        return round(sum(e["cost_usd"] for e in self.entries), 6)

    @property
    def total_input_tokens(self) -> int:
        return sum(e["input_tokens"] for e in self.entries)

    @property
    def total_output_tokens(self) -> int:
        return sum(e["output_tokens"] for e in self.entries)

    def summary(self) -> dict:
        by_model: dict[str, float] = {}
        for e in self.entries:
            by_model[e["model"]] = by_model.get(e["model"], 0) + e["cost_usd"]

        return {
            "total_cost_usd": self.total_cost,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "steps": len(self.entries),
            "cost_by_model": {k: round(v, 6) for k, v in sorted(by_model.items(), key=lambda x: -x[1])},
            "db_monthly_cost_usd": DB_MONTHLY_COST,
        }


def estimate_pipeline_cost() -> dict:
    """Estimate cost for a full evaluation pipeline run based on typical token usage."""
    estimates = [
        ("openai-gpt-oss-120b", 2000, 3000, "input_processor"),
        ("openai-gpt-oss-120b", 2000, 4000, "architect"),
        ("openai-gpt-oss-120b", 2000, 4000, "scout"),
        ("openai-gpt-oss-120b", 2000, 4000, "guardian"),
        ("openai-gpt-oss-120b", 2000, 4000, "catalyst"),
        ("openai-gpt-oss-120b", 2000, 4000, "advocate"),
        ("deepseek-r1-distill-llama-70b", 8000, 6000, "cross_examination"),
        ("deepseek-r1-distill-llama-70b", 10000, 5000, "strategist_verdict"),
        ("alibaba-qwen3-32b", 3000, 8000, "doc_generation"),
        ("openai-gpt-oss-120b", 5000, 12000, "code_generation"),
        ("fal-ai/flux/schnell", 500, 500, "image_generation"),
    ]

    tracker = CostTracker()
    for model, inp, out, step in estimates:
        tracker.record(model, inp, out, step)

    return {
        **tracker.summary(),
        "note": "Estimated cost per full pipeline run (idea → deploy)",
    }
