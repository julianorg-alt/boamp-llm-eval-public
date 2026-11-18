"""Rapport Markdown : tout chiffre vient des fichiers de résultats."""

import json

from boamp_eval import report_md

M = "claude-haiku-5-5"
REC = {"idweb": "26-1", "famille": "FNS", "texte": "Ville X publie « Voirie ».",
       "verite": {"acheteur": "Ville X", "objet": "Voirie"}}  # fmt: skip
GOOD = {"acheteur": "Ville X", "objet": "Voirie", "lieu": None, "procedure": None,
        "date_limite": None, "cpv": [], "lots": [], "montant_estime": None, "criteres": []}  # fmt: skip


def _setup(tmp_path):
    line = {"custom_id": "26-1", "result": {"type": "succeeded", "message": {
        "stop_reason": "end_turn", "usage": {"input_tokens": 1000, "output_tokens": 200},
        "content": [{"type": "text", "text": json.dumps(GOOD)}]}}}  # fmt: skip
    (tmp_path / "r.jsonl").write_text(json.dumps(line) + "\n")
    (tmp_path / "r.meta.json").write_text(json.dumps({"latency_s": 450.0, "n": 1}))
    return {"dev": [REC]}, {("dev", M): tmp_path / "r"}


def test_run_stats_cout_recalcule_depuis_usage(tmp_path):
    recs, runs = _setup(tmp_path)
    st = report_md.load_run(recs["dev"], M, runs[("dev", M)])
    assert st["cost_usd"] == (1000 * 0.10 + 200 * 0.50) / 1e6 * 0.5
    assert st["cost_per_avis"] == st["cost_usd"] and st["latency_s"] == 450.0
    assert st["summary"]["n"] == 1


def test_rapport_contient_sections_et_chiffres(tmp_path):
    recs, runs = _setup(tmp_path)
    md = report_md.build(recs, runs)
    for titre in (
        "Protocole",
        "Score dur",
        "Par champ",
        "Par famille",
        "inventé",
        "Coût",
        "Annexe",
        "Limites",
    ):
        assert titre in md
    assert "claude-haiku-5-5" in md and "450" in md


def test_section_effort_par_defaut(tmp_path):
    recs, runs = _setup(tmp_path)
    p = runs[("dev", M)]
    md = report_md.build_default_effort(recs["dev"], {M: p}, {M: p})
    assert "effort par défaut" in md and "| défaut |" in md and "| low |" in md
