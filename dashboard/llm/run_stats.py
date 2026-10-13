"""Aggregate numbers for one categorization run (no concept text, safe to log)."""

from collections import Counter

from dashboard.config import settings

FALLBACK = ("Otros", "General")
HIGH_CONFIDENCE = 0.9


class RunStats:
    def __init__(self) -> None:
        self.total = 0
        self.errors = 0
        self.fallbacks = 0
        self.from_memory = 0
        self.from_similar = 0
        self.low_confidence = 0
        self.high_confidence = 0
        self.confidence_sum = 0.0
        self.confidence_count = 0
        self.elapsed_ms = 0.0
        self.categories: Counter[str] = Counter()

    def record_memory(self) -> None:
        self.from_memory += 1

    def record_similar(self) -> None:
        self.from_similar += 1

    @property
    def mid_confidence(self) -> int:
        return self.confidence_count - self.low_confidence - self.high_confidence

    @property
    def average_confidence(self) -> float | None:
        return self.confidence_sum / self.confidence_count if self.confidence_count else None

    def record(
        self, category: str, subcategory: str | None, elapsed_ms: float, confidence: float | None = None
    ) -> None:
        self.total += 1
        if confidence is not None:
            self.confidence_sum += confidence
            self.confidence_count += 1
            if confidence < settings.llm_confidence_threshold:
                self.low_confidence += 1
            elif confidence >= HIGH_CONFIDENCE:
                self.high_confidence += 1
        self.elapsed_ms += elapsed_ms
        self.categories[category] += 1
        if (category, subcategory) == FALLBACK:
            self.fallbacks += 1

    def record_error(self) -> None:
        self.errors += 1

    def summary(self) -> str:
        done = self.total
        avg = self.elapsed_ms / done if done else 0.0
        top = ", ".join(f"{name}={count}" for name, count in self.categories.most_common(6))
        return (
            f"categorization run: {done} by the model ({self.low_confidence} low confidence), "
            f"{self.from_memory} from the merchant memory, {self.from_similar} by similarity, {self.fallbacks} fell back to Otros/General, "
            f"{self.errors} errors, avg {avg:.0f} ms/call, total {self.elapsed_ms / 1000:.1f} s; "
            f"top categories: {top or 'none'}"
        )
