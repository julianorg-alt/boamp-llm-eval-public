"""Smoke tests: run the whole tool end to end on the committed data, with the network cut.

Each test copies the data, docs and reports into a temporary directory and calls the
real entry points (the ones the README tells readers to run). They check that the
published numbers come back out of the committed raw answers, that the guards still
refuse what they must refuse, and that nothing leaves the machine.
"""

import hashlib
import json
import re
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

from boamp_eval import batch, costs, errors, report_md

ROOT = Path(__file__).resolve().parents[1]

# Hard global scores published in the README and the report (3 decimals).
PUBLISHED = {
    ("dev", "haiku"): 0.852,
    ("dev", "sonnet"): 0.864,
    ("dev", "opus"): 0.917,
    ("holdout", "haiku"): 0.896,
    ("holdout", "sonnet"): 0.909,
    ("holdout", "opus"): 0.859,
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*_a, **_k):
        raise AssertionError("network access during a smoke test")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    for d in ("data", "docs", "reports"):
        shutil.copytree(ROOT / d, tmp_path / d)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _summary(capsys) -> dict:
    out = capsys.readouterr().out
    return json.loads(out[out.index("{") : out.rindex("}") + 1])


@pytest.mark.parametrize(("split", "model"), sorted(PUBLISHED))
def test_replay_gives_back_the_published_score(workdir, capsys, monkeypatch, split, model):
    monkeypatch.setattr(batch, "require_freeze", lambda _s: None)  # tmp dir is not a git checkout
    batch.main(["replay", "--model", f"claude-{model}-5-5", "--split", split,
                "--name", f"e3-{split}-{model}"])  # fmt: skip
    sm = _summary(capsys)
    assert sm["n"] == (80 if split == "dev" else 20)
    assert round(sm["hard_global"]["mean"], 3) == PUBLISHED[(split, model)]
    lo, hi = sm["hard_global"]["ci"]
    assert lo <= sm["hard_global"]["mean"] <= hi


def test_replay_does_not_touch_the_cost_ledger(workdir, capsys, monkeypatch):
    monkeypatch.setattr(batch, "require_freeze", lambda _s: None)
    before = (workdir / "data/costs-ledger.json").read_bytes()
    batch.main(["replay", "--model", "claude-haiku-5-5", "--name", "e3-dev-haiku"])
    assert (workdir / "data/costs-ledger.json").read_bytes() == before


def test_report_regenerates_identically(workdir):
    committed = (workdir / "reports/results-2026-11.md").read_text()
    (workdir / "reports/results-2026-11.md").unlink()
    report_md.main()
    assert (workdir / "reports/results-2026-11.md").read_text() == committed


def test_error_analysis_regenerates_identically(workdir, capsys):
    committed = (workdir / "reports/analyse-erreurs.md").read_text()
    (workdir / "reports/analyse-erreurs.md").unlink()
    errors.main()
    assert (workdir / "reports/analyse-erreurs.md").read_text() == committed


def test_dataset_matches_its_manifest(workdir):
    manifest = json.loads((workdir / "data/manifest.json").read_text())
    for split, n in (("dev", 80), ("holdout", 20)):
        path = workdir / f"data/{split}.jsonl"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["sha256"][split]
        assert len(path.read_text().splitlines()) == n
    ids = [json.loads(x)["idweb"] for s in ("dev", "holdout")
           for x in (workdir / f"data/{s}.jsonl").read_text().splitlines()]  # fmt: skip
    assert len(ids) == len(set(ids)) == 100


EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\d)0[1-9](?:[ .]?\d{2}){4}(?!\d)")


def test_no_personal_contact_left_in_the_dataset(workdir):
    for split in ("dev", "holdout"):
        text = (workdir / f"data/{split}.jsonl").read_text()
        assert not EMAIL.search(text), split
        assert not PHONE.search(text), split


def test_holdout_is_refused_without_a_committed_freeze(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no docs/FREEZE.md, not a git checkout
    with pytest.raises(SystemExit, match="hold-out refusé"):
        batch.require_freeze("holdout")
    batch.require_freeze("dev")  # dev stays open


def test_freeze_is_committed_in_this_repository(monkeypatch):
    monkeypatch.chdir(ROOT)
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "docs/FREEZE.md"],  # noqa: S607
                             capture_output=True, check=False)  # fmt: skip
    if tracked.returncode != 0 and not (ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    assert tracked.returncode == 0


def test_submit_refuses_a_batch_that_would_break_the_budget(tmp_path):
    ledger = costs.CostLedger(tmp_path / "ledger.json", cap_usd=0.0001)

    class FakeClient:
        created = False

        def count_tokens(self, _params):
            return 2000

        def create_batch(self, _reqs):
            FakeClient.created = True
            return {"id": "never"}

    recs = [json.loads(x) for x in (ROOT / "data/dev.jsonl").read_text().splitlines()][:3]
    with pytest.raises(costs.BudgetExceededError):
        batch.submit(FakeClient(), "claude-opus-5-5", recs, ledger)
    assert not FakeClient.created


def test_ledger_total_matches_the_published_spend():
    ledger = costs.CostLedger(ROOT / "data/costs-ledger.json")
    assert round(ledger.total_usd, 2) == 1.42
    assert ledger.total_usd < ledger.cap_usd
