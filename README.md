# Six-Ball Review

[Open the app](https://eazyhood.github.io/six-ball-review/) · [Two-minute walkthrough](WALKTHROUGH.md) · [Validation](VALIDATION.md) · [Credits](CREDITS.md)

Six-Ball Review is a local descriptive cricket-analysis prototype prepared for AQX Sports Analytics Data Bowl 4.0. It combines training-only player profiles, explicit abstention, match provenance and an exportable review sheet. Publication and submission are managed separately; this repository does not itself establish an accepted submission.

Its task is to help an analyst choose phase-specific bowling profiles for video review. It does not choose a lineup, estimate wins, infer causal player ability, or provide betting advice. Players are initially ordered by name; the analyst chooses up to three cases and writes review questions. Cases from different phases retain their own context and are not ranked against each other. No sports video is bundled.

## Run the interface

With Node.js 20 or newer, run `npm start`, then open `http://127.0.0.1:4182`. No install, API key or backend service is required. The local server exposes only `dist/`. The prebuilt `dist/data.json` is the source for displayed and exported numbers. `npm test` runs the interface logic tests; browser verification is documented by the interface reviewer separately.

## Reproduce

Python 3.10+ and its standard library are sufficient for all calculations and semantic checks. No API keys or paid services are required. JSON Schema validation additionally used the already available `jsonschema` library as a separate verification; the producer does not depend on it.

```powershell
python -m unittest -v test_pipeline test_profiles
python profiles.py --dataset-dir /path/to/frozen-cricsheet-ipl
python reproduce.py --dataset-dir /path/to/frozen-cricsheet-ipl --output-dir /path/to/new-audit-output
```

Replace the example paths with existing local locations. The dataset directory must contain acquisition.json and the checksum-matching ZIP; the portable producer resolves its basename even if the original manifest records a Windows path. `profiles.py` regenerates `dist/data.json` from the committed sufficient statistics and verifies the canonical ZIP, original plan and pipeline fingerprints. It never reruns the 2026 evaluation. Generated timestamps change on rerun, while fixed-seed numerical content is deterministic.

`reproduce.py` is a portability adapter around unchanged pipeline functions. By default it recreates the audit and sufficient statistics into a **new** directory; existing output is refused. Our executed portability check produced byte-identical match manifests and counts. Only the explicit `--models` option also reruns the already observed fixed comparison into that new directory. Doing so does not create a new untouched test. The original pipeline, plan and result files remain unchanged.

The historical acquisition script uses a local default path and downloads only the official [Cricsheet IPL JSON](https://cricsheet.org/downloads/) archive. It reuses a checksum-verified existing ZIP. The exact snapshot is deliberately frozen; the provider may revise its current archive, in which case the checksum guard stops instead of silently substituting data. Do not edit the frozen pipeline to change paths or replace the dataset to obtain a more favorable result.

## Frozen archive for durable reproduction

The planned `v1.0.0` release asset is `ipl-json-2026-10-18.zip` in [EazyHood/six-ball-review releases](https://github.com/EazyHood/six-ball-review/releases/tag/v1.0.0). **Publication of this release asset has not yet been confirmed.** Once the coordinator confirms it, download that asset manually; the adapter does not fetch files or require an account. The intended asset URL is `https://github.com/EazyHood/six-ball-review/releases/download/v1.0.0/ipl-json-2026-10-18.zip`.

The unchanged archive is 5,187,770 bytes, SHA-256 `5757e04287179767ff8495f02902bd13812b9572ec8fa2ac1347ec2e9c6d4709`. Its original README.txt and full LICENSE.txt remain inside. It contains information from [Cricsheet](https://cricsheet.org/) under [ODC-By 1.0](https://opendatacommons.org/licenses/by/1-0/); the code's MIT license does not replace the data license. Preserve these notices when redistributing the archive or derived data. No affiliation or endorsement is claimed.

Use a ZIP downloaded to any local directory, without an acquisition manifest:

```text
python reproduce.py --archive /path/to/ipl-json-2026-10-18.zip --output-dir /path/to/new-audit-output
```

The adapter verifies the recorded SHA-256 before reading matches and writes only to a fresh output directory. It neither copies nor extracts the ZIP. Add `--models` only to reproduce the previously observed fixed temporal comparison, never to retune it. A different upstream archive will be rejected rather than treated as equivalent.

To also regenerate `dist/data.json` from this manual ZIP, place a file named `acquisition.json` beside it with the following exact content, then run `python profiles.py --dataset-dir /path/to/that-directory`. This small compatibility manifest identifies the already downloaded file; it does not download or duplicate it. If a manifest already exists, inspect it rather than replacing it blindly.

```json
{"local_path":"ipl-json-2026-10-18.zip","sha256":"5757e04287179767ff8495f02902bd13812b9572ec8fa2ac1347ec2e9c6d4709"}
```

## Scope

IPL men's cricket, first innings, scheduled 20 six-ball overs. Revised matches and reduced chase targets are excluded conservatively, including cases where the first innings was complete. Incomplete first innings are excluded. Early all-outs remain included. A completed first innings remains usable even if the overall match later had no result. Other innings and super overs are not modeled.

The three analytical blocks are overs 1–6, 7–15 and 16–20. They are intervals, not inferred field-restriction metadata. Categories on legal deliveries are zero total runs, batter boundary, and other. Wides/no-balls are counted separately and are excluded from that denominator. The prototype does not compute conventional bowling economy or wicket credit.

## Outputs

- `analysis-plan.json`: temporal split and model-selection contract written before the archive and model results.
- `data-gate.json`: actual source coverage, inclusion/exclusion counts, versions and checksums.
- `match-manifest.json`: every candidate match and its inclusion reason or exclusion, raw-member checksum and provenance.
- `match-phase-counts.json`: match × bowler × phase sufficient statistics, preserving illegal deliveries and provenance.
- `baseline-results.json`: validation candidates, the selected model, 2026 held-out comparison, calibration bins and paired match bootstrap.
- `profiles.py` / `dist/data.json`: fixed 2023–2025 profiles, training-match bootstrap bands, sensitivity, explicit abstention, sources and copied evaluation aggregates.
- `venue-aliases.json`: one documented Mullanpur/New Chandigarh stadium alias pair used only for dominant-venue sensitivity; raw labels remain in provenance.
- `reproduce.py`: portable adapter for reproducing the unchanged experiment in a separate output directory.
- `scorecard-check.md`: completed independent agent check of three selected match totals/overs against official sports sources, with access limits.
- `VALIDATION.md`: current results, limitations and unfinished checks.
- `ui-data-contract.md` and `ui-contract.schema.json`: specification for the training-only profile/export dataset; see the contract for implementation status.

Displayed and exported statistics come from these files. Reusing the 2026 holdout to choose further models would make it development data; it must not keep the label “untouched test”. The profile generator uses only known 2023–2025 bowlers crossed with three phases, including phases with no history. It does not add players discovered in 2026 or pick examples from their test outcomes.

The generated snapshot has 519 profiles for 173 bowlers, based on 212 matches and 25,297 legal deliveries. It labels 81 profiles with no phase history, 297 with limited evidence and 141 with enough volume for review. After uncertainty and sensitivity checks, 378 abstain, 138 remain uncertain and three are reviewable. “Reviewable” means the stated contrast is separated and does not reverse under these checks; it does not mean better, causally skilled, or suitable for a lineup. Default thresholds are 60 legal deliveries and five matches, with the effect of increasing the delivery threshold to 120 retained.

## Main result and limit

The fixed experiment trained on 2023–2024, selected one global smoothing value using 2025, then refitted on 2023–2025 and evaluated on 2026. Selected smoothing: 240 equivalent legal deliveries.

In the 2026 sample of 71 first innings and 8,479 legal deliveries, multiclass Brier loss was 0.626730 for the regularized profile, 0.628136 for the pooled phase reference, and 0.639197 for the unregularized player/phase table. Lower is better. The improvement against the pooled reference is small: 0.001407 absolute Brier units. This is retrospective predictive evaluation on an observational, filtered sample, not demonstrated impact in coaching decisions.

21.02% of evaluated deliveries had no earlier player/phase history in the selected training population and used the pooled reference. Match bootstrap intervals capture only part of uncertainty; dependence between recurring players, venues and opponents is not fully removed by resampling matches. Data revisions, contextual confounding and drift remain relevant.

## Data and code licenses

Contains information from [Cricsheet](https://cricsheet.org/), available under the [ODC Attribution License 1.0](https://opendatacommons.org/licenses/by/1-0/). See [Cricsheet licensing](https://cricsheet.org/licensing/). The canonical ZIP retains the provider's README.txt and LICENSE.txt. Derived datasets must retain the attribution and relevant data notices. MIT covers our original source code only.

No affiliation with Cricsheet, IPL, BCCI, franchises or players is claimed. No logos, photographs or video are included. See CREDITS.md for the actual use of AI and external resources.
