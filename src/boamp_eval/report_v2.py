"""Rapport v2 (reports/results-v2.md) : généré par le code depuis data/runs/, aucun chiffre saisi.

Protocole : docs/FREEZE-v2.md. Métrique principale `hard_global`, trois différences appariées
(Opus-Haiku, Opus-Sonnet, Sonnet-Haiku), IC à 98,33 % (Bonferroni, 3 comparaisons) ; un écart est
établi si cet IC exclut 0. Les analyses par champ et par famille sont secondaires.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from boamp_eval import metrics as m
from boamp_eval import report
from boamp_eval.report_md import MODELS, _f, _ic, load_run

OUT = Path("reports/results-v2.md")
FREEZE_V2 = Path("docs/FREEZE-v2.md")
PAIRS = (("claude-opus-5-5", "claude-haiku-5-5"), ("claude-opus-5-5", "claude-sonnet-5-5"),
         ("claude-sonnet-5-5", "claude-haiku-5-5"))  # fmt: skip
N_BOOT_V2 = 10_000
ALPHA_V2 = 0.05 / 3  # IC à 98,33 % : Bonferroni sur 3 comparaisons
SEED_V1 = 20261118  # graine et réglages de l'analyse appariée v1 faite après coup
N_BOOT_V1 = 2000
SHORT = {"claude-haiku-5-5": "Haiku", "claude-sonnet-5-5": "Sonnet", "claude-opus-5-5": "Opus"}


def decide(a: str, b: str, ci: tuple[float, float, float] | None) -> str:
    """Verdict de règle : écart établi si l'IC de la différence exclut 0."""
    if ci is None:
        return "indisponible"
    if not report.excludes_zero(ci):
        return "non établi (l'IC contient 0)"
    return f"établi : {SHORT[a] if ci[0] > 0 else SHORT[b]} > {SHORT[b] if ci[0] > 0 else SHORT[a]}"


def _d(ci) -> str:
    return "n/a" if ci is None else f"{ci[0]:+.3f} [{ci[1]:+.3f} ; {ci[2]:+.3f}]"


def truncations(rows: list[dict]) -> int:
    return sum(1 for r in rows if r["error"] == "stop_reason=max_tokens")


def freeze_commit() -> str:
    out = subprocess.run(["git", "log", "-1", "--format=%H", "--", str(FREEZE_V2)],  # noqa: S603, S607
                         capture_output=True, text=True, check=False)  # fmt: skip
    return out.stdout.strip() or "inconnu"


def paired_table(st: dict, *, n_boot: int, alpha: float, seed: int, stat=report.hard_global):
    return {
        (a, b): report.paired_diff_ci(
            st[a]["eval"], st[b]["eval"], stat, n_boot=n_boot, alpha=alpha, seed=seed
        )  # fmt: skip
        for a, b in PAIRS
    }


