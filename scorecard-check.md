# Independent scorecard check — three prespecified first innings

Reviewed on 18 October 2026, completed at approximately 12:08 UTC, by Codex subagent `scorecard_check`. This is a narrow data-quality check for Six-Ball Review. It is not model validation or a review of the reserved season's aggregate results.

## Method and scope

Read only `1359475.json`, `1473468.json` and `1527686.json` directly from the canonical archive `D:/IA/datasets/cricsheet-ipl/ipl-json-2026-10-18.zip`. These cases were assigned before this review: a full first innings, an early all-out, and a reduced match. I did not read, import or run the project's parser/pipeline, model, ranking or holdout aggregates.

An independent, one-off standard-library JSON read listed first-innings runs, legal deliveries and dismissals by over. I reconciled the displayed over sums below with official sporting sources. Runs include every delivery's `runs.total`, including illegal deliveries. A delivery with `extras.wides` or `extras.noballs` does not count toward legal balls. Dismissals here count the actual wicket records; all three cases have ordinary team-wicket events. This check does not establish correct treatment of every rare dismissal type in the complete dataset.

All three source JSON files identify `data_version: 1.2.0` and `revision: 1`. No new dataset copy or sports media was saved. No UI, publication, registration or organizer contact occurred.

## Results

| Raw file and first innings | Official total and duration observed | Independent raw count | Result and intended filter behavior |
|---|---|---|---|
| `1359475.json`, Chennai Super Kings against Gujarat Titans, 31 March 2023, match 1 | 178/7 in 20 overs, in Gujarat Titans' official match report | 178 runs, 7 dismissals, 120 legal balls; 121 delivery records | Totals and duration agree. Complete first innings: retain if other eligibility checks pass. Official club report fallback, not a recovered full IPL scorecard. |
| `1473468.json`, Punjab Kings against Kolkata Knight Riders, 15 April 2025, match 31 | IPL scorecard header: Punjab 111, 15.3 overs; IPL report explicitly says bowled out | 111 runs, 10 dismissals, 93 legal balls; 96 delivery records | Totals, all-out status and duration agree. Retain the completed all-out innings despite fewer than 120 legal balls. |
| `1527686.json`, Rajasthan Royals against Mumbai Indians, 7 April 2026, match 13 | IPL scorecard header: Rajasthan 150/3, 11.0 overs; IPL report explicitly describes rain and an 11-over allotment | 150 runs, 3 dismissals, 66 legal balls; 72 delivery records | Totals and duration agree. Exclude from the planned ordinary 20-over first-innings population: this is a reduced innings, not an all-out. |

In cricket notation, **15.3 means 15 complete overs plus 3 legal balls: `15 × 6 + 3 = 93`**, not 15.3 decimal overs and not 91.8 balls. Similarly, 20.0 is 120 and 11.0 is 66. Illegal-delivery records explain why record counts exceed these denominators.

## Arithmetic trace from the raw JSON

**1359475 — CSK.** Per-over runs, overs 1 through 20:

`2 + 11 + 1 + 15 + 17 + 5 + 13 + 8 + 18 + 3 + 7 + 14 + 7 + 4 + 8 + 7 + 11 + 4 + 10 + 13 = 178`.

Twenty over groups contain six legal deliveries each. The fifth over also contains one no-ball record: 121 records minus one no-ball = 120 legal balls. Dismissals occur in overs 3, 6, 8, 13, 18 (two) and 19: seven in total. The last record has `actual_delivery: 19.6` and one run.

**1473468 — PBKS.** Per-over runs, overs 1 through 16 (the last is incomplete):

`4 + 9 + 20 + 6 + 3 + 12 + 4 + 8 + 10 + 4 + 6 + 4 + 4 + 10 + 5 + 2 = 111`.

Fifteen complete overs plus three legal balls = 93. Three wide records, two in over 8 and one in over 13, bring the record count to 96. Dismissals by over: 4 (two), 5, 6, 9, 10, 11 (two), 16 (two), totaling ten. The last record has `actual_delivery: 15.3`, one run, and Xavier Bartlett run out. This is a completed innings; requiring 120 balls would incorrectly remove it.

