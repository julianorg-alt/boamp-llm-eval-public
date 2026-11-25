# Résultats v2 : extraction de champs d'avis BOAMP par Claude (2026-11)

## Protocole

- Gel : `docs/FREEZE-v2.md`, commit `c582c88dfdd620f51c65280e9b539ce4e9a1be03`, posé avant tout appel sur le jeu de test.
- Jeu de test : 500 avis nouveaux, publiés à partir du 2026-11-16 (JOUE 200, FNS 175, MAPA 125), dont 128 avec des critères d'attribution notés. Le lot de mise au point (30 avis) est exclu de ce rapport.
- Prompt et schéma identiques à la v1 ; rendu corrigé (plus de suffixe de type après le libellé des critères). Effort `low`, `max_tokens` 8192, Message Batches API (tarif -50 %).
- Métrique principale : `hard_global` (moyenne par champ des champs durs applicables). Bootstrap sur les avis (10000 tirages, graine 20261118).
- Règle de décision : un écart est établi si l'IC à 98,33 % de la différence appariée exclut 0 (Bonferroni, 3 comparaisons). Les analyses par champ et par famille sont secondaires.

## Score dur global (IC 95 %)

| Modèle | n | `hard_global` [IC 95 %] |
|---|---|---|
| claude-haiku-5-5 | 500 | 0.939 [0.924 ; 0.954] |
| claude-sonnet-5-5 | 500 | 0.943 [0.928 ; 0.958] |
| claude-opus-5-5 | 500 | 0.953 [0.939 ; 0.967] |

## Différences appariées (analyse principale)

Même rééchantillonnage d'avis pour les deux modèles ; IC à 98,33 %.

| Différence | Écart [IC 98,33 %] | Verdict |
|---|---|---|
| Opus - Haiku | +0.014 [+0.003 ; +0.025] | établi : Opus > Haiku |
| Opus - Sonnet | +0.010 [-0.000 ; +0.022] | non établi (l'IC contient 0) |
| Sonnet - Haiku | +0.004 [-0.007 ; +0.014] | non établi (l'IC contient 0) |

## Analyses secondaires (déclarées secondaires dans le gel)

### Par champ dur (moyenne [IC 95 %])

| Champ | n | claude-haiku-5-5 | claude-sonnet-5-5 | claude-opus-5-5 |
|---|---|---|---|---|
| date_limite | 474 | 1.000 [1.000 ; 1.000] | 1.000 [1.000 ; 1.000] | 1.000 [1.000 ; 1.000] |
| montant_estime | 113 | 1.000 [1.000 ; 1.000] | 0.991 [0.971 ; 1.000] | 1.000 [1.000 ; 1.000] |
| criteres | 128 | 0.720 [0.644 ; 0.795] | 0.734 [0.663 ; 0.808] | 0.776 [0.708 ; 0.844] |
| cpv | 363 | 1.000 [1.000 ; 1.000] | 1.000 [1.000 ; 1.000] | 1.000 [1.000 ; 1.000] |
| lieu | 460 | 0.976 [0.961 ; 0.989] | 0.989 [0.978 ; 0.998] | 0.989 [0.978 ; 0.998] |

### Par famille (`hard_global` [IC 95 %])

| Famille | n | claude-haiku-5-5 | claude-sonnet-5-5 | claude-opus-5-5 |
|---|---|---|---|---|
| JOUE | 200 | 0.928 [0.909 ; 0.947] | 0.930 [0.910 ; 0.950] | 0.940 [0.920 ; 0.958] |
| FNS | 175 | 0.991 [0.984 ; 0.997] | 0.994 [0.989 ; 0.999] | 0.994 [0.989 ; 0.999] |
| MAPA | 125 | 0.951 [0.914 ; 0.982] | 0.963 [0.929 ; 0.991] | 0.984 [0.960 ; 1.000] |

### Différences appariées par champ (IC 98,33 %, secondaire)

| Champ | Opus - Haiku | Opus - Sonnet | Sonnet - Haiku |
|---|---|---|---|
| date_limite | +0.000 [+0.000 ; +0.000] | +0.000 [+0.000 ; +0.000] | +0.000 [+0.000 ; +0.000] |
| montant_estime | +0.000 [+0.000 ; +0.000] | +0.009 [+0.000 ; +0.036] | -0.009 [-0.036 ; +0.000] |
| criteres | +0.056 [+0.004 ; +0.112] | +0.043 [-0.008 ; +0.097] | +0.013 [-0.035 ; +0.062] |
| cpv | +0.000 [+0.000 ; +0.000] | +0.000 [+0.000 ; +0.000] | +0.000 [+0.000 ; +0.000] |
| lieu | +0.013 [+0.002 ; +0.028] | +0.000 [+0.000 ; +0.000] | +0.013 [+0.002 ; +0.028] |

## Troncatures, réponses inexploitables, valeurs inventées

| Modèle | Tronqués (`max_tokens` 8192) | Inexploitables (total) | Inventés (tous champs) |
|---|---|---|---|
| claude-haiku-5-5 | 0 | 0 | 6 |
| claude-sonnet-5-5 | 0 | 0 | 1 |
| claude-opus-5-5 | 0 | 0 | 0 |

## Coût

Recalculé depuis `usage` au tarif lot (`docs/sources.md`).

| Modèle | Coût $ | $ par avis | Tokens entrée / sortie / cache lu | Latence de lot (s) |
|---|---|---|---|---|
| claude-haiku-5-5 | 0.0616 | 0.00012 | 358675 / 157641 / 827342 | 423 |
| claude-sonnet-5-5 | 1.0365 | 0.00207 | 358675 / 126882 / 827342 | 446 |
| claude-opus-5-5 | 2.0832 | 0.00417 | 358675 / 127893 / 827342 | 433 |

Total des trois lots : 3.1813 $.

## v1 : analyse appariée faite après coup

Calculée après la lecture des résultats v1, hors protocole : ce n'est pas une analyse planifiée. Même rééchantillonnage d'avis pour les deux modèles, graine 20261118, 2000 tirages, IC à 95 %, score `hard_global`, effort `low`, `max_tokens` 4096. Rendu v1 (avec le suffixe de type sur les critères).

| Jeu | Avis | Différence | Écart [IC 95 %] |
|---|---|---|---|
| dev | 80 | Opus - Haiku | +0.066 [+0.024 ; +0.110] |
| dev | 80 | Opus - Sonnet | +0.054 [+0.013 ; +0.104] |
| dev | 80 | Sonnet - Haiku | +0.012 [-0.023 ; +0.050] |
| holdout | 20 | Opus - Haiku | -0.037 [-0.178 ; +0.040] |
| holdout | 20 | Opus - Sonnet | -0.050 [-0.200 ; +0.000] |
| holdout | 20 | Sonnet - Haiku | +0.013 [+0.000 ; +0.044] |

## Limites

- Entrée reconstruite : rendu texte généré depuis le JSON structuré, pas l'avis publié ; la vérité vient des mêmes champs (circularité, voir v1).
- Échantillon d'une seule période (avis publiés du 2026-11-16 au 2026-11-24), quotas par famille choisis (40/35/25), non représentatif de toute la commande publique.
- Un seul passage par modèle, effort `low` : les efforts par défaut ne sont pas comparés ici.
- Les analyses par champ et par famille sont secondaires : les IC ne sont pas corrigés pour comparaisons multiples au-delà de ce qui est indiqué.
- Un écart « établi » vaut pour ce jeu, ce rendu et ce prompt, et pour la métrique `hard_global` ; il ne dit pas que le modèle est meilleur dans toute situation.
