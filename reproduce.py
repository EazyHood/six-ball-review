"""Portable adapter for the frozen experiment; writes only to a fresh output folder.

The default recreates the data audit. --models explicitly reproduces the already
observed fixed experiment; it does not create a new untouched test or new model.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path, PureWindowsPath

import pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--dataset-dir', type=Path, help='Existing ZIP plus acquisition.json directory.')
    source.add_argument('--archive', type=Path, help='Manually downloaded frozen ZIP; no acquisition.json required.')
    parser.add_argument('--output-dir', required=True, type=Path,
                        help='New directory; original evidence is never overwritten.')
    parser.add_argument('--models', action='store_true', help='Also reproduce the fixed historical comparison.')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if out.exists():
        raise ValueError('Output directory exists; choose a new directory to preserve earlier evidence')
    root = Path(__file__).resolve().parent
    original = {name: pipeline.sha(root / name) for name in
                ('pipeline.py', 'analysis-plan.json', 'baseline-results.json', 'data-gate.json')}
    plan = json.loads((root / 'analysis-plan.json').read_text(encoding='utf-8'))
    fixed = json.loads((root / 'baseline-results.json').read_text(encoding='utf-8'))
    if args.archive is not None:
        archive = args.archive
        archive_sha256 = pipeline.sha(archive)
    else:
        acquisition = json.loads((args.dataset_dir / 'acquisition.json').read_text(encoding='utf-8'))
        archive = args.dataset_dir / PureWindowsPath(acquisition['local_path']).name
        archive_sha256 = pipeline.sha(archive)
        if archive_sha256 != acquisition['sha256']:
            raise ValueError('Archive differs from acquisition manifest')
    if archive_sha256 != fixed['archive_sha256']:
        raise ValueError('Archive is not the frozen snapshot; no silent replacement')
    if original['pipeline.py'] != fixed['pipeline_sha256'] or original['analysis-plan.json'] != fixed['analysis_plan_sha256']:
        raise ValueError('Frozen code or plan has changed')
    rows, manifest, report = pipeline.audit(archive, plan)
    report.update({'generated_at_utc': datetime.now(timezone.utc).isoformat(),
                   'archive_sha256': archive_sha256, 'pipeline_sha256': original['pipeline.py'],
                   'analysis_plan_sha256': original['analysis-plan.json'], 'analysis_plan': plan,
                   'adapter_sha256': pipeline.sha(Path(__file__)), 'attribution': fixed['attribution'],
                   'reproduction_note': 'Portable adapter calls unchanged audit/model functions; independent review remains documented separately.'})
    result = pipeline.run_models(rows, plan) if args.models else None
    out.mkdir(parents=True, exist_ok=False)
    (out / 'LEEME.md').write_text(
        'Reproduccion del experimento fijo Six-Ball Review.\n'
        'Creada por el adaptador reproduce.py de Codex.\n'
        f'Fecha: {datetime.now(timezone.utc).date()}.\n'
        'La usa la comprobacion de portabilidad; no sustituye resultados originales.\n'
        'Se puede borrar y regenerar desde el ZIP y codigo fijados.\n', encoding='utf-8')
    pipeline.dump(out / 'match-manifest.json', manifest)
    pipeline.dump(out / 'match-phase-counts.json', rows)
    pipeline.dump(out / 'data-gate.json', report)
    if result is not None:
        result.update({key: report[key] for key in ('generated_at_utc', 'archive_sha256', 'pipeline_sha256', 'analysis_plan_sha256', 'attribution')})
        pipeline.dump(out / 'baseline-results.json', result)
    if any(pipeline.sha(root / name) != expected for name, expected in original.items()):
        raise RuntimeError('Original experiment changed during reproduction')
    print(json.dumps({'output': str(out), 'rows': len(rows), 'matches': len(manifest),
                      'models_reproduced': args.models, 'original_experiment_unchanged': True}, indent=2))


if __name__ == '__main__':
    main()
