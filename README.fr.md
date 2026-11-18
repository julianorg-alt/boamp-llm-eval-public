# boamp-llm-eval

English: [README.md](README.md)

Un petit banc d'essai reproductible. Trois modèles Claude extraient des champs structurés d'avis de marchés publics français (BOAMP), et chaque champ est noté face à une référence. Tout est dans le dépôt : les 100 avis, les réponses brutes des modèles, le code de notation et le suivi des coûts.

Les modèles sont Claude Haiku 5.5, Sonnet 5.5 et Opus 5.5. Les neuf champs : acheteur, objet, lieu d'exécution, procédure, date limite, codes CPV, lots, montant estimé et critères d'attribution.

Lisez les limites avant les chiffres. L'entrée n'est pas l'avis publié, et les intervalles de confiance se recouvrent. Ces données n'établissent aucun classement des trois modèles.

## Ce que fait l'outil

1. `build` tire 100 avis dans les données ouvertes du BOAMP (du 1er septembre au 15 novembre 2026) et les répartit en 80 pour la mise au point et 20 pour un hold-out. L'échantillon est stratifié par famille (JOUE 40, FNS 35, MAPA 25) et par type de marché.
2. Chaque avis est rendu en texte français, les données personnelles sont masquées, et les champs structurés servent de référence.
3. Un seul prompt figé et un seul schéma JSON partent vers les trois modèles par l'API Message Batches.
4. Chaque champ a sa métrique (égalité normalisée, F1 sur des ensembles, tolérance sur les montants et les dates). Un bootstrap donne des intervalles à 95 %.
5. Le rapport donne les scores, les intervalles, le coût par avis et le nombre de réponses inexploitables.

## Relancer

