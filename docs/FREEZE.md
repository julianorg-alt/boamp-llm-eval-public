# Gel avant le hold-out (2026-11-18)

Prompt, schéma de sortie et métriques sont figés avant tout passage sur `data/holdout.jsonl`. Le hold-out n'a été ni lu ni affiché avant ce commit. Les passages dev (E3) ont été faits avec ces mêmes versions, sans modification entre les deux.

| Élément | SHA-256 |
|---|---|
| `SYSTEM_PROMPT` (`schema.py`) | `12f464155ee40c1608dab3da17fa1196f2199521bfd7774b9cdc860c29d7c58d` |
| `OUTPUT_SCHEMA` (JSON trié) | `96259228ec9d300d478843a713735c304998b2f69242f6933c2466a64b46f345` |
| `metrics.py` | `094413727e91189a45637a55ab7c2383ab7f205a49f03a8c682f6291e2aa6c8a` |
| `report.py` | `fcf0155c7859b4615323c19e18f44ceef4d0735356a82373c74b5cbf7e9afc7b` |
| `data/holdout.jsonl` | `b6179a11acad83f573d1a56e1e4f069278f7312156d9b70a7f66ead9b930d2b3` |

Paramètres : `effort: low`, `max_tokens: 4096`, tarif lot, identiques pour les 3 modèles. Un seul passage hold-out par modèle ; aucun re-passage.
