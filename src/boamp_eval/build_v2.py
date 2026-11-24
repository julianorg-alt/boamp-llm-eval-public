"""Échantillon v2 : avis NOUVEAUX (publiés après le 2026-11-15), jeu de test + lot de mise au point.

Même pipeline que la v1 (build : récupération, rendu, masquage PII ; sample : tirage stratifié).
Le lot de mise au point (30 avis) est disjoint du jeu de test et exclu de tous les résultats.

Usage : uv run python -m boamp_eval.build_v2 [--end 2026-11-24]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from boamp_eval import build
from boamp_eval.client import BASE_URL, BoampClient
from boamp_eval.sample import stratified_pick, weekly_windows

SEED = 20261124
START = "2026-11-16"  # strictement après le 15/11/2026 : la fenêtre v1 s'arrête au 2026-11-15
TEST_QUOTAS = {"JOUE": 200, "FNS": 175, "MAPA": 125}  # 40 / 35 / 25 % de 500
TUNING_QUOTAS = {"JOUE": 12, "FNS": 10, "MAPA": 8}
OVERSAMPLE = 3
MIN_CRITERES = 100


def n_criteres(records: list[dict]) -> int:
    return sum("criteres" in r["verite"] for r in records)


def _pool(client: BoampClient, famille: str, end: str) -> list[dict]:
    pool: dict[str, dict] = {}
    for a, b in weekly_windows(START, end):
        where = (f"{build.BASE_WHERE} AND famille='{famille}' "
                 f"AND dateparution>='{a}' AND dateparution<='{b}'")  # fmt: skip
        offset = 0
        while True:
            page = client.records(where=where, select="idweb,type_marche_facette",
                                  limit=100, offset=offset, order_by="idweb")  # fmt: skip
            pool.update({r["idweb"]: r for r in page["results"]})
            offset += 100
            if offset >= page["total_count"] or offset >= 10000:
                break
    return sorted(pool.values(), key=lambda r: r["idweb"])


def pick_sets(by_fam: dict[str, list[dict]], test_q: dict[str, int], tune_q: dict[str, int],
              seed: int) -> tuple[list[dict], list[dict]]:  # fmt: skip
    """Mise au point d'abord, puis test sur le reste ; une famille courte donne tout ce qu'elle a."""
    tuning, test = [], []
    for fam, recs in by_fam.items():
        t = stratified_pick(recs, tune_q[fam], seed)
        ids = {r["idweb"] for r in t}
        tuning += t
        test += stratified_pick([r for r in recs if r["idweb"] not in ids], test_q[fam], seed)
    return sorted(tuning, key=lambda r: r["idweb"]), sorted(test, key=lambda r: r["idweb"])


def _write(path: Path, records: list[dict]) -> str:
    lines = [json.dumps(r, ensure_ascii=False, sort_keys=True) for r in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(end: str, out_dir: str = "data", cache: str = "data/raw",
         test_q: dict[str, int] | None = None) -> None:  # fmt: skip
    test_q = test_q or TEST_QUOTAS
    client = BoampClient(cache_dir=cache)
    by_fam: dict[str, list[dict]] = {}
    pool_sizes: dict[str, int] = {}
    for fam in test_q:
        pool = _pool(client, fam, end)
        pool_sizes[fam] = len(pool)
        need = (test_q[fam] + TUNING_QUOTAS[fam]) * OVERSAMPLE
        cand = stratified_pick([{"idweb": r["idweb"], "strate": build.type_marche(r)}
                                for r in pool], need, SEED)  # fmt: skip
        rows = build.fetch_rows(client, [c["idweb"] for c in cand])
        by_fam[fam] = [r for r in (build.build_record(x) for x in rows) if r]
    tuning, test = pick_sets(by_fam, test_q, TUNING_QUOTAS, SEED)
    build.assert_no_pii(tuning + test)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sha = {"v2-test": _write(out / "v2-test.jsonl", test),
           "v2-tuning": _write(out / "v2-tuning.jsonl", tuning)}  # fmt: skip
    manifest = {
        "version": 2,
        "date_extraction": datetime.now(UTC).strftime("%Y-%m-%d"),
        "source": BASE_URL,
        "requete": {
            "where": f"{build.BASE_WHERE} AND famille='<JOUE|FNS|MAPA>' "
            f"AND dateparution entre {START} et {end}",
            "fenetre_dates": [START, end],
            "taille_pool": pool_sizes,
        },  # fmt: skip
        "seed": SEED,
        "quotas_test": test_q,
        "quotas_mise_au_point": TUNING_QUOTAS,
        "n_test": len(test),
        "n_mise_au_point": len(tuning),
        "par_famille_test": {f: sum(r["famille"] == f for r in test) for f in test_q},
        "n_criteres_test": n_criteres(test),
        "par_strate_test": {
            s: sum(r["strate"] == s for r in test) for s in sorted({r["strate"] for r in test})
        },  # fmt: skip
        "couverture_test": build.coverage(test),
        "licence": build.LICENCE,
        "sha256": sha,
    }
    (out / "manifest-v2.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: manifest[k]
                for k in ("n_test", "n_mise_au_point", "par_famille_test", "n_criteres_test")
            }
        )
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--end", default="2026-11-24")
    args = ap.parse_args()
    main(args.end)
