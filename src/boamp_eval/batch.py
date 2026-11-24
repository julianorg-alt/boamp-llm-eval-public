"""Passages par Message Batches API : estimation, soumission, attente, collecte, CLI.

Tarif lot : -50 % (`costs.cost_usd(batch=True)`). Les lignes brutes de résultat sont
conservées telles quelles (JSONL) pour rejouer les scores sans réseau.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from boamp_eval import report
from boamp_eval.costs import CostLedger, Usage, cost_usd
from boamp_eval.schema import (
    DEFAULT_EFFORT,
    DEFAULT_MAX_TOKENS,
    batch_requests,
    build_params,
    parse_batch_line,
)

SCHEMA_MARGIN_TOKENS = 2000  # le schéma de sortie et le prompt système injecté par l'API (majorant)
LEDGER = Path("data/costs-ledger.json")
FREEZE = Path("docs/FREEZE.md")
FREEZE_V2 = Path("docs/FREEZE-v2.md")
FREEZE_FOR = {"holdout": FREEZE, "v2-test": FREEZE_V2}  # jeux lus seulement après un gel commité
MODELS = ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5")


@dataclass(frozen=True)
class Estimate:
    n: int
    input_tokens: int
    output_tokens: int  # pire cas : max_tokens par avis
    usd: float


def estimate(client, model: str, records: list[dict], *, max_tokens: int = DEFAULT_MAX_TOKENS,
             effort: str = DEFAULT_EFFORT) -> Estimate:  # fmt: skip
    """Pire cas, tarif lot : entrée comptée par l'endpoint + marge, sortie = max_tokens, sans cache."""
    tin = sum(
        client.count_tokens(build_params(model, r["texte"], effort=effort, max_tokens=max_tokens))
        + SCHEMA_MARGIN_TOKENS
        for r in records
    )
    tout = max_tokens * len(records)
    usd = cost_usd(model, Usage(input_tokens=tin, output_tokens=tout), batch=True)
    return Estimate(len(records), tin, tout, usd)


def submit(client, model: str, records: list[dict], ledger: CostLedger, *,
           max_tokens: int = DEFAULT_MAX_TOKENS, effort: str = DEFAULT_EFFORT) -> dict:  # fmt: skip
    est = estimate(client, model, records, max_tokens=max_tokens, effort=effort)
    ledger.guard(est.usd)
    return client.create_batch(batch_requests(model, records, effort=effort, max_tokens=max_tokens))


def wait(client, batch_id: str, *, poll_s: float = 30, sleep=time.sleep) -> dict:
    while True:
        b = client.get_batch(batch_id)
        if b["processing_status"] == "ended":
            return b
        sleep(poll_s)


