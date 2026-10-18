# Validation at the data gate

Executed on 2026-10-18. This file reports a minimum analytical foundation, not completion of the proposed product.

## Acquisition and coverage

The official Cricsheet IPL ZIP downloaded without payment, credentials or account has 1,243 JSON files, README.txt and LICENSE.txt. It is 5,187,770 bytes. SHA-256:

`5757e04287179767ff8495f02902bd13812b9572ec8fa2ac1347ec2e9c6d4709`

All 1,243 actual match files report schema 1.2.0. The provider's README mentions both 1.2.0 and 1.3.0; the audit reports file contents, not the broader README declaration.

| Season | Source matches | Included first innings | Excluded | Legal deliveries | Illegal deliveries |
|---|---:|---:|---:|---:|---:|
| 2023 | 74 | 71 | 3 | 8,505 | 374 |
| 2024 | 71 | 70 | 1 | 8,369 | 425 |
| 2025 | 74 | 71 | 3 | 8,423 | 421 |
| 2026 | 74 | 71 | 3 | 8,479 | 431 |
| Total | 293 | 283 | 10 | 33,776 | 1,651 |

Exclusions: four revised-method matches, three explicitly reduced chase targets and three unfinished/reduced first innings. A shortened game can still have info.overs=20 and no D/L label: the chase target is material. The parser keeps 18 early all-out innings and two completed first innings in matches that later had no result. Every candidate is recorded in match-manifest.json.

Internal checks passed for included data: required run components, extras reconciliation, sequential over indices, six legal deliveries in non-final overs, presence of a bowler registry ID, category count conservation, group total conservation and first-innings total against the unmodified chase target when present. The independent code/data review additionally checked actual bowling-team roster membership, registry-ID format and duplicate dismissals with no errors in the included data; roster membership is not an automatic guard in the current parser. These are consistency checks, not proof that every provider event is correct.

## Behavioral controls

`python -m unittest -v test_pipeline` passed 13 tests. They cover dots, actual and non-boundary fours/sixes, byes, wides/no-balls, absent or inconsistent fields, phase boundaries, early all-out versus unfinished innings, reduction without a D/L flag, retired hurt, complete innings in no-result matches, missing identity, miscounted overs, optional missing metadata, target reconciliation, independently expanded Brier arithmetic and simple shrinkage/unseen fallback.

These synthetic controls are not real-user or predictive validation. Real-data evaluation below is separate.

Executed pipeline SHA-256:

`55399e5b11724076005b6ff21c805a2a7a4020cab98dde157f56e8277946409a`

Pre-result analysis-plan SHA-256:

`599ee1e5fe31b5e20048696686db6c79312c181ead70bd141199ccb46a766d06`

## Temporal comparison

Train 2023–2024; validation 2025; reserved test 2026. Dates were checked to be strictly ordered between splits. The single global value m=240 minimized validation Brier among the locally recorded pre-result values 24, 60, 120 and 240. This was a local plan written before downloading and viewing model results, not an independently timestamped public preregistration. The model was refitted on 2023–2025 before test evaluation. No test outcome was used to select m.

| 2026 test | Mean multiclass Brier | Mean log loss | Macro player/phase Brier |
|---|---:|---:|---:|
| B0: pooled league/phase | 0.628136 | 1.042688 | 0.640599 |
| B1: unregularized player/phase | 0.639197 | 1.157349 | 0.653597 |
| C: regularized player/phase | 0.626730 | 1.040566 | 0.639597 |

All methods saw the same 71 matches / 8,479 legal deliveries. Brier here sums squared error across three categories and then averages over deliveries; it is not an accuracy percentage. Log loss clips at 1e-6 and renormalizes for all models.

Paired resampling of 71 whole matches, 2,000 replicates, seed 20261018, percentile 95% intervals for candidate minus baseline:

- C − B0: −0.0014067; interval [−0.0021793, −0.0006602].
- C − B1: −0.0124678; interval [−0.0162183, −0.0089160].

Negative favors C. The margin against B0 is small, despite this interval excluding zero under the chosen resampling scheme. Players, teams and venues recur between matches, so match clustering does not fully model all dependence. These intervals are conditional on the selected model and this dataset; they do not account for all model-selection or data-quality uncertainty.

Unseen player/phase history accounts for 21.02% of test deliveries, which fall back to B0. Calibration bins and per-phase results, including sample sizes, are retained in baseline-results.json; no claim of perfect calibration is made. m=240 lies at the top of the planned grid. The grid was not expanded after inspecting test results.

## Independent checks and remaining work

The independent scorecard review is documented separately in scorecard-check.md, with exact source links and limits. It checks a complete first innings, an early all-out and a reduced game; it does not certify the full archive.

At the original data gate, profile bands and sensitivity were pending; their subsequent execution is recorded below. Interface behavior, browser/export validation, judge access, full form and submission are separate checks. Contextual effects of opponents, batters, venues, fielding, score and selection remain uncontrolled. Cohort inclusion uses completion/reduction information from the chase: this is a retrospective evaluation conditional on the stated filtered population, not a live forecast available before the match. There is no coaching user study, no causal skill estimate and no measured time saved.

Gate verdict: data access and the planned temporal experiment are feasible. Proceed to a narrowly scoped descriptive review interface only with these limitations visible; do not present the loss difference as a promised sporting improvement.

