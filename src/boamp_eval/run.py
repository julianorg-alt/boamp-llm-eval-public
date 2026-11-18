"""CLI : `python -m boamp_eval.run --model M --per-famille 1 [--live | --replay FICHIER]`.

Travaille sur le jeu de dev uniquement (le hold-out n'est jamais lu ici).
Sans `--live` ni `--replay`, rien n'est appelé : le mode est obligatoire.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from boamp_eval import harness, report
from boamp_eval.costs import CostLedger
from boamp_eval.llm import HttpClient, RecordedClient

DEV = Path("data/dev.jsonl")
LEDGER = Path("data/costs-ledger.json")


def pick(records: list[dict], per_famille: int) -> list[dict]:
    """Les `per_famille` premiers avis de chaque famille, dans l'ordre du fichier (déterministe)."""
    seen: dict[str, int] = {}
    out = []
    for r in records:
        if seen.get(r["famille"], 0) < per_famille:
            seen[r["famille"]] = seen.get(r["famille"], 0) + 1
            out.append(r)
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--per-famille", type=int, default=1)
    ap.add_argument("--effort", default="low")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true", help="appels réels (ANTHROPIC_API_KEY)")
    mode.add_argument("--replay", type=Path, help="rejoue un JSONL enregistré, sans réseau")
    ap.add_argument("--out", type=Path, help="JSONL des réponses brutes (mode --live)")
    ap.add_argument("--label", default="e2")
    a = ap.parse_args(argv)

    records = pick([json.loads(x) for x in DEV.read_text().splitlines()], a.per_famille)
    ledger = CostLedger(LEDGER)
    client = HttpClient() if a.live else RecordedClient(a.replay)
    rows = harness.run(
        records, a.model, client, ledger, label=a.label,
        out_path=a.out if a.live else None, effort=a.effort,
    )  # fmt: skip
    sm = report.summarize(report.evaluate(records, rows))
    print(json.dumps(sm, ensure_ascii=False, indent=1))
    print(
        f"coût de ce passage : {sum(r['cost_usd'] for r in rows):.5f} $ ; cumul {ledger.total_usd:.5f} $"
    )


if __name__ == "__main__":
    main()
