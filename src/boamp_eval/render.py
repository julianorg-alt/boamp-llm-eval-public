"""Rendu TEXTE d'un avis (entrée donnée aux modèles), distinct de la vérité terrain.

L'API BOAMP ne fournit pas le texte de l'avis officiel (la page boamp.fr est une application
JavaScript qui affiche ces mêmes données structurées ; pas de PDF servi). Le rendu est donc généré
depuis `donnees` en prose française neutre : phrases, aucune clé JSON ni libellé de champ, codes
traduits (procédure) ou dits tels quels (CPV, NUTS), dates en toutes lettres. Les blocs de contact
ne sont pas rendus ; tout le texte passe ensuite par le masqueur de données personnelles.
"""

import re
from typing import Any

from boamp_eval.extract import (
    _as_list,
    _eforms_buyer,
    _eforms_notice,
    _get,
    _text,
    extract_truth,
)
from boamp_eval.pii import Masker

MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]  # fmt: skip
PROCEDURE_LABELS = {
    "open": "procédure ouverte",
    "restricted": "procédure restreinte",
    "neg-w-call": "procédure concurrentielle avec négociation",
    "comp-dial": "dialogue compétitif",
    "innovation": "partenariat d'innovation",
    "neg-wo-call": "procédure négociée sans mise en concurrence préalable",
    "oth-single": "autre procédure en une seule étape",
    "oth-mult": "autre procédure en plusieurs étapes",
    "adapted-open": "procédure adaptée ouverte",
    "adapted-restricted": "procédure adaptée restreinte",
    "adapted": "procédure adaptée",
}
CRITERION_LABELS = {"price": "prix", "quality": "qualité", "cost": "coût"}


def fr_number(x: float) -> str:
    whole, _, frac = f"{x:.2f}".partition(".")
    whole = f"{int(whole):,}".replace(",", " ")
    frac = frac.rstrip("0")
    return f"{whole},{frac}" if frac else whole


def fr_datetime(iso: str) -> str:
    m = re.match(
        r"(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::\d{2})?(Z|[+-]\d{2}:\d{2})?)?", iso
    )
    if not m:
        return iso
    y, mo, d, hh, mm, tz = m.groups()
    day = "1er" if int(d) == 1 else str(int(d))
    out = f"{day} {MONTHS[int(mo) - 1]} {y}"
    if hh is not None:
        out += f" à {hh}h{mm}"
        if tz:
            out += " (UTC" + ("+00:00" if tz == "Z" else tz) + ")"
    return out


def _money(m: dict) -> str:
    unit = "euros" if m.get("devise") == "EUR" else (m.get("devise") or "")
    return f"{fr_number(m['valeur'])} {unit}".strip()


def _criteria_sentence(crit: list[dict]) -> str:
    parts = []
    for c in crit:
        label = c.get("libelle") or CRITERION_LABELS.get(c.get("type") or "", "critère non précisé")
        if c.get("type") in CRITERION_LABELS and c.get("libelle"):
            label = f"{label} ({CRITERION_LABELS[c['type']]})"
        parts.append(
            f"{label}, pondéré à {fr_number(c['poids'])} %" if c.get("poids") is not None else label
        )
    return "Les offres sont jugées selon les critères suivants : " + " ; ".join(parts) + "."


def _common(t: dict, *, deadline_note: bool = True) -> list[str]:
    out = []
    if t.get("cpv"):
        out.append("Classification CPV : " + ", ".join(t["cpv"]) + ".")
    if t.get("procedure"):
        out.append(
            "Mode de passation : "
            + PROCEDURE_LABELS.get(t["procedure"], f"procédure de type « {t['procedure']} »")
            + "."
        )
    if t.get("montant_estime"):
        out.append(f"Le montant total estimé du marché s'élève à {_money(t['montant_estime'])}.")
    if t.get("lieu"):
        out.append(f"Le marché est exécuté en : {t['lieu']}.")
    if t.get("date_limite") and deadline_note:
        out.append(f"Les offres doivent être remises avant le {fr_datetime(t['date_limite'])}.")
    if t.get("criteres"):
        out.append(_criteria_sentence(t["criteres"]))
    return out


