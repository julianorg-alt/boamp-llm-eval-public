"""Client de lots, estimation, collecte (réponses enregistrées, hors réseau)."""

import io
import json

import pytest

from boamp_eval import batch, llm
from boamp_eval.costs import BudgetExceededError, CostLedger

M = "claude-sonnet-5-5"
RECS = [
    {"idweb": "26-1", "famille": "FNS", "texte": "Ville X publie « Voirie »."},
    {"idweb": "26-2", "famille": "MAPA", "texte": "Ville Y publie « Eau »."},
]
GOOD = {"acheteur": "Ville X", "objet": "Voirie", "lieu": None, "procedure": None,
        "date_limite": None, "cpv": [], "lots": [], "montant_estime": None, "criteres": []}  # fmt: skip


def _line(cid, obj=GOOD, typ="succeeded", **usage):
    res = {"type": typ}
    if typ == "succeeded":
        res["message"] = {
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 1000, "output_tokens": 200, **usage},
            "content": [{"type": "text", "text": json.dumps(obj)}],
        }
    return json.dumps({"custom_id": cid, "result": res})


class FakeBatchClient:
    live = True

    def __init__(self, statuses, lines, counts=1000):
        self.statuses, self.lines, self.counts = list(statuses), lines, counts
        self.created = []
        self.gets = 0

    def count_tokens(self, params):
        return self.counts

    def create_batch(self, requests):
        self.created.append(requests)
        return {"id": "msgbatch_1", "processing_status": "in_progress",
                "created_at": "2026-11-18T10:00:00Z", "ended_at": None}  # fmt: skip

    def get_batch(self, bid):
        self.gets += 1
        return self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]

    def batch_results(self, bid):
        return self.lines


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_http_batch_endpoints(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k-test")
    seen = []

    def fake(req, timeout):
        seen.append((req.get_method(), req.full_url, req.headers, req.data))
        if req.full_url.endswith("/results"):
            return _Resp(b'{"custom_id":"a"}\n{"custom_id":"b"}\n')
        if req.full_url.endswith("count_tokens"):
            return _Resp(b'{"input_tokens": 1234}')
        return _Resp(b'{"id": "msgbatch_1"}')

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake)
    c = llm.HttpClient()
    assert c.create_batch([{"custom_id": "a", "params": {}}])["id"] == "msgbatch_1"
    assert c.get_batch("msgbatch_1")["id"] == "msgbatch_1"
    assert c.batch_results("msgbatch_1") == ['{"custom_id":"a"}', '{"custom_id":"b"}']
    p = {"model": M, "max_tokens": 9, "system": "s", "messages": [], "output_config": {"x": 1}}
    assert c.count_tokens(p) == 1234
    assert [(m, u) for m, u, *_ in seen] == [
        ("POST", "https://api.anthropic.com/v1/messages/batches"),
        ("GET", "https://api.anthropic.com/v1/messages/batches/msgbatch_1"),
        ("GET", "https://api.anthropic.com/v1/messages/batches/msgbatch_1/results"),
        ("POST", "https://api.anthropic.com/v1/messages/count_tokens"),
    ]
    assert json.loads(seen[0][3]) == {"requests": [{"custom_id": "a", "params": {}}]}
    # comptage : seulement les champs acceptés (pas de max_tokens)
    assert set(json.loads(seen[3][3])) <= {"model", "system", "messages", "output_config"}
    assert seen[0][2]["X-api-key"] == "k-test"


def test_estimation_pire_cas(tmp_path):
    c = FakeBatchClient([], [], counts=1000)
    est = batch.estimate(c, M, RECS, max_tokens=4096)
    assert est.n == 2 and est.input_tokens == 2 * (1000 + batch.SCHEMA_MARGIN_TOKENS)
    assert est.output_tokens == 2 * 4096
    attendu = (est.input_tokens * 2.0 + est.output_tokens * 10.0) / 1e6 * 0.5
    assert est.usd == pytest.approx(attendu)


def test_soumission_refusee_si_budget(tmp_path):
    c = FakeBatchClient([], [])
    led = CostLedger(tmp_path / "l.json", cap_usd=0.0)
    with pytest.raises(BudgetExceededError):
        batch.submit(c, M, RECS, led, max_tokens=4096)
    assert c.created == []


