"""Sélection stratifiée à graine fixe, découpage hold-out, fenêtres de dates."""

import hashlib
import random
from datetime import date, timedelta


def _key(seed: int, idweb: str) -> str:
    return hashlib.sha256(f"{seed}:{idweb}".encode()).hexdigest()


def stratified_pick(candidates: list[dict], n: int, seed: int) -> list[dict]:
    """Tourniquet sur les strates (ordre trié), chaque strate triée par empreinte(seed, idweb).

    Indépendant de l'ordre d'entrée. Une strate épuisée cède sa place aux autres.
    """
    strata: dict[str, list[dict]] = {}
    for c in sorted(candidates, key=lambda c: _key(seed, c["idweb"])):
        strata.setdefault(c["strate"], []).append(c)
    order = sorted(strata)
    random.Random(seed).shuffle(order)  # noqa: S311 - tirage reproductible, pas de crypto
    picked: list[dict] = []
    while len(picked) < n and any(strata.values()):
        for s in order:
            if strata[s] and len(picked) < n:
                picked.append(strata[s].pop(0))
    return picked


def split_holdout(records: list[dict], seed: int, frac: float = 0.2) -> set[str]:
    """idweb du hold-out : `frac` de chaque famille (arrondi), choisis par empreinte(seed, idweb)."""
    by_fam: dict[str, list[str]] = {}
    for r in records:
        by_fam.setdefault(r["famille"], []).append(r["idweb"])
    out: set[str] = set()
    for ids in by_fam.values():
        ids.sort(key=lambda i: _key(seed, i))
        out.update(ids[: round(len(ids) * frac)])
    return out


def weekly_windows(start: str, end: str) -> list[tuple[str, str]]:
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    out = []
    while s <= e:
        w_end = min(s + timedelta(days=6), e)
        out.append((s.isoformat(), w_end.isoformat()))
        s = w_end + timedelta(days=1)
    return out
