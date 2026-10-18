"""Training-only review profiles. Does not fit/select models or rerun the test.

Contains information from Cricsheet under ODC-By 1.0.
All computations use Python's standard library.
"""
from __future__ import annotations

import argparse
from array import array
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PureWindowsPath
import random

ROOT = Path(__file__).resolve().parent
PHASES = ('1-6', '7-15', '16-20')
CATEGORIES = ('dot', 'boundary', 'other')
SEASONS = (2023, 2024, 2025)
M = 240
REPLICATES = 2000
SEED = 20261018
EPSILON = 1e-12
VENUE_ALIASES = json.loads((ROOT / 'venue-aliases.json').read_text(encoding='utf-8'))['aliases']


def venue_key(raw_venue):
    """Canonicalize only documented aliases for venue-deletion sensitivity."""
    return VENUE_ALIASES.get(raw_venue, raw_venue)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def named(values):
    return dict(zip(CATEGORIES, values))


def rates(counts):
    total = sum(counts)
    return [c / total for c in counts] if total else None


def estimate(counts, pool):
    """Return q, C, q kind, q denominator; same fixed model as pipeline.C."""
    n = sum(counts)
    peers = [p - c for p, c in zip(pool, counts)]
    if min(peers) < 0 or not sum(pool):
        raise ValueError('Invalid or absent phase population')
    use_peers = n > 0 and sum(peers) > 0
    reference = peers if use_peers else pool
    q = rates(reference)
    regularized = [(c + M * p) / (n + M) for c, p in zip(counts, q)]
    return q, regularized, 'excluding_player' if use_peers else 'pooled_fallback', sum(reference)


def quantile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def interval(values):
    return {'lower': quantile(values, .025), 'upper': quantile(values, .975)}


def evidence_status(n, matches):
    if n == 0:
        return {'status': 'no_history', 'reasons': ['no_legal_delivery_history']}
    reasons = []
    if n < 60:
        reasons.append('fewer_than_60_legal_deliveries')
    if matches < 5:
        reasons.append('fewer_than_5_matches')
    return {'status': 'limited' if reasons else 'adequate_for_review', 'reasons': reasons}


def review_status(evidence, checks):
    if evidence['status'] in ('no_history', 'limited'):
        return {'status': 'abstain', 'reasons': list(evidence['reasons'])}
    if checks['status'] != 'complete':
        return {'status': 'pending_checks', 'reasons': ['required_checks_unavailable']}
    reasons = []
    for category in ('dot', 'boundary'):
        band = checks['contrasts_vs_reference'][category]
        if band['lower'] <= 0 <= band['upper']:
            reasons.append(category + '_contrast_not_separated_from_reference')
    if checks['leave_one_match']['sign_reversal_ids']:
        reasons.append('contrast_sign_changes_without_one_match')
    venue = checks['remove_dominant_venue']
    if venue['status'] == 'complete' and venue['sign_reversal_ids']:
        reasons.append('contrast_sign_changes_without_dominant_venue')
    return {'status': 'uncertain' if reasons else 'reviewable', 'reasons': reasons}


