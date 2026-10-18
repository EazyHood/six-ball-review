"""Reproducible data gate and temporal baselines; standard library only.

Contains information from Cricsheet, https://cricsheet.org/, available under
ODC-By 1.0: https://opendatacommons.org/licenses/by/1-0/.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import zipfile

ROOT = Path(__file__).resolve().parent
DATA = Path('D:/IA/datasets/cricsheet-ipl')
PHASES = ('1-6', '7-15', '16-20')
CATEGORIES = ('dot', 'boundary', 'other')
SUPPORTED = {'1.2.0', '1.3.0'}
NON_DISMISSALS = {'retired hurt', 'retired not out'}

class Excluded(ValueError):
    pass

def integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0

def phase_for(over):
    if not integer(over) or over > 19:
        raise Excluded('invalid_over_index')
    return PHASES[0 if over < 6 else 1 if over < 15 else 2]

def classify_delivery(delivery):
    """Return category or None for an illegal delivery; validate required runs."""
    runs = delivery.get('runs', {})
    if any(not integer(runs.get(k)) for k in ('batter', 'extras', 'total')):
        raise Excluded('missing_or_invalid_run_field')
    if runs['total'] != runs['batter'] + runs['extras']:
        raise Excluded('unreconciled_runs')
    extras = delivery.get('extras', {})
    if not isinstance(extras, dict) or any(not integer(v) for v in extras.values()):
        raise Excluded('invalid_extras')
    if sum(extras.values()) != runs['extras']:
        raise Excluded('unreconciled_extras')
    if 'non_boundary' in runs and not isinstance(runs['non_boundary'], bool):
        raise Excluded('invalid_non_boundary_flag')
    if extras.get('wides', 0) or extras.get('noballs', 0):
        return None
    if runs['total'] == 0:
        return 0
    if runs['batter'] in (4, 6) and not runs.get('non_boundary', False):
        return 1
    return 2

def parse_match(document, match_id):
    info = document.get('info', {})
    if document.get('meta', {}).get('data_version') not in SUPPORTED:
        raise Excluded('unsupported_data_version')
    if info.get('gender') != 'male' or info.get('match_type') != 'T20':
        raise Excluded('wrong_population')
    if info.get('event', {}).get('name') != 'Indian Premier League':
        raise Excluded('wrong_event')
    if info.get('balls_per_over') != 6 or info.get('overs') != 20:
        raise Excluded('not_scheduled_20_six_ball_overs')
    if info.get('outcome', {}).get('method'):
        raise Excluded('revised_match_method')
    innings = document.get('innings', [])
    if not innings:
        raise Excluded('no_innings')
    first = innings[0]
    if first.get('super_over'):
        raise Excluded('first_entry_is_super_over')
    # Quarantine an explicitly reduced target even when a method is not recorded.
    if any(x.get('target', {}).get('overs', 20) != 20 for x in innings[1:] if not x.get('super_over')):
        raise Excluded('reduced_chase_target')
    if first.get('miscounted_overs'):
        raise Excluded('miscounted_over_needs_review')
    people = info.get('registry', {}).get('people', {})
    teams = info.get('teams', [])
    if len(teams) != 2 or len(set(teams)) != 2 or first.get('team') not in teams:
        raise Excluded('invalid_team_metadata')
    bowling_team = next(t for t in teams if t != first['team'])
    season = str(info.get('season', ''))
    dates = info.get('dates', [])
    if not dates or not all(isinstance(x, str) for x in dates):
        raise Excluded('missing_dates')
    try:
        for d in dates:
            datetime.strptime(d, '%Y-%m-%d')
    except ValueError as error:
        raise Excluded('invalid_dates') from error
    groups = {}
    delivery_total = legal_total = dismissal_total = run_total = 0
    overs = first.get('overs', [])
    if not overs:
        raise Excluded('no_deliveries')
    over_indices = [o.get('over') for o in overs]
    if over_indices != list(range(len(overs))):
        raise Excluded('noncontiguous_or_duplicate_overs')
    special_counts = Counter()
    for index, over in enumerate(overs):
        phase = phase_for(over['over'])
        over_legal = 0
        for delivery in over.get('deliveries', []):
            name = delivery.get('bowler')
            player_id = people.get(name)
            if not name or not player_id:
                raise Excluded('missing_bowler_registry_id')
            category = classify_delivery(delivery)
            key = (player_id, phase)
            if key not in groups:
                groups[key] = {'match_id': match_id, 'season': season, 'date': min(dates),
                    'player_id': player_id, 'player_name': name, 'phase': phase,
                    'bowling_team': bowling_team, 'opponent': first['team'],
                    'venue': info.get('venue'), 'counts': [0, 0, 0], 'illegal': 0,
                    'all_deliveries': 0, 'team_runs_while_delivering': 0}
            group = groups[key]
            group['all_deliveries'] += 1
            group['team_runs_while_delivering'] += delivery['runs']['total']
            delivery_total += 1
            run_total += delivery['runs']['total']
            for kind in delivery.get('extras', {}):
                special_counts[kind] += 1
            if delivery['runs'].get('non_boundary'):
                special_counts['non_boundary'] += 1
            if category is None:
                group['illegal'] += 1
            else:
                group['counts'][category] += 1
                legal_total += 1
                over_legal += 1
            for wicket in delivery.get('wickets', []):
                kind = wicket.get('kind')
                if not isinstance(kind, str):
                    raise Excluded('invalid_wicket_record')
                dismissal_total += int(kind not in NON_DISMISSALS)
        if over_legal > 6 or (index < len(overs)-1 and over_legal != 6):
            raise Excluded('unexplained_over_length')
    if legal_total > 120:
        raise Excluded('too_many_legal_deliveries')
    if legal_total < 120 and dismissal_total != 10:
        raise Excluded('incomplete_or_reduced_first_innings')
    if dismissal_total > 10:
        raise Excluded('too_many_dismissals')
    penalties = first.get('penalty_runs', {})
    if any(not integer(v) for v in penalties.values()):
        raise Excluded('invalid_innings_penalty')
    total_team_runs = run_total + sum(penalties.values())
    if len(innings) > 1 and not innings[1].get('super_over'):
        target_runs = innings[1].get('target', {}).get('runs')
        if target_runs is not None and target_runs != total_team_runs + 1:
            raise Excluded('first_total_vs_target_mismatch')
    rows = list(groups.values())
    assert sum(sum(r['counts']) + r['illegal'] for r in rows) == delivery_total
    assert sum(r['team_runs_while_delivering'] for r in rows) == run_total
    return rows, {'legal': legal_total, 'all_deliveries': delivery_total,
        'illegal': delivery_total-legal_total, 'dismissals': dismissal_total,
        'all_out_early': legal_total < 120, 'team_total': total_team_runs,
        'special_counts': dict(special_counts), 'completed_first_no_result': info.get('outcome', {}).get('result') == 'no result',
        'extra_innings_not_used': max(0, len(innings)-1)}

def dump(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def audit(archive, plan):
    all_seasons = Counter()
    versions = Counter()
    manifest = []
    rows = []
    names_by_id = defaultdict(set)
    dates_by_season = defaultdict(list)
    wanted = {str(x) for x in plan['training_seasons']+plan['validation_seasons']+plan['test_seasons']}
    with zipfile.ZipFile(archive) as z:
        members = z.namelist()
        if len(members) != len(set(members)):
            raise ValueError('Duplicate ZIP member names')
        notices = {name: {'sha256': hashlib.sha256(z.read(name)).hexdigest(), 'bytes': len(z.read(name))}
                   for name in members if not name.endswith('.json')}
        for name in sorted(members):
            if not name.endswith('.json'):
                continue
            raw = z.read(name)
            doc = json.loads(raw)
            season = str(doc.get('info', {}).get('season'))
            all_seasons[season] += 1
            versions[doc.get('meta', {}).get('data_version')] += 1
            if season not in wanted:
                continue
            info = doc.get('info', {})
            entry = {'match_id': Path(name).stem, 'archive_member': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                'season': season, 'dates': info.get('dates'), 'teams': info.get('teams'), 'venue': info.get('venue'),
                'data_version': doc.get('meta', {}).get('data_version'), 'revision': doc.get('meta', {}).get('revision'),
                'provider_missing_flags': info.get('missing', [])}
            dates_by_season[season] += info.get('dates', [])
            try:
                parsed, summary = parse_match(doc, entry['match_id'])
                entry.update({'status': 'included', 'summary': summary})
                rows.extend(parsed)
                for row in parsed:
                    names_by_id[row['player_id']].add(row['player_name'])
            except Excluded as error:
                entry.update({'status': 'excluded', 'reason': str(error)})
            manifest.append(entry)
    report = {'archive_match_count': sum(all_seasons.values()), 'archive_seasons': dict(sorted(all_seasons.items())),
        'versions': dict(versions), 'notices_in_archive': notices, 'target_match_count': len(manifest),
        'by_season': {}, 'excluded': [x for x in manifest if x['status']=='excluded'],
        'name_aliases': {k: sorted(v) for k,v in names_by_id.items() if len(v)>1},
        'independent_scorecard_verification': 'Separate review pending; internal reconciliation is not independent validation.'}
    for season in sorted(wanted):
        selected = [r for r in rows if r['season']==season]
        included = [x for x in manifest if x['season']==season and x['status']=='included']
        excluded = [x for x in manifest if x['season']==season and x['status']=='excluded']
        report['by_season'][season] = {'source_matches': all_seasons[season], 'included_matches': len(included),
            'excluded_matches': len(excluded), 'exclusion_reasons': dict(Counter(x['reason'] for x in excluded)),
            'date_min': min(dates_by_season[season]) if dates_by_season[season] else None,
            'date_max': max(dates_by_season[season]) if dates_by_season[season] else None,
            'legal_deliveries': sum(sum(x['counts']) for x in selected), 'illegal_deliveries': sum(x['illegal'] for x in selected),
            'unique_bowlers': len({x['player_id'] for x in selected}),
            'early_all_out_kept': sum(x['summary']['all_out_early'] for x in included),
            'complete_first_innings_no_result_kept': sum(x['summary']['completed_first_no_result'] for x in included),
            'legal_by_phase': {p: sum(sum(r['counts']) for r in selected if r['phase']==p) for p in PHASES}}
    return rows, manifest, report

def aggregate(rows):
    players = defaultdict(lambda: [0,0,0])
    phases = {p: [0,0,0] for p in PHASES}
    for row in rows:
        key = (row['player_id'],row['phase'])
        for k,c in enumerate(row['counts']):
            players[key][k] += c
            phases[row['phase']][k] += c
    return players, phases

def predictions(model, player_id, phase, method, m=None):
    players, phases = model
    c = players.get((player_id, phase), [0,0,0])
    pool = phases[phase]
    if not sum(pool):
        raise ValueError('No training data for a phase; cannot evaluate')
    baseline = [x/sum(pool) for x in pool]
    if method == 'B0' or not sum(c):
        return baseline
    if method == 'B1':
        return [x/sum(c) for x in c]
    peers = [pool[k]-c[k] for k in range(3)]
    q = [x/sum(peers) for x in peers] if sum(peers) else baseline
    return [(c[k]+m*q[k])/(sum(c)+m) for k in range(3)]

def losses(counts, probability):
    n = sum(counts)
    brier = n*(1+sum(p*p for p in probability))-2*sum(c*p for c,p in zip(counts,probability))
    clipped = [max(1e-6,p) for p in probability]
    clipped = [p/sum(clipped) for p in clipped]
    log_loss = -sum(c*math.log(p) for c,p in zip(counts,clipped))
    return brier, log_loss

def evaluate(model, rows, method, m=None):
    match_sums = defaultdict(lambda: [0.0,0.0,0])
    phase_sums = {p: [0.0,0.0,0] for p in PHASES}
    player_sums = defaultdict(lambda: [0.0,0])
    calibration = [[[0.0,0,0] for _ in range(10)] for _ in range(3)]
    unseen = 0
    for row in rows:
        n = sum(row['counts'])
        if not n:
            continue
        key = (row['player_id'],row['phase'])
        p = predictions(model,*key,method,m)
        b,ll = losses(row['counts'],p)
        for target in (match_sums[row['match_id']], phase_sums[row['phase']]):
            target[0] += b; target[1] += ll; target[2] += n
        player_sums[key][0] += b; player_sums[key][1] += n
        unseen += n if not sum(model[0].get(key,[])) else 0
        for k in range(3):
            cell = calibration[k][min(9,int(p[k]*10))]
            cell[0] += p[k]*n; cell[1] += row['counts'][k]; cell[2] += n
    n = sum(x[2] for x in match_sums.values())
    return {'mean_brier': sum(x[0] for x in match_sums.values())/n,
        'mean_log_loss': sum(x[1] for x in match_sums.values())/n,
        'macro_player_phase_brier': sum(v[0]/v[1] for v in player_sums.values())/len(player_sums),
        'legal_deliveries': n,'matches': len(match_sums),'player_phase_groups': len(player_sums),
        'unseen_player_phase_deliveries': unseen, 'unseen_fraction': unseen/n,
        'by_phase': {p:{'brier': s[0]/s[2], 'log_loss': s[1]/s[2], 'n':s[2]} for p,s in phase_sums.items()},
        'calibration': {CATEGORIES[k]:[{'bin_left':i/10,'bin_right':(i+1)/10,'n':v[2],
            'predicted':v[0]/v[2] if v[2] else None,'observed':v[1]/v[2] if v[2] else None}
            for i,v in enumerate(cells)] for k,cells in enumerate(calibration)},
        'match_sums': dict(match_sums)}

def quantile(values, p):
    values = sorted(values)
    x = (len(values)-1)*p
    low = int(x); high = min(low+1,len(values)-1)
    return values[low]+(values[high]-values[low])*(x-low)

def bootstrap_difference(candidate, baseline, plan):
    ids = sorted(candidate['match_sums'])
    if ids != sorted(baseline['match_sums']):
        raise ValueError('Mismatched evaluation match IDs')
    values=[]; rng=random.Random(plan['bootstrap']['seed'])
    for _ in range(plan['bootstrap']['replicates']):
        selected=rng.choices(ids,k=len(ids))
        numerator=sum(candidate['match_sums'][k][0]-baseline['match_sums'][k][0] for k in selected)
        denominator=sum(candidate['match_sums'][k][2] for k in selected)
        values.append(numerator/denominator)
    return {'difference_candidate_minus_baseline': candidate['mean_brier']-baseline['mean_brier'],
        'percentile_95_interval': [quantile(values,.025),quantile(values,.975)],
        'negative_favors_candidate': True, **plan['bootstrap']}

def run_models(rows, plan):
    parts={name:[r for r in rows if int(r['season']) in plan[name+'_seasons']] for name in ('training','validation','test')}
    for name, part in parts.items():
        if not part:
            raise ValueError(f'No usable {name} data. Stop; do not silently alter split.')
    dates={name:{r['date'] for r in part} for name,part in parts.items()}
    if not max(dates['training']) < min(dates['validation']) <= max(dates['validation']) < min(dates['test']):
        raise ValueError('Temporal partition dates overlap or are unordered')
    training=aggregate(parts['training'])
    validation={str(m):evaluate(training,parts['validation'],'C',m) for m in plan['smoothing_candidates']}
    chosen=min(plan['smoothing_candidates'],key=lambda m:(validation[str(m)]['mean_brier'],-m))
    refit=aggregate(parts['training']+parts['validation'])
    test={method:evaluate(refit,parts['test'],method,chosen if method=='C' else None) for method in ('B0','B1','C')}
    return {'selected_m': chosen,'selection_metric':'validation_mean_brier',
        'validation_candidates':validation,
        'validation_baselines': {method:evaluate(training,parts['validation'],method) for method in ('B0','B1')},
        'test':test,'test_differences':{b:bootstrap_difference(test['C'],test[b],plan) for b in ('B0','B1')},
        'partition_dates':{name:{'min':min(d),'max':max(d)} for name,d in dates.items()},
        'status':'retrospective_held_out_evaluation_not_real_time_forecast'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    plan=json.loads((ROOT/'analysis-plan.json').read_text(encoding='utf-8'))
    acquisition=json.loads((DATA/'acquisition.json').read_text(encoding='utf-8'))
    archive=Path(acquisition['local_path'])
    if sha(archive)!=acquisition['sha256']:
        raise ValueError('Archive checksum mismatch')
    rows,manifest,report=audit(archive,plan)
    report.update({'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'archive_sha256':acquisition['sha256'],'pipeline_sha256':sha(Path(__file__)),
        'analysis_plan_sha256':sha(ROOT/'analysis-plan.json'), 'analysis_plan':plan,
        'attribution':'Contains information from Cricsheet (https://cricsheet.org/) under ODC-By 1.0 (https://opendatacommons.org/licenses/by/1-0/).',
        'data_gate':'pass_internal_consistency_pending_independent_review'})
    dump(ROOT/'match-manifest.json',manifest)
    dump(ROOT/'match-phase-counts.json',rows)
    dump(ROOT/'data-gate.json',report)
    if not args.audit_only:
        result=run_models(rows,plan)
        result.update({k:report[k] for k in ('generated_at_utc','archive_sha256','pipeline_sha256','analysis_plan_sha256','attribution')})
        dump(ROOT/'baseline-results.json',result)
    print(json.dumps({'target_matches':report['target_match_count'],'by_season':report['by_season'],
        'models_run':not args.audit_only, 'results_file':str(ROOT/('data-gate.json' if args.audit_only else 'baseline-results.json'))},indent=2))

if __name__=='__main__':
    main()
