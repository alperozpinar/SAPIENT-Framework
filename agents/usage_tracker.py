"""Deney boyunca API kullanımını takip eder. Thread-safe."""

import threading


class UsageTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self.calls = []

    def record(self, response):
        """LLMResponse nesnesini kaydet."""
        with self._lock:
            self.calls.append({
                "model": response.model,
                "provider": response.provider,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_ms": response.latency_ms,
                "cost_usd": response.cost_usd,
            })

    def summary(self) -> dict:
        """Toplam kullanım özeti döndür."""
        if not self.calls:
            return {}
        return {
            "total_calls": len(self.calls),
            "total_input_tokens": sum(c["input_tokens"] for c in self.calls),
            "total_output_tokens": sum(c["output_tokens"] for c in self.calls),
            "total_cost_usd": round(sum(c["cost_usd"] for c in self.calls), 4),
            "mean_latency_ms": round(
                sum(c["latency_ms"] for c in self.calls) / len(self.calls), 1
            ),
            "model": self.calls[0]["model"],
            "provider": self.calls[0]["provider"],
        }
