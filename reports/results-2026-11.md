# Résultats : extraction de champs d'avis BOAMP par Claude (2026-11)

## Protocole

- Un seul prompt et un seul schéma de sortie pour les trois modèles (`docs/FREEZE.md`), effort `low` pour les trois (choix de protocole : extraction, comparaison équitable ; les efforts par défaut diffèrent), `max_tokens` 4096, Message Batches API (tarif -50 %).
- Jeu : dev = 80 avis, holdout = 20 avis. Le hold-out n'a été passé qu'une fois, après gel du prompt et des métriques.
- Score dur = moyenne par champ des champs durs applicables (date limite, montant, critères, CPV, lieu). IC 95 % : bootstrap sur les avis (`docs/METRICS.md`).

## Score dur (IC 95 %)

| Modèle | dev | holdout |
|---|---|---|
| claude-haiku-5-5 | 0.852 [0.803 ; 0.900] | 0.896 [0.800 ; 0.988] |
| claude-sonnet-5-5 | 0.864 [0.808 ; 0.920] | 0.909 [0.800 ; 1.000] |
| claude-opus-5-5 | 0.917 [0.863 ; 0.967] | 0.859 [0.700 ; 1.000] |

- dev : claude-haiku-5-5 / claude-sonnet-5-5 : indistinguable (IC qui se recouvrent)
- dev : claude-haiku-5-5 / claude-opus-5-5 : indistinguable (IC qui se recouvrent)
- dev : claude-sonnet-5-5 / claude-opus-5-5 : indistinguable (IC qui se recouvrent)
- holdout : claude-haiku-5-5 / claude-sonnet-5-5 : indistinguable (IC qui se recouvrent)
- holdout : claude-haiku-5-5 / claude-opus-5-5 : indistinguable (IC qui se recouvrent)
- holdout : claude-sonnet-5-5 / claude-opus-5-5 : indistinguable (IC qui se recouvrent)

## Par champ (champs durs)

### dev

| Champ | n | claude-haiku-5-5 | claude-sonnet-5-5 | claude-opus-5-5 |
|---|---|---|---|---|
| date_limite | 78 | 0.974 [0.936 ; 1.000] | 0.987 [0.961 ; 1.000] | 0.987 [0.961 ; 1.000] |
| montant_estime | 17 | 1.000 [1.000 ; 1.000] | 0.941 [0.812 ; 1.000] | 1.000 [1.000 ; 1.000] |
| criteres | 19 | 0.316 [0.111 ; 0.533] | 0.421 [0.200 ; 0.650] | 0.632 [0.409 ; 0.842] |
| cpv | 58 | 0.983 [0.943 ; 1.000] | 0.983 [0.943 ; 1.000] | 0.983 [0.943 ; 1.000] |
| lieu | 69 | 0.986 [0.954 ; 1.000] | 0.986 [0.954 ; 1.000] | 0.986 [0.954 ; 1.000] |

### holdout

| Champ | n | claude-haiku-5-5 | claude-sonnet-5-5 | claude-opus-5-5 |
|---|---|---|---|---|
| date_limite | 18 | 1.000 [1.000 ; 1.000] | 1.000 [1.000 ; 1.000] | 1.000 [1.000 ; 1.000] |
| montant_estime | 4 | 1.000 [1.000 ; 1.000] | 1.000 [1.000 ; 1.000] | 0.750 [0.000 ; 1.000] |
| criteres | 5 | 0.533 [0.000 ; 1.000] | 0.600 [0.000 ; 1.000] | 0.600 [0.000 ; 1.000] |
| cpv | 15 | 1.000 [1.000 ; 1.000] | 1.000 [1.000 ; 1.000] | 1.000 [1.000 ; 1.000] |
| lieu | 19 | 0.947 [0.833 ; 1.000] | 0.947 [0.833 ; 1.000] | 0.947 [0.833 ; 1.000] |

## Par famille (score dur global)

### dev

| Famille | n | claude-haiku-5-5 | claude-sonnet-5-5 | claude-opus-5-5 |
|---|---|---|---|---|
| FNS | 28 | 0.991 [0.973 ; 1.000] | 1.000 [1.000 ; 1.000] | 1.000 [1.000 ; 1.000] |
| JOUE | 32 | 0.780 [0.738 ; 0.800] | 0.795 [0.724 ; 0.857] | 0.872 [0.786 ; 0.943] |
| MAPA | 20 | 1.000 [1.000 ; 1.000] | 1.000 [1.000 ; 1.000] | 1.000 [1.000 ; 1.000] |

