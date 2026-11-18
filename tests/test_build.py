import json

import pytest

from boamp_eval.build import PiiLeakError, assert_no_pii, build_record, coverage
from tests.test_extract import FNS, MAPA, _joue


def row(famille, donnees, idweb="26-1", tm="Travaux"):
    return {
        "idweb": idweb,
        "famille": famille,
        "type_marche_facette": tm,
        "dateparution": "2026-10-01",
        "url_avis": "https://x/" + idweb,
        "donnees": json.dumps(donnees),
    }


def test_build_record_masks_truth_and_text():
    fns = json.loads(json.dumps(FNS))
    fns["FNSimple"]["initial"]["natureMarche"]["description"] = (
        "Contact Marc EXEMPLE, d.exemple@mairie.fr, 01 23 45 67 89."
    )
    rec = build_record(row("FNS", fns))
    blob = json.dumps(rec, ensure_ascii=False)
    assert "EXEMPLE" not in blob and "@" not in blob and "01 23" not in blob
    assert rec["strate"] == "Travaux|avec_lots"
    assert rec["verite"]["acheteur"] == "Mairie de Testville"


def test_build_record_masks_name_inside_truth():
    mapa = json.loads(json.dumps(MAPA))
    mapa["MAPA"]["initial"]["description"]["objet"] = "Mission confiée à TESTNOM conseil"
    rec = build_record(row("MAPA", mapa))
    assert "TESTNOM" not in rec["verite"]["objet"] and "[PERSONNE]" in rec["verite"]["objet"]


def test_build_record_none_if_no_truth():
    assert build_record(row("JOUE", {"x": 1})) is None


def test_assert_no_pii_raises():
    with pytest.raises(PiiLeakError):
        assert_no_pii([{"texte": "écrire à a@b.fr"}])
    assert_no_pii([{"texte": "rien à signaler 2026-0412"}])


def test_coverage_counts_by_family():
    recs = [build_record(row("JOUE", _joue())), build_record(row("MAPA", MAPA, idweb="26-2"))]
    cov = coverage(recs)
    assert cov["JOUE"]["n"] == 1 and cov["JOUE"]["champs"]["cpv"] == 1
    assert cov["MAPA"]["champs"]["cpv"] == 0 and cov["MAPA"]["champs"]["objet"] == 1


def test_type_marche_list_is_normalised():
    from boamp_eval.build import type_marche

    assert type_marche({"type_marche_facette": ["Travaux", "Services"]}) == "Services+Travaux"
    assert type_marche({}) == "inconnu"
