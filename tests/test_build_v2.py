from boamp_eval import build_v2


def _recs(fam, n):
    fam = {"J": "JOUE", "F": "FNS", "M": "MAPA"}.get(fam, fam)
    return [
        {"idweb": f"{fam}{i:03d}", "famille": fam, "strate": "s", "verite": {}} for i in range(n)
    ]


def test_ensembles_disjoints_et_quotas():
    by_fam = {"JOUE": _recs("J", 50), "FNS": _recs("F", 40), "MAPA": _recs("M", 12)}
    tune, test = build_v2.pick_sets(
        by_fam, {"JOUE": 20, "FNS": 15, "MAPA": 10}, {"JOUE": 3, "FNS": 2, "MAPA": 1}, 1
    )
    assert len(tune) == 6
    assert {r["idweb"] for r in tune}.isdisjoint(r["idweb"] for r in test)
    assert sum(r["famille"] == "JOUE" for r in test) == 20
    assert sum(r["famille"] == "MAPA" for r in test) == 10  # 12 - 1 de mise au point = 11 >= 10


def test_famille_courte_donne_tout_ce_qu_elle_a():
    by_fam = {"JOUE": _recs("J", 5), "FNS": _recs("F", 5), "MAPA": _recs("M", 6)}
    _, test = build_v2.pick_sets(
        by_fam, {"JOUE": 3, "FNS": 3, "MAPA": 10}, {"JOUE": 1, "FNS": 1, "MAPA": 1}, 1
    )
    assert sum(r["famille"] == "MAPA" for r in test) == 5


def test_fenetre_apres_v1():
    from boamp_eval import build

    assert build_v2.START > build.WINDOW[1]


def test_n_criteres():
    assert build_v2.n_criteres([{"verite": {"criteres": []}}, {"verite": {}}]) == 1