def training_context(all_rows, manifest):
    """The only path into profile computations; reject leakage and duplicates."""
    rows = [r for r in all_rows if int(r['season']) in SEASONS]
    allowed = {m['match_id']: m for m in manifest
               if int(m['season']) in SEASONS and m['status'] == 'included'}
    if not rows or set(r['match_id'] for r in rows) != set(allowed):
        raise ValueError('Training rows and included manifest do not match')
    seen = set()
    aliases = defaultdict(set)
    for r in rows:
        key = (r['match_id'], r['player_id'], r['phase'])
        if key in seen:
            raise ValueError('Duplicate match/player/phase row')
        seen.add(key)
        if r['phase'] not in PHASES or not r['player_id']:
            raise ValueError('Invalid phase/player')
        if r['date'][:4] != str(r['season']) or not r['date'] < '2026-01-01':
            raise ValueError('Invalid profile date or held-out leakage')
        if len(r['counts']) != 3 or any(type(c) is not int or c < 0 for c in r['counts']):
            raise ValueError('Invalid category count')
        if type(r['illegal']) is not int or r['illegal'] < 0:
            raise ValueError('Invalid illegal-delivery count')
        if sum(r['counts']) + r['illegal'] != r['all_deliveries']:
            raise ValueError('Unreconciled delivery count')
        if str(allowed[r['match_id']]['season']) != str(r['season']):
            raise ValueError('Season differs from source manifest')
        aliases[r['player_id']].add(r['player_name'])
    names = {player: sorted(values, key=lambda s: (s.casefold(), s))[0] for player, values in aliases.items()}
    keys = [(player, phase) for player in sorted(names, key=lambda p: (names[p].casefold(), p)) for phase in PHASES]
    positions = {key: i for i, key in enumerate(keys)}
    match_ids = sorted(allowed)
    match_positions = {m: i for i, m in enumerate(match_ids)}
    by_match = [[] for _ in match_ids]
    match_pools = [[[0, 0, 0] for _ in PHASES] for _ in match_ids]
    by_profile = [[] for _ in keys]
    counts = [[0, 0, 0] for _ in keys]
    pools = [[0, 0, 0] for _ in PHASES]
    for row in rows:
        i = positions[(row['player_id'], row['phase'])]
        j = match_positions[row['match_id']]
        p = PHASES.index(row['phase'])
        by_profile[i].append(row)
        by_match[j].append((i, row['counts']))
        for k, count in enumerate(row['counts']):
            counts[i][k] += count
            pools[p][k] += count
            match_pools[j][p][k] += count
    for match_id, j in match_positions.items():
        actual = sum(sum(row_counts) for _, row_counts in by_match[j])
        if actual != allowed[match_id]['summary']['legal']:
            raise ValueError('Training match legal count differs from audit')
    return {'rows': rows, 'manifest': allowed, 'keys': keys, 'names': names,
            'match_ids': match_ids, 'match_positions': match_positions,
            'by_match': by_match, 'match_pools': match_pools,
            'by_profile': by_profile, 'counts': counts, 'pools': pools}


def bootstrap_profiles(context, replicates=REPLICATES, seed=SEED):
    """Paired full-match resampling from final training only, with fixed m."""
    keys = context['keys']
    phase_indices = [PHASES.index(phase) for _, phase in keys]
    # Three profile probabilities and two contrasts per row. Doubles avoid object-heavy storage.
    samples = [[array('d') for _ in range(5)] for _ in keys]
    absent = [0] * len(keys)
    rng = random.Random(seed)
    population = range(len(context['match_ids']))
    for _ in range(replicates):
        weights = Counter(rng.choices(population, k=len(population)))
        counts = [[0, 0, 0] for _ in keys]
        pools = [[0, 0, 0] for _ in PHASES]
        for j, weight in weights.items():
            for p in range(3):
                for k in range(3):
                    pools[p][k] += weight * context['match_pools'][j][p][k]
            for i, values in context['by_match'][j]:
                for k in range(3):
                    counts[i][k] += weight * values[k]
        for i, values in enumerate(counts):
            q, profile, _, _ = estimate(values, pools[phase_indices[i]])
            absent[i] += int(sum(values) == 0)
            for k in range(3):
                samples[i][k].append(profile[k])
            samples[i][3].append(profile[0] - q[0])
            samples[i][4].append(profile[1] - q[1])
    return samples, absent


def reverses(original, changed):
    return any(a > EPSILON and b < -EPSILON or a < -EPSILON and b > EPSILON
               for a, b in zip(original[:2], changed[:2]))


