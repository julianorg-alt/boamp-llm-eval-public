"""Métriques par champ (définitions : docs/METRICS.md).

Chaque fonction `score_*` renvoie un score dans [0, 1] pour un champ dont la vérité existe.
Un champ absent de la vérité est « non applicable » : exclu du score, jamais compté faux.
S'il est pourtant fourni et introuvable dans le texte d'entrée, il compte comme « inventé ».
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

FIELDS = (
    "acheteur", "objet", "cpv", "lots", "montant_estime",
    "procedure", "date_limite", "criteres", "lieu",
)  # fmt: skip
# Circularité : l'entrée est générée depuis la vérité. Champs recopiables = « faciles » (annexe) ;
# score global = moyenne des champs « durs » (calcul, conversion, sélection dans le texte).
EASY_FIELDS = ("objet", "acheteur", "lots", "procedure")
HARD_FIELDS = ("date_limite", "montant_estime", "criteres", "cpv", "lieu")

AMOUNT_TOLERANCE = 0.01
WEIGHT_TOLERANCE = 1.0

_STOP = {
    "de",
    "du",
    "des",
    "la",
    "le",
    "les",
    "sur",
    "sous",
    "en",
    "et",
    "d",
    "l",
    "france",
    "cedex",
}
_MONTHS = (
    "janvier fevrier mars avril mai juin juillet aout septembre octobre novembre decembre".split()
)


def norm_text(s: Any) -> str:
    """Minuscules, sans accents, ponctuation et espaces réduits à un espace."""
    s = unicodedata.normalize("NFKD", str(s)).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _strip_paren(s: str) -> str:
    return re.sub(r"\([^)]*\)", " ", str(s))


def present(v: Any) -> bool:
    return v not in (None, "", [], {})


# --- exact normalisé -------------------------------------------------------------------------
def score_exact(truth: str, pred: Any, *, paren: bool = False) -> float:
    if not present(pred):
        return 0.0
    a, b = (_strip_paren(x) if paren else x for x in (truth, pred))
    return float(norm_text(a) == norm_text(b))


# --- date limite -----------------------------------------------------------------------------
_DATE = re.compile(
    r"^\s*(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}):(\d{2})(?::\d{2})?(?:\.\d+)?)?\s*(Z|[+-]\d{2}:?\d{2})?\s*$"
)


def _parse_date(s: Any) -> tuple[str, datetime | None, bool] | None:
    """(jour, heure locale naïve ou None, aware ?) ; l'heure locale est celle écrite dans la chaîne."""
    m = _DATE.match(str(s))
    if not m:
        return None
    day, hh, mm, tz = m.groups()
    if hh is None:
        return day, None, False
    local = datetime.fromisoformat(f"{day}T{hh}:{mm}:00")
    if tz is None:
        return day, local, False
    if tz == "Z":
        off = timezone.utc  # noqa: UP017
    else:
        sign = -1 if tz[0] == "-" else 1
        digits = tz[1:].replace(":", "")
        off = timezone(sign * timedelta(hours=int(digits[:2]), minutes=int(digits[2:])))
    return day, local.replace(tzinfo=off), True


def score_date(truth: str, pred: Any) -> float:
    t, p = _parse_date(truth), _parse_date(pred)
    if t is None or p is None:
        return 0.0
    if t[1] is None:  # vérité sans heure : on compare le jour
        return float(t[0] == p[0])
    if p[1] is None:
        return 0.0
    if t[2] and p[2]:  # deux décalages connus : même instant
        return float(t[1].astimezone(UTC) == p[1].astimezone(UTC))
    return float(t[1].replace(tzinfo=None) == p[1].replace(tzinfo=None))  # heure locale écrite


# --- montant ---------------------------------------------------------------------------------
def _float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def score_amount(truth: dict, pred: Any) -> float:
    if not isinstance(pred, dict):
        return 0.0
    t, p = _float(truth.get("valeur")), _float(pred.get("valeur"))
    if t is None or p is None:
        return 0.0
    if str(truth.get("devise", "")).casefold() != str(pred.get("devise", "")).casefold():
        return 0.0
    return float(abs(p - t) <= AMOUNT_TOLERANCE * abs(t))


# --- ensembles -------------------------------------------------------------------------------
def f1(tp: int, n_pred: int, n_truth: int) -> float:
    if tp == 0 or n_pred == 0 or n_truth == 0:
        return 0.0
    p, r = tp / n_pred, tp / n_truth
    return 2 * p * r / (p + r)


def _cpv_codes(items: Any) -> set[str]:
    out = set()
    for x in items if isinstance(items, list) else []:
        code = re.sub(r"\D", "", str(x).split("-")[0])
        if code:
            out.add(code)
    return out


def score_cpv(truth: list, pred: Any) -> float:
    t, p = _cpv_codes(truth), _cpv_codes(pred)
    return f1(len(t & p), len(p), len(t))


def _lot_key(titre: Any) -> str:
    return re.sub(r"^lot\s*\d+\s*", "", norm_text(_strip_paren(titre)))


def _titles(items: Any) -> list[str]:
    return [
        k for x in (items if isinstance(items, list) else []) if isinstance(x, dict)
        if (k := _lot_key(x.get("titre", "")))
    ]  # fmt: skip


