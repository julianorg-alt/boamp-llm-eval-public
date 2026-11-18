# Métriques par champ (E2)

Code : `src/boamp_eval/metrics.py`, tests : `tests/test_metrics.py` (écrits avant tout appel réel). Un champ absent de la vérité est « non applicable » : exclu du score.

| Champ | Famille de score | Règle |
|---|---|---|
| `acheteur` | exact normalisé | minuscules, sans accents ni ponctuation ; parenthèse finale ignorée (des deux côtés) |
| `objet`, `procedure` | exact normalisé | idem, sans règle de parenthèse |
| `date_limite` | exact | deux décalages connus : même instant ; sinon heure locale écrite égale (MAPA : sans décalage) ; vérité sans heure : jour égal |
| `montant_estime` | tolérance | `valeur` à ±1 % (relatif) et même `devise` |
| `cpv` | F1 d'ensemble | codes réduits aux chiffres avant le tiret |
| `lots` | F1 d'ensemble | titres normalisés ; préfixe « lot n » et parenthèses ignorés ; `id` non scoré (non déductible) |
| `criteres` | F1 d'ensemble | élément = libellé normalisé égal ET poids à ±1 point (libellé seul si la vérité n'a pas de poids) ; `type` non scoré ; doublons appariés un à un |
| `lieu` | code NUTS puis texte | si la vérité contient un code NUTS : le code doit figurer dans la réponse ; sinon (FNS, MAPA, partie texte) : inclusion des mots significatifs dans un sens ou l'autre (sans articles, « France », « cedex », nombres) |

Réponse inexploitable (refus, `max_tokens`, JSON invalide) : chaque champ applicable compte 0 et `parse_errors` est incrémenté.

## Inventé (hallucination)
Compteur séparé, jamais mélangé au score. Une valeur est « inventée » si : la vérité est absente pour ce champ, le modèle fournit une valeur, et cette valeur est introuvable dans le texte d'entrée (`is_grounded` : montant retrouvé parmi les nombres du texte à ±1 %, date retrouvée en ISO ou en toutes lettres, CPV à 8 chiffres, titres de lots, critères, lieu, texte normalisé). Une valeur absente de la vérité mais présente dans le texte (ex. montant libre d'un MAPA) n'est ni fausse ni inventée : vérité inconnue, exclue. Taux = inventés / avis où la vérité est absente, par champ.

## Faciles et durs
L'entrée est générée depuis la vérité (circularité). **Faciles** (annexe) : `objet`, `acheteur`, `lots`, `procedure` (recopie, ou traduction par vocabulaire donné dans le prompt). **Durs** : `date_limite`, `montant_estime`, `criteres`, `cpv`, `lieu`. Score global = moyenne des moyennes par champ (macro) des champs durs applicables. `procedure` classée facile.

## Intervalles et comparaisons
Bootstrap percentile 95 % sur les avis (rééchantillonnage avec remise, `random.Random(20261118)`, 2000 tirages) : par champ et pour le score global. `report.verdict` : si les IC de deux modèles se recouvrent, « indistinguable », aucune conclusion d'écart.

## Validation
Test oracle : prédire la vérité elle-même donne 1,0 sur les 80 avis du dev, 0 inventé (normalisations validées sur données réelles). Les valeurs vraies sont retrouvées dans le texte (`is_grounded`) pour 100 % des champs sauf 4 titres de lots sur 47 (sans effet : l'ancrage ne sert que quand la vérité est absente).