### holdout

| Famille | n | claude-haiku-5-5 | claude-sonnet-5-5 | claude-opus-5-5 |
|---|---|---|---|---|
| FNS | 7 | 0.952 [0.857 ; 1.000] | 0.952 [0.857 ; 1.000] | 0.952 [0.857 ; 1.000] |
| JOUE | 8 | 0.800 [0.800 ; 1.000] | 0.800 [0.800 ; 1.000] | 0.750 [0.650 ; 1.000] |
| MAPA | 5 | 0.963 [0.889 ; 1.000] | 1.000 [1.000 ; 1.000] | 1.000 [1.000 ; 1.000] |

## Compteur « inventé »

Valeur fournie alors que la vérité est absente ET introuvable dans le texte (`docs/METRICS.md`).

| Split | Modèle | Inventés (tous champs) | Réponses inexploitables |
|---|---|---|---|
| dev | claude-haiku-5-5 | 1 (criteres 1) | 1 |
| dev | claude-sonnet-5-5 | 0 | 1 |
| dev | claude-opus-5-5 | 0 | 1 |
| holdout | claude-haiku-5-5 | 0 | 0 |
| holdout | claude-sonnet-5-5 | 0 | 0 |
| holdout | claude-opus-5-5 | 0 | 0 |

## Coût réel et latence de lot

Coût recalculé depuis `usage` des réponses au tarif lot (`docs/sources.md`) ; le registre `data/costs-ledger.json` porte les mêmes montants.

| Split | Modèle | Coût $ | $ par avis | Tokens entrée / sortie / cache lu | Latence de lot (s) |
|---|---|---|---|---|---|
| dev | claude-haiku-5-5 | 0.0112 | 0.00014 | 72562 / 27106 / 130982 | 411 |
| dev | claude-sonnet-5-5 | 0.2035 | 0.00254 | 72562 / 24465 / 130982 | 424 |
| dev | claude-opus-5-5 | 0.4054 | 0.00507 | 72562 / 24307 / 130982 | 241 |
| holdout | claude-haiku-5-5 | 0.0022 | 0.00011 | 12875 / 5041 / 31502 | 396 |
| holdout | claude-sonnet-5-5 | 0.0385 | 0.00193 | 12875 / 4404 / 31502 | 372 |
| holdout | claude-opus-5-5 | 0.0766 | 0.00383 | 12875 / 4353 / 31502 | 371 |

Total des passages ci-dessus : 0.7374 $.

## Passage complémentaire : effort par défaut (dev seulement)

Sonnet 5.5 à l'effort par défaut `high`, Opus 5.5 à `medium` (`docs/sources.md`), même prompt gelé, même schéma, `max_tokens` 4096, lot, 80 avis du dev. Haiku n'est pas repassé. Passage fait après la lecture des résultats `low` : il ne remplace pas le protocole principal.

| Modèle | effort | score dur | `criteres` | inexploitables | $ | $ par avis | tokens sortie | latence (s) |
|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | low | 0.864 [0.808 ; 0.920] | 0.421 [0.200 ; 0.650] | 1 | 0.2035 | 0.00254 | 24465 | 424 |
| claude-sonnet-5-5 | défaut | 0.864 [0.808 ; 0.921] | 0.421 [0.188 ; 0.667] | 1 | 0.2190 | 0.00274 | 27565 | 324 |
| claude-opus-5-5 | low | 0.917 [0.863 ; 0.967] | 0.632 [0.409 ; 0.842] | 1 | 0.4054 | 0.00507 | 24307 | 241 |
| claude-opus-5-5 | défaut | 0.916 [0.856 ; 0.969] | 0.684 [0.467 ; 0.895] | 1 | 0.4677 | 0.00585 | 30535 | 270 |

## Annexe : champs faciles (entrée générée depuis la vérité : recopie)

### dev

| Champ | claude-haiku-5-5 | claude-sonnet-5-5 | claude-opus-5-5 |
|---|---|---|---|
| objet | 0.900 | 0.975 | 0.975 |
| acheteur | 0.950 | 0.988 | 0.988 |
| lots | 0.713 | 0.745 | 0.755 |
| procedure | 0.988 | 0.988 | 0.988 |

