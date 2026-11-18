# Dépense API (plafond 15 $ au total)

Tarifs : `docs/sources.md`. Registre machine : `data/costs-ledger.json` (créé au premier appel réel).

| Date | Épopée | Modèle | Tokens (entrée / sortie / cache) | Batch | $ | Cumul $ |
|---|---|---|---|---|---|---|
| 2026-11-18 | E0 | — | aucun appel API | — | 0,00 | 0,00 |
| 2026-11-18 | E1 | — | aucun appel API | — | 0,00 | 0,00 |
| 2026-11-18 | E2 | claude-haiku-5-5 | 1 751 / 765 / 1 658 écrits + 3 316 lus | non | 0,00080 | 0,00080 |

Cumul : **0,0008 $ / 15 $**.

## Estimations avant lot (E3, 2026-11-18)
Méthode : tokens d'entrée comptés par `POST /v1/messages/count_tokens` (+ 2 000 tokens de marge par avis pour le schéma), sortie = `max_tokens` 4 096 par avis (pire cas, sans cache, sans réflexion mesurée), tarif lot (-50 %). Le pire cas est un majorant : la sortie réelle (essai E2) est de l'ordre de 300 tokens.

| Lot | Avis | Entrée (tokens) | Sortie max (tokens) | Estimé pire cas $ |
|---|---|---|---|---|
| dev Haiku 5.5 | 80 | 365 202 | 327 680 | 0,50 |
| dev Sonnet 5.5 | 80 | 365 202 | 327 680 | 2,00 |
| dev Opus 5.5 | 80 | 365 202 | 327 680 | 4,01 |

Pire cas des 3 lots dev : 6,51 $, plus cumul 0,0008 $, sous le plafond de 15 $. Le hold-out (20 avis x 3 modèles) sera estimé à part avant soumission.

Note : l'estimation Haiku du lot dev (0,50 $) applique le tarif « prompt > 100 000 tokens » à la somme des 80 avis, alors que chaque requête est tarifée seule (docs/sources.md) : majorant très large. Mesuré : 0,0112 $.

## Estimations avant lot hold-out (E3, 2026-11-18, après gel `docs/FREEZE.md`)
Même méthode. 20 avis, 86 035 tokens d'entrée (comptés + marge), 81 920 tokens de sortie max.

| Lot | Estimé pire cas $ |
|---|---|
| hold-out Haiku 5.5 | 0,025 |
| hold-out Sonnet 5.5 | 0,50 |
| hold-out Opus 5.5 | 0,99 |

## Coûts réels E3 (2026-11-18, tarif lot, source : `data/costs-ledger.json`)
| Épopée | Modèle | Lot | Avis | Tokens entrée / sortie / cache lu | $ | $ par avis |
|---|---|---|---|---|---|---|
| E3 | Haiku 5.5 | dev | 80 | 72 562 / 27 106 / 130 982 | 0,0112 | 0,00014 |
| E3 | Sonnet 5.5 | dev | 80 | 72 562 / 24 465 / 130 982 | 0,2035 | 0,00254 |
| E3 | Opus 5.5 | dev | 80 | 72 562 / 24 307 / 130 982 | 0,4054 | 0,00507 |
| E3 | Haiku 5.5 | hold-out | 20 | 12 875 / 5 041 / 31 502 | 0,0022 | 0,00011 |
| E3 | Sonnet 5.5 | hold-out | 20 | 12 875 / 4 404 / 31 502 | 0,0385 | 0,00193 |
| E3 | Opus 5.5 | hold-out | 20 | 12 875 / 4 353 / 31 502 | 0,0766 | 0,00383 |

Cumul (E2 comprise) : **0,7382 $ / 15 $** (303 entrées au registre).

## Passage complémentaire E4 : effort par défaut (2026-11-18, dev seulement, tarif lot, source : `data/costs-ledger.json`)
Pire cas : identique à celui de E3 pour le même `max_tokens` et les mêmes entrées (Sonnet 2,00 $, Opus 4,01 $ ; l'estimation propre à ce lot n'a pas été relancée, `submit` la calcule et applique le garde de budget). Les tokens de réflexion comptent dans `max_tokens`.

| Épopée | Modèle | Effort | Avis | Tokens sortie | $ | $ par avis |
|---|---|---|---|---|---|---|
| E4 | Sonnet 5.5 | high (défaut) | 80 | 27 565 | 0,2190 | 0,00274 |
| E4 | Opus 5.5 | medium (défaut) | 80 | 30 535 | 0,4677 | 0,00585 |

Cumul (E2, E3, E4) : **1,4249 $ / 15 $** (463 entrées au registre).

