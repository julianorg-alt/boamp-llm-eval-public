"""Exécution d'un modèle sur des avis : garde de budget, coût, enregistrement des réponses."""

from __future__ import annotations

import json
from pathlib import Path

from boamp_eval.costs import CostLedger, Usage, cost_usd
from boamp_eval.schema import (
    DEFAULT_EFFORT,
    DEFAULT_MAX_TOKENS,
    SYSTEM_PROMPT,
    build_params,
    parse_response,
)

CHARS_PER_TOKEN = 2.0  # majorant prudent pour l'estimation avant appel (non mesuré)


def estimate_usd(model: str, texte: str, max_tokens: int) -> float:
    est_in = int((len(SYSTEM_PROMPT) + len(texte)) / CHARS_PER_TOKEN) + 2000  # + schéma injecté
    return cost_usd(model, Usage(input_tokens=est_in, output_tokens=max_tokens))


def run(
    records: list[dict],
    model: str,
    client,
    ledger: CostLedger,
    *,
    label: str,
    out_path: Path | None,
    effort: str = DEFAULT_EFFORT,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> list[dict]:
    """Un appel par avis. Chaque ligne : idweb, pred, usage, error, cost_usd."""
    rows = []
    for rec in records:
        params = build_params(model, rec["texte"], effort=effort, max_tokens=max_tokens)
        if client.live:
            ledger.guard(estimate_usd(model, rec["texte"], max_tokens))
        resp = client.create(params, key=rec["idweb"])
        parsed = parse_response(resp)
        cost = (
            ledger.record(model, parsed.usage, label=f"{label}:{rec['idweb']}")
            if client.live
            else 0.0
        )
        if out_path is not None:
            with Path(out_path).open("a") as f:
                f.write(
                    json.dumps({"idweb": rec["idweb"], "model": model, "response": resp}) + "\n"
                )
        rows.append(
            {
                "idweb": rec["idweb"],
                "pred": parsed.pred,
                "usage": parsed.usage.__dict__,
                "error": parsed.error,
                "cost_usd": cost,
            }
        )
    return rows
