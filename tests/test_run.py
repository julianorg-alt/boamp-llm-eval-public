"""Rejeu hors réseau de l'essai réel Haiku (3 avis du dev) enregistré dans data/runs/."""

import json
from pathlib import Path

from boamp_eval import harness, report, run
from boamp_eval.costs import CostLedger
from boamp_eval.llm import RecordedClient

RUN = Path("data/runs/e2-haiku-3.jsonl")


def test_pick_un_par_famille_deterministe():
    recs = [json.loads(x) for x in Path("data/dev.jsonl").read_text().splitlines()]
    a = run.pick(recs, 1)
    assert sorted(r["famille"] for r in a) == ["FNS", "JOUE", "MAPA"]
    assert a == run.pick(recs, 1)


def test_rejeu_essai_haiku(tmp_path):
    recs = run.pick([json.loads(x) for x in Path("data/dev.jsonl").read_text().splitlines()], 1)
    led = CostLedger(tmp_path / "l.json")
    rows = harness.run(
        recs, "claude-haiku-5-5", RecordedClient(RUN), led, label="replay", out_path=None
    )
    assert led.total_usd == 0.0 and all(r["error"] is None for r in rows)
    sm = report.summarize(report.evaluate(recs, rows))
    assert sm["parse_errors"] == 0 and sm["hard_global"]["mean"] is not None
    assert sum(r["usage"]["cache_read_tokens"] for r in rows) > 0  # le cache de prompt a servi
