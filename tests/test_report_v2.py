import json
from pathlib import Path

from boamp_eval import report_v2

A, B = "claude-opus-5-5", "claude-haiku-5-5"


def test_decide_regle_de_gel():
    assert report_v2.decide(A, B, (0.05, 0.01, 0.09)).startswith("établi : Opus > Haiku")
    assert report_v2.decide(A, B, (-0.05, -0.09, -0.01)).startswith("établi : Haiku > Opus")
    assert report_v2.decide(A, B, (0.05, -0.01, 0.09)).startswith("non établi")
    assert report_v2.decide(A, B, None) == "indisponible"


def test_alpha_bonferroni():
    assert abs(report_v2.ALPHA_V2 - 0.05 / 3) < 1e-12  # IC à 98,33 %


def test_section_v1_apres_coup_reproduit_les_chiffres_connus():
    t = report_v2.build_v1_paired()
    assert "faite après coup" in t and "hors protocole" in t
    assert "| dev | 80 | Opus - Haiku | +0.066 [+0.024 ; +0.110] |" in t
    assert "| holdout | 20 | Opus - Haiku | -0.037 [-0.178 ; +0.040] |" in t


def test_rapport_complet_sur_runs_v1_rejoues(monkeypatch):
    monkeypatch.setattr(report_v2, "N_BOOT_V2", 100)
    recs = [json.loads(x) for x in Path("data/dev.jsonl").read_text().splitlines()]
    runs = {mo: Path(f"data/runs/e3-dev-{mo.split('-')[1]}") for mo in report_v2.MODELS}
    t = report_v2.build_v2(recs, runs)
    for s in ("## Protocole", "Différences appariées", "Troncatures", "## Coût", "Bonferroni"):
        assert s in t
    assert "Opus - Haiku" in t and "Sonnet - Haiku" in t
