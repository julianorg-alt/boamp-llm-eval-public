"""Rapport Markdown des résultats : relit les lignes brutes de lot et les méta versionnées.

Aucun chiffre n'est saisi à la main : scores, IC, coûts (recalculés depuis `usage` au tarif lot),
latences (méta de lot) sortent de `data/runs/`. Un texte de lecture facultatif (`reports/lecture.md`)
est ajouté tel quel.
"""

from __future__ import annotations

import json
from pathlib import Path

from boamp_eval import batch, report
from boamp_eval import metrics as m
from boamp_eval.costs import CostLedger, Usage, cost_usd

MODELS = ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5")
OUT = Path("reports/results-2026-11.md")
LECTURE = Path("reports/lecture.md")


def load_run(records: list[dict], model: str, base: Path) -> dict:
    base = Path(base)
    meta = json.loads(base.with_suffix(".meta.json").read_text())
    scratch = CostLedger(Path("/nonexistent/ledger.json"))
    rows = batch.collect(
        batch.RecordedBatch(base.with_suffix(".jsonl")), "replay", model, records, scratch,
        label="rapport", out_path=None, record_costs=False,
    )  # fmt: skip
    cost = sum(cost_usd(model, Usage(**r["usage"]), batch=True) for r in rows)
    ev = report.evaluate(records, rows)
    return {
        "rows": rows,
        "eval": ev,
        "summary": report.summarize(ev, ci=True),
        "cost_usd": cost,
        "cost_per_avis": cost / len(records),
        "latency_s": meta.get("latency_s"),
        "tokens": {
            k: sum(r["usage"][k] for r in rows)
            for k in ("input_tokens", "output_tokens", "cache_read_tokens")
        },
    }


def _f(x, nd=3):
    return "n/a" if x is None else f"{x:.{nd}f}"


def _ic(mean, ci):
    return f"{_f(mean)} [{_f(ci[0])} ; {_f(ci[1])}]" if ci else f"{_f(mean)} [IC n/a]"


