"""Métriques par champ : définies et testées avant tout appel réseau (voir docs/METRICS.md)."""

import pytest

from boamp_eval import metrics as m


def test_norm_text_accents_casse_ponctuation():
    assert m.norm_text("  Éco-Quartier « Les Près », N°2. ") == "eco quartier les pres n 2"


# --- exact normalisé -------------------------------------------------------------------------
def test_exact_acheteur_ignore_parenthese_finale_et_casse():
    assert m.score_exact("Mairie Saint-Cyr (37540)", "mairie saint cyr", paren=True) == 1.0
    assert m.score_exact("Ville de Créteil", "Ville de Creteil") == 1.0
    assert m.score_exact("Ville de Créteil", "Ville de Vitry") == 0.0


def test_exact_objet_guillemets_et_point_final():
    assert m.score_exact("Travaux de voirie", "« Travaux de voirie. »") == 1.0


def test_procedure_casse_et_espaces():
    assert m.score_exact("adapted-open", " Adapted-Open ") == 1.0
    assert m.score_exact("open", "restricted") == 0.0


# --- date limite -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("truth", "pred", "ok"),
    [
        ("2026-12-16T12:00:00+02:00", "2026-12-16T12:00:00+02:00", True),
        ("2026-12-16T12:00:00+02:00", "2026-12-16T10:00:00+00:00", True),  # même instant
        ("2026-12-16T12:00:00+02:00", "2026-12-16T12:00:00", True),  # heure locale, sans décalage
        ("2026-11-04T12:00:00", "2026-11-04T12:00:00+01:00", True),  # MAPA : sans décalage
        ("2026-11-04T12:00:00", "2026-11-04T13:00:00", False),
        ("2026-11-04T12:00:00", "2026-11-05T12:00:00", False),
        ("2026-11-04T12:00:00", "pas une date", False),
    ],
)
def test_date_limite(truth, pred, ok):
    assert m.score_date(truth, pred) == (1.0 if ok else 0.0)


def test_date_sans_heure_dans_la_verite():
    assert m.score_date("2026-11-04", "2026-11-04T12:00:00") == 1.0
    assert m.score_date("2026-11-04", "2026-11-05") == 0.0


# --- montant ---------------------------------------------------------------------------------
def test_montant_tolerance_un_pour_cent():
    truth = {"valeur": 100000.0, "devise": "EUR"}
    assert m.score_amount(truth, {"valeur": 100900, "devise": "eur"}) == 1.0
    assert m.score_amount(truth, {"valeur": 101100, "devise": "EUR"}) == 0.0
    assert m.score_amount(truth, {"valeur": 100000, "devise": "USD"}) == 0.0
    assert m.score_amount(truth, None) == 0.0
    assert m.score_amount({"valeur": 0.0, "devise": "EUR"}, {"valeur": 0, "devise": "EUR"}) == 1.0


# --- F1 --------------------------------------------------------------------------------------
def test_f1_cas_limites():
    assert m.f1(2, 2, 2) == 1.0
    assert m.f1(0, 2, 2) == 0.0
    assert m.f1(1, 1, 2) == pytest.approx(2 * 1 * 0.5 / 1.5)
    assert m.f1(0, 0, 3) == 0.0


def test_cpv_f1_sur_codes_numeriques():
    assert m.score_cpv(["45233140", "45233000"], ["45233140-7", "45233000"]) == 1.0
    assert m.score_cpv(["45233140", "45233000"], ["45233140"]) == pytest.approx(2 / 3)
    assert m.score_cpv(["45233140"], []) == 0.0
    assert m.score_cpv(["45233140"], ["45233140", "1"]) == pytest.approx(2 / 3)


def test_lots_f1_titres_normalises():
    truth = [
        {"id": "LOT-0001", "titre": "Lot 1 - Désamiantage"},
        {"id": "2", "titre": "Démolition"},
    ]
    pred = [{"titre": "lot 1 : DESAMIANTAGE"}, {"titre": "Démolition (bâtiments)"}]
    assert m.score_lots(truth, pred) == 1.0  # préfixe « lot n » et parenthèse ignorés
    assert m.score_lots(truth, pred[:1]) == pytest.approx(2 / 3)


def test_criteres_poids_a_un_point_et_doublons():
    truth = [
        {"libelle": "Prix", "poids": 40.0, "type": "price"},
        {"libelle": "Se référer au RC", "poids": 50.0, "type": "quality"},
        {"libelle": "Se référer au RC", "poids": 10.0, "type": "quality"},
    ]
    pred = [
        {"libelle": "prix", "poids": 40.9},
        {"libelle": "Se référer au RC", "poids": 10},
        {"libelle": "Se référer au RC", "poids": 55},  # hors tolérance
    ]
    assert m.score_criteres(truth, pred) == pytest.approx(2 / 3)


def test_criteres_poids_absent_de_la_verite_compare_le_libelle():
    truth = [{"libelle": "Le prix", "poids": None, "type": None}]
    assert m.score_criteres(truth, [{"libelle": "le prix", "poids": 30}]) == 1.0


# --- lieu ------------------------------------------------------------------------------------
def test_lieu_nuts_exact():
    assert m.score_lieu("FRK26", "FRK26") == 1.0
    assert m.score_lieu("FRK26", "frk26") == 1.0
    assert m.score_lieu("FRK26", "FRK2") == 0.0
    assert m.score_lieu("FRK26", "Lyon") == 0.0


