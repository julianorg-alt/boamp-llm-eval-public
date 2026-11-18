"""Analyse d'erreurs du champ `criteres` à partir des réponses enregistrées (aucun appel API).

Catégories par avis (score `criteres` < 1), dans cet ordre :
- `inexploitable` : réponse sans objet JSON (max_tokens, refus).
- `suffixe_type` : les libellés et les poids sont justes, mais le modèle a recopié le type
  « (qualité) », « (prix) », « (coût) » que le rendu de l'entrée ajoute après chaque libellé.
- `libelle_autre` : poids justes, libellés différents.
- `poids` : libellés justes, poids différents.
- `ensemble` : critères manquants ou en trop.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from boamp_eval import batch
from boamp_eval import metrics as m
from boamp_eval.costs import CostLedger

MODELS = ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5")
_TYPE_IN_TEXT = re.compile(r"\((?:qualit[ée]|prix|co[uû]t)\)", re.IGNORECASE)
_SUFFIX = re.compile(r"\s*\((?:qualit[ée]|prix|co[uû]t)\)\s*$", re.IGNORECASE)


def strip_suffix(items: list) -> list:
    return [
        {**x, "libelle": _SUFFIX.sub("", x.get("libelle", ""))} if isinstance(x, dict) else x
        for x in items
    ]


def categorize(truth: list, pred: list | None, error: str | None) -> str:
    if error is not None or pred is None:
        return "inexploitable"
    if m.score_criteres(truth, pred) == 1.0:
        return "ok"
    if m.score_criteres(truth, strip_suffix(pred)) == 1.0:
        return "suffixe_type"
    t, p = m._crit_items(truth), m._crit_items(strip_suffix(pred))
    if len(t) == len(p):
        if all(a[0] == b[0] for a, b in zip(sorted(t), sorted(p), strict=True)):
            return "poids"
        if sorted(x[1] or -1 for x in t) == sorted(x[1] or -1 for x in p):
            return "libelle_autre"
    return "ensemble"


def analyse(records: list[dict], rows: list[dict]) -> dict:
    cats: Counter = Counter()
    scores, scores_strip, cases = [], [], []
    for rec, row in zip(records, rows, strict=True):
        t = rec["verite"].get("criteres")
        if t is None:
            continue
        pred = (row["pred"] or {}).get("criteres") if row["pred"] is not None else None
        c = categorize(t, pred, row["error"])
        cats[c] += 1
        scores.append(m.score_criteres(t, pred))
        scores_strip.append(m.score_criteres(t, strip_suffix(pred or [])))
        if c not in ("ok", "suffixe_type"):
            cases.append((rec["idweb"], rec["famille"], c))
    n = len(scores)
    return {"n": n, "categories": dict(cats), "score": sum(scores) / n,
            "score_sans_suffixe": sum(scores_strip) / n, "cas": cases}  # fmt: skip


def load(split: str, name: str, model: str) -> tuple[list[dict], list[dict]]:
    recs = [json.loads(x) for x in Path(f"data/{split}.jsonl").read_text().splitlines()]
    rows = batch.collect(
        batch.RecordedBatch(Path(f"data/runs/{name}.jsonl")), "replay", model, recs,
        CostLedger(Path("/nonexistent/ledger.json")), label="erreurs", out_path=None,
        record_costs=False,
    )  # fmt: skip
    return recs, rows


def main() -> None:
    runs = {(mo, "low"): f"e3-dev-{mo.split('-')[1]}" for mo in MODELS}
    runs |= {
        (mo, "défaut"): f"e4-dev-{mo.split('-')[1]}-default"
        for mo in MODELS
        if Path(f"data/runs/e4-dev-{mo.split('-')[1]}-default.jsonl").exists()
    }
    o = ["# Analyse d'erreurs : champ `criteres` (jeu de dev)\n",
         "Source : réponses enregistrées dans `data/runs/e3-dev-*.jsonl` et `data/runs/e4-dev-*.jsonl`, rejouées sans appel API "
         "(`python -m boamp_eval.errors`). Avis où la vérité `criteres` existe : "
         "19 sur 80 (JOUE et MAPA). Le hold-out n'est pas relu.\n",
         "| Modèle | effort | n | score gelé | ok | suffixe de type | libellé autre | poids | "
         "ensemble | inexploitable | score si suffixe ignoré |", "|---|---|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
    detail = []
    dev = [json.loads(x) for x in Path("data/dev.jsonl").read_text().splitlines()]
    avec = [r for r in dev if "criteres" in r["verite"]]
    suf = [r for r in avec if _TYPE_IN_TEXT.search(r["texte"])]
    fams = Counter(r["famille"] for r in avec)
    o.insert(
        2,
        f"Répartition des {len(avec)} avis : {dict(fams)}. Le rendu de l'entrée ajoute le type "
        f"entre parenthèses après chaque libellé dans {len(suf)} d'entre eux "
        f"(familles : {dict(Counter(r['famille'] for r in suf))}), et dans aucun avis MAPA "
        "(type absent de la vérité). Le prompt gelé demande de recopier les valeurs « telles "
        "qu'elles sont écrites » ; la métrique exige un libellé égal.\n",
    )
    cas_max = next(r for r in dev if r["idweb"] == "26-108247")
    o.append(
        f"Avis 26-108247 : {len(cas_max['verite'].get('lots', []))} lots en vérité, texte de "
        f"{len(cas_max['texte'])} caractères. Les {len(runs)} passages s'arrêtent à "
        "`max_tokens` (4096) : la liste des lots dépasse la limite de sortie (voir "
        "`reports/results-2026-11.md`).\n"
    )
    for (mo, eff), name in runs.items():
        recs, rows = load("dev", name, mo)
        a = analyse(recs, rows)
        c = a["categories"]
        o.append(
            f"| {mo} | {eff} | {a['n']} | {a['score']:.3f} | {c.get('ok', 0)} | {c.get('suffixe_type', 0)} | "
            f"{c.get('libelle_autre', 0)} | {c.get('poids', 0)} | {c.get('ensemble', 0)} | "
            f"{c.get('inexploitable', 0)} | {a['score_sans_suffixe']:.3f} |"
        )
        detail += [f"- {mo} ({eff}) : {i} ({fam}) : {cat}" for i, fam, cat in a["cas"]]
    o += ["", "## Avis hors « ok » et hors « suffixe de type »\n", *detail, ""]
    Path("reports/analyse-erreurs.md").write_text("\n".join(o))
    print("\n".join(o))


if __name__ == "__main__":
    main()