def sensitivity(context, profile_index, remove_dominant_venue=False):
    player, phase = context['keys'][profile_index]
    p = PHASES.index(phase)
    counts = context['counts'][profile_index]
    pool = context['pools'][p]
    q, regularized, _, _ = estimate(counts, pool)
    original = [regularized[k] - q[k] for k in range(3)]
    own_rows = context['by_profile'][profile_index]
    own = {r['match_id']: r['counts'] for r in own_rows}
    reason = None
    if remove_dominant_venue:
        venue_counts = defaultdict(int)
        for row in own_rows:
            if row['venue'] is not None:
                venue_counts[venue_key(row['venue'])] += sum(row['counts'])
        venue_counts = {v: n for v, n in venue_counts.items() if n > 0}
        if not venue_counts:
            return {'status': 'unavailable', 'reason': 'no_known_venue_with_legal_history',
                    'removed_ids': [], 'sign_reversal_ids': [], 'dot_contrast_range': None,
                    'boundary_contrast_range': None, 'remaining_legal_deliveries': None}
        venue = sorted(venue_counts, key=lambda v: (-venue_counts[v], v))[0]
        groups = [[m for m in context['match_ids'] if venue_key(context['manifest'][m]['venue']) == venue]]
        if venue in VENUE_ALIASES.values():
            reason = 'documented_venue_aliases_grouped'
        if any(r['venue'] is None for r in own_rows):
            reason = 'dominant_known_venue_only_missing_venues_excluded_from_choice'
    else:
        groups = [[m] for m in context['match_ids']]
    changed = []
    remaining = []
    reversal_ids = []
    removed_ids = []
    for group in groups:
        remaining_counts = list(counts)
        remaining_pool = list(pool)
        for match_id in group:
            match_pool = context['match_pools'][context['match_positions'][match_id]][p]
            own_counts = own.get(match_id, (0, 0, 0))
            for k in range(3):
                remaining_counts[k] -= own_counts[k]
                remaining_pool[k] -= match_pool[k]
        if not sum(remaining_pool):
            return {'status': 'unavailable', 'reason': 'deletion_removes_all_phase_data',
                    'removed_ids': sorted(group), 'sign_reversal_ids': [], 'dot_contrast_range': None,
                    'boundary_contrast_range': None, 'remaining_legal_deliveries': None}
        q2, profile2, _, _ = estimate(remaining_counts, remaining_pool)
        contrast = [profile2[k] - q2[k] for k in range(3)]
        changed.append(contrast)
        remaining.append(sum(remaining_counts))
        removed_ids.extend(group)
        if reverses(original, contrast):
            reversal_ids.extend(group)
    return {'status': 'complete', 'reason': reason, 'removed_ids': sorted(set(removed_ids)),
            'sign_reversal_ids': sorted(set(reversal_ids)),
            'dot_contrast_range': {'estimate': original[0], 'lower': min(x[0] for x in changed), 'upper': max(x[0] for x in changed)},
            'boundary_contrast_range': {'estimate': original[1], 'lower': min(x[1] for x in changed), 'upper': max(x[1] for x in changed)},
            'remaining_legal_deliveries': min(remaining)}


def produce_profiles(context, replicates=REPLICATES, seed=SEED):
    samples, absent = bootstrap_profiles(context, replicates, seed)
    output = []
    for i, (player, phase) in enumerate(context['keys']):
        counts = context['counts'][i]
        n = sum(counts)
        raw = rates(counts)
        q, regularized, kind, reference_n = estimate(counts, context['pools'][PHASES.index(phase)])
        source_rows = sorted(context['by_profile'][i], key=lambda r: (r['date'], r['match_id']))
        illegal = sum(r['illegal'] for r in source_rows)
        matches = len(source_rows)
        evidence = evidence_status(n, matches)
        leave_one = sensitivity(context, i)
        venue = sensitivity(context, i, remove_dominant_venue=True)
        checks = {
            'status': 'complete' if leave_one['status'] == 'complete' else 'unavailable',
            'reason': leave_one['reason'],
            'bands': {category: interval(samples[i][k]) for k, category in enumerate(CATEGORIES)},
            'contrasts_vs_reference': {category: {'estimate': regularized[k] - q[k], **interval(samples[i][k + 3])}
                                       for k, category in enumerate(('dot', 'boundary'))},
            'absent_bootstrap_replicates': absent[i],
            'leave_one_match': leave_one, 'remove_dominant_venue': venue,
            'threshold_120_eligible': n >= 120 and matches >= 5,
        }
        output.append({
            'profile_id': player + ':' + phase, 'player_id': player, 'player_name': context['names'][player],
            'phase': phase, 'legal_deliveries': n, 'illegal_deliveries': illegal,
            'illegal_rate': illegal / (n + illegal) if n + illegal else None,
            'matches': matches, 'counts': named(counts), 'raw': named(raw) if raw is not None else None,
            'reference': {'kind': kind, 'legal_deliveries': reference_n, 'rates': named(q)},
            'regularized': named(regularized), 'evidence': evidence,
            'checks': checks, 'review': review_status(evidence, checks),
            'match_rows': [{'match_id': r['match_id'], 'source_sha256': context['manifest'][r['match_id']]['sha256'],
                            'date': r['date'], 'season': int(r['season']), 'bowling_team': r['bowling_team'],
                            'opponent': r['opponent'], 'venue': r['venue'], 'counts': named(r['counts']),
                            'illegal_deliveries': r['illegal']} for r in source_rows],
        })
    return output