def _lots_paragraph(lots: list[dict], descriptions: dict[int, str] | None = None) -> str:
    lines = [f"Le marché est alloti en {len(lots)} lots :"]
    for i, lot in enumerate(lots, 1):
        line = f"lot {i} — {lot.get('titre') or 'sans intitulé'}"
        if descriptions and descriptions.get(i):
            line += f" ({descriptions[i]})"
        lines.append(line + ";")
    return "\n".join(lines)


def _joue(donnees: dict, t: dict) -> list[str]:
    n = _eforms_notice(donnees) or {}
    proj = n.get("cac:ProcurementProject") or {}
    out = [
        f"{t.get('acheteur') or _eforms_buyer(n) or 'Un acheteur public'} lance la consultation suivante : « {t.get('objet', '')} »."
    ]
    if _text(proj.get("cbc:Description")):
        out.append(_text(proj.get("cbc:Description")))
    out += _common(t)
    if t.get("lots"):
        raw = [x for x in _as_list(n.get("cac:ProcurementProjectLot")) if isinstance(x, dict)]
        desc = {
            i: _text(_get(x, "cac:ProcurementProject", "cbc:Description"))
            for i, x in enumerate(raw, 1)
        }
        out.append(_lots_paragraph(t["lots"], {k: v for k, v in desc.items() if v}))
    return out


def _fns(donnees: dict, t: dict) -> list[str]:
    root = donnees.get("FNSimple") or {}
    ini = root.get("initial") or {}
    nm = ini.get("natureMarche") or {}
    org = root.get("organisme") or {}
    place = " ".join(p for p in [org.get("cp"), org.get("ville")] if p)
    out = [
        f"{t.get('acheteur', 'Un acheteur public')}{f' ({place})' if place else ''} publie un avis de marché : « {t.get('objet', '')} »."
    ]
    if _text(nm.get("description")) and _text(nm.get("description")) != t.get("objet"):
        out.append(_text(nm.get("description")))
    if _text(nm.get("dureeMois")):
        out.append(f"Durée du marché : {_text(nm.get('dureeMois'))} mois.")
    out += _common(t)
    if t.get("lots"):
        out.append(_lots_paragraph(t["lots"]))
    proc = ini.get("procedure") or {}
    if _text(proc.get("criteresAttrib")):
        out.append("Attribution : " + _text(proc.get("criteresAttrib")))
    for key, lead in (
        ("capaciteExercice", "Aptitude à exercer l'activité"),
        ("capaciteEcoFin", "Capacité économique et financière"),
        ("capaciteTech", "Capacité technique"),
    ):
        if _text(proc.get(key)):
            out.append(f"{lead} : {_text(proc.get(key))}")
    info = _get(ini, "informComplementaire", "autresInformComplementaire")
    if _text(info):
        out.append("Renseignements complémentaires : " + _text(info))
    return out


def _mapa(donnees: dict, t: dict) -> list[str]:
    root = donnees.get("MAPA") or {}
    ini = root.get("initial") or {}
    org = root.get("organisme") or {}
    ville = _text(_get(org, "adr", "ville"))
    out = [
        f"{t.get('acheteur', 'Un acheteur public')}{f' ({ville})' if ville else ''} lance un marché à procédure adaptée : « {t.get('objet', '')} »."
    ]
    car = ini.get("caracteristiques") or {}
    for key in ("principales", "quantites"):
        if _text(car.get(key)):
            out.append(_text(car.get(key)))
    dur = _get(ini, "duree", "nbMois")
    if _text(dur):
        out.append(f"Durée : {_text(dur)} mois.")
    out += _common(t)
    if t.get("lots"):
        out.append(_lots_paragraph(t["lots"]))
    cond = ini.get("conditions") or {}
    if _text(cond.get("modFinancement")):
        out.append(_text(cond.get("modFinancement")))
    if _text(cond.get("formeJuridique")):
        out.append(_text(cond.get("formeJuridique")))
    for node in (_get(ini, "justifications", "justificationAutre"), ini.get("infosSup"),
                 _get(ini, "renseignements", "rensgComplt")):  # fmt: skip
        if _text(node):
            out.append(_text(node))
    return out


def render_text(famille: str, donnees: dict[str, Any], masker: Masker) -> str:
    t = extract_truth(famille, donnees)
    parts = {"JOUE": _joue, "FNS": _fns, "MAPA": _mapa}[famille](donnees, t)
    return masker.mask("\n\n".join(p for p in parts if p))