def test_lieu_nuts_dans_une_verite_mixte():
    assert m.score_lieu("FRJ23 - Haute-Garonne", "FRJ23") == 1.0
    assert m.score_lieu("FRJ23 - Haute-Garonne", "FRJ13") == 0.0


def test_lieu_texte_inclusion_normalisee():
    assert m.score_lieu("Val-de-Marne", "Val de Marne (94)") == 1.0
    assert m.score_lieu("La Roche sur Yon 85000", "La Roche-sur-Yon") == 1.0
    assert (
        m.score_lieu("Divers bâtiments, 37541, Saint-Cyr-sur-Loire", "Saint-Cyr-sur-Loire") == 1.0
    )
    assert m.score_lieu("Val-de-Marne", "France") == 0.0
    assert m.score_lieu("Val-de-Marne", "Seine-Saint-Denis") == 0.0


# --- ancrage (hallucination) -----------------------------------------------------------------
TEXTE = "Le marché est de 20.000 euros HT. Offres avant le 4 novembre 2026 à 12h00. CPV 45233140."


def test_ancrage_montant_dans_le_texte():
    assert m.is_grounded("montant_estime", {"valeur": 20000, "devise": "EUR"}, TEXTE)
    assert not m.is_grounded("montant_estime", {"valeur": 35000, "devise": "EUR"}, TEXTE)


def test_ancrage_date_cpv_lots_lieu_criteres():
    assert m.is_grounded("date_limite", "2026-11-04T12:00:00", TEXTE)
    assert not m.is_grounded("date_limite", "2026-11-05T12:00:00", TEXTE)
    assert m.is_grounded("cpv", ["45233140"], TEXTE)
    assert not m.is_grounded("cpv", ["45233140", "79411000"], TEXTE)
    t2 = "Le marché est alloti en 2 lots : lot 1 — Voirie; lot 2 — Réseaux;"
    assert m.is_grounded("lots", [{"titre": "Voirie"}, {"titre": "Réseaux"}], t2)
    assert not m.is_grounded("lots", [{"titre": "Voirie"}, {"titre": "Éclairage"}], t2)
    assert m.is_grounded("lieu", "Val-de-Marne", "exécuté en : Val-de-Marne.")
    assert not m.is_grounded("lieu", "Paris", "exécuté en : Val-de-Marne.")
    assert m.is_grounded(
        "criteres", [{"libelle": "Le prix", "poids": 30}], "critères : Le prix, pondéré à 30 %"
    )
    assert not m.is_grounded("criteres", [{"libelle": "Le prix", "poids": 30}], "aucun critère")


# --- score_record ----------------------------------------------------------------------------
def _rec():
    return {
        "idweb": "x",
        "famille": "JOUE",
        "texte": "Acheteur A. Aucun lot.",
        "verite": {"acheteur": "Acheteur A", "objet": "Objet", "cpv": ["45233140"]},
    }


def test_score_record_applicable_et_non_applicable():
    pred = {
        "acheteur": "acheteur a",
        "objet": "Autre",
        "cpv": ["45233140"],
        "lots": [],
        "montant_estime": None,
    }
    res = m.score_record(_rec(), pred)
    assert res["acheteur"].score == 1.0
    assert res["objet"].score == 0.0
    assert res["cpv"].score == 1.0
    assert res["lots"].applicable is False and res["lots"].invented is False
    assert res["montant_estime"].applicable is False and res["montant_estime"].invented is False


def test_score_record_invente_si_valeur_non_ancree_et_verite_absente():
    pred = {"lots": [{"titre": "Lot fantôme"}], "montant_estime": {"valeur": 5000, "devise": "EUR"}}
    res = m.score_record(_rec(), pred)
    assert res["lots"].invented and res["montant_estime"].invented
    assert res["lots"].score is None


def test_score_record_valeur_ancree_dans_le_texte_non_comptee_inventee():
    rec = _rec()
    rec["texte"] += " Montant estimatif de 20.000 euros."
    res = m.score_record(rec, {"montant_estime": {"valeur": 20000, "devise": "EUR"}})
    assert res["montant_estime"].invented is False


def test_score_record_echec_analyse_compte_zero():
    res = m.score_record(_rec(), None)
    assert res["acheteur"].score == 0.0 and res["cpv"].score == 0.0
    assert res["lots"].applicable is False


def test_champs_faciles_et_durs_disjoints():
    assert set(m.HARD_FIELDS) == {"date_limite", "montant_estime", "criteres", "cpv", "lieu"}
    assert not set(m.HARD_FIELDS) & set(m.EASY_FIELDS)
    assert set(m.HARD_FIELDS) | set(m.EASY_FIELDS) == set(m.FIELDS)


def test_oracle_sur_le_jeu_de_dev():
    """Prédire la vérité elle-même doit donner 1,0 partout (valide les normalisations sur données réelles)."""
    import json
    from pathlib import Path

    recs = [json.loads(x) for x in Path("data/dev.jsonl").read_text().splitlines()]
    for rec in recs:
        res = m.score_record(rec, rec["verite"])
        bad = {f: r.score for f, r in res.items() if r.applicable and r.score != 1.0}
        assert not bad, (rec["idweb"], bad)
        assert not any(r.invented for r in res.values())