def build(records: dict[str, list[dict]], runs: dict[tuple[str, str], Path]) -> str:
    st = {k: load_run(records[k[0]], k[1], p) for k, p in runs.items()}
    splits = [s for s in ("dev", "holdout") if s in records]
    models = [mo for mo in MODELS if any((s, mo) in st for s in splits)]
    o = ["# Résultats : extraction de champs d'avis BOAMP par Claude (2026-11)\n"]
    o.append("## Protocole\n")
    o.append(
        "- Un seul prompt et un seul schéma de sortie pour les trois modèles (`docs/FREEZE.md`), "
        "effort `low` pour les trois (choix de protocole : extraction, comparaison équitable ; "
        "les efforts par défaut diffèrent), `max_tokens` 4096, Message Batches API (tarif -50 %).\n"
        "- Jeu : " + ", ".join(f"{s} = {len(records[s])} avis" for s in splits) + ". "
        "Le hold-out n'a été passé qu'une fois, après gel du prompt et des métriques.\n"
        "- Score dur = moyenne par champ des champs durs applicables (date limite, montant, "
        "critères, CPV, lieu). IC 95 % : bootstrap sur les avis (`docs/METRICS.md`).\n"
    )
    o.append("## Score dur (IC 95 %)\n")
    o.append("| Modèle | " + " | ".join(splits) + " |\n|---|" + "---|" * len(splits))
    for mo in models:
        cells = []
        for s in splits:
            g = st[(s, mo)]["summary"]["hard_global"] if (s, mo) in st else None
            cells.append(_ic(g["mean"], g["ci"]) if g else "n/a")
        o.append(f"| {mo} | " + " | ".join(cells) + " |")
    o.append("")
    for s in splits:
        for i, a in enumerate(models):
            for b in models[i + 1 :]:
                if (s, a) in st and (s, b) in st:
                    ga, gb = (st[(s, x)]["summary"]["hard_global"] for x in (a, b))
                    o.append(f"- {s} : {report.verdict(a, ga['ci'], b, gb['ci'])}")
    o.append("\n## Par champ (champs durs)\n")
    for s in splits:
        o.append(f"### {s}\n")
        o.append("| Champ | n | " + " | ".join(models) + " |\n|---|---|" + "---|" * len(models))
        for f in m.HARD_FIELDS:
            n = next(st[(s, mo)]["summary"]["hard"][f]["n"] for mo in models if (s, mo) in st)
            cells = [
                _ic(h["mean"], h["ci"])
                for mo in models
                if (s, mo) in st
                for h in [st[(s, mo)]["summary"]["hard"][f]]
            ]
            o.append(f"| {f} | {n} | " + " | ".join(cells) + " |")
        o.append("")
    o.append("## Par famille (score dur global)\n")
    for s in splits:
        o.append(f"### {s}\n")
        o.append("| Famille | n | " + " | ".join(models) + " |\n|---|---|" + "---|" * len(models))
        fams = sorted({r["famille"] for r in records[s]})
        for fam in fams:
            cells = []
            for mo in models:
                if (s, mo) not in st:
                    continue
                sub = [r for r in st[(s, mo)]["eval"] if r["famille"] == fam]
                mean = report.hard_global(sub)
                cells.append(_ic(mean, report.bootstrap_ci(sub, report.hard_global)))
            o.append(
                f"| {fam} | {sum(r['famille'] == fam for r in records[s])} | "
                + " | ".join(cells)
                + " |"
            )
        o.append("")
    o.append("## Compteur « inventé »\n")
    o.append(
        "Valeur fournie alors que la vérité est absente ET introuvable dans le texte (`docs/METRICS.md`).\n"
    )
    o.append(
        "| Split | Modèle | Inventés (tous champs) | Réponses inexploitables |\n|---|---|---|---|"
    )
    for s in splits:
        for mo in models:
            if (s, mo) in st:
                sm = st[(s, mo)]["summary"]
                tot = sum(v["inventes"] for v in sm["invented"].values())
                par = ", ".join(
                    f"{f} {v['inventes']}" for f, v in sm["invented"].items() if v["inventes"]
                )
                o.append(
                    f"| {s} | {mo} | {tot}{' (' + par + ')' if par else ''} | {sm['parse_errors']} |"
                )
    o.append("\n## Coût réel et latence de lot\n")
    o.append(
        "Coût recalculé depuis `usage` des réponses au tarif lot (`docs/sources.md`) ; le registre `data/costs-ledger.json` porte les mêmes montants.\n"
    )
    o.append(
        "| Split | Modèle | Coût $ | $ par avis | Tokens entrée / sortie / cache lu | Latence de lot (s) |\n|---|---|---|---|---|---|"
    )
    for s in splits:
        for mo in models:
            if (s, mo) in st:
                r = st[(s, mo)]
                t = r["tokens"]
                o.append(
                    f"| {s} | {mo} | {r['cost_usd']:.4f} | {r['cost_per_avis']:.5f} | "
                    f"{t['input_tokens']} / {t['output_tokens']} / {t['cache_read_tokens']} | {_f(r['latency_s'], 0)} |"
                )
    tot = sum(r["cost_usd"] for r in st.values())
    o.append(f"\nTotal des passages ci-dessus : {tot:.4f} $.\n")
    o.append("## Annexe : champs faciles (entrée générée depuis la vérité : recopie)\n")
    for s in splits:
        o.append(f"### {s}\n")
        o.append("| Champ | " + " | ".join(models) + " |\n|---|" + "---|" * len(models))
        for f in m.EASY_FIELDS:
            cells = [
                _f(st[(s, mo)]["summary"]["easy"][f]["mean"]) for mo in models if (s, mo) in st
            ]
            o.append(f"| {f} | " + " | ".join(cells) + " |")
        o.append("")
    o.append("## Limites\n")
    o.append(
        "- Entrée reconstruite : rendu texte généré depuis le JSON structuré (le texte officiel n'est pas disponible), pas l'avis publié.\n"
        "- Circularité : la vérité vient des mêmes champs structurés que le rendu ; l'objet, l'acheteur et les titres de lots sont recopiables (champs faciles, en annexe). Le score mesure la lecture d'un rendu, pas celle d'un avis réel.\n"
        "- Échantillon d'automne : 100 avis (2026-09-01 à 2026-11-15), quotas par famille choisis (40/35/25), non représentatifs de toute la commande publique.\n"
        "- Hold-out de 20 avis (JOUE 8, FNS 7, MAPA 5) : IC larges, aucune conclusion par famille.\n"
        "- Effort `low` fixé pour les trois modèles ; le passage à l'effort par défaut (Sonnet, Opus, dev seulement) est présenté à part.\n"
        "- Vérité FNS et MAPA : des montants ou critères présents en texte libre n'y figurent pas (champ non applicable, exclu).\n"
        "- Les IC se recouvrent souvent : sans écart d'IC, aucune supériorité n'est affirmée.\n"
    )
    if LECTURE.exists():
        o.append("## Lecture\n\n" + LECTURE.read_text().strip() + "\n")
    return "\n".join(o)