def _t(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def latency_s(b: dict) -> float:
    return (_t(b["ended_at"]) - _t(b["created_at"])).total_seconds()


class RecordedBatch:
    """Rejoue les lignes brutes d'un lot enregistré."""

    live = False

    def __init__(self, path: Path) -> None:
        self.lines = [x for x in Path(path).read_text().splitlines() if x.strip()]

    def batch_results(self, batch_id: str) -> list[str]:  # noqa: ARG002
        return self.lines


def collect(client, batch_id: str, model: str, records: list[dict], ledger: CostLedger, *,
            label: str, out_path: Path | None, record_costs: bool = True) -> list[dict]:  # fmt: skip
    """Lit les résultats, écrit les lignes brutes, enregistre le coût (tarif lot), un row par avis."""
    lines = client.batch_results(batch_id)
    if out_path is not None:
        Path(out_path).write_text("\n".join(lines) + "\n")
    parsed = dict(parse_batch_line(ln) for ln in lines)
    rows = []
    for rec in records:
        p = parsed.get(rec["idweb"])
        if p is None:
            rows.append({"idweb": rec["idweb"], "pred": None, "usage": Usage().__dict__,
                         "error": "batch: absent", "cost_usd": 0.0})  # fmt: skip
            continue
        cost = (
            ledger.record(model, p.usage, label=f"{label}:{rec['idweb']}", batch=True)
            if record_costs and p.error != "batch: expired" and p.usage != Usage()
            else 0.0
        )
        rows.append({"idweb": rec["idweb"], "pred": p.pred, "usage": p.usage.__dict__,
                     "error": p.error, "cost_usd": cost})  # fmt: skip
    return rows


def require_freeze(split: str) -> None:
    """Un jeu protégé (hold-out v1, test v2) n'est lu qu'après le commit de son gel versionné."""
    freeze = FREEZE_FOR.get(split)
    if freeze is None:
        return
    ok = freeze.exists() and subprocess.run(  # noqa: S603
        ["git", "ls-files", "--error-unmatch", str(freeze)],  # noqa: S607
        capture_output=True, check=False,
    ).returncode == 0  # fmt: skip
    if not ok:
        sys.exit(
            f"{'hold-out' if split == 'holdout' else split} refusé : {freeze} absent ou non versionné (geler d'abord)"
        )


def _load(split: str) -> list[dict]:
    require_freeze(split)
    return [json.loads(x) for x in Path(f"data/{split}.jsonl").read_text().splitlines()]


def main(argv: list[str] | None = None) -> None:
    from boamp_eval.llm import HttpClient  # noqa: PLC0415

    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["estimate", "submit", "collect", "replay"])
    ap.add_argument("--model", required=True, choices=MODELS)
    ap.add_argument("--split", choices=["dev", "holdout", "v2-test", "v2-tuning"], default="dev")
    ap.add_argument("--effort", default=DEFAULT_EFFORT)
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument("--cap", type=float, help="plafond $ cumulé du registre (remplace 15 $)")
    ap.add_argument("--limit", type=int, help="premiers avis seulement (mise au point)")
    ap.add_argument("--name", required=True, help="préfixe des fichiers data/runs/<name>.*")
    ap.add_argument("--poll", type=float, default=30)
    a = ap.parse_args(argv)

    records = _load(a.split)[: a.limit]
    base = Path("data/runs") / a.name
    meta_p, raw_p = base.with_suffix(".meta.json"), base.with_suffix(".jsonl")
    ledger = CostLedger(LEDGER, cap_usd=a.cap) if a.cap else CostLedger(LEDGER)
    if a.action == "replay":
        client, bid, meta = RecordedBatch(raw_p), "replay", json.loads(meta_p.read_text())
        rows = collect(client, bid, a.model, records, ledger, label=a.name, out_path=None,
                       record_costs=False)  # fmt: skip
    else:
        client = HttpClient()
        if a.action == "estimate":
            e = estimate(client, a.model, records, effort=a.effort, max_tokens=a.max_tokens)
            print(json.dumps(e.__dict__))
            return
        if a.action == "submit":
            b = submit(client, a.model, records, ledger, effort=a.effort, max_tokens=a.max_tokens)
            meta_p.parent.mkdir(parents=True, exist_ok=True)
            meta_p.write_text(json.dumps({"batch_id": b["id"], "model": a.model, "split": a.split,
                                          "effort": a.effort, "max_tokens": a.max_tokens, "n": len(records),
                                          "created_at": b["created_at"]}, indent=1) + "\n")  # fmt: skip
            print(b["id"])
            return
        meta = json.loads(meta_p.read_text())
        b = wait(client, meta["batch_id"], poll_s=a.poll)
        meta.update(ended_at=b["ended_at"], request_counts=b["request_counts"],
                    latency_s=latency_s(b))  # fmt: skip
        rows = collect(client, meta["batch_id"], a.model, records, ledger, label=a.name,
                       out_path=raw_p)  # fmt: skip
        meta["cost_usd"] = sum(r["cost_usd"] for r in rows)
        meta_p.write_text(json.dumps(meta, indent=1) + "\n")
    sm = report.summarize(report.evaluate(records, rows), ci=True)
    print(json.dumps(sm, ensure_ascii=False, indent=1, default=list))
    print(f"coût : {sum(r['cost_usd'] for r in rows):.4f} $ ; cumul {ledger.total_usd:.4f} $")


if __name__ == "__main__":
    main()