**1527686 — RR.** Per-over runs, overs 1 through 11:

`22 + 14 + 22 + 4 + 18 + 9 + 8 + 13 + 12 + 10 + 18 = 150`.

Eleven complete overs = 66 legal balls. Six wide records (one each in overs 3, 6 and 10; three in over 11) bring the count to 72. Dismissals in overs 5, 6 and 9 total three. The last record has `actual_delivery: 10.6` and four runs.

Important metadata limitation: this reduced match still has `info.overs: 20`. Its first-innings metadata contains the batting team and a mandatory powerplay ending at 3.2, with no explicit first-innings reduction flag in the fields observed. Therefore, `info.overs == 20` alone cannot establish an unreduced innings. The official match report supplies the rain/reduction evidence for this prespecified case. A generic filter must also distinguish completed all-outs from short, non-all-out innings and report ambiguous cases instead of treating scheduled overs as actual duration. This review did not test that filter implementation.

## Official sources and access limits

- **2023 primary source actually opened:** [Gujarat Titans — Terrific Titans clinch final over thriller in TATA IPL 2023 opener](https://www.gujarattitansipl.com/news/terrific-titans-clinch-final-over-thriller-in-tata-ipl-2023-opener), dated 31 March 2023. Both its narrative and Brief Scores state CSK 178/7 in 20 overs. This is the participating team's official report, not a cricket-board scorecard. The indexed [legacy IPL match report](https://www.iplt20.com/index.php/news/3868/tata-ipl-2023-match-01-gt-vs-csk-match-report) corroborated 178/7 but its direct open returned 404. An attempted Tamil Nadu Cricket Association annual-report read did not yield a usable scorecard. **The exact full IPL/board scorecard for this case remains unverified.** The official club report is sufficient to corroborate these two headline values, not individual scorecard rows.
- **2025:** [IPL official PBKS–KKR scorecard](https://www.iplt20.com/matches/b3d84270-1203-4a15-adda-4996f0327a7a/punjab-kings-vs-kolkata-knight-riders/scorecard), whose accessible header shows PBKS 111 in 15.3 on 15 April 2025. The [official IPL match report](https://www.iplt20.com/news/article/tata-ipl-2025-match-31-pbks-vs-kkr-match-report) independently identifies the 111 total as all-out. The detailed scorecard table remained at “Loading Scorecard…” in the text renderer; individual player rows were not verified.
- **2026:** [IPL official RR–MI scorecard](https://www.iplt20.com/matches/ff35ae9d-2a74-4dea-94fa-793d45d09347/rajasthan-royals-vs-mumbai-indians/scorecard), whose accessible header shows RR 150/3 in 11.0 on 7 April 2026. The [official IPL match report](https://www.iplt20.com/news/article/tata-ipl-2026-match-13-rr-vs-mi-match-report) confirms the rain-shortened 11-over allocation. As above, the detailed table did not render; this check covers its accessible headline plus the official report.

The official pages and raw data are distinct evidence paths, but may ultimately share underlying scoring sources. This is an independent check of our extraction, not proof of independent ground-truth collection, complete dataset accuracy, phase classification, delivery outcomes, player identity, or predictive performance.

## Exact raw-file fingerprints

SHA-256 values of the uncompressed JSON members inspected:

| Member | Created field | SHA-256 |
|---|---|---|
| `1359475.json` | 2023-04-01 | `1650ba3deaf13e6f597e144da04b24dad35a6c080cdb4ad5d2d3397850ffe1c5` |
| `1473468.json` | 2025-04-16 | `f78e3bc155f3d6cc0344fbaa8b0801298039e8fee659c6c127feab14179ba3ca` |
| `1527686.json` | 2026-04-08 | `bd8d76fbe8efdf194520f83fc7b0fd0cad81acf20ad9d55f35045916c9dc28d1` |

Contains information from [Cricsheet](https://cricsheet.org/), available under the [ODC Attribution License](https://opendatacommons.org/licenses/by/1-0/). The raw archive remains at its canonical dataset path; its acquisition/license manifest is maintained separately by the project coordinator.
