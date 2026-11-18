"""Construction du jeu figé : sélection stratifiée, rendu texte, masquage, JSONL + manifeste.

Usage : uv run python -m boamp_eval.build [--seed N] [--out data]
"""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from boamp_eval.client import BASE_URL, BoampClient
from boamp_eval.extract import FIELDS, contact_names, extract_truth, org_words
from boamp_eval.pii import EMAIL_RE, PHONE_RE, Masker
from boamp_eval.render import render_text
from boamp_eval.sample import split_holdout, stratified_pick, weekly_windows

SEED = 20261118
WINDOW = ("2026-09-01", "2026-11-15")
QUOTAS = {"JOUE": 40, "FNS": 35, "MAPA": 25}
OVERSAMPLE = 4  # candidats récupérés par place à pourvoir
BASE_WHERE = "nature_categorise='appeloffre/standard' AND etat='INITIAL'"
LICENCE = {
    "nom": "Licence Ouverte / Open Licence (Etalab, fr-lo)",
    "url": "https://www.etalab.gouv.fr/wp-content/uploads/2017/04/ETALAB-Licence-Ouverte-v2.0.pdf",
    "source": "https://www.data.gouv.fr/datasets/boamp (métadonnée data.gouv.fr, id 559390f9c751df0139a453ba)",
    "mention": "Source : BOAMP, DILA (Premier ministre), Licence Ouverte 2.0, données interrogées le 2026-11-18.",
}


class PiiLeakError(RuntimeError):
    pass


def type_marche(row: dict) -> str:
    v = row.get("type_marche_facette")
    if isinstance(v, list):
        v = "+".join(sorted(str(x) for x in v))
    return v or "inconnu"


def build_record(row: dict) -> dict | None:
    famille = row["famille"]
    try:
        donnees = json.loads(row["donnees"])
    except (TypeError, ValueError):
        return None
    truth = extract_truth(famille, donnees)
    if not truth.get("acheteur") or not truth.get("objet"):
        return None
    masker = Masker(contact_names(famille, donnees), keep=org_words(famille, donnees))
    truth = masker.mask_obj(truth)
    strate = f"{type_marche(row)}|{'avec' if 'lots' in truth else 'sans'}_lots"
    return {
        "idweb": row["idweb"],
        "famille": famille,
        "type_marche": type_marche(row),
        "strate": strate,
        "date_parution": row.get("dateparution"),
        "url_avis": row.get("url_avis"),
        "texte": render_text(famille, donnees, masker),
        "verite": truth,
    }


def assert_no_pii(records: list[dict]) -> None:
    for r in records:
        blob = json.dumps({"texte": r.get("texte"), "verite": r.get("verite")}, ensure_ascii=False)
        leaks = EMAIL_RE.findall(blob) + PHONE_RE.findall(blob)
        if leaks:
            raise PiiLeakError(f"{r.get('idweb')}: {len(leaks)} fuite(s) détectée(s)")


def coverage(records: list[dict]) -> dict:
    out: dict = {}
    for r in records:
        c = out.setdefault(r["famille"], {"n": 0, "champs": dict.fromkeys(FIELDS, 0)})
        c["n"] += 1
        for f in FIELDS:
            if f in r["verite"]:
                c["champs"][f] += 1
    return out


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def list_pool(client: BoampClient, famille: str) -> list[dict]:
    pool: dict[str, dict] = {}
    for a, b in weekly_windows(*WINDOW):
        where = (
            f"{BASE_WHERE} AND famille='{famille}' AND dateparution>='{a}' AND dateparution<='{b}'"
        )
        offset = 0
        while True:
            page = client.records(
                where=where,
                select="idweb,type_marche_facette",
                limit=100,
                offset=offset,
                order_by="idweb",
            )
            for r in page["results"]:
                pool[r["idweb"]] = r
            offset += 100
            if offset >= page["total_count"] or offset >= 10000:
                break
    return sorted(pool.values(), key=lambda r: r["idweb"])


def fetch_rows(client: BoampClient, ids: list[str]) -> list[dict]:
    rows = []
    for i in range(0, len(ids), 20):
        chunk = sorted(ids[i : i + 20])
        quoted = ",".join(f"'{x}'" for x in chunk)
        page = client.records(
            where=f"idweb in ({quoted})",
            select="idweb,famille,type_marche_facette,dateparution,url_avis,donnees",
            limit=100,
            order_by="idweb",
        )
        rows.extend(page["results"])
    return rows


def main(seed: int = SEED, out_dir: str = "data", cache: str = "data/raw") -> None:
    client = BoampClient(cache_dir=cache)
    selected: list[dict] = []
    pool_sizes: dict[str, int] = {}
    for famille, quota in QUOTAS.items():
        pool = list_pool(client, famille)
        pool_sizes[famille] = len(pool)
        shuffled = stratified_pick(
            [{"idweb": r["idweb"], "strate": type_marche(r)} for r in pool],
            quota * OVERSAMPLE,
            seed,
        )
        rows = fetch_rows(client, [c["idweb"] for c in shuffled])
        recs = [r for r in (build_record(x) for x in rows) if r]
        selected += stratified_pick(recs, quota, seed)
    selected.sort(key=lambda r: r["idweb"])
    assert_no_pii(selected)

    hold = split_holdout(selected, seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {"dev": out / "dev.jsonl", "holdout": out / "holdout.jsonl"}
    for name, path in files.items():
        lines = [
            json.dumps(r, ensure_ascii=False, sort_keys=True)
            for r in selected
            if (r["idweb"] in hold) == (name == "holdout")
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "version": 1,
        "date_extraction": datetime.now(UTC).strftime("%Y-%m-%d"),
        "source": BASE_URL,
        "requete": {
            "where": f"{BASE_WHERE} AND famille='<JOUE|FNS|MAPA>' AND dateparution entre {WINDOW[0]} et {WINDOW[1]}",
            "fenetre_dates": list(WINDOW),
            "taille_pool": pool_sizes,
        },
        "seed": seed,
        "quotas": QUOTAS,
        "methode": "tourniquet sur strates type_marche x (avec|sans lots), tri par sha256(seed:idweb)",
        "holdout": {"fraction": 0.2, "par": "famille", "regle": "sha256(seed:idweb), arrondi"},
        "licence": LICENCE,
        "n_avis": len(selected),
        "par_famille": {f: sum(r["famille"] == f for r in selected) for f in QUOTAS},
        "par_split": {"dev": len(selected) - len(hold), "holdout": len(hold)},
        "par_strate": {
            s: sum(r["strate"] == s for r in selected)
            for s in sorted({r["strate"] for r in selected})
        },
        "couverture_par_famille": coverage(selected),
        "sha256": {name: _sha256(p) for name, p in files.items()},
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: manifest[k] for k in ("n_avis", "par_famille", "par_split")}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default="data")
    args = ap.parse_args()
    main(args.seed, args.out)
