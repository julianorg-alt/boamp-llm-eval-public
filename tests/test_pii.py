from boamp_eval.pii import Masker, find_residual_pii


def test_masks_emails_and_phones():
    m = Masker()
    out = m.mask(
        "Contact : jean.exemple@mairie-x.fr ou secretariat@ville.fr, tel 01 98 76 54 32, +33 1 23 45 67 89, 0198765432."
    )
    assert "@" not in out
    assert "[EMAIL]" in out
    assert out.count("[TEL]") == 3
    assert not find_residual_pii(out)


def test_masks_civility_names():
    m = Masker()
    out = m.mask("Renseignements auprès de Monsieur Marc EXEMPLE ou Mme Claire Modele-Test, maire.")
    assert "EXEMPLE" not in out and "Modele-Test" not in out and "Marc" not in out
    assert out.count("[PERSONNE]") == 2
    assert "maire" in out


def test_does_not_mask_institutions():
    m = Masker()
    s = "Madame la Maire, M. le Président du Département, Mairie de Testville."
    assert m.mask(s) == s


def test_blocklist_names_masked_everywhere_but_not_inside_words_or_compounds():
    m = Masker(["Marc EXEMPLE, Maire de Testville"])
    out = m.mask("Ouverture par exemple et Marc. Rue Saint-Marc, Marcville.")
    assert "exemple" not in out.lower()
    assert "Saint-Marc" in out and "Marcville" in out
    assert out.count("[PERSONNE]") == 2


def test_blocklist_ignores_service_words():
    m = Masker(["Service des marchés publics", "TESTNOM"])
    out = m.mask("Le service des marchés publics de la mairie. TESTNOM")
    assert "service des marchés publics" in out
    assert "TESTNOM" not in out


def test_mask_obj_recursive():
    m = Masker()
    obj = {"a": ["x@y.fr", {"b": "tel 0198765432"}], "n": 3}
    out = m.mask_obj(obj)
    assert out == {"a": ["[EMAIL]", {"b": "tel [TEL]"}], "n": 3}


def test_residual_detects_leaks():
    assert find_residual_pii("écrire à a@b.fr")
    assert find_residual_pii("appeler 01 98 76 54 32")
    assert not find_residual_pii("Marché n° 2026-0412, montant 139460 euros, CPV 45233140")


def test_contact_that_is_an_organisation_is_not_masked():
    m = Masker(["Mairie de Créteil", "Service marchés Créteil"])
    s = "Ville de Créteil, hôtel de ville de Créteil."
    assert m.mask(s) == s


def test_keep_words_protect_buyer_name():
    m = Masker(["Créteil Paul"], keep=["Ville de Créteil"])
    out = m.mask("Ville de Créteil, contact Paul.")
    assert out == "Ville de Créteil, contact [PERSONNE]."


def test_label_like_contact_is_not_a_person():
    m = Masker(["Cellule Juridique des contrats de la commande publique - DRMP"])
    s = "Code de la Commande Publique, Cellule Juridique."
    assert m.mask(s) == s
