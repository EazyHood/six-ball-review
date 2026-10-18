# Contract for the next profile dataset

Status: producer implemented and executed, 2026-10-18. This does not modify analysis-plan.json, select a model or recompute the observed 2026 test. The JSON Schema and semantic invariants passed; independent method review and interface integration are coordinated by root.

The producer emits compact `dist/data.json`, validated against `ui-contract.schema.json`. The interface consumes that file and uses the same values for its review-sheet export. Do not type statistics into components. No example with invented player statistics is provided.

## Exact minimum fields

| Meaning | JSON field | Definition |
|---|---|---|
| Stable row identity | profiles[].profile_id | player_id + ":" + phase within this fixed-window snapshot |
| Player and phase | player_id, player_name, phase | Registry ID, display name, one of 1-6 / 7-15 / 16-20 |
| n and matches | legal_deliveries, matches | Legal-ball count and distinct included matches in that phase |
| Observations | counts.dot / boundary / other | Counts summing to n |
| Raw | raw.dot / boundary / other | counts / n, or raw=null if n=0 |
| q | reference.rates.dot / boundary / other | Excluding-player phase rates, or explicitly labeled pooled fallback |
| Shrunk | regularized.dot / boundary / other | (counts + 240*q)/(n+240) |
| Illegal deliveries | illegal_deliveries, illegal_rate | Count; rate=illegal/(legal+illegal), or null if total=0 |
| Provenance | match_rows[].match_id, source_sha256 | Exact member ID/hash; also date, season, teams, venue, counts and illegal count |
| Training bands | checks.bands.dot / boundary / other | Each has lower/upper, or whole object null until computed |
| Contrast bands | checks.contrasts_vs_reference.dot / boundary | Each has estimate/lower/upper; reference is recomputed in paired training resamples |
| Bootstrap absence | checks.absent_bootstrap_replicates | Replicates with no player/phase history; null until computed |
| Sensitivity | checks.leave_one_match, checks.remove_dominant_venue | Status, deletion IDs, reversal IDs and contrast ranges; null until computed |
| Abstention | evidence.status/reasons, checks.status/reason, review.status/reasons | Separate sample coverage, computation status and comparison state |
| Review sheet | review_sheet.phase, selected[].profile_id/question/note | phase is active view only; manual selection max three unique profiles, each retaining its own phase; export copies snapshot rows and provenance |

Profile fields in the table are relative to `profiles[]` unless a full path is shown. A sensitivity range's estimate is the original full-training contrast; lower/upper are min/max after deletions, not confidence bounds. `remaining_legal_deliveries` is the smallest remaining n across deletion cases. Removed and sign-reversal IDs always identify matches, including matches at a removed venue. The venue is recoverable from those provenance rows.

## Frozen scope and provenance

- Evidence for profiles is the included 2023–2025 first innings only. This is the final training population after model selection, not the 2026 evaluation set. A default view uses the full fixed population; dynamic season, opponent and venue filters are outside the minimum contract.
- Smoothing remains m=240, chosen on 2025 by the existing pipeline. Do not tune m, evidence thresholds or sample selection against 2026 performance. Record the selected model source file and its hash.
- The 2026 evaluation carries the immutable baseline-results.json filename and SHA-256 plus copied aggregate model metrics, calibration and paired differences (excluding per-match losses). No metric is recomputed. It is not mixed into profile counts, bootstrap bands, examples chosen for apparent success, or sensitivity.
- Record the canonical dataset hash, profile producer code hash, plan hash, all input artifact hashes, generation UTC time, scope, seasons, phase definitions and license attribution. IDs are Cricsheet registry identifiers, not display names.
- The displayed player universe is bowlers already present in included 2023–2025 data, crossed with the three phases. Do not discover players from 2026 just to manufacture no-history examples.
- `match_ids` resolve through the manifest. Every per-match row carries its source SHA-256, date, teams, venue if available, phase and counts. Missing optional venue is null; no invented venue or opponent.

## Values and uncertainty

The ordered category object is dot / boundary / other, but consumers access names, not array position. Counts use legal deliveries. A dot has zero total runs; a boundary is an actual batter four/six, excluding `non_boundary`; illegal deliveries have a separate integer count and denominator. These are not conventional economy or credited wickets.

For each player/phase, preserve raw counts, legal deliveries, illegal deliveries, number of distinct matches, and contributing match IDs. Raw rates are null when n=0. The league reference is calculated excluding the player when it has data; the reference object must say whether it uses `excluding_player` or `pooled_fallback`. The regularized vector is the existing C formula. Do not present the reference excluding a player as the pooled B0 used in the experiment.

