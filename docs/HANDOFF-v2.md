# Passation v2 (2026-11-25)

## État : terminé, branche `v2` poussée (pas de PR, pas de fusion : décision du propriétaire)
- Gel : `docs/FREEZE-v2.md`, commit `c582c88dfdd620f51c65280e9b539ce4e9a1be03`, posé avant tout appel sur le jeu de test. Rapport : `reports/results-v2.md` (généré par `python -m boamp_eval.report_v2`).
- Trois lots (Message Batches, un passage chacun, 500 avis, 0 erreur de lot, 0 troncature, 0 réponse inexploitable). Coût : 3,1813 $ pour les trois lots (Haiku 0,0616 ; Sonnet 1,0365 ; Opus 2,0832), 3,185 $ avec le lot de mise au point ; registre 4,6099 $ cumulés sur 15 $, v2 sous le plafond de 8 $.

## Chiffres clés (`hard_global`, 500 avis)
| Différence | Écart [IC 98,33 %] | Verdict |
|---|---|---|
| Opus - Haiku | +0,014 [+0,003 ; +0,025] | établi |
| Opus - Sonnet | +0,010 [-0,000 ; +0,022] | non établi |
| Sonnet - Haiku | +0,004 [-0,007 ; +0,014] | non établi |

Scores : Haiku 0,939, Sonnet 0,943, Opus 0,953. Le champ `criteres` (128 avis) reste le plus bas (0,72 à 0,78) : analyse secondaire, rien d'établi seul.

## Écarts au plan, à connaître
- Garde de budget : le garde au pire cas (73,67 $) interdisait tout lancement sous 8 $. Sur QCM du propriétaire (25/11), `submit --guard expected` compare un coût attendu (1,5 x le plus fort coût par avis mesuré en v1) au plafond 9,42 $. Les prompt, schéma et métriques gelés n'ont pas changé ; le coût réel (3,18 $) est resté sous 8 $.
- Les trois `collect` ont tourné en parallèle : une course sur `data/costs-ledger.json` a fait échouer la fin du `collect` Opus (réponses brutes déjà écrites). Les coûts Opus ont été enregistrés ensuite depuis ces réponses brutes, sans nouvel appel au modèle ; la méta Opus a été complétée par un `GET` du lot. Les 500 entrées Opus sont au registre, une fois.
- `report_v2.py` n'a pas été modifié depuis le gel.
- La borne basse de Opus - Sonnet s'affiche « -0,000 » : elle est légèrement négative, donc l'IC contient 0.

## Limites
Rendu texte reconstruit (circularité), une seule période (16 au 24/11/2026), un passage par modèle à l'effort `low`, analyses par champ et par famille secondaires, écart établi valable pour ce jeu et cette métrique seulement.

## Note sur l'historique (2026-11-28)
L'historique du dépôt a été réécrit (auteur anonyme, messages sans trailer) ; les arbres de fichiers sont identiques. Le commit de gel `c582c88dfdd620f51c65280e9b539ce4e9a1be03` cité plus haut et dans `reports/results-v2.md` est devenu `30818623188ff9ed35d6826d01c9fd6e2fbee22e`.
