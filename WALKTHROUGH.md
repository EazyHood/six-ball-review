# Try Six-Ball Review in two minutes

Open the live app, or run `npm start` and open the address printed by the local server. No account or API key is needed. This walkthrough uses the published historical snapshot; it does not claim that anyone reviewed match footage.

1. Select **16–20** and search **Noor Ahmad**. The profile has 72 legal deliveries from 10 matches. Its observed dot rate is 45.8%; the regularized rate is 30.6%. The boundary rates are 18.1% and 22.9%. The large change illustrates the influence of a small sample; it does not establish player superiority. The comparison remains **uncertain**.
2. Open **Difference from the reference**, **Sensitivity & evidence checks** and **Contributing matches**. Read the comparison bands and deletion ranges separately. The dominant-venue check removes that venue's matches from the full training population, including the reference. Exact source labels remain visible; the documented Mullanpur/New Chandigarh alias is grouped for this sensitivity check.
3. Choose **Add to review +**. Replace the suggested question with “What match situations might explain the observed dot rate, and what should I check in permitted footage?” Add a note only if useful. A question is a prompt, not a reported finding.
4. Search **JR Hazlewood** in the same phase. This case is below the coverage threshold. Add it as a question if you want to investigate the missing context; the abstention warning stays attached. Then select **7–15**, search **A Badoni**, and inspect the **no-history** fallback. It is not a personal estimate. You may add this third question, but no selection is required or filled automatically.
5. Use **Export readable sheet** and **Export exact JSON**. Open the HTML file and check that each case kept its own phase, question, warnings, match IDs and snapshot checksum. Different-phase cases are not a comparative ranking. Notes remain only in the current tab unless you save the export.
6. Open **Method & evidence**. The separate 2026 evaluation compares the fixed model with pooled-phase and raw-profile baselines. The small Brier improvement is not an accuracy percentage or demonstrated coaching benefit. Coverage, retrospective filtering and uncertainty limits are shown with the result.

## Why these examples

The illustrative regularization case was chosen by a recorded rule: largest absolute observed-to-regularized category change among profiles meeting the declared volume threshold, using only 2023–2025 evidence. The limited-evidence case is the first by stable profile ID. The no-history case is the first alphabetical player in overs 7–15. These are demonstrations of interface states, not randomly sampled results, endorsements or confirmatory discoveries. The 2026 test was not used to choose them.

Contains information from [Cricsheet](https://cricsheet.org/) under the [ODC Attribution License 1.0](https://opendatacommons.org/licenses/by/1-0/). See README, VALIDATION and CREDITS for definitions, reproduction and limits.