def build_v2(records: list[dict], runs: dict[str, Path]) -> str:
    st = {mo: load_run(records, mo, p) for mo, p in runs.items()}
    models = [mo for mo in MODELS if mo in st]
    n = len(records)
    n_crit = sum("criteres" in r["verite"] for r in records)
    o = ["# Résultats v2 : extraction de champs d'avis BOAMP par Claude (2026-11)\n"]
    o.append("## Protocole\n")
    o.append(
        f"- Gel : `docs/FREEZE-v2.md`, commit `{freeze_commit()}`, posé avant tout appel sur le jeu de test.\n"
        f"- Jeu de test : {n} avis nouveaux, publiés à partir du 2026-11-16 ({', '.join(f'{f} {sum(r["famille"] == f for r in records)}' for f in ('JOUE', 'FNS', 'MAPA'))}), "
        f"dont {n_crit} avec des critères d'attribution notés. Le lot de mise au point (30 avis) est exclu de ce rapport.\n"
        "- Prompt et schéma identiques à la v1 ; rendu corrigé (plus de suffixe de type après le libellé des critères). "
        "Effort `low`, `max_tokens` 8192, Message Batches API (tarif -50 %).\n"
        "- Métrique principale : `hard_global` (moyenne par champ des champs durs applicables). "
        f"Bootstrap sur les avis ({N_BOOT_V2} tirages, graine {report.SEED}).\n"
        "- Règle de décision : un écart est établi si l'IC à 98,33 % de la différence appariée "
        "exclut 0 (Bonferroni, 3 comparaisons). Les analyses par champ et par famille sont secondaires.\n"
    )
    o.append("## Score dur global (IC 95 %)\n")
    o.append("| Modèle | n | `hard_global` [IC 95 %] |\n|---|---|---|")
    for mo in models:
        g = st[mo]["summary"]["hard_global"]
        o.append(f"| {mo} | {n} | {_ic(g['mean'], g['ci'])} |")
    o.append("\n## Différences appariées (analyse principale)\n")
    o.append("Même rééchantillonnage d'avis pour les deux modèles ; IC à 98,33 %.\n")
    o.append("| Différence | Écart [IC 98,33 %] | Verdict |\n|---|---|---|")
    pt = (
        paired_table(st, n_boot=N_BOOT_V2, alpha=ALPHA_V2, seed=report.SEED)
        if len(models) == 3
        else {}
    )
    for (a, b), ci in pt.items():
        o.append(f"| {SHORT[a]} - {SHORT[b]} | {_d(ci)} | {decide(a, b, ci)} |")
    o.append("\n## Analyses secondaires (déclarées secondaires dans le gel)\n")
    o.append("### Par champ dur (moyenne [IC 95 %])\n")
    o.append("| Champ | n | " + " | ".join(models) + " |\n|---|---|" + "---|" * len(models))
    for f in m.HARD_FIELDS:
        n_f = st[models[0]]["summary"]["hard"][f]["n"]
        cells = [_ic(st[mo]["summary"]["hard"][f]["mean"], st[mo]["summary"]["hard"][f]["ci"])
                 for mo in models]  # fmt: skip
        o.append(f"| {f} | {n_f} | " + " | ".join(cells) + " |")
    o.append("\n### Par famille (`hard_global` [IC 95 %])\n")
    o.append("| Famille | n | " + " | ".join(models) + " |\n|---|---|" + "---|" * len(models))
    for fam in ("JOUE", "FNS", "MAPA"):
        cells = []
        for mo in models:
            sub = [r for r in st[mo]["eval"] if r["famille"] == fam]
            cells.append(_ic(report.hard_global(sub), report.bootstrap_ci(sub, report.hard_global)))
        o.append(
            f"| {fam} | {sum(r['famille'] == fam for r in records)} | " + " | ".join(cells) + " |"
        )
    o.append("\n### Différences appariées par champ (IC 98,33 %, secondaire)\n")
    o.append(
        "| Champ | "
        + " | ".join(f"{SHORT[a]} - {SHORT[b]}" for a, b in PAIRS)
        + " |\n|---|---|---|---|"
    )
    for f in m.HARD_FIELDS:
        cells = [_d(report.paired_diff_ci(st[a]["eval"], st[b]["eval"],
                                          lambda rs, f=f: report.field_mean(rs, f),
                                          n_boot=N_BOOT_V2, alpha=ALPHA_V2, seed=report.SEED))
                 for a, b in PAIRS]  # fmt: skip
        o.append(f"| {f} | " + " | ".join(cells) + " |")
    o.append("\n## Troncatures, réponses inexploitables, valeurs inventées\n")
    o.append(
        "| Modèle | Tronqués (`max_tokens` 8192) | Inexploitables (total) | Inventés (tous champs) |\n|---|---|---|---|"
    )
    for mo in models:
        sm = st[mo]["summary"]
        inv = sum(v["inventes"] for v in sm["invented"].values())
        o.append(f"| {mo} | {truncations(st[mo]['rows'])} | {sm['parse_errors']} | {inv} |")
    o.append("\n## Coût\n")
    o.append("Recalculé depuis `usage` au tarif lot (`docs/sources.md`).\n")
    o.append(
        "| Modèle | Coût $ | $ par avis | Tokens entrée / sortie / cache lu | Latence de lot (s) |\n|---|---|---|---|---|"
    )
    for mo in models:
        r = st[mo]
        t = r["tokens"]
        o.append(f"| {mo} | {r['cost_usd']:.4f} | {r['cost_per_avis']:.5f} | "
                 f"{t['input_tokens']} / {t['output_tokens']} / {t['cache_read_tokens']} | {_f(r['latency_s'], 0)} |")  # fmt: skip
    o.append(f"\nTotal des trois lots : {sum(st[mo]['cost_usd'] for mo in models):.4f} $.\n")
    return "\n".join(o)


def build_v1_paired() -> str:
    """Section v1 : comparaison appariée faite après coup (graine 20261118, 2000 tirages, IC 95 %)."""
    o = ["## v1 : analyse appariée faite après coup\n"]
    o.append(
        "Calculée après la lecture des résultats v1, hors protocole : ce n'est pas une analyse "
        f"planifiée. Même rééchantillonnage d'avis pour les deux modèles, graine {SEED_V1}, "
        f"{N_BOOT_V1} tirages, IC à 95 %, score `hard_global`, effort `low`, `max_tokens` 4096. "
        "Rendu v1 (avec le suffixe de type sur les critères).\n"
    )
    o.append("| Jeu | Avis | Différence | Écart [IC 95 %] |\n|---|---|---|---|")
    for split in ("dev", "holdout"):
        recs = [json.loads(x) for x in Path(f"data/{split}.jsonl").read_text().splitlines()]
        runs = {mo: Path(f"data/runs/e3-{split}-{mo.split('-')[1]}") for mo in MODELS}
        st = {mo: load_run(recs, mo, p) for mo, p in runs.items()}
        pt = paired_table(st, n_boot=N_BOOT_V1, alpha=report.ALPHA, seed=SEED_V1)
        for (a, b), ci in pt.items():
            o.append(f"| {split} | {len(recs)} | {SHORT[a]} - {SHORT[b]} | {_d(ci)} |")
    o.append("")
    return "\n".join(o)


def limits() -> str:
    return (
        "## Limites\n\n"
        "- Entrée reconstruite : rendu texte généré depuis le JSON structuré, pas l'avis publié ; la vérité vient des mêmes champs (circularité, voir v1).\n"
        "- Échantillon d'une seule période (avis publiés du 2026-11-16 au 2026-11-24), quotas par famille choisis (40/35/25), non représentatif de toute la commande publique.\n"
        "- Un seul passage par modèle, effort `low` : les efforts par défaut ne sont pas comparés ici.\n"
        "- Les analyses par champ et par famille sont secondaires : les IC ne sont pas corrigés pour comparaisons multiples au-delà de ce qui est indiqué.\n"
        "- Un écart « établi » vaut pour ce jeu, ce rendu et ce prompt, et pour la métrique `hard_global` ; il ne dit pas que le modèle est meilleur dans toute situation.\n"
    )


def main() -> None:
    recs = [json.loads(x) for x in Path("data/v2-test.jsonl").read_text().splitlines()]
    runs = {mo: Path(f"data/runs/v2-test-{mo.split('-')[1]}") for mo in MODELS}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(build_v2(recs, runs) + "\n" + build_v1_paired() + "\n" + limits())
    print(f"écrit {OUT}")


if __name__ == "__main__":
    main()