def validate_snapshot(snapshot):
    """Semantic invariants beyond JSON Schema; raise instead of publishing bad data."""
    if snapshot['scope']['evidence_seasons'] != list(SEASONS) or snapshot['method']['m'] != M:
        raise ValueError('Changed evidence window or smoothing')
    ids = set()
    for profile in snapshot['profiles']:
        profile_id = profile['profile_id']
        if profile_id in ids or profile_id != profile['player_id'] + ':' + profile['phase']:
            raise ValueError('Duplicate or malformed profile identity')
        ids.add(profile_id)
        counts = profile['counts']
        n = sum(counts.values())
        illegal = profile['illegal_deliveries']
        if n != profile['legal_deliveries']:
            raise ValueError('Profile count does not reconcile')
        match_rows = profile['match_rows']
        if len({r['match_id'] for r in match_rows}) != len(match_rows) or len(match_rows) != profile['matches']:
            raise ValueError('Profile match count does not reconcile')
        if any(r['season'] not in SEASONS or r['date'] >= '2026-01-01' for r in match_rows):
            raise ValueError('Holdout appears in profile provenance')
        if any(sum(r['counts'][k] for r in match_rows) != counts[k] for k in CATEGORIES):
            raise ValueError('Provenance category counts do not reconcile')
        if sum(r['illegal_deliveries'] for r in match_rows) != illegal:
            raise ValueError('Provenance illegal counts do not reconcile')
        expected_illegal_rate = illegal / (n + illegal) if n + illegal else None
        if profile['illegal_rate'] != expected_illegal_rate:
            raise ValueError('Wrong illegal-delivery denominator')
        if (n == 0) != (profile['raw'] is None):
            raise ValueError('Raw null/no-history mismatch')
        vectors = [profile['regularized'], profile['reference']['rates']]
        if n:
            vectors.append(profile['raw'])
            if any(abs(profile['raw'][k] - counts[k] / n) > 1e-12 for k in CATEGORIES):
                raise ValueError('Raw rate differs from counts')
        for vector in vectors:
            if any(not math.isfinite(p) or not 0 <= p <= 1 for p in vector.values()) or abs(sum(vector.values()) - 1) > 1e-9:
                raise ValueError('Invalid probability vector')
        for k in CATEGORIES:
            expected = (counts[k] + M * profile['reference']['rates'][k]) / (n + M)
            if abs(profile['regularized'][k] - expected) > 1e-12:
                raise ValueError('Regularized rate differs from fixed formula')
            band = profile['checks']['bands'][k]
            if not 0 <= band['lower'] <= band['upper'] <= 1:
                raise ValueError('Invalid profile band')
        for band in profile['checks']['contrasts_vs_reference'].values():
            if not -1 <= band['lower'] <= band['upper'] <= 1:
                raise ValueError('Invalid contrast band')
        if profile['evidence'] != evidence_status(n, profile['matches']):
            raise ValueError('Wrong evidence status')
        if profile['review'] != review_status(profile['evidence'], profile['checks']):
            raise ValueError('Wrong review/abstention status')
        if profile['checks']['threshold_120_eligible'] != (n >= 120 and profile['matches'] >= 5):
            raise ValueError('Wrong threshold sensitivity')
    selected = snapshot['review_sheet']['selected']
    selected_ids = [s['profile_id'] for s in selected]
    if len(selected_ids) > 3 or len(set(selected_ids)) != len(selected_ids) or not set(selected_ids) <= ids:
        raise ValueError('Invalid review-sheet selection')
    # Ensure NaN/infinity cannot survive serialization, including nested sensitivity/evaluation fields.
    json.dumps(snapshot, allow_nan=False)


