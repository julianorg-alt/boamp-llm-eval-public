"""Contrôles d'intégrité du jeu figé versionné (hors réseau)."""

import hashlib
import json
from pathlib import Path

from boamp_eval.build import assert_no_pii
from boamp_eval.extract import FIELDS

DATA = Path(__file__).resolve().parent.parent / "data"


def load(name):
    return [
        json.loads(x) for x in (DATA / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def test_hashes_match_manifest():
    m = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    for name, sha in m["sha256"].items():
        assert hashlib.sha256((DATA / f"{name}.jsonl").read_bytes()).hexdigest() == sha, name


def test_counts_and_disjoint_splits():
    m = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    dev, hold = load("dev"), load("holdout")
    assert len(dev) + len(hold) == m["n_avis"] == 100
    assert len(hold) == m["par_split"]["holdout"] == 20
    assert not {r["idweb"] for r in dev} & {r["idweb"] for r in hold}
    assert {r["famille"] for r in dev + hold} == {"JOUE", "FNS", "MAPA"}


def test_schema_and_no_pii():
    recs = load("dev") + load("holdout")
    for r in recs:
        assert set(r["verite"]) <= set(FIELDS)
        assert r["verite"]["acheteur"] and r["verite"]["objet"] and r["texte"]
        assert "cbc:" not in r["texte"] and "FNSimple" not in r["texte"]
    assert_no_pii(recs)


def test_licence_and_provenance_in_manifest():
    m = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    assert m["licence"]["nom"].startswith("Licence Ouverte")
    assert m["seed"] and m["date_extraction"] and m["requete"]["where"]
