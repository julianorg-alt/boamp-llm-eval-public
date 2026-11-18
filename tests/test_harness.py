"""Harnais : client simulé, garde de budget, enregistrement, rapport (hors réseau)."""

import json

import pytest

from boamp_eval import harness, report
from boamp_eval import metrics as m
from boamp_eval.costs import BudgetExceededError, CostLedger
from boamp_eval.llm import RecordedClient

REC = {
    "idweb": "26-1", "famille": "FNS", "texte": "Ville X publie « Voirie ». Exécuté en : Val-de-Marne.",
    "verite": {"acheteur": "Ville X", "objet": "Voirie", "lieu": "Val-de-Marne"},
}  # fmt: skip


def _resp(obj, **usage):
    return {
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 1000, "output_tokens": 200, **usage},
        "content": [{"type": "text", "text": json.dumps(obj)}],
    }


GOOD = {"acheteur": "Ville X", "objet": "Voirie", "lieu": "Val-de-Marne", "procedure": None,
        "date_limite": None, "cpv": [], "lots": [], "montant_estime": None, "criteres": []}  # fmt: skip


class Fake:
    live = True

    def __init__(self, resp):
        self.resp, self.calls = resp, []

    def create(self, params, *, key):
        self.calls.append((key, params))
        return self.resp


def test_run_enregistre_cout_et_reponses(tmp_path):
    led = CostLedger(tmp_path / "led.json")
    out = tmp_path / "run.jsonl"
    rows = harness.run([REC], "claude-haiku-5-5", Fake(_resp(GOOD)), led, label="t", out_path=out)
    assert rows[0]["pred"]["objet"] == "Voirie" and rows[0]["error"] is None
    assert led.total_usd == pytest.approx((1000 * 0.10 + 200 * 0.50) / 1e6)
    saved = [json.loads(line) for line in out.read_text().splitlines()]
    assert saved[0]["idweb"] == "26-1" and saved[0]["model"] == "claude-haiku-5-5"
    assert saved[0]["response"]["usage"]["input_tokens"] == 1000


def test_run_garde_de_budget_avant_l_appel(tmp_path):
    led = CostLedger(tmp_path / "led.json", cap_usd=0.0)
    c = Fake(_resp(GOOD))
    with pytest.raises(BudgetExceededError):
        harness.run([REC], "claude-opus-5-5", c, led, label="t", out_path=tmp_path / "r.jsonl")
    assert c.calls == []


def test_run_rejeu_enregistre_sans_cout(tmp_path):
    out = tmp_path / "run.jsonl"
    harness.run([REC], "claude-haiku-5-5", Fake(_resp(GOOD)), CostLedger(tmp_path / "a.json"),
                label="t", out_path=out)  # fmt: skip
    led = CostLedger(tmp_path / "b.json")
    rc = RecordedClient(out)
    rows = harness.run([REC], "claude-haiku-5-5", rc, led, label="replay", out_path=None)
    assert rows[0]["pred"]["acheteur"] == "Ville X" and led.total_usd == 0.0


def test_rejeu_cle_inconnue(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text("")
    with pytest.raises(KeyError):
        RecordedClient(p).create({}, key="absent")


def test_evaluate_et_resume_bout_en_bout(tmp_path):
    rows = harness.run([REC], "claude-haiku-5-5", Fake(_resp(GOOD)), CostLedger(tmp_path / "l.json"),
                       label="t", out_path=None)  # fmt: skip
    scored = report.evaluate([REC], rows)
    assert scored[0]["res"]["lieu"].score == 1.0
    sm = report.summarize(scored)
    assert sm["easy"]["acheteur"]["mean"] == 1.0
    assert sm["hard"]["lieu"]["n"] == 1


# --- agrégation et bootstrap -----------------------------------------------------------------
def _row(fam, **scores):
    res = {f: m.FieldResult(False, None, False, False) for f in m.FIELDS}
    for f, v in scores.items():
        res[f] = m.FieldResult(True, v, False, True)
    return {"famille": fam, "res": res, "error": None}


def test_global_dur_est_la_moyenne_des_champs_durs():
    rows = [_row("JOUE", cpv=1.0, lieu=0.0), _row("JOUE", cpv=0.0, lieu=0.0)]
    assert report.hard_global(rows) == pytest.approx(
        (0.5 + 0.0) / 2
    )  # macro sur champs applicables


def test_non_applicable_exclu_et_inventes_comptes():
    rows = [_row("MAPA", lieu=1.0), _row("MAPA")]
    rows[1]["res"]["cpv"] = m.FieldResult(False, None, True, True)
    sm = report.summarize(rows)
    assert sm["hard"]["lieu"]["n"] == 1 and sm["hard"]["cpv"]["n"] == 0
    assert sm["invented"]["cpv"] == {"inventes": 1, "absents": 2}


def test_bootstrap_reproductible_et_encadre_la_moyenne():
    rows = [_row("JOUE", cpv=float(i % 2)) for i in range(40)]
    a = report.bootstrap_ci(rows, report.hard_global, n_boot=300, seed=7)
    b = report.bootstrap_ci(rows, report.hard_global, n_boot=300, seed=7)
    assert a == b and a[0] <= 0.5 <= a[1] and a[0] < a[1]


def test_verdict_pas_de_conclusion_si_les_ic_se_recouvrent():
    assert "indistinguable" in report.verdict("A", (0.5, 0.7), "B", (0.65, 0.9))
    assert "A > B" in report.verdict("A", (0.8, 0.9), "B", (0.5, 0.7))
    assert "B > A" in report.verdict("A", (0.1, 0.2), "B", (0.5, 0.7))


def test_erreur_d_analyse_comptee():
    rows = [_row("JOUE", cpv=1.0)]
    rows[0]["error"] = "refusal"
    assert report.summarize(rows)["parse_errors"] == 1
