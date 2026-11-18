# boamp-llm-eval

Français : [README.fr.md](README.fr.md)

A small, reproducible benchmark. It asks three Claude models to pull structured fields out of French public procurement notices (BOAMP) and scores each field against a reference. Everything is in the repository: the 100-notice dataset, the raw model responses, the scoring code, and the cost accounting.

The models are Claude Haiku 5.5, Sonnet 5.5 and Opus 5.5. The nine fields are buyer, object, place of performance, procedure, deadline, CPV codes, lots, estimated amount and award criteria.

Read the limits before the numbers. The input is not the published notice, and the confidence intervals overlap. The data does not rank the three models.

## What it does

1. `build` samples 100 notices from the BOAMP open data (September 1 to November 15, 2026) and splits them into 80 for development and 20 for a hold-out. The sample is stratified by market family (JOUE 40, FNS 35, MAPA 25) and by contract type.
2. It renders each notice as plain French text, masks personal data, and keeps the structured fields as the reference.
3. One frozen prompt and one JSON schema go to all three models through the Message Batches API.
4. Each field has its own metric (normalized equality, F1 on sets, tolerance on amounts and dates). A bootstrap gives 95 % intervals.
5. The report lists scores, intervals, cost per notice and error counts.

## Run it

Python 3.13 or later and [uv](https://docs.astral.sh/uv/) are required.

```bash
uv sync
uv run pytest
uv run ruff check .
```

Rebuild the report from the saved responses. This needs no network and no API key.

```bash
uv run python -m boamp_eval.report_md      # writes reports/results-2026-11.md
uv run python -m boamp_eval.errors         # writes reports/analyse-erreurs.md
uv run python -m boamp_eval.batch replay --model claude-opus-5-5 --split dev --name e3-dev-opus
```

Run the models again. This spends money. Pass the key through the environment of the command only.

```bash
export ANTHROPIC_API_KEY=...   # your own key
uv run python -m boamp_eval.batch estimate --model claude-sonnet-5-5 --split dev --name my-run
uv run python -m boamp_eval.batch submit   --model claude-sonnet-5-5 --split dev --name my-run
uv run python -m boamp_eval.batch collect  --model claude-sonnet-5-5 --split dev --name my-run
```

`estimate` prices the worst case. `submit` refuses to start if the ledger in `data/costs-ledger.json` would pass the cap set in `src/boamp_eval/costs.py` (15 USD by default). `--effort` sets the effort level (default in this tool: `low`). `--split holdout` is refused unless `docs/FREEZE.md` is committed.

Rebuild the dataset from the BOAMP API (network needed):

```bash
uv run python -m boamp_eval.build --seed 20261118 --out data
```

The BOAMP database changes over time, so a rebuild can differ from the committed files. The committed files are the reference.

## Results

All figures come from `reports/results-2026-11.md`, which is generated from `data/runs/`. Same prompt, same schema and the same `max_tokens` (4096) for the three models, effort `low`, batch pricing.

The hard score is the mean over the fields that cannot be copied from the input: deadline, amount, criteria, CPV and place. 95 % intervals in brackets.

| Model | Dev (80 notices) | Hold-out (20 notices) | Cost per notice (dev, USD) |
|---|---|---|---|
| Haiku 5.5 | 0.852 [0.803 ; 0.900] | 0.896 [0.800 ; 0.988] | 0.00014 |
| Sonnet 5.5 | 0.864 [0.808 ; 0.920] | 0.909 [0.800 ; 1.000] | 0.00254 |
| Opus 5.5 | 0.917 [0.863 ; 0.967] | 0.859 [0.700 ; 1.000] | 0.00507 |

All the intervals overlap, on dev and on hold-out. The order changes between the two sets. No ranking is established.

Per field on dev, `criteres` is the weak one: Haiku 0.316, Sonnet 0.421, Opus 0.632 (19 notices). The other hard fields sit between 0.94 and 1.00 for all three models.

Default effort. After reading the results above, I ran Sonnet at its default effort (`high`) and Opus at its default (`medium`) on the dev set only. Same prompt.

| Model | Effort | Hard score (dev) | `criteres` | Cost per notice (USD) |
|---|---|---|---|---|
| Sonnet 5.5 | low | 0.864 [0.808 ; 0.920] | 0.421 | 0.00254 |
| Sonnet 5.5 | default (high) | 0.864 [0.808 ; 0.921] | 0.421 | 0.00274 |
| Opus 5.5 | low | 0.917 [0.863 ; 0.967] | 0.632 | 0.00507 |
| Opus 5.5 | default (medium) | 0.916 [0.856 ; 0.969] | 0.684 | 0.00585 |

More effort cost 8 to 15 % more and changed no score beyond the intervals.

Total spent on API calls for the whole project: 1.42 USD (including the first trial and the default-effort runs).

### Where the criteria errors come from

`reports/analyse-erreurs.md` classifies every wrong answer from the saved responses, with no new call. On dev, `criteres` has a reference for 19 notices (13 JOUE, 6 MAPA).

Most errors are a formatting artifact. For JOUE notices, my rendering of the input adds the criterion type after each label, for example "Prix (prix)" or "Valeur technique (qualité)". The prompt says to copy values as written, so many answers keep the suffix, and the metric requires an equal label. Haiku did it on 12 of 19 notices, Sonnet on 10, Opus on 6. With the suffix removed, all three models score 0.947 on this field. The remaining 0.053 is one notice, 26-108247.

That notice has 250 lots. The JSON list of lots is longer than `max_tokens`, so all three models are cut off and the answer is unusable. The same happens at default effort. I did not change the frozen parameters to recover it.

So the 0.316 to 0.632 gap on `criteres` mostly measures how literally each model copies a label that my input format decorated. It says little about reading award criteria. I kept the frozen metric for the headline numbers and report the suffix-free figure next to it as an after-the-fact reading.

## Limits

- The input is rebuilt from structured fields. The official notice text was not available, so the model reads a French rendering generated from the same JSON that gives the reference, not the notice as published.
- That makes the task partly circular. Object, buyer and lot titles are copied almost verbatim. They are reported separately (annex of the report) and left out of the main score.
- The sample covers 11 weeks of autumn 2026, with quotas chosen by me (40/35/25), not the real proportions of the notices.
- The numbers are small. 80 notices on dev, 20 on hold-out (JOUE 8, FNS 7, MAPA 5), and only 19 and 5 for `criteres`. Per-family conclusions are out of reach.
- The intervals overlap. I claim no superiority of one model over another.
- Effort `low` was a protocol choice for a fair comparison. The default-effort run covers Sonnet and Opus on dev only.
- The reference is the structured part of each notice. For FNS and MAPA, amounts and criteria that appear only in free text are not in the reference and are excluded from scoring.
- Masking uses patterns and the contact fields of each notice. A personal name with no title and outside those fields could remain.
- The hold-out was used once, after the freeze (`docs/FREEZE.md`). It must not be run again to tune anything.

## Layout

```
src/boamp_eval/   code (collection, rendering, masking, metrics, batch client, report)
data/             dev.jsonl, holdout.jsonl, manifest, raw responses (runs/), cost ledger
docs/             sources, metrics, freeze, costs
reports/          generated report and error analysis
tests/            tests, offline
```

## License

The code is under the MIT license (`LICENSE`).

The dataset (`data/dev.jsonl`, `data/holdout.jsonl`) is derived from BOAMP notices.

Source: BOAMP, DILA (Premier ministre). Data queried through the BOAMP API on November 18, 2026, published at https://www.data.gouv.fr/datasets/boamp. Licence Ouverte / Open Licence, version 1.0 (identifier `fr-lo` on data.gouv.fr, text: https://www.etalab.gouv.fr/wp-content/uploads/2014/05/Licence_Ouverte.pdf). Dataset page last updated: November 12, 2026.

The files are a modified selection: text rendering, extracted reference fields, masked personal data. They are not the official notices and the DILA neither endorses nor guarantees them. See `data/NOTICE.md`.