The implemented profile band calculation resamples the **whole final-training match population**, with replacement, recomputing both the reference q and player profile at fixed m in each replicate. It uses 2,000 replicates, seed 20261018, percentile 95% intervals. A profile absent from a replicate uses the declared pooled fallback, and the output reports its absent-replicate count. This band describes resampling stability conditional on the selected model, not a probability of intrinsic skill or a full posterior. Execution and actual coverage are recorded in VALIDATION.md.

Keep paired bootstrap contrasts against the reference for dot and boundary, and against a second profile only when such a comparison is actually computed. Dot and boundary stay separate: no opaque overall score. Intervals spanning zero mean no separation by that contrast; they do not prove equality. Multiple inspected profiles remain exploratory. Avoid stars, winner badges and claims of simultaneous statistical significance.

Leave-one-match sensitivity includes the range of the recomputed regularized contrast and the match IDs causing a sign reversal relative to the reference. It also removes the dominant venue (most legal deliveries, tie broken by canonical venue text) when known. `venue-aliases.json` merges only the documented Mullanpur/New Chandigarh stadium alias pair, backed by Punjab Cricket Association; raw provenance labels remain intact. All 15 distinct training labels were inspected and Mohali remains separate. Report coverage and before/after rates. Missing venue sensitivity is `unavailable`, with a reason. A 120-delivery threshold check changes eligibility coverage only; it does not refit m. No new ranking statistic is introduced.

## Evidence and abstention

Two independent fields prevent an uncomputed check from looking reassuring:

1. `evidence.status`: `no_history` for n=0; `limited` for fewer than 60 legal deliveries or fewer than five distinct matches; `adequate_for_review` otherwise. These are operational thresholds, not statistical guarantees. Every value includes a reason code.
2. `checks.status`: `not_computed`, `complete`, or `unavailable`. For an adequate-sample profile, until required bands and leave-one-match checks are available, `review.status` is `pending_checks`; never label the profile stable. No-history and limited-sample profiles already have a definite abstention, even before these checks run.

After checks: no-history and limited profiles have `review.status=abstain` with explicit reasons. With enough evidence, a sign reversal or a dot/boundary contrast interval crossing zero yields `review.status=uncertain`; otherwise it is `reviewable`. This status describes the stated comparison with the reference, not all possible comparisons. Boundary and dot directions remain visible, including conflicts. Neither `uncertain` nor `reviewable` automatically recommends a lineup. A selected pair must retain its own comparison result rather than inheriting a blanket claim of separation.

The analyst may save a case with limited or uncertain evidence as a **review question**, provided its abstention reason is carried verbatim into the export. There is no automatic top-three or forced filling. A missing-data/failed-check state cannot be silently dropped. No-history cases show a league fallback, not a personal estimate or rank.

## Minimal workflow and export

The supported workflow is fixed evidence window → phase → inspect raw and regularized values together → inspect provenance/sensitivity → manually select zero to three profiles → export a review sheet. Default ordering is player display name followed by player ID, not outcome ranking.

The export retains dataset/producer/plan versions, fixed seasons and active viewing phase, snapshot creation time, up to three unique profile IDs with each profile's own phase, numbers and evidence/check/review state, the analyst's review question and note, match IDs, license notice and short contextual limitations. Profiles from different phases may be saved together but must not be numerically compared across phases; notes survive phase changes. It does not include video assets or claim the user reviewed footage. A default review question is explicitly a prompt, never a reported finding.

Contract invariants require executable validation when the producer is built: finite values only; probabilities and interval bounds in [0,1]; vectors sum to one within 1e-9; legal n equals the three counts; distinct match count matches provenance; illegal+legal equals all deliveries; intervals ordered; source matches belong only to 2023–2025; n=0 has null raw rates; incomplete checks cannot produce a `reviewable` state; selected profiles are unique and at most three; export numbers and states equal the source snapshot. JSON Schema alone cannot verify these relations.

Root's independent code review may identify necessary correctness fixes. Record any corrected experiment version and its reason rather than rewriting the original selection history or quietly presenting a recomputed 2026 result as a new untouched test.

## Reproducible next steps

Run `python -m unittest -v test_profiles`, then `python profiles.py --dataset-dir <existing-canonical-directory>`. This generates only dist/data.json; the existing four experiment artifacts are hash-checked before and after. Validate the JSON against ui-contract.schema.json, consume it through the UI, and compare the exported values/states to the source snapshot. The profile CLI verifies the existing ZIP but does not download or copy it. `reproduce.py` separately provides a portable audit adapter and refuses an existing output directory. Its default audit execution does not rerun 2026 model evaluation.