Contains information from [Cricsheet](https://cricsheet.org/) under [ODC-By 1.0](https://opendatacommons.org/licenses/by/1-0/).

## Training-profile extension, 18 October 2026

`profiles.py` generated compact `dist/data.json` exclusively from included 2023–2025 data. It does not invoke the baseline-fitting or evaluation functions. The universe is 173 known bowlers crossed with three phases: 519 profiles, 212 matches, 25,297 legal deliveries and 1,220 illegal deliveries. Eighty-one profiles have no history in their phase; these show null raw rates and an explicitly labeled league fallback.

All 519 regularized vectors agree exactly with the frozen pipeline's C prediction on the same final-training counts (maximum absolute discrepancy 0.0). The three categories reconcile with per-match provenance. Illegal rate uses illegal/(legal+illegal). All probability vectors, bands, dates, source IDs, evidence thresholds and review states passed semantic validation; the complete payload passed Draft 2020-12 JSON Schema validation using the available jsonschema library.

The producer executed 2,000 whole-training-match bootstrap replicates with seed 20261018, recalculating the excluding-player reference and profile at fixed m=240. It records absent-player replicates, paired profile-minus-reference dot/boundary intervals, all-match leave-one-out ranges and removal of each profile's dominant known venue. These are exploratory stability summaries, not simultaneous discoveries or a posterior distribution of player talent. Leave-one-out and venue ranges are min/max after deletions, not confidence intervals.

Coverage states are 81 no-history, 297 limited and 141 adequate for review. Final comparison states are 378 abstain, 138 uncertain and three reviewable. Both favorable and unfavorable separated contrasts can be reviewable; there is no automatic ranking or claim of superiority. The 2026 panel is an exact copy of existing aggregate results, with its source hash. The macro test metric averages 254 player/phase pairs; those pairs are not the 519 training UI profiles.

Thirteen new behavioral tests passed: closed-form excluding-player shrinkage, no-history fallback, both evidence thresholds and their exact boundaries, illegal denominator, count/provenance conservation, 2026 leakage prevention, duplicate rejection, deterministic paired bootstrap, leave-one-match reference recomputation, full-venue deletion, missing-venue abstention, pending/uncertain states and export selection constraints. Together with the original parser suite there are 26 Python tests. A portability audit via reproduce.py produced byte-identical match-manifest.json and match-phase-counts.json without rerunning models. Original pipeline.py, analysis-plan.json, baseline-results.json and data-gate.json remained unchanged.

First profile-handoff SHA-256 was `f22a7ff6ac5a53ffaadfd4a09afc42908314930dd6bd0d8c2c50ccd784ef99b3`; the documented venue correction below supersedes it. Later generations can differ in timestamp and producer fingerprint; retain the exact delivered version and its checks. No per-player pairwise comparison is computed. Browser validation and independent profile-code review must report their own findings rather than inheriting these numeric checks.

### Venue-alias correction after independent review

The independent profile reviewer identified Mullanpur and New Chandigarh labels for the same stadium. [Punjab Cricket Association's primary document](https://cricketpunjab.in/pdf/Terms-condition--2024444.pdf) identifies its new international ground at Mullanpur (New Chandigarh). All 15 distinct training labels were inspected; this was the only documented alias pair merged. Mohali remains a different ground. venue-aliases.json records the map and source; the original data, per-match raw labels and source hashes are unchanged.

The corrected sensitivity removes all 11 matches of this stadium together instead of splitting them 10+1. Eleven profiles' dominant-venue checks change; raw/shrunk/reference probabilities, all bootstrap bands, leave-one-match checks, provenance and every evidence/review status and reason are unchanged. This corrects a grouping defect, not model selection. A new alias regression test passed, bringing the profile suite to 14 and the Python suites to 27. JSON Schema and semantic checks passed again.

Current profile snapshot SHA-256: `0f911ad37a21689493e33b23d496a2fdcd0dbb429c3527c8b7cbdfc4a2892d60`. The venue adapter stores match IDs in a removed group; a group of 11 IDs is one venue deletion, not 11 separate stability trials. No 2026 model evaluation was rerun.

### Independent profile and interface closure

A separate agent implementation read the raw ZIP and reproduced all 519 point estimates and provenance, all leave-one-match checks, and the 438 available dominant-venue checks. It independently reproduced 2,000 bootstrap replicates for eight selected profiles, including the three reviewable cases, within 1e-12. The venue correction was then retested against the raw data: the 11 affected checks include all 11 matches at the grouped stadium. Fingerprints confirmed the non-venue fields and original experiment were unchanged. This is independent agent code review, not an external statistical audit or human user study.

The final integrated run passed 27 Python tests and nine Node interface/server tests. Actual browser checks covered filtering, empty results, phase changes, three-case limits, question validation, Unicode notes, readable HTML and exact JSON downloads. The final downloaded JSON's source checksum matched the snapshot above and all three exported profile objects equaled their complete source objects. Synthetic script text was displayed literally in exported HTML. Targeted 390- and 320-pixel viewport checks found no document overflow, with local scrolling for the table; keyboard activation was checked. Full screen-reader behavior and physical devices were not tested. See README-UI.md for the UI review scope.
