from boamp_eval.pii import Masker
from boamp_eval.render import fr_datetime, fr_number, render_text
from tests.test_extract import FNS, MAPA, _joue


def test_fr_datetime():
    assert fr_datetime("2026-10-21T16:00:00+02:00") == "21 octobre 2026 à 16h00 (UTC+02:00)"
    assert fr_datetime("2026-11-20T12:00:00") == "20 novembre 2026 à 12h00"
    assert fr_datetime("2026-03-01") == "1er mars 2026"


def test_fr_number():
    assert fr_number(139460.0) == "139 460"
    assert fr_number(1234.5) == "1 234,5"


def test_joue_text_is_prose_without_keys_or_contacts():
    t = render_text("JOUE", _joue(), Masker(["Jean Martin"]))
    assert "Commune d'Hyères" in t and "Travaux de voirie" in t
    assert "procédure ouverte" in t
    assert "21 octobre 2026 à 16h00" in t
    assert "139 460" in t and "45233140" in t
    assert "Lot A" in t and "Lot B" in t
    assert "60 %" in t and "40 %" in t
    for forbidden in ("cbc:", "cac:", "EFORMS", "ContractNotice", "a@b.fr", "Martin", '{"'):
        assert forbidden not in t


def test_fns_text():
    t = render_text("FNS", FNS, Masker(["Marc EXEMPLE, Maire de Testville"]))
    assert "Mairie de Testville" in t and "procédure adaptée ouverte" in t
    assert "6 novembre 2026 à 12h00" in t
    assert "EXEMPLE" not in t and "FNSimple" not in t and "nomContact" not in t


def test_mapa_text():
    t = render_text("MAPA", MAPA, Masker(["TESTNOM", "Xavier"]))
    assert "COMMUNE DE MIEUSSY" in t and "Site internet" in t
    assert "TESTNOM" not in t and "Xavier" not in t and "MAPA" not in t.replace("MAPA ", "")
    assert "Plâtrerie" in t and "40 %" in t


def test_joue_criteria_have_no_type_suffix():
    """v2 : le libellé du critère est rendu tel quel, sans le type entre parenthèses."""
    t = render_text("JOUE", _joue(), Masker(["Jean Martin"]))
    sentence = next(p for p in t.split("\n\n") if p.startswith("Les offres sont jugées"))
    assert "(prix)" not in sentence and "(qualité)" not in sentence and "(coût)" not in sentence
    assert "pondéré à 60 %" in sentence and "pondéré à 40 %" in sentence


def test_mapa_sous_noeuds_en_chaine_ne_plantent_pas():
    donnees = {"MAPA": {"organisme": "x", "initial": {"conditions": "texte", "caracteristiques": "t"}}}
    assert isinstance(render_text("MAPA", donnees, Masker([])), str)
