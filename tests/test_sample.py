from boamp_eval.sample import split_holdout, stratified_pick, weekly_windows


def cands(n_per, strata):
    return [{"idweb": f"26-{s}-{i}", "strate": s} for s in strata for i in range(n_per)]


def test_stratified_pick_is_deterministic_and_balanced():
    c = cands(20, ["a", "b", "c", "d"])
    p1 = stratified_pick(c, 8, seed=1)
    p2 = stratified_pick(list(reversed(c)), 8, seed=1)
    assert [x["idweb"] for x in p1] == [x["idweb"] for x in p2]
    assert len(p1) == 8
    assert {s: sum(x["strate"] == s for x in p1) for s in "abcd"} == dict.fromkeys("abcd", 2)
    assert [x["idweb"] for x in p1] != [x["idweb"] for x in stratified_pick(c, 8, seed=2)]


def test_stratified_pick_small_stratum_gives_way():
    c = cands(1, ["rare"]) + cands(20, ["big"])
    p = stratified_pick(c, 6, seed=3)
    assert len(p) == 6 and sum(x["strate"] == "rare" for x in p) == 1


def test_stratified_pick_not_enough():
    assert len(stratified_pick(cands(2, ["a"]), 10, seed=1)) == 2


def test_split_holdout_20_percent_per_family_and_stable():
    recs = [{"idweb": f"26-{i}", "famille": f} for f in ("JOUE", "FNS") for i in range(25)]
    h1 = split_holdout(recs, seed=7, frac=0.2)
    h2 = split_holdout(list(reversed(recs)), seed=7, frac=0.2)
    assert h1 == h2
    for f in ("JOUE", "FNS"):
        assert sum(1 for r in recs if r["famille"] == f and r["idweb"] in h1) == 5


def test_weekly_windows_cover_range_without_overlap():
    w = weekly_windows("2026-09-01", "2026-09-20")
    assert w == [
        ("2026-09-01", "2026-09-07"),
        ("2026-09-08", "2026-09-14"),
        ("2026-09-15", "2026-09-20"),
    ]