### holdout

| Champ | claude-haiku-5-5 | claude-sonnet-5-5 | claude-opus-5-5 |
|---|---|---|---|
| objet | 0.950 | 0.950 | 0.950 |
| acheteur | 0.950 | 1.000 | 1.000 |
| lots | 0.500 | 0.500 | 0.500 |
| procedure | 0.950 | 1.000 | 1.000 |

## Limites

- Entrée reconstruite : rendu texte généré depuis le JSON structuré (le texte officiel n'est pas disponible), pas l'avis publié.
- Circularité : la vérité vient des mêmes champs structurés que le rendu ; l'objet, l'acheteur et les titres de lots sont recopiables (champs faciles, en annexe). Le score mesure la lecture d'un rendu, pas celle d'un avis réel.
- Échantillon d'automne : 100 avis (2026-09-01 à 2026-11-15), quotas par famille choisis (40/35/25), non représentatifs de toute la commande publique.
- Hold-out de 20 avis (JOUE 8, FNS 7, MAPA 5) : IC larges, aucune conclusion par famille.
- Effort `low` fixé pour les trois modèles ; le passage à l'effort par défaut (Sonnet, Opus, dev seulement) est présenté à part.
- Vérité FNS et MAPA : des montants ou critères présents en texte libre n'y figurent pas (champ non applicable, exclu).
- Les IC se recouvrent souvent : sans écart d'IC, aucune supériorité n'est affirmée.

## Lecture

- Aucun écart de score dur global n'est établi : sur dev comme sur hold-out, tous les IC 95 % des trois modèles se recouvrent. L'ordre observé change d'un jeu à l'autre (dev : Opus 0,917 > Sonnet 0,864 > Haiku 0,852 ; hold-out : Sonnet 0,909 > Haiku 0,896 > Opus 0,859) : pas de classement à retenir.
- Le seul champ où l'écart de moyennes est net sur dev est `criteres` (Opus 0,632, Sonnet 0,421, Haiku 0,316 ; n = 19, IC larges et qui se recouvrent en partie). Sur hold-out, n = 5 : sans portée. Cause analysée dans `reports/analyse-erreurs.md` : voir ci-dessous.
- Les familles FNS et MAPA sont à 0,95-1,00 pour les trois modèles ; l'essentiel de la perte se situe sur JOUE (dev : 0,780 à 0,872), où les critères sont les plus nombreux. Sur hold-out, JOUE n = 8.
- Un avis du dev (26-108247, 18 748 tokens d'entrée) dépasse `max_tokens` (4096) pour les trois modèles : réponse inexploitable, comptée 0 sur ses champs applicables, signalée dans le tableau « inventé ». Le prompt et les paramètres gelés n'ont pas été modifiés pour le récupérer.
- « Inventé » : 1 cas au total sur 300 réponses (Haiku, dev, `criteres`).
- Coût : le pire cas estimé avant lot (6,51 $ pour le dev, 1,52 $ pour le hold-out) est très supérieur au coût mesuré (0,62 $ dev, 0,12 $ hold-out). L'effort `low` a produit de courtes sorties (environ 300 tokens par avis).
- Effort par défaut (Sonnet `high`, Opus `medium`, dev seulement, section dédiée) : score dur 0,864 [0,808 ; 0,921] pour Sonnet et 0,916 [0,856 ; 0,969] pour Opus, soit les valeurs de l'effort `low` aux IC près ; coût par avis +8 % (Sonnet) et +15 % (Opus). Aucun gain établi.
- Erreurs sur `criteres` (`reports/analyse-erreurs.md`, réponses enregistrées, sans nouvel appel) : le rendu de l'entrée ajoute le type entre parenthèses après chaque libellé des 13 avis JOUE concernés ; les modèles le recopient (Haiku 12 avis, Sonnet 10, Opus 6 sur 19), et la métrique exige un libellé égal. Sans le suffixe, les trois modèles font 0,947 : l'écart de `criteres` mesure surtout la recopie littérale d'un libellé décoré par le format d'entrée. La métrique gelée reste celle des chiffres principaux.
- Avis 26-108247 : 250 lots, la liste dépasse `max_tokens` pour les cinq passages (trois à l'effort `low`, deux à l'effort par défaut) ; paramètres figés non modifiés.
