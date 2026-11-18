# Analyse d'erreurs : champ `criteres` (jeu de dev)

Source : réponses enregistrées dans `data/runs/e3-dev-*.jsonl` et `data/runs/e4-dev-*.jsonl`, rejouées sans appel API (`python -m boamp_eval.errors`). Avis où la vérité `criteres` existe : 19 sur 80 (JOUE et MAPA). Le hold-out n'est pas relu.

Répartition des 19 avis : {'JOUE': 13, 'MAPA': 6}. Le rendu de l'entrée ajoute le type entre parenthèses après chaque libellé dans 13 d'entre eux (familles : {'JOUE': 13}), et dans aucun avis MAPA (type absent de la vérité). Le prompt gelé demande de recopier les valeurs « telles qu'elles sont écrites » ; la métrique exige un libellé égal.

| Modèle | effort | n | score gelé | ok | suffixe de type | libellé autre | poids | ensemble | inexploitable | score si suffixe ignoré |
|---|---|---|---|---|---|---|---|---|---|---|
Avis 26-108247 : 250 lots en vérité, texte de 30280 caractères. Les 5 passages s'arrêtent à `max_tokens` (4096) : la liste des lots dépasse la limite de sortie (voir `reports/results-2026-11.md`).

| claude-haiku-5-5 | low | 19 | 0.316 | 6 | 12 | 0 | 0 | 0 | 1 | 0.947 |
| claude-sonnet-5-5 | low | 19 | 0.421 | 8 | 10 | 0 | 0 | 0 | 1 | 0.947 |
| claude-opus-5-5 | low | 19 | 0.632 | 12 | 6 | 0 | 0 | 0 | 1 | 0.947 |
| claude-sonnet-5-5 | défaut | 19 | 0.421 | 8 | 10 | 0 | 0 | 0 | 1 | 0.947 |
| claude-opus-5-5 | défaut | 19 | 0.684 | 13 | 5 | 0 | 0 | 0 | 1 | 0.947 |

## Avis hors « ok » et hors « suffixe de type »

- claude-haiku-5-5 (low) : 26-108247 (JOUE) : inexploitable
- claude-sonnet-5-5 (low) : 26-108247 (JOUE) : inexploitable
- claude-opus-5-5 (low) : 26-108247 (JOUE) : inexploitable
- claude-sonnet-5-5 (défaut) : 26-108247 (JOUE) : inexploitable
- claude-opus-5-5 (défaut) : 26-108247 (JOUE) : inexploitable
