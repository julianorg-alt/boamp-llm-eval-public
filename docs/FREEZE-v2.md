# Gel v2 (2026-11-24), avant tout appel sur le jeu de test

Ce fichier est commité avant le moindre appel API sur `data/v2-test.jsonl`. Rien de ce qui suit n'est modifié après les appels. Le lot de mise au point (`data/v2-tuning.jsonl`, 30 avis, un passage Haiku 5.5 pour vérifier le rendu et l'analyse JSON : 0 réponse inexploitable, 0 troncature) est disjoint du jeu de test et exclu de tous les résultats.

## Jeu de test
- 500 avis BOAMP nouveaux, publiés du 2026-11-16 au 2026-11-24 (la v1 s'arrête au 2026-11-15) : JOUE 200, FNS 175, MAPA 125 (quotas 40 / 35 / 25 %), tirage stratifié à graine fixe 20261124. Aucun avis commun avec la v1 ni avec le lot de mise au point. Source et licence : `data/manifest-v2.json`.
- 128 avis portent des critères d'attribution notés (objectif : au moins 100). Quotas par famille inchangés : la part de JOUE n'a pas été augmentée.

## Protocole figé
- Prompt système et schéma de sortie inchangés depuis la v1 (mêmes empreintes que `docs/FREEZE.md`).
- Rendu : seule modification, plus de suffixe de type après le libellé des critères (`render.py`), plus un garde pour les sous-nœuds en chaîne.
- Effort `low`, `max_tokens` 8192, Message Batches API (tarif lot), un seul passage par modèle (Haiku 5.5, Sonnet 5.5, Opus 5.5), aucun re-passage.
- Plafond de dépense : 8 $ pour la v2 (estimation au pire cas avant soumission ; arrêt et question si elle dépasse 8 $).

## Analyse
- Métrique principale : `hard_global` (moyenne par champ des champs durs applicables : date limite, montant estimé, critères, CPV, lieu).
- Trois différences appariées sur les mêmes avis : Opus - Haiku, Opus - Sonnet, Sonnet - Haiku. Bootstrap apparié : 10 000 tirages, graine 20261118, même tirage d'avis pour les deux modèles.
- Règle de décision : un écart est établi si l'intervalle à 98,33 % de la différence (Bonferroni, 3 comparaisons, alpha 0,05 / 3) exclut 0. Sinon : non établi.
- Analyses secondaires, déclarées comme telles : scores par champ, par famille, différences appariées par champ. Elles n'établissent rien seules.
- Rapportés aussi : coût par avis, troncatures (`stop_reason=max_tokens`), réponses inexploitables, valeurs inventées.
- Une section v1 « analyse appariée faite après coup » (graine 20261118, 2 000 tirages, IC 95 %) est ajoutée au rapport ; elle est hors protocole.

## Empreintes (SHA-256)
| Élément | SHA-256 |
|---|---|
| `SYSTEM_PROMPT` (`schema.py`) | `12f464155ee40c1608dab3da17fa1196f2199521bfd7774b9cdc860c29d7c58d` |
| `OUTPUT_SCHEMA` (JSON trié) | `96259228ec9d300d478843a713735c304998b2f69242f6933c2466a64b46f345` |
| `metrics.py` | `094413727e91189a45637a55ab7c2383ab7f205a49f03a8c682f6291e2aa6c8a` |
| `report.py` | `ce06c7e6363161c3e3d1ae23c1d442dcaaab90c1c3a158b43d75e17f45e0651b` |
| `render.py` | `bcf5bc4244f1163c86bd007141fb15fc7e89ac2a5a65a5caa769bdf717d4976a` |
| `report_v2.py` | `e82efa08518a4dab77297f27c577ffb068a85e76835ffc3d325917bfe2f06346` |
| `data/v2-test.jsonl` | `2045034ab2a91d0a2b7e73c0e9fe0cb20b361be5d4d5e2a0d708b4dceb1919fc` |

Le générateur de rapport (`report_v2.py`) est gelé comme le reste : une correction de simple présentation, sans effet sur un chiffre, serait signalée dans le rapport.
