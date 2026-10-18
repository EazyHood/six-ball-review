import copy
import unittest

import profiles as p


def fixture():
    rows, manifest = [], []
    for j in range(5):
        match_id = str(j)
        local = []
        for phase in p.PHASES:
            for player, counts in [('a', [4, 1, 1]), ('b', [1, 2, 3])]:
                if phase == '16-20' and player == 'b':
                    continue
                local.append({'match_id': match_id, 'season': '2023', 'date': f'2023-04-0{j+1}',
                              'player_id': player, 'player_name': player.upper(), 'phase': phase,
                              'counts': counts, 'illegal': 1, 'all_deliveries': sum(counts) + 1,
                              'venue': 'One' if j < 3 else 'Two', 'bowling_team': 'Home', 'opponent': 'Away'})
        rows.extend(local)
        manifest.append({'match_id': match_id, 'season': '2023', 'status': 'included',
                         'sha256': 'a' * 64, 'venue': 'One' if j < 3 else 'Two',
                         'summary': {'legal': sum(sum(r['counts']) for r in local)}})
    return rows, manifest


def snapshot(profiles):
    return {'scope': {'evidence_seasons': list(p.SEASONS)}, 'method': {'m': 240}, 'profiles': profiles,
            'review_sheet': {'phase': '1-6', 'selected': [], 'selection_mode': 'manual'}}


class ProfilesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.manifest = fixture()
        cls.context = p.training_context(cls.rows, cls.manifest)
        cls.profiles = p.produce_profiles(cls.context, replicates=24, seed=123)

    def test_closed_form_and_reference_excludes_player(self):
        q, shrunk, kind, denominator = p.estimate([20, 5, 5], [25, 15, 20])
        self.assertEqual(q, [5 / 30, 10 / 30, 15 / 30])
        self.assertEqual(kind, 'excluding_player')
        self.assertEqual(denominator, 30)
        for got, count, prior in zip(shrunk, [20, 5, 5], q):
            self.assertAlmostEqual(got, (count + 240 * prior) / 270)

    def test_absence_is_reference_and_null_raw_not_personal_ranking(self):
        row = next(x for x in self.profiles if x['profile_id'] == 'b:16-20')
        self.assertIsNone(row['raw'])
        self.assertEqual(row['regularized'], row['reference']['rates'])
        self.assertEqual(row['reference']['kind'], 'pooled_fallback')
        self.assertEqual(row['checks']['absent_bootstrap_replicates'], 24)
        self.assertEqual(row['evidence']['status'], 'no_history')
        self.assertEqual(row['review']['status'], 'abstain')

    def test_thresholds_are_both_required_and_exact_boundary_is_allowed(self):
        self.assertEqual(p.evidence_status(59, 5)['status'], 'limited')
        self.assertEqual(p.evidence_status(60, 4)['status'], 'limited')
        self.assertEqual(p.evidence_status(60, 5)['status'], 'adequate_for_review')
        self.assertEqual(p.evidence_status(0, 10)['status'], 'no_history')

    def test_illegal_rate_uses_all_deliveries(self):
        row = self.profiles[0]
        self.assertEqual(row['legal_deliveries'], 30)
        self.assertEqual(row['illegal_deliveries'], 5)
        self.assertAlmostEqual(row['illegal_rate'], 5 / 35)

    def test_probabilities_and_provenance_reconcile(self):
        p.validate_snapshot(snapshot(self.profiles))
        self.assertEqual(sum(x['legal_deliveries'] for x in self.profiles), 150)
        broken = copy.deepcopy(self.profiles)
        broken[0]['counts']['dot'] += 1
        with self.assertRaisesRegex(ValueError, 'count'):
            p.validate_snapshot(snapshot(broken))

    def test_holdout_does_not_change_profile_universe_or_counts(self):
        heldout = dict(self.rows[0], match_id='future', season='2026', date='2026-04-01',
                       player_id='new-test-player', player_name='Future')
        future_manifest = dict(self.manifest[0], match_id='future', season='2026')
        context = p.training_context(self.rows + [heldout], self.manifest + [future_manifest])
        self.assertEqual(context['keys'], self.context['keys'])
        self.assertEqual(context['counts'], self.context['counts'])
        bad = dict(self.rows[0], date='2026-04-01')
        with self.assertRaisesRegex(ValueError, 'leakage'):
            p.training_context([bad] + self.rows[1:], self.manifest)

    def test_duplicate_group_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            p.training_context(self.rows + [self.rows[0]], self.manifest)

    def test_bootstrap_recomputes_paired_reference_and_repeats_by_seed(self):
        a, aa = p.bootstrap_profiles(self.context, replicates=12, seed=4)
        b, bb = p.bootstrap_profiles(self.context, replicates=12, seed=4)
        self.assertEqual(a, b)
        self.assertEqual(aa, bb)
        # Every synthetic match has identical counts: all bootstrap vectors equal the closed-form result.
        q, shrunk, _, _ = p.estimate(self.context['counts'][0], self.context['pools'][0])
        self.assertTrue(all(abs(x - shrunk[0]) < 1e-12 for x in a[0][0]))
        self.assertTrue(all(abs(x - (shrunk[0] - q[0])) < 1e-12 for x in a[0][3]))

    def test_leave_one_match_removes_both_profile_and_reference_data(self):
        sensitivity = self.profiles[0]['checks']['leave_one_match']
        q, shrunk, _, _ = p.estimate([16, 4, 4], [20, 12, 16])
        self.assertAlmostEqual(sensitivity['dot_contrast_range']['lower'], shrunk[0] - q[0])
        self.assertEqual(sensitivity['remaining_legal_deliveries'], 24)
        self.assertEqual(sensitivity['removed_ids'], ['0', '1', '2', '3', '4'])

    def test_venue_removes_whole_matches_not_only_player_rows(self):
        sensitivity = self.profiles[0]['checks']['remove_dominant_venue']
        q, shrunk, _, _ = p.estimate([8, 2, 2], [10, 6, 8])
        self.assertEqual(sensitivity['removed_ids'], ['0', '1', '2'])
        self.assertAlmostEqual(sensitivity['dot_contrast_range']['lower'], shrunk[0] - q[0])
        self.assertEqual(sensitivity['remaining_legal_deliveries'], 12)

    def test_unknown_venue_remains_unavailable(self):
        rows, manifest = fixture()
        for row in rows:
            row['venue'] = None
        for row in manifest:
            row['venue'] = None
        context = p.training_context(rows, manifest)
        sensitivity = p.sensitivity(context, 0, remove_dominant_venue=True)
        self.assertEqual(sensitivity['status'], 'unavailable')
        self.assertIsNone(sensitivity['dot_contrast_range'])

    def test_documented_aliases_merge_sensitivity_but_keep_raw_provenance(self):
        rows, manifest = fixture()
        aliases = list(p.VENUE_ALIASES)
        labels = [aliases[0], aliases[0], aliases[1], 'Other ground', 'Other ground']
        for row in rows:
            row['venue'] = labels[int(row['match_id'])]
        for row in manifest:
            row['venue'] = labels[int(row['match_id'])]
        context = p.training_context(rows, manifest)
        sensitivity = p.sensitivity(context, 0, remove_dominant_venue=True)
        self.assertEqual(sensitivity['removed_ids'], ['0', '1', '2'])
        self.assertEqual(sensitivity['reason'], 'documented_venue_aliases_grouped')
        self.assertEqual(sensitivity['remaining_legal_deliveries'], 12)
        self.assertEqual(context['by_profile'][0][2]['venue'], aliases[1])

    def test_review_state_does_not_fake_finished_checks_or_separation(self):
        enough = p.evidence_status(60, 5)
        self.assertEqual(p.review_status(enough, {'status': 'not_computed'})['status'], 'pending_checks')
        checks = copy.deepcopy(self.profiles[0]['checks'])
        checks['contrasts_vs_reference']['dot'].update(lower=-.01, upper=.02)
        self.assertEqual(p.review_status(enough, checks)['status'], 'uncertain')
        checks['contrasts_vs_reference']['dot'].update(lower=.01, upper=.02)
        checks['contrasts_vs_reference']['boundary'].update(lower=-.02, upper=-.01)
        self.assertEqual(p.review_status(enough, checks)['status'], 'reviewable')
        checks['leave_one_match']['sign_reversal_ids'] = ['0']
        self.assertEqual(p.review_status(enough, checks)['status'], 'uncertain')

    def test_export_selection_unique_at_most_three_and_known(self):
        data = snapshot(self.profiles)
        data['review_sheet']['selected'] = [{'profile_id': self.profiles[0]['profile_id']}] * 2
        with self.assertRaisesRegex(ValueError, 'selection'):
            p.validate_snapshot(data)
        data['review_sheet']['selected'] = [{'profile_id': 'unknown'}]
        with self.assertRaisesRegex(ValueError, 'selection'):
            p.validate_snapshot(data)


if __name__ == '__main__':
    unittest.main()