def test_soumission_ok_et_requetes():
    c = FakeBatchClient([], [])
    led = CostLedger(__import__("pathlib").Path("/nonexistent/l.json"))
    b = batch.submit(c, M, RECS, led, max_tokens=4096)
    assert b["id"] == "msgbatch_1"
    reqs = c.created[0]
    assert [r["custom_id"] for r in reqs] == ["26-1", "26-2"]
    assert reqs[0]["params"]["output_config"]["effort"] == "low"


def test_attente_puis_fin():
    ended = {"id": "msgbatch_1", "processing_status": "ended",
             "created_at": "2026-11-18T10:00:00Z", "ended_at": "2026-11-18T10:07:30Z"}  # fmt: skip
    c = FakeBatchClient([{"processing_status": "in_progress"}, ended], [])
    slept = []
    b = batch.wait(c, "msgbatch_1", poll_s=5, sleep=slept.append)
    assert b["processing_status"] == "ended" and slept == [5]
    assert batch.latency_s(b) == 450


def test_collecte_ordre_quelconque_cout_et_erreurs(tmp_path):
    lines = [_line("26-2", cache_read_input_tokens=500), _line("26-1")]
    c = FakeBatchClient([], lines)
    led = CostLedger(tmp_path / "l.json")
    out = tmp_path / "raw.jsonl"
    rows = batch.collect(c, "msgbatch_1", M, RECS, led, label="t", out_path=out)
    assert [r["idweb"] for r in rows] == ["26-1", "26-2"]  # ordre des avis, pas du lot
    assert rows[0]["error"] is None and rows[0]["pred"]["objet"] == "Voirie"
    # tarif lot : -50 %
    assert rows[0]["cost_usd"] == pytest.approx((1000 * 2.0 + 200 * 10.0) / 1e6 * 0.5)
    assert led.entries[0]["batch"] is True
    assert out.read_text().count("\n") == 2


def test_collecte_resultat_errored_ou_manquant(tmp_path):
    c = FakeBatchClient([], [_line("26-1", typ="expired")])
    led = CostLedger(tmp_path / "l.json")
    rows = batch.collect(c, "msgbatch_1", M, RECS, led, label="t", out_path=None)
    assert rows[0]["error"] == "batch: expired" and rows[0]["pred"] is None
    assert rows[1]["error"] == "batch: absent" and rows[1]["cost_usd"] == 0.0


def test_rejeu_de_lignes_enregistrees(tmp_path):
    f = tmp_path / "raw.jsonl"
    f.write_text(_line("26-1") + "\n" + _line("26-2") + "\n")
    c = batch.RecordedBatch(f)
    led = CostLedger(tmp_path / "l.json")
    rows = batch.collect(c, "x", M, RECS, led, label="t", out_path=None, record_costs=False)
    assert all(r["error"] is None for r in rows) and led.entries == []


def test_holdout_exige_le_gel(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        batch.require_freeze("holdout")
    batch.require_freeze("dev")


def test_require_freeze_v2_test_refuse_sans_gel(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # pas un dépôt git : gel absent
    with pytest.raises(SystemExit):
        batch.require_freeze("v2-test")
    batch.require_freeze("v2-tuning")  # la mise au point reste ouverte
    batch.require_freeze("dev")


def test_garde_attendu_refuse_si_depasse_et_passe_sinon(tmp_path):
    c = FakeBatchClient([], [])
    petit = CostLedger(tmp_path / "l.json", cap_usd=0.001)
    with pytest.raises(BudgetExceededError):
        batch.submit(c, M, RECS, petit, max_tokens=8192, guard="expected")
    assert c.created == []
    large = CostLedger(tmp_path / "l2.json", cap_usd=9.42)
    with pytest.raises(BudgetExceededError):  # le garde pire cas refuse le même lot
        batch.submit(c, M, RECS * 400, large, max_tokens=8192)
    batch.submit(c, M, RECS * 200, large, max_tokens=8192, guard="expected")
    assert len(c.created) == 1


def test_cout_attendu_par_avis_v1():
    assert batch.expected_usd("claude-opus-5-5", 500) == pytest.approx(3.8)
