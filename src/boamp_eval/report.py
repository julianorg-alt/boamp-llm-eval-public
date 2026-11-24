"""Agrégation par champ, intervalles de confiance par bootstrap, verdict entre modèles."""

from __future__ import annotations

import random

from boamp_eval import metrics as m

SEED = 20261118
N_BOOT = 2000
ALPHA = 0.05


def evaluate(records: list[dict], rows: list[dict]) -> list[dict]:
    by_id = {r["idweb"]: r for r in rows}
    out = []
    for rec in records:
        row = by_id[rec["idweb"]]
        out.append(
            {
                "idweb": rec["idweb"],
                "famille": rec["famille"],
                "res": m.score_record(rec, row["pred"]),
                "error": row["error"],
            }
        )
    return out


def field_mean(rows: list[dict], field: str) -> float | None:
    s = [r["res"][field].score for r in rows if r["res"][field].applicable]
    return sum(s) / len(s) if s else None


def _macro(rows: list[dict], fields: tuple[str, ...]) -> float | None:
    means = [v for f in fields if (v := field_mean(rows, f)) is not None]
    return sum(means) / len(means) if means else None


def hard_global(rows: list[dict]) -> float | None:
    """Score global : moyenne (par champ) des champs durs applicables."""
    return _macro(rows, m.HARD_FIELDS)


def easy_global(rows: list[dict]) -> float | None:
    return _macro(rows, m.EASY_FIELDS)


def bootstrap_ci(rows, stat, *, n_boot: int = N_BOOT, seed: int = SEED, alpha: float = ALPHA):
    """IC percentile par rééchantillonnage des avis (seed fixe) ; None si rien à estimer."""
    rng = random.Random(seed)  # noqa: S311
    vals = []
    for _ in range(n_boot):
        v = stat([rows[rng.randrange(len(rows))] for _ in rows])
        if v is not None:
            vals.append(v)
    if not vals:
        return None
    vals.sort()
    lo = vals[int(len(vals) * alpha / 2)]
    hi = vals[min(len(vals) - 1, int(len(vals) * (1 - alpha / 2)))]
    return lo, hi


def paired_diff_ci(rows_a: list[dict], rows_b: list[dict], stat=None, *,
                   n_boot: int = N_BOOT, seed: int = SEED, alpha: float = ALPHA):  # fmt: skip
    """Bootstrap apparié de stat(A) - stat(B) : même tirage d'avis pour A et B.

    `rows_a` et `rows_b` sont alignés par `idweb` (même ensemble d'avis, ordre trié ici).
    Retourne (écart observé, bas, haut), IC percentile à 1 - alpha ; None si rien à estimer.
    """
    stat = stat or hard_global
    a = {r["idweb"]: r for r in rows_a}
    b = {r["idweb"]: r for r in rows_b}
    if a.keys() != b.keys():
        raise ValueError("comparaison appariée : les deux modèles n'ont pas les mêmes avis")
    ids = sorted(a)
    if not ids:
        return None
    sa, sb = stat([a[i] for i in ids]), stat([b[i] for i in ids])
    if sa is None or sb is None:
        return None
    rng = random.Random(seed)  # noqa: S311
    diffs = []
    for _ in range(n_boot):
        draw = [ids[rng.randrange(len(ids))] for _ in ids]
        va, vb = stat([a[i] for i in draw]), stat([b[i] for i in draw])
        if va is not None and vb is not None:
            diffs.append(va - vb)
    if not diffs:
        return None
    diffs.sort()
    lo = diffs[int(len(diffs) * alpha / 2)]
    hi = diffs[min(len(diffs) - 1, int(len(diffs) * (1 - alpha / 2)))]
    return sa - sb, lo, hi


def excludes_zero(ci: tuple[float, float, float] | None) -> bool:
    return ci is not None and (ci[1] > 0 or ci[2] < 0)


def _stat(rows, field, *, ci=True):
    n = sum(r["res"][field].applicable for r in rows)
    mean = field_mean(rows, field)
    return {
        "mean": mean,
        "n": n,
        "ci": bootstrap_ci(rows, lambda rs: field_mean(rs, field)) if ci and n else None,
    }


def summarize(rows: list[dict], *, ci: bool = False) -> dict:
    inv = {}
    for f in m.FIELDS:
        absent = [r for r in rows if not r["res"][f].applicable]
        inv[f] = {"inventes": sum(r["res"][f].invented for r in absent), "absents": len(absent)}
    return {
        "n": len(rows),
        "parse_errors": sum(1 for r in rows if r["error"]),
        "hard": {f: _stat(rows, f, ci=ci) for f in m.HARD_FIELDS},
        "easy": {f: _stat(rows, f, ci=ci) for f in m.EASY_FIELDS},
        "hard_global": {
            "mean": hard_global(rows),
            "ci": bootstrap_ci(rows, hard_global) if ci else None,
        },
        "easy_global": {"mean": easy_global(rows)},
        "invented": inv,
        "by_famille": {
            fam: {"n": len(sub), "hard_global": hard_global(sub)}
            for fam in sorted({r["famille"] for r in rows})
            for sub in [[r for r in rows if r["famille"] == fam]]
        },
    }


def verdict(a: str, ci_a, b: str, ci_b) -> str:
    """Aucune conclusion d'écart si les intervalles de confiance se recouvrent."""
    if ci_a is None or ci_b is None:
        return f"{a} / {b} : intervalle indisponible, pas de conclusion"
    if ci_a[0] <= ci_b[1] and ci_b[0] <= ci_a[1]:
        return f"{a} / {b} : indistinguable (IC qui se recouvrent)"
    return f"{a} > {b}" if ci_a[0] > ci_b[1] else f"{b} > {a}"