def score_lots(truth: list, pred: Any) -> float:
    t, p = Counter(_titles(truth)), Counter(_titles(pred))
    return f1(sum((t & p).values()), sum(p.values()), sum(t.values()))


def _crit_items(items: Any) -> list[tuple[str, float | None]]:
    return [
        (norm_text(x.get("libelle", "")), _float(x.get("poids")))
        for x in (items if isinstance(items, list) else []) if isinstance(x, dict)
    ]  # fmt: skip


def score_criteres(truth: list, pred: Any) -> float:
    t, p = _crit_items(truth), _crit_items(pred)
    used: set[int] = set()
    tp = 0
    for lib, w in t:
        for i, (plib, pw) in enumerate(p):
            if i in used or plib != lib:
                continue
            if w is None or (pw is not None and abs(pw - w) <= WEIGHT_TOLERANCE):
                used.add(i)
                tp += 1
                break
    return f1(tp, len(p), len(t))


# --- lieu ------------------------------------------------------------------------------------
_NUTS = re.compile(r"\b[A-Z]{2}[A-Z0-9]{2,3}\b")


def _nuts(s: str) -> set[str]:
    return {c for c in _NUTS.findall(s) if any(ch.isdigit() for ch in c)}


def _place_tokens(s: str) -> set[str]:
    return {t for t in norm_text(s).split() if t not in _STOP and not t.isdigit()}


def score_lieu(truth: str, pred: Any) -> float:
    if not present(pred):
        return 0.0
    pred = str(pred)
    codes = _nuts(truth)
    if codes and codes & _nuts(pred.upper()):
        return 1.0
    a, b = _place_tokens(_NUTS.sub(" ", truth) if codes else truth), _place_tokens(pred)
    return float(bool(a) and bool(b) and (a <= b or b <= a))  # vérité = code seul : a vide -> 0


# --- ancrage dans le texte (détection d'invention) -------------------------------------------
_NUM = re.compile(r"\d[\d   .,]*\d|\d")


def _numbers(text: str) -> list[float]:
    out = []
    for raw in _NUM.findall(text):
        s = re.sub(r"[   ]", "", raw)
        if "." in s and "," in s:
            dec = "." if s.rfind(".") > s.rfind(",") else ","
            s = s.replace("," if dec == "." else ".", "").replace(dec, ".")
        elif re.fullmatch(r"\d{1,3}([.,]\d{3})+", s):
            s = re.sub(r"[.,]", "", s)
        else:
            s = s.replace(",", ".")
        if (v := _float(s)) is not None:
            out.append(v)
    return out


def _text_dates(text: str) -> set[str]:
    nt = norm_text(text)
    days = set(re.findall(r"\d{4}-\d{2}-\d{2}", text))
    for d, mon, y in re.findall(r"\b(\d{1,2})(?:er)? (" + "|".join(_MONTHS) + r") (\d{4})\b", nt):
        days.add(f"{y}-{_MONTHS.index(mon) + 1:02d}-{int(d):02d}")
    return days


def is_grounded(field: str, value: Any, text: str) -> bool:
    """La valeur fournie figure-t-elle dans le texte d'entrée ? Sinon : inventée."""
    nt = f" {norm_text(text)} "
    if field == "montant_estime":
        v = _float(value.get("valeur")) if isinstance(value, dict) else None
        return v is not None and any(
            abs(n - v) <= AMOUNT_TOLERANCE * abs(v) for n in _numbers(text)
        )
    if field == "date_limite":
        p = _parse_date(value)
        return p is not None and p[0] in _text_dates(text)
    if field == "cpv":
        codes = _cpv_codes(value)
        return bool(codes) and all(c in re.findall(r"\d{8}", text) for c in codes)
    if field == "lots":
        keys = _titles(value)
        return bool(keys) and all(f" {k} " in nt for k in keys)
    if field == "criteres":
        libs = [lib for lib, _ in _crit_items(value) if lib]
        return bool(libs) and all(f" {lib} " in nt for lib in libs)
    return f" {norm_text(value)} " in nt


# --- score d'un enregistrement ---------------------------------------------------------------
@dataclass(frozen=True)
class FieldResult:
    applicable: bool  # la vérité existe pour ce champ
    score: float | None  # None si non applicable
    invented: bool  # fourni, vérité absente, introuvable dans le texte
    provided: bool  # le modèle a fourni une valeur


def _score_field(field: str, truth: Any, pred: Any) -> float:
    if field == "acheteur":
        return score_exact(truth, pred, paren=True)
    if field in ("objet", "procedure"):
        return score_exact(truth, pred)
    return {
        "date_limite": score_date,
        "montant_estime": score_amount,
        "cpv": score_cpv,
        "lots": score_lots,
        "criteres": score_criteres,
        "lieu": score_lieu,
    }[field](truth, pred)


def score_record(rec: dict, pred: dict | None) -> dict[str, FieldResult]:
    """`pred` None = réponse inexploitable : chaque champ applicable compte 0."""
    truth = rec["verite"]
    out = {}
    for f in FIELDS:
        value = (pred or {}).get(f)
        provided = present(value)
        if present(truth.get(f)):
            s = _score_field(f, truth[f], value) if provided else 0.0
            out[f] = FieldResult(True, s, False, provided)
        else:
            inv = provided and not is_grounded(f, value, rec["texte"])
            out[f] = FieldResult(False, None, inv, provided)
    return out