Il faut Python 3.13 ou plus récent et [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
uv run ruff check .
```

Refaire le rapport à partir des réponses enregistrées. Aucun réseau, aucune clé d'API.

```bash
uv run python -m boamp_eval.report_md      # écrit reports/results-2026-11.md
uv run python -m boamp_eval.errors         # écrit reports/analyse-erreurs.md
uv run python -m boamp_eval.batch replay --model claude-opus-5-5 --split dev --name e3-dev-opus
```

Relancer les modèles. Cela coûte de l'argent. La clé ne passe que par l'environnement de la commande.

```bash
export ANTHROPIC_API_KEY=...   # votre propre clé
uv run python -m boamp_eval.batch estimate --model claude-sonnet-5-5 --split dev --name mon-essai
uv run python -m boamp_eval.batch submit   --model claude-sonnet-5-5 --split dev --name mon-essai
uv run python -m boamp_eval.batch collect  --model claude-sonnet-5-5 --split dev --name mon-essai
```

`estimate` chiffre le pire cas. `submit` refuse de partir si le registre `data/costs-ledger.json` dépasserait le plafond fixé dans `src/boamp_eval/costs.py` (15 $ par défaut). `--effort` règle le niveau d'effort (défaut de l'outil : `low`). `--split holdout` est refusé tant que `docs/FREEZE.md` n'est pas versionné.

Reconstruire le jeu depuis l'API du BOAMP (réseau nécessaire) :

```bash
uv run python -m boamp_eval.build --seed 20261118 --out data
```

La base du BOAMP évolue : une reconstruction peut différer des fichiers versionnés. Ce sont ces derniers qui font référence.

## Résultats

Tous les chiffres viennent de `reports/results-2026-11.md`, généré depuis `data/runs/`. Même prompt, même schéma et même `max_tokens` (4096) pour les trois modèles, effort `low`, tarif lot.

Le score dur est la moyenne des champs qui ne se recopient pas depuis l'entrée : date limite, montant, critères, CPV et lieu. Intervalles à 95 % entre crochets.

| Modèle | Dev (80 avis) | Hold-out (20 avis) | Coût par avis (dev, USD) |
|---|---|---|---|
| Haiku 5.5 | 0,852 [0,803 ; 0,900] | 0,896 [0,800 ; 0,988] | 0,00014 |
| Sonnet 5.5 | 0,864 [0,808 ; 0,920] | 0,909 [0,800 ; 1,000] | 0,00254 |
| Opus 5.5 | 0,917 [0,863 ; 0,967] | 0,859 [0,700 ; 1,000] | 0,00507 |

Tous les intervalles se recouvrent, sur le dev comme sur le hold-out, et l'ordre change d'un jeu à l'autre. Aucun classement n'est établi.

Par champ sur le dev, `criteres` est le point faible : Haiku 0,316, Sonnet 0,421, Opus 0,632 (19 avis). Les autres champs durs restent entre 0,94 et 1,00 pour les trois modèles.

Effort par défaut. Après avoir lu les résultats ci-dessus, j'ai relancé Sonnet à son effort par défaut (`high`) et Opus au sien (`medium`), sur le dev seulement, avec le même prompt.

| Modèle | Effort | Score dur (dev) | `criteres` | Coût par avis (USD) |
|---|---|---|---|---|
| Sonnet 5.5 | low | 0,864 [0,808 ; 0,920] | 0,421 | 0,00254 |
| Sonnet 5.5 | défaut (high) | 0,864 [0,808 ; 0,921] | 0,421 | 0,00274 |
| Opus 5.5 | low | 0,917 [0,863 ; 0,967] | 0,632 | 0,00507 |
| Opus 5.5 | défaut (medium) | 0,916 [0,856 ; 0,969] | 0,684 | 0,00585 |

Plus d'effort coûte 8 à 15 % de plus et ne change aucun score au-delà des intervalles.

Dépense totale en appels d'API pour tout le projet : 1,42 $ (essai initial et passages à l'effort par défaut compris).

### D'où viennent les erreurs sur les critères

`reports/analyse-erreurs.md` classe chaque mauvaise réponse à partir des réponses enregistrées, sans nouvel appel. Sur le dev, `criteres` a une référence pour 19 avis (13 JOUE, 6 MAPA).

L'essentiel des erreurs tient au format. Pour les avis JOUE, mon rendu de l'entrée ajoute le type du critère après chaque libellé, par exemple « Prix (prix) » ou « Valeur technique (qualité) ». Le prompt demande de recopier les valeurs telles qu'écrites, donc beaucoup de réponses gardent le suffixe, et la métrique exige un libellé identique. Haiku l'a fait sur 12 avis sur 19, Sonnet sur 10, Opus sur 6. Une fois le suffixe retiré, les trois modèles obtiennent 0,947 sur ce champ. Les 0,053 restants correspondent à un seul avis, le 26-108247.

Cet avis compte 250 lots. La liste JSON des lots dépasse `max_tokens` : les trois modèles sont coupés net et la réponse est inutilisable. C'est pareil à l'effort par défaut. Je n'ai pas touché aux paramètres figés pour le récupérer.

L'écart de 0,316 à 0,632 sur `criteres` mesure donc surtout la fidélité avec laquelle chaque modèle recopie un libellé que mon format d'entrée avait décoré. Il dit peu de choses sur la lecture des critères d'attribution. J'ai gardé la métrique figée pour les chiffres principaux et je donne le chiffre sans suffixe à côté, comme lecture faite après coup.

## Limites

- L'entrée est reconstruite depuis les champs structurés. Le texte officiel de l'avis n'était pas disponible : le modèle lit un rendu français généré depuis le JSON qui fournit aussi la référence, pas l'avis tel que publié.
- La tâche est donc en partie circulaire. L'objet, l'acheteur et les titres de lots sont recopiés presque mot pour mot. Ils sont comptés à part (annexe du rapport) et exclus du score principal.
- L'échantillon couvre onze semaines de l'automne 2026, avec des quotas que j'ai choisis (40/35/25), pas les proportions réelles des avis.
- Les effectifs sont faibles. 80 avis au dev, 20 au hold-out (JOUE 8, FNS 7, MAPA 5), et seulement 19 et 5 pour `criteres`. Aucune conclusion par famille n'est possible.
- Les intervalles se recouvrent. Je n'affirme la supériorité d'aucun modèle.
- L'effort `low` est un choix de protocole pour une comparaison équitable. Le passage à l'effort par défaut ne porte que sur Sonnet et Opus, au dev.
- La référence est la partie structurée de chaque avis. Pour FNS et MAPA, les montants et critères présents seulement en texte libre n'y figurent pas et sont exclus du score.
- Le masquage repose sur des motifs et sur les champs de contact de chaque avis. Un nom de personne sans civilité et hors de ces champs peut subsister.
- Le hold-out a été passé une seule fois, après le gel (`docs/FREEZE.md`). Il ne doit plus servir à régler quoi que ce soit.

## Organisation

```
src/boamp_eval/   code (collecte, rendu, masquage, métriques, client de lots, rapport)
data/             dev.jsonl, holdout.jsonl, manifeste, réponses brutes (runs/), registre des coûts
docs/             sources, métriques, gel, coûts
reports/          rapport généré et analyse d'erreurs
tests/            tests, sans réseau
```

## Licence

Le code est sous licence MIT (`LICENSE`).

Le jeu de données (`data/dev.jsonl`, `data/holdout.jsonl`) est dérivé d'avis du BOAMP.

Source : BOAMP, DILA (Premier ministre). Données interrogées par l'API du BOAMP le 18 novembre 2026, publiées sur https://www.data.gouv.fr/datasets/boamp. Licence Ouverte / Open Licence, version 1.0 (identifiant `fr-lo` sur data.gouv.fr, texte : https://www.etalab.gouv.fr/wp-content/uploads/2014/05/Licence_Ouverte.pdf). Dernière mise à jour de la fiche du jeu : 12 novembre 2026.

Les fichiers sont une sélection modifiée : rendu en texte, champs de référence extraits, données personnelles masquées. Ce ne sont pas les avis officiels, et la DILA ne les cautionne ni ne les garantit. Voir `data/NOTICE.md`.