def build_snapshot(dataset_dir):
    plan = read(ROOT / 'analysis-plan.json')
    result = read(ROOT / 'baseline-results.json')
    acquisition = read(dataset_dir / 'acquisition.json')
    archive = dataset_dir / PureWindowsPath(acquisition['local_path']).name
    if sha(archive) != acquisition['sha256'] or result['archive_sha256'] != acquisition['sha256']:
        raise ValueError('Canonical dataset checksum differs from fixed experiment')
    if result['analysis_plan_sha256'] != sha(ROOT / 'analysis-plan.json'):
        raise ValueError('The original analysis plan has changed')
    if result['pipeline_sha256'] != sha(ROOT / 'pipeline.py'):
        raise ValueError('The original pipeline has changed')
    if result['selected_m'] != M or plan['training_seasons'] + plan['validation_seasons'] != list(SEASONS):
        raise ValueError('Model or final-training seasons differ from the fixed experiment')
    context = training_context(read(ROOT / 'match-phase-counts.json'), read(ROOT / 'match-manifest.json'))
    profiles = produce_profiles(context)
    result_path = ROOT / 'baseline-results.json'
    snapshot = {
        'schema_version': '0.1', 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'provenance': {
            'dataset_sha256': acquisition['sha256'], 'producer_sha256': sha(Path(__file__)),
            'plan_sha256': sha(ROOT / 'analysis-plan.json'),
            'inputs': [{'file': name, 'sha256': sha(ROOT / name)} for name in
                       ('match-phase-counts.json', 'match-manifest.json', 'baseline-results.json', 'ui-contract.schema.json', 'venue-aliases.json')],
            'attribution': result['attribution'],
        },
        'scope': {'competition': 'IPL', 'gender': 'male', 'innings': 1, 'evidence_seasons': list(SEASONS),
                  'description': 'Included first innings of scheduled 20-over matches; revised/reduced/incomplete excluded, early all-outs retained. Retrospective cohort uses later chase information.'},
        'method': {'m': M, 'minimum_legal_deliveries': 60, 'minimum_matches': 5,
                   'bootstrap': {'unit': 'whole_final_training_matches', 'replicates': REPLICATES, 'seed': SEED,
                                 'level': .95, 'reference_recomputed': True},
                   'limitations': [
                       'Review prioritization, not lineup selection, causal skill, win prediction or betting advice.',
                       'Observational first-innings sample; opponents, venues, batters, fielding and assignment decisions are not controlled.',
                       'Match bootstrap is conditional on the fixed model; repeated players/teams/venues leave residual dependence.',
                       'Profile contrasts are exploratory, not simultaneous confirmatory discoveries or pairwise player comparisons.',
                       'Adequate sample and reviewable status do not imply superiority or professional validation.',
                       'Illegal deliveries are counted separately; legal-ball boundary and dot rates do not capture all bowling cost.',
                       'Plan was recorded locally before acquisition/results, not independently registered in public.',
                   ]},
        'evaluation': {
            'source': {'file': result_path.name, 'sha256': sha(result_path)}, 'status': result['status'],
            'seasons': [2026], 'selected_m': result['selected_m'],
            'models': {name: {k: v for k, v in metrics.items() if k != 'match_sums'} for name, metrics in result['test'].items()},
            'differences': result['test_differences'],
            'interpretation': 'Small improvement against the pooled phase reference in the retrospective filtered 2026 sample; no measured coaching impact. These aggregates are copied from the fixed evaluation, not recomputed.'},
        'profiles': profiles, 'review_sheet': {'phase': PHASES[0], 'selected': [], 'selection_mode': 'manual'},
    }
    validate_snapshot(snapshot)
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-dir', type=Path, default=Path('D:/IA/datasets/cricsheet-ipl'),
                        help='Existing canonical ZIP/acquisition directory; no download or relocation occurs.')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist' / 'data.json')
    args = parser.parse_args()
    before = {name: sha(ROOT / name) for name in ('pipeline.py', 'analysis-plan.json', 'baseline-results.json', 'data-gate.json')}
    snapshot = build_snapshot(args.dataset_dir)
    after = {name: sha(ROOT / name) for name in before}
    if before != after:
        raise RuntimeError('Immutable experiment changed during profile production')
    if not args.output.parent.exists():
        raise ValueError('Create/document output directory before generation')
    args.output.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'sha256': sha(args.output),
                      'profiles': len(snapshot['profiles']), 'bowlers': len({p['player_id'] for p in snapshot['profiles']}),
                      'legal_deliveries': sum(p['legal_deliveries'] for p in snapshot['profiles']),
                      'matches': len({r['match_id'] for p in snapshot['profiles'] for r in p['match_rows']}),
                      'evidence': dict(Counter(p['evidence']['status'] for p in snapshot['profiles'])),
                      'review': dict(Counter(p['review']['status'] for p in snapshot['profiles'])),
                      'immutable_experiment_verified': before == after}, indent=2))


if __name__ == '__main__':
    main()
