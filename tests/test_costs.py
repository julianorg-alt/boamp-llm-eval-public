import json

import pytest

from boamp_eval.costs import BudgetExceededError, CostLedger, Usage, cost_usd

SONNET = "claude-sonnet-5-5"
HAIKU = "claude-haiku-5-5"
OPUS = "claude-opus-5-5"


def test_sonnet_standard_cost():
    u = Usage(input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost_usd(SONNET, u) == pytest.approx(2 + 10)


def test_batch_is_half_price():
    u = Usage(input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost_usd(OPUS, u, batch=True) == pytest.approx((4 + 20) / 2)


def test_cache_read_and_write_rates():
    u = Usage(cache_write_5m_tokens=1_000_000, cache_read_tokens=1_000_000)
    assert cost_usd(SONNET, u) == pytest.approx(2.50 + 0.10)


def test_haiku_tiers_by_prompt_length():
    short = Usage(input_tokens=100_000, output_tokens=1_000_000)
    assert cost_usd(HAIKU, short) == pytest.approx(0.1 * 0.1 + 0.50)
    long = Usage(input_tokens=100_001, output_tokens=1_000_000)
    assert cost_usd(HAIKU, long) == pytest.approx(0.5 * 100_001 / 1e6 + 2.50)


def test_unknown_model_rejected():
    with pytest.raises(KeyError):
        cost_usd("claude-inconnu", Usage())


def test_ledger_blocks_before_exceeding_cap(tmp_path):
    ledger = CostLedger(tmp_path / "ledger.json", cap_usd=1.0)
    ledger.record(SONNET, Usage(input_tokens=100_000), label="a")  # 0.20 $
    ledger.guard(0.79)
    with pytest.raises(BudgetExceededError):
        ledger.guard(0.81)


def test_ledger_persists_and_sums(tmp_path):
    p = tmp_path / "ledger.json"
    CostLedger(p, cap_usd=15).record(SONNET, Usage(input_tokens=1_000_000), label="a")
    again = CostLedger(p, cap_usd=15)
    assert again.total_usd == pytest.approx(2.0)
    entries = json.loads(p.read_text())["entries"]
    assert entries[0]["model"] == SONNET and entries[0]["label"] == "a"


def test_registre_partage_ne_perd_pas_les_ecritures_concurrentes(tmp_path):
    p = tmp_path / "l.json"
    a, b = CostLedger(p), CostLedger(p)  # deux processus, même fichier
    u = Usage(input_tokens=1000)
    a.record(HAIKU, u, label="a")
    b.record(HAIKU, u, label="b")
    assert [e["label"] for e in CostLedger(p).entries] == ["a", "b"]
    assert b.total_usd == CostLedger(p).total_usd
