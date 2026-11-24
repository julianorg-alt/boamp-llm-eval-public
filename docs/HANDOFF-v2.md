# Passation v2 (2026-11-24)

## État
- Branche `v2` (base : `main` du dépôt public). Fait : rendu corrigé (plus de suffixe de type sur les critères, test), `report.paired_diff_ci` (tests), échantillon v2 (500 avis de test publiés du 2026-11-16 au 2026-11-24, JOUE 200, FNS 175, MAPA 125, dont 128 avec critères notés ; 30 avis de mise au point, disjoints), lot de mise au point Haiku (30 avis : 0 inexploitable, 0 troncature, 0,0037 $), gel `docs/FREEZE-v2.md` (commit `c582c88dfdd620f51c65280e9b539ce4e9a1be03`), générateur `report_v2.py` testé hors réseau.
- **Aucun appel n'a été fait sur les 500 avis.** Arrêt à l'étape 5 : l'estimation dépasse 8 $.

## Estimation (au pire cas, tarif lot, `max_tokens` 8192, 500 avis, 2 187 675 tokens d'entrée)
| Modèle | Pire cas $ |
|---|---|
| Haiku 5.5 | 5,67 (majoré : tarif « prompt > 100 000 tokens » appliqué à la somme) |
| Sonnet 5.5 | 22,67 |
| Opus 5.5 | 45,34 |
| Total | 73,67 |

Le pire cas suppose 8 192 tokens de sortie pour chaque avis. Mesuré en v1 (80 avis dev, `max_tokens` 4096) : 0,00014 $ (Haiku), 0,00254 $ (Sonnet), 0,00507 $ (Opus) par avis, soit environ 0,07 + 1,27 + 2,54 = 3,9 $ pour 500 avis (extrapolation, non vérifiée sur ce jeu). Registre actuel : 1,4286 $ ; plafond du registre à passer à 9,42 $ (`--cap 9.42`) pour tenir les 8 $ de la v2.

## Question ouverte
La règle « estimation > 8 $ : stop » s'applique à la lettre. Options :
1. **Lancer avec un garde au réel (recommandé)** : garde de budget par avis impossible en lot, mais la dépense attendue est d'environ 4 $ ; le plafond de 8 $ ne peut être dépassé que si les sorties explosent (peu probable à l'effort `low`). Seule voie qui tient le protocole gelé. À lancer : `submit` puis `collect` pour les trois modèles avec `--split v2-test --max-tokens 8192 --cap 9.42`.
2. Lancer d'abord Haiku et Sonnet (≈ 1,3 $), puis Opus seulement si le coût mesuré le permet : même protocole, trois lots soumis en deux temps (aucun effet sur les résultats).
3. Réduire `max_tokens` à 4096 : divise le pire cas par deux (≈ 36 $), reste au-dessus de 8 $, et change le protocole gelé (à refaire avant tout appel).

## Limites
Rendu texte reconstruit (circularité), une seule période, un passage par modèle, analyses par champ et par famille secondaires.

QUESTION : l'estimation au pire cas de 73,67 $ dépasse 8 $ alors que le coût attendu est d'environ 4 $ ; lancer les trois lots (option 1, recommandée), Haiku et Sonnet d'abord (option 2) ou réduire `max_tokens` (option 3) ?
