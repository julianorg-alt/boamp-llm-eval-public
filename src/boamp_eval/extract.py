"""Vérité terrain : 9 champs extraits des champs structurés `donnees` d'un avis BOAMP.

Un champ absent de l'avis structuré est simplement omis (« non applicable » : exclu du score).
Familles : JOUE (eForms), FNS (FNSimple), MAPA.
"""

import re
from typing import Any

FIELDS = (
    "acheteur", "objet", "cpv", "lots", "montant_estime",
    "procedure", "date_limite", "criteres", "lieu",
)  # fmt: skip

FNS_PROCEDURES = {"procedureAdapteeO": "adapted-open", "procedureAdapteeR": "adapted-restricted"}


def _as_list(x: Any) -> list:
    if x is None or x == "":
        return []
    return x if isinstance(x, list) else [x]


def _text(node: Any) -> str | None:
    """Texte d'un noeud eForms : chaîne, {'#text': ...} ou liste (première valeur)."""
    for n in _as_list(node):
        v = n.get("#text") if isinstance(n, dict) else n
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, int | float):
            return str(v)
    return None


def _num(v: Any) -> float | None:
    try:
        return float(str(v).replace(",", ".").replace(" ", ""))
    except (TypeError, ValueError):
        return None


def _get(d: Any, *path: str) -> Any:
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _walk(o: Any, key: str):
    """Valeurs de toutes les clés `key` dans l'arbre (profondeur quelconque)."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key:
                yield v
            yield from _walk(v, key)
    elif isinstance(o, list):
        for v in o:
            yield from _walk(v, key)


def _iso(value: str) -> str:
    """Retire les millisecondes (2026-11-06T12:00:00.000+01:00 -> ...T12:00:00+01:00)."""
    return re.sub(r"(T\d{2}:\d{2}:\d{2})\.\d+", r"\1", value.strip())


def _drop_none(t: dict) -> dict:
    return {k: v for k, v in t.items() if v not in (None, "", [], {})}


# --- JOUE (eForms) ---------------------------------------------------------------------------


def _eforms_notice(donnees: dict) -> dict | None:
    n = _get(donnees, "EFORMS", "ContractNotice")
    return n if isinstance(n, dict) else None


def _eforms_orgs(notice: dict) -> list[dict]:
    out = []
    for orgs in _walk(notice, "efac:Organizations"):
        for o in _as_list(_get(orgs, "efac:Organization")):
            c = o.get("efac:Company") if isinstance(o, dict) else None
            if isinstance(c, dict):
                out.append(c)
    return out


def _eforms_buyer(notice: dict) -> str | None:
    pid = _text(_get(_as_list(notice.get("cac:ContractingParty"))[0], "cac:Party", "cac:PartyIdentification", "cbc:ID")) \
        if _as_list(notice.get("cac:ContractingParty")) else None  # fmt: skip
    for c in _eforms_orgs(notice):
        if _text(_get(c, "cac:PartyIdentification", "cbc:ID")) == pid:
            return _text(_get(c, "cac:PartyName", "cbc:Name"))
    return None


def _eforms_deadline(lots: list[dict], notice: dict) -> str | None:
    cands = []
    for src in [*lots, notice]:
        for p in _walk(src, "cac:TenderSubmissionDeadlinePeriod"):
            end, time = _text(_get(p, "cbc:EndDate")), _text(_get(p, "cbc:EndTime"))
            if end:
                d = end[:10]
                cands.append(f"{d}T{time}" if time else d)
        if cands:
            break
    return min(cands) if cands else None


def _eforms_criteria(lots: list[dict], notice: dict) -> list[dict]:
    for src in [*lots, notice]:
        subs = [s for s in _walk(src, "cac:SubordinateAwardingCriterion") for s in _as_list(s)]
        if not subs:
            continue
        out = []
        for s in subs:
            weight = next(iter(_walk(s, "efbc:ParameterNumeric")), None)
            out.append(
                {
                    "type": _text(s.get("cbc:AwardingCriterionTypeCode")),
                    "libelle": _text(s.get("cbc:Description")),
                    "poids": _num(weight),
                }
            )
        return out
    return []


def _eforms_place(project: dict) -> str | None:
    addr = _get(project, "cac:RealizedLocation", "cac:Address")
    if not isinstance(addr, dict):
        return None
    return _text(addr.get("cbc:CountrySubentityCode")) or _text(addr.get("cbc:CityName"))


def _joue(donnees: dict) -> dict:
    n = _eforms_notice(donnees)
    if n is None:
        return {}
    proj = n.get("cac:ProcurementProject") or {}
    lots = [x for x in _as_list(n.get("cac:ProcurementProjectLot")) if isinstance(x, dict)]
    cpv = [
        _text(_get(proj, "cac:MainCommodityClassification", "cbc:ItemClassificationCode")),
        *[
            _text(_get(a, "cbc:ItemClassificationCode"))
            for a in _as_list(proj.get("cac:AdditionalCommodityClassification"))
        ],
    ]
    amount = _get(proj, "cac:RequestedTenderTotal", "cbc:EstimatedOverallContractAmount")
    value = _num(_text(amount))
    lot_list = [
        {
            "id": _text(lot.get("cbc:ID")) or str(i),
            "titre": _text(_get(lot, "cac:ProcurementProject", "cbc:Name")),
        }
        for i, lot in enumerate(lots, 1)
    ]
    place = _eforms_place(proj)
    if not place:
        for lot in lots:
            place = _eforms_place(lot.get("cac:ProcurementProject") or {})
            if place:
                break
    return _drop_none(
        {
            "acheteur": _eforms_buyer(n),
            "objet": _text(proj.get("cbc:Name")),
            "cpv": sorted({c for c in cpv if c}),
            "lots": lot_list if len(lot_list) >= 2 else None,
            "montant_estime": {"valeur": value, "devise": amount.get("@currencyID")}
            if value is not None and isinstance(amount, dict)
            else None,
            "procedure": _text(_get(n, "cac:TenderingProcess", "cbc:ProcedureCode")),
            "date_limite": _eforms_deadline(lots, n),
            "criteres": _eforms_criteria(lots, n),
            "lieu": place,
        }
    )


# --- FNS ------------------------------------------------------------------------------------


def _fns(donnees: dict) -> dict:
    root = donnees.get("FNSimple")
    if not isinstance(root, dict):
        return {}
    ini = root.get("initial") or {}
    nm = ini.get("natureMarche") or {}
    proc = ini.get("procedure") or {}
    cpv = [v for k, v in _walk_items(nm.get("codeCPV")) if k.startswith("class") and v]
    lots = [lot for lot in _as_list(_get(ini, "lots", "lot")) if isinstance(lot, dict)]
    val = nm.get("valeurEstimee") if isinstance(nm.get("valeurEstimee"), dict) else {}
    amount = _num(val.get("valeur"))
    procedure = next((v for k, v in FNS_PROCEDURES.items() if k in proc), None)
    return _drop_none(
        {
            "acheteur": _text(_get(root, "organisme", "nomOfficiel")),
            "objet": _text(nm.get("intitule")),
            "cpv": sorted(set(cpv)),
            "lots": [
                {"id": str(i), "titre": _text(lot.get("description"))}
                for i, lot in enumerate(lots, 1)
            ]
            if len(lots) >= 2
            else None,
            "montant_estime": {"valeur": amount, "devise": val.get("@devise")}
            if amount is not None
            else None,
            "procedure": procedure,
            "date_limite": _iso(proc["dateReceptionOffres"])
            if proc.get("dateReceptionOffres")
            else None,
            "lieu": _text(nm.get("lieuExecution")),
        }
    )


def _walk_items(o: Any):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str):
                yield k, v
            else:
                yield from _walk_items(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk_items(v)


# --- MAPA -----------------------------------------------------------------------------------


def _mapa(donnees: dict) -> dict:
    root = donnees.get("MAPA")
    if not isinstance(root, dict):
        return {}
    ini = root.get("initial") or {}
    desc = ini.get("description") or {}
    lots = [lot for lot in _as_list(_get(ini, "lots", "lot")) if isinstance(lot, dict)]
    place = desc.get("lieuExecutionLivraison") or desc.get("lieuExecution") or {}
    place_txt = ", ".join(
        p
        for p in [
            _text(_get(place, "voie", "nomvoie")),
            _text(place.get("cp")),
            _text(place.get("ville")),
        ]
        if p
    )
    crit = [
        {"type": None, "libelle": _text(c.get("critere")), "poids": _num(c.get("criterePCT"))}
        for c in _as_list(_get(ini, "criteres", "criterePondere"))
        if isinstance(c, dict)
    ]
    return _drop_none(
        {
            "acheteur": _text(_get(root, "organisme", "acheteurPublic")),
            "objet": _text(desc.get("objet")),
            "lots": [
                {"id": _text(lot.get("numLot")) or str(i), "titre": _text(lot.get("description"))}
                for i, lot in enumerate(lots, 1)
            ]
            if len(lots) >= 2
            else None,
            "procedure": "adapted" if "procedureAdaptee" in (ini.get("procedure") or {}) else None,
            "date_limite": _iso(_text(_get(ini, "delais", "receptionOffres")) or "") or None,
            "criteres": crit,
            "lieu": place_txt or None,
        }
    )


# --- API ------------------------------------------------------------------------------------


def extract_truth(famille: str, donnees: dict) -> dict:
    fn = {"JOUE": _joue, "FNS": _fns, "MAPA": _mapa}.get(famille)
    if fn is None or not isinstance(donnees, dict):
        return {}
    return fn(donnees)


def contact_names(famille: str, donnees: dict) -> list[str]:
    """Noms de contact structurés (pour alimenter le masquage)."""
    if famille == "JOUE":
        n = _eforms_notice(donnees)
        return [
            t
            for t in (_text(_get(c, "cac:Contact", "cbc:Name")) for c in _eforms_orgs(n or {}))
            if t
        ]
    if famille == "FNS":
        n = _text(_get(donnees, "FNSimple", "initial", "communication", "nomContact"))
        return [n] if n else []
    if famille == "MAPA":
        p = _get(donnees, "MAPA", "organisme", "correspondantPRM") or {}
        return [t for t in (_text(p.get("nom")), _text(p.get("pren"))) if t]
    return []


def org_words(famille: str, donnees: dict) -> list[str]:
    """Textes de l'organisme (nom, ville) dont les mots ne doivent pas être pris pour des noms."""
    t = extract_truth(famille, donnees)
    extra = []
    if famille == "FNS":
        extra = [_text(_get(donnees, "FNSimple", "organisme", "ville"))]
    elif famille == "MAPA":
        extra = [_text(_get(donnees, "MAPA", "organisme", "adr", "ville"))]
    return [x for x in [t.get("acheteur"), t.get("lieu"), *extra] if x]