DEFAULT_EFFORT_NAMES = {"claude-sonnet-5-5": "e4-dev-sonnet-default",
                        "claude-opus-5-5": "e4-dev-opus-default"}  # fmt: skip


def build_default_effort(dev: list[dict], low: dict[str, Path], default: dict[str, Path]) -> str:
    """Section à part : effort par défaut (jeu de dev seulement), face à l'effort `low` gelé."""
    o = ["## Passage complémentaire : effort par défaut (dev seulement)\n"]
    o.append(
        "Sonnet 5.5 à l'effort par défaut `high`, Opus 5.5 à `medium` (`docs/sources.md`), même "
        "prompt gelé, même schéma, `max_tokens` 4096, lot, 80 avis du dev. Haiku n'est pas "
        "repassé. Passage fait après la lecture des résultats `low` : il ne remplace pas le "
        "protocole principal.\n"
    )
    o.append(
        "| Modèle | effort | score dur | `criteres` | inexploitables | $ | $ par avis | "
        "tokens sortie | latence (s) |\n|---|---|---|---|---|---|---|---|---|"
    )
    for mo, dpath in default.items():
        for label, path in (("low", low[mo]), ("défaut", dpath)):
            r = load_run(dev, mo, path)
            sm = r["summary"]
            g, c = sm["hard_global"], sm["hard"]["criteres"]
            o.append(
                f"| {mo} | {label} | {_ic(g['mean'], g['ci'])} | {_ic(c['mean'], c['ci'])} | "
                f"{sm['parse_errors']} | {r['cost_usd']:.4f} | {r['cost_per_avis']:.5f} | "
                f"{r['tokens']['output_tokens']} | {_f(r['latency_s'], 0)} |"
            )
    o.append("")
    return "\n".join(o)


def main() -> None:
    records = {
        s: [json.loads(x) for x in Path(f"data/{s}.jsonl").read_text().splitlines()]
        for s in ("dev", "holdout")
        if any(Path(f"data/runs/e3-{s}-{mo.split('-')[1]}.jsonl").exists() for mo in MODELS)
    }
    runs = {
        (s, mo): Path(f"data/runs/e3-{s}-{mo.split('-')[1]}")
        for s in records
        for mo in MODELS
        if Path(f"data/runs/e3-{s}-{mo.split('-')[1]}.jsonl").exists()
    }
    OUT.parent.mkdir(exist_ok=True)
    text = build(records, runs)
    dflt = {mo: Path(f"data/runs/{n}") for mo, n in DEFAULT_EFFORT_NAMES.items()}
    if all(p.with_suffix(".jsonl").exists() for p in dflt.values()):
        low = {mo: Path(f"data/runs/e3-dev-{mo.split('-')[1]}") for mo in dflt}
        sec = build_default_effort(records["dev"], low, dflt)
        text = text.replace("## Annexe : champs faciles", sec + "\n## Annexe : champs faciles", 1)
    OUT.write_text(text)
    print(f"écrit {OUT}")


if __name__ == "__main__":
    main()
