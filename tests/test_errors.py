from boamp_eval.errors import analyse, categorize, strip_suffix

T = [{"libelle": "Valeur technique", "poids": 60.0}, {"libelle": "Prix", "poids": 40.0}]


def test_strip_suffix_removes_type_only():
    out = strip_suffix(
        [{"libelle": "Prix (coût)", "poids": 1}, {"libelle": "Délai (jours)", "poids": 2}]
    )
    assert [x["libelle"] for x in out] == ["Prix", "Délai (jours)"]


def test_categories():
    ok = [{"libelle": "Valeur technique", "poids": 60}, {"libelle": "Prix", "poids": 40}]
    suf = [
        {"libelle": "Valeur technique (qualité)", "poids": 60},
        {"libelle": "Prix (prix)", "poids": 40},
    ]
    poids = [{"libelle": "Valeur technique", "poids": 50}, {"libelle": "Prix", "poids": 50}]
    autre = [{"libelle": "Technique", "poids": 60}, {"libelle": "Coût", "poids": 40}]
    assert categorize(T, ok, None) == "ok"
    assert categorize(T, suf, None) == "suffixe_type"
    assert categorize(T, poids, None) == "poids"
    assert categorize(T, autre, None) == "libelle_autre"
    assert categorize(T, ok[:1], None) == "ensemble"
    assert categorize(T, None, "stop_reason=max_tokens") == "inexploitable"


def test_analyse_skips_records_without_criteres():
    recs = [{"idweb": "a", "famille": "JOUE", "verite": {"criteres": T}},
            {"idweb": "b", "famille": "FNS", "verite": {}}]  # fmt: skip
    rows = [{"pred": {"criteres": [{"libelle": "Prix (prix)", "poids": 40}]}, "error": None},
            {"pred": {"criteres": []}, "error": None}]  # fmt: skip
    a = analyse(recs, rows)
    assert a["n"] == 1 and a["categories"] == {"ensemble": 1}
