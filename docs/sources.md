# Sources vérifiées

Chaque fait ci-dessous a été relevé à la source le 2026-11-18.

## API BOAMP
- Jeu `boamp` sur Opendatasoft (DILA) : `https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp` (API Explore v2.1, accès anonyme, HTTP 200 sans clé, réponses gzip : utiliser `--compressed`).
- Volume : 1 727 663 enregistrements (`records_count`), données traitées le 2026-11-18.
- Endpoint enregistrements : `.../datasets/boamp/records` avec `where`, `select`, `limit`, `group_by`.
- Champs (41) : `idweb`, `id`, `contractfolderid`, `objet`, `famille`, `dateparution`, `datelimitereponse`, `nomacheteur`, `type_procedure`, `nature`, `nature_categorise`, `criteres`, `descripteur_code`, `type_marche`, `url_avis`, `donnees` (contenu structuré de l'avis en JSON texte), etc.
- `donnees` : EFORMS (`famille=JOUE`, eForms SDK, ex. `eforms-sdk-1.12`, ~40 Ko), `FNSimple` (`famille=FNS`) ou `MAPA` (`famille=MAPA`), ces deux derniers ~2,5 Ko (clés racine `organisme`, `initial`).
- Appels d'offres standard (`nature_categorise='appeloffre/standard'`) parus depuis le 2026-09-01 : 18 296 (JOUE 10 268, FNS 6 601, MAPA 1 348, DSP 56, DIVERS 23).

## Licence
- Métadonnée data.gouv.fr du jeu BOAMP (`https://www.data.gouv.fr/datasets/boamp`, id `559390f9c751df0139a453ba`, producteur Premier ministre) : licence `fr-lo`, « Licence Ouverte / Open Licence » (`https://www.etalab.gouv.fr/wp-content/uploads/2014/05/Licence_Ouverte.pdf`). Le champ licence des métadonnées Opendatasoft est vide : la référence est data.gouv.fr.
- Version applicable : la fiche data.gouv.fr (`/api/1/datasets/boamp/`, relevée le 2026-11-18) déclare `license: fr-lo`. Dans le registre des licences de data.gouv.fr (`/api/1/datasets/licenses/`, même date), `fr-lo` est « Licence Ouverte / Open Licence » (URL 2014 ci-dessus) ; la version 2.0 a un identifiant distinct (`lov2`), que le jeu n'utilise pas. Le jeu est donc sous la **version 1.0**.
- Texte de la version 1.0 relu le 2026-11-18 (`https://www.etalab.gouv.fr/wp-content/uploads/2014/05/Licence_Ouverte.pdf`, document daté octobre 2011, « Cette licence est une version 1.0 de la Licence Ouverte »). Libertés : reproduire, copier, publier, transmettre, diffuser, redistribuer, adapter, modifier, extraire, transformer (informations dérivées), exploiter à titre commercial. Condition unique : mentionner la paternité, soit la source (a minima le nom du producteur) et la date de dernière mise à jour ; des liens hypertextes y suffisent. La mention ne doit ni conférer un caractère officiel à la réutilisation, ni suggérer une caution du producteur ou d'une entité publique. La réutilisation ne doit pas induire en erreur sur le contenu, la source et la date de mise à jour. Information fournie sans garantie. Les informations contenant des données personnelles ne sont réutilisables que si les personnes y ont consenti, si elles sont anonymisées ou si un texte le permet : d'où le masquage des noms, e-mails et téléphones dans le jeu. Droit français.
- La licence 2.0 (avril 2017, `.../2017/04/ETALAB-Licence-Ouverte-v2.0.pdf`) a été relue plus tôt le même jour mais ne s'applique pas à ce jeu.
- Date de mise à jour portée dans la mention : date d'interrogation de l'API BOAMP (2026-11-18), la métadonnée data.gouv.fr indiquant `last_update` 2026-11-12 pour la fiche du jeu (vérifié par l'API data.gouv.fr le 2026-11-18).

## Données personnelles
- Un avis eForms contient des blocs de contact (nom du représentant légal, e-mails, téléphones). Exemple vu : un champ nom + fonction de la présidente de l'acheteur. Règle : jeu de données figé sans noms de personnes physiques, e-mails ni téléphones (E1).

## Modèles Claude
Source : `https://platform.claude.com/docs/en/about-claude/models/overview.md`.
| Modèle | ID API | Contexte | Sortie max | Réflexion |
|---|---|---|---|---|
| Claude Opus 5.5 | `claude-opus-5-5` | 1M | 128K | adaptative, effort par défaut `medium` |
| Claude Sonnet 5.5 | `claude-sonnet-5-5` | 1M | 128K | adaptative, effort par défaut `high` |
| Claude Haiku 5.5 | `claude-haiku-5-5` | 1M | 128K | adaptative, effort par défaut `medium` |

## Prix (USD / million de tokens)
Source : `https://platform.claude.com/docs/en/about-claude/pricing.md`.
| Modèle | Entrée | Écriture cache 5 min | Écriture cache 1 h | Lecture cache | Sortie | Batch entrée | Batch sortie |
|---|---|---|---|---|---|---|---|
| Opus 5.5 | 4 | 5 | 8 | 0,20 | 20 | 2 | 10 |
| Sonnet 5.5 | 2 | 2,50 | 4 | 0,10 | 10 | 1 | 5 |
| Haiku 5.5 (prompt <= 100 000 tokens) | 0,10 | 0,125 | 0,20 | 0,01 | 0,50 | 0,05 | 0,25 |
| Haiku 5.5 (prompt > 100 000 tokens) | 0,50 | 0,625 | 1 | 0,05 | 2,50 | 0,25 | 1,25 |
- Batch API : -50 % entrée et sortie. Les tokens de réflexion sont de la sortie facturée (comportement général de l'API, non relu en détail ici : à confirmer en E3 sur `usage`).
- Seuil Haiku : tout le prompt compte, cache compris ; chaque requête est tarifée seule.
- Minimum cacheable : Opus 5.5 et Sonnet 5.5 286 tokens, Haiku 5.5 286 ou 406 tokens (la page ne dit pas laquelle des deux valeurs s'applique à Haiku ; à vérifier en E3).
- Tokenizer récent (4.7 et après) : environ 30 % de tokens de plus pour un même texte (la page le dit pour les modèles 4.7+ ; non mesuré ici).

## Vérifications E1 (2026-11-18)
- Texte de l'avis officiel : non disponible via l'API. `https://www.boamp.fr/avis/detail/<idweb>` répond 200 mais c'est une application JavaScript (la page ne contient pas le nom de l'acheteur) ; `https://www.boamp.fr/avis/pdf/<idweb>` et `https://www.boamp.fr/api/avis/pdf/<idweb>` répondent 404. D'où un rendu texte généré depuis `donnees` (voir `docs/HANDOFF.md`).
- Valeurs du jeu (fenêtre 2026-09-01 à 2026-11-15, familles JOUE/FNS/MAPA) : `etat` = INITIAL, RECTIFICATIF, ANNULATION (JOUE) ; INITIAL seul pour FNS et MAPA ; `type_marche_facette` = Fournitures, Services, Travaux (valeur renvoyée en liste dans les enregistrements).
- Pagination Explore v2.1 : `offset + limit <= 10000` (erreur `InvalidRESTParameterError` sinon, relevée) ; d'où des fenêtres de dates hebdomadaires pour lister le pool.
- Structure `donnees` (relevée sur 100 avis par famille, 2026-09 à 2026-11) : JOUE = `EFORMS/ContractNotice` (acheteur dans `efac:Organizations` référencé par `cac:ContractingParty`, procédure `cbc:ProcedureCode`, date limite par lot `cac:TenderSubmissionDeadlinePeriod`, critères `cac:SubordinateAwardingCriterion` avec poids `efbc:ParameterNumeric`) ; FNS = `FNSimple` (procédure `procedureAdapteeO` ou `procedureAdapteeR`, critères en texte libre) ; MAPA = `MAPA` (aucun CPV structuré, aucun montant structuré, critères pondérés `criterePondere`).

## Vérifications E2 (2026-11-18)
- Sorties structurées : `output_config.format = {"type": "json_schema", "schema": ...}` (pas d'en-tête beta), tous objets `additionalProperties: false`. Limites : 24 paramètres optionnels, 16 paramètres à type union (`anyOf` ou type tableau) ; `minimum`/`maximum`/`minLength`/`maxLength`/`oneOf`/`$ref` externes refusés ; refus (`stop_reason: refusal`) et `max_tokens` peuvent donner une sortie hors schéma. Un système de prompt est ajouté automatiquement par l'API (tokens facturés). Source : `https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md`.
- Requête : `POST https://api.anthropic.com/v1/messages`, en-têtes `x-api-key`, `anthropic-version: 2026-10-21` (valeur des exemples de la doc), `content-type: application/json`. Source : même page.
- Réflexion adaptative ; l'effort se règle par `output_config.effort` (`low` à `max`, `medium` par défaut pour Opus 5.5 et Haiku 5.5, `high` pour Sonnet 5.5) ; tokens de réflexion facturés comme sortie. Source : `.../build-with-claude/effort.md` et `.../adaptive-thinking.md`.
- Usage : `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, détail `cache_creation.ephemeral_5m_input_tokens` / `ephemeral_1h_input_tokens` (relevés sur l'essai réel), `output_tokens_details.thinking_tokens`. Source : `.../prompt-caching.md` et essai réel.
- Message Batches : `custom_id` de 1 à 64 caractères `^[a-zA-Z0-9_-]{1,64}$` ; lignes de résultat `{"custom_id", "result": {"type": "succeeded" | "errored" | ...}}`. Source : `.../batch-processing.md`.
- Essai réel Haiku 5.5 (3 avis du dev, `effort: low`) : cache de prompt effectif (1 658 tokens écrits au 1er appel, lus aux 2e et 3e, donc le minimum de cache de Haiku 5.5 est <= 1 658 ; valeur exacte non déterminée), 0 token de réflexion, `stop_reason: end_turn`.
