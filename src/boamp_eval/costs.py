"""Tarifs publics, calcul de coût et registre cumulé avec plafond de dépense.

Tarifs en USD par million de tokens, relevés le 2026-11-18 sur
https://platform.claude.com/docs/en/about-claude/pricing (voir docs/sources.md).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

HAIKU_LONG_PROMPT_THRESHOLD = 100_000
BATCH_FACTOR = 0.5

# input, cache write 5 min, cache write 1 h, cache hit, output
_Rates = tuple[float, float, float, float, float]
PRICES: dict[str, _Rates] = {
    "claude-opus-5-5": (4.0, 5.0, 8.0, 0.20, 20.0),
    "claude-sonnet-5-5": (2.0, 2.50, 4.0, 0.10, 10.0),
    "claude-haiku-5-5": (0.10, 0.125, 0.20, 0.01, 0.50),
}
# Haiku 5.5 : prompt de plus de 100 000 tokens (lecture + écriture de cache comprises).
HAIKU_LONG_RATES: _Rates = (0.50, 0.625, 1.0, 0.05, 2.50)


class BudgetExceededError(RuntimeError):
    """Un appel ferait dépasser le plafond de dépense."""


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0  # y compris les tokens de réflexion, facturés comme sortie
    cache_write_5m_tokens: int = 0
    cache_write_1h_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def prompt_tokens(self) -> int:
        return (
            self.input_tokens
            + self.cache_write_5m_tokens
            + self.cache_write_1h_tokens
            + self.cache_read_tokens
        )


def cost_usd(model: str, usage: Usage, *, batch: bool = False) -> float:
    rates = PRICES[model]
    if model == "claude-haiku-5-5" and usage.prompt_tokens > HAIKU_LONG_PROMPT_THRESHOLD:
        rates = HAIKU_LONG_RATES
    r_in, r_w5, r_w1, r_hit, r_out = rates
    total = (
        usage.input_tokens * r_in
        + usage.cache_write_5m_tokens * r_w5
        + usage.cache_write_1h_tokens * r_w1
        + usage.cache_read_tokens * r_hit
        + usage.output_tokens * r_out
    ) / 1_000_000
    return total * BATCH_FACTOR if batch else total


class CostLedger:
    """Registre JSON des dépenses ; `guard` refuse tout appel qui dépasserait le plafond."""

    def __init__(self, path: Path, cap_usd: float = 15.0) -> None:
        self.path = Path(path)
        self.cap_usd = cap_usd
        self.entries: list[dict] = []
        if self.path.exists():
            self.entries = json.loads(self.path.read_text())["entries"]

    @property
    def total_usd(self) -> float:
        return sum(e["cost_usd"] for e in self.entries)

    def guard(self, estimated_usd: float) -> None:
        if self.total_usd + estimated_usd > self.cap_usd:
            raise BudgetExceededError(
                f"{self.total_usd:.4f} $ déjà dépensés + {estimated_usd:.4f} $ estimés "
                f"dépasseraient le plafond de {self.cap_usd:.2f} $"
            )

    def record(self, model: str, usage: Usage, *, label: str, batch: bool = False) -> float:
        cost = cost_usd(model, usage, batch=batch)
        if self.path.exists():  # un autre processus a pu écrire : on repart du fichier
            self.entries = json.loads(self.path.read_text())["entries"]
        self.entries.append(
            {
                "model": model,
                "label": label,
                "batch": batch,
                "usage": usage.__dict__,
                "cost_usd": cost,
            }
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"entries": self.entries}, indent=2) + "\n")
        return cost
