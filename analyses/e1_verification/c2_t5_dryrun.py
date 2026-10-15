"""C2-T5 dry-run checks: the runner end to end on the made-up target, before the freeze. Produces no real result.

  A  uninterrupted dry run (all 32 arms, seeds 0-1), processes 1 x n_jobs 8
  B  the same, stopped after 20 fits and resumed. It must equal A byte for byte.
  C  processes 4 x n_jobs 2, compared with A. Whether they are equal shows if the thread count changes the results.
  D  processes 1 x n_jobs 2. It must equal C: only the thread count may matter, never the number of processes.
  T  timing mode (400 trees + SHAP on 300 trees) for the layouts 1x8, 2x4, 4x2 and 1x2, with the fingerprints of
     the full-size models. 1x2 must equal 4x2 (the dry run's models keep only a few trees, so this repeats the
     process-count check at full size). The 1x8 and 1x2 fingerprints are the laptop references for Colab.
  S  one fit of A recomputed in a fresh process, which must be identical
  plus checks of A's outputs (Appendix B columns, row counts, dry-run labels) and of the real outputs folder (empty).

Report: outputs/dryrun/c2_t5_dryrun_report.txt. Exit code 1 if a required check fails.
Usage: python c2_t5_dryrun.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

import c2_xgb_confirm as rn
import c2x_features as cx
import c2x_verdict as cv

DRY = cx.OUT / 'dryrun'
RUNNER = cx.HERE / 'c2_xgb_confirm.py'
FILES = ['dry_pooled.csv', 'dry_city.csv', 'dry_predictions.npz', 'dry_verdict.json', 'dry_verdict.txt']
LINES: list[str] = []
FAILED: list[str] = []


def say(line: str) -> None:
    print(line, flush=True)
    LINES.append(line)


def check(name: str, ok: bool, detail: str = '') -> None:
    say(f'  {"PASS" if ok else "FAIL"} {name}' + (f': {detail}' if detail else ''))
    if not ok:
        FAILED.append(name)


def runner(*args: str) -> tuple[int, float, str]:
    t0 = time.time()
    p = subprocess.run([sys.executable, str(RUNNER), *args], cwd=cx.HERE, capture_output=True, text=True)
    if p.returncode not in (0, 3):
        print(p.stdout[-3000:], p.stderr[-3000:])
    return p.returncode, time.time() - t0, p.stdout


def fresh(folder: Path) -> Path:
    if folder.exists():
        for f in sorted(folder.rglob('*'), reverse=True):
            f.unlink() if f.is_file() else f.rmdir()
        folder.rmdir()
    return folder


def same_bytes(a: Path, b: Path) -> bool:
    return a.read_bytes() == b.read_bytes()


def verdict_without_provenance(path: Path) -> dict:
    v = json.loads(path.read_text(encoding='utf-8'))
    v.pop('provenance')
    return v


def main() -> int:
    say('C2-T5 dry-run checks (made-up target: independent noise, seed '
        f'{rn.DRY_SEED}; no real result is produced)')
    a, b, c = fresh(DRY / 'A'), fresh(DRY / 'B'), fresh(DRY / 'C')
    fresh(DRY / 'timing')                                      # one set of timing lines per run

    say('\nA: uninterrupted, processes 1 x n_jobs 8')
    code, sec, _ = runner('--dry-run', '--seeds', '0', '1', '--processes', '1', '--n-jobs', '8', '--out', str(a))
    check('A completes', code == 0, f'{sec:.0f} s for 64 fits')

    say('\nB: stopped after 20 fits, then resumed')
    code1, sec1, _ = runner('--dry-run', '--seeds', '0', '1', '--n-jobs', '8', '--stop-after', '20', '--out', str(b))
    n_parts = len(list((b / 'parts').glob('*.json')))
    check('B stops as asked', code1 == 3 and n_parts == 20, f'exit {code1}, {n_parts} finished parts')
    code2, sec2, out2 = runner('--dry-run', '--seeds', '0', '1', '--n-jobs', '8', '--out', str(b))
    check('B resumes the remaining 44 fits only', code2 == 0 and '44 to run now' in out2)
    for f in FILES:
        check(f'B equals A byte for byte: {f}', same_bytes(a / f, b / f))

    say('\nC: processes 4 x n_jobs 2 (thread count changed)')
    code, sec, _ = runner('--dry-run', '--seeds', '0', '1', '--processes', '4', '--n-jobs', '2', '--out', str(c))
    check('C completes', code == 0, f'{sec:.0f} s for 64 fits')
    data_same = all(same_bytes(a / f, c / f) for f in FILES[:3])
    with np.load(a / 'dry_predictions.npz') as pa, np.load(c / 'dry_predictions.npz') as pc:
        diff = float(np.abs(pa['pred'].astype(np.float64) - pc['pred']).max())
    verdict_same = verdict_without_provenance(a / 'dry_verdict.json') == verdict_without_provenance(c / 'dry_verdict.json')
    say(f'  INFO C against A: tables and predictions identical: {data_same}; largest prediction difference {diff:.3g}; '
        f'verdict identical apart from provenance: {verdict_same}')

    say('\nD: processes 1 x n_jobs 2 (same thread count as C, one process)')
    d = fresh(DRY / 'D')
    code, sec, _ = runner('--dry-run', '--seeds', '0', '1', '--processes', '1', '--n-jobs', '2', '--out', str(d))
    check('D completes', code == 0, f'{sec:.0f} s for 64 fits')
    for f in FILES[:3]:
        check(f'D equals C byte for byte (only the thread count matters, not the process count): {f}',
              same_bytes(c / f, d / f))
    check('D verdict equals C apart from provenance',
          verdict_without_provenance(c / 'dry_verdict.json') == verdict_without_provenance(d / 'dry_verdict.json'))

    say("\nOutputs of A")
    pooled, city = pd.read_csv(a / 'dry_pooled.csv'), pd.read_csv(a / 'dry_city.csv')
    check('pooled columns are Appendix B', list(pooled.columns) == ['arm', 'seed', 'period'] + cv.POOLED_COLS)
    check('city columns are Appendix B', list(city.columns) == ['arm', 'seed', 'city'] + cv.CITY_COLS)
    check('pooled rows = 32 arms x 2 seeds x 3 periods', len(pooled) == 32 * 2 * 3, str(len(pooled)))
    check('city rows = 32 x 2 x cities >= 150', len(city) == 32 * 2 * city.city.nunique() and city.n.min() >= 150,
          f'{city.city.nunique()} cities')
    check('BASE weather shares are 0', (pooled.loc[pooled.arm == 'BASE', cv.WEATHER_COLS] == 0).all().all())
    v = json.loads((a / 'dry_verdict.json').read_text(encoding='utf-8'))
    check('verdict labelled a dry run', v['provenance']['mode'].startswith('DRY RUN')
          and any('dry run' in w for w in v['warnings']) and v['seeds'] == [0, 1])
    check('verdict records the approved hashes', v['pre_registration_sha256'] == cx.PREREG_SHA256
          and v['addendum_A1_sha256'] == cx.ADDENDUM_A1_SHA256 and v['addendum_A2_sha256'] == cx.ADDENDUM_A2_SHA256)
    check('max additivity gap < 0.01', v['provenance']['max additivity gap'] < rn.ADDITIVITY_TOL,
          f"{v['provenance']['max additivity gap']:.1e}")
    check('provenance records the threads XGBoost used and the CPU',
          v['provenance']['xgboost threads used per fit'] == v['provenance']['xgboost n_jobs per fit'] == 8
          and v['provenance']['cpu'] not in ('', 'unknown'), v['provenance']['cpu'])
    check('provenance records the machine of every fit and the run key (addendum A2.3)',
          v['provenance']['fits made on (addendum A2.3)'] == {rn.machine(): 64}
          and v['provenance']['run key'] == rn.run_key(True, 8, 'cpu'))
    vb = json.loads((b / 'dry_verdict.json').read_text(encoding='utf-8'))
    check('stopped-and-resumed B also lists all 64 fits on this machine',
          vb['provenance']['fits made on (addendum A2.3)'] == {rn.machine(): 64})
    check('no text output has CRLF', all(b'\r\n' not in (a / f).read_bytes() for f in FILES if f.endswith(('csv', 'json', 'txt'))))
    real = [p.name for p in cx.OUT.glob('c2x_*')]
    check('the real outputs folder holds no c2x_ file', not real, ', '.join(real))

    say('\nS: one fit of A recomputed in this process')
    r = rn.fit_one(rn.load(True), 'MET_PP', 0, n_jobs=8)
    part = json.loads((a / 'parts' / 'MET_PP__s00.json').read_text(encoding='utf-8'))
    check('fresh fit equals the stored part (metrics, shares, cities, predictions)',
          part['pooled'] == r['pooled'] and part['city'] == r['city']
          and np.array_equal(np.load(a / 'parts' / 'MET_PP__s00.npy'), r['pred']))

    say('\nT: timing (fixed 400 trees + SHAP on 300 trees, made-up target) and full-size fingerprints')
    timing = DRY / 'timing'
    fps = {}
    for p, j in ((1, 8), (2, 4), (4, 2), (1, 2)):
        code, _, out = runner('--timing', '--processes', str(p), '--n-jobs', str(j), '--out', str(timing))
        line = [x for x in out.splitlines() if x.startswith('TIMING')]
        fp = rn.fingerprint_path(timing, 'cpu', p, j)
        check(f'timing {p} x {j} runs', code == 0 and len(line) == 1 and fp.is_file())
        if line:
            say('    ' + line[0])
        if fp.is_file():
            fps[p, j] = json.loads(fp.read_text(encoding='utf-8'))['arms']
    check('full-size models (400 trees): 1 x 2 equals 4 x 2 in all 8 arms (only the thread count matters)',
          fps.get((1, 2)) is not None and fps.get((1, 2)) == fps.get((4, 2)))
    if (1, 8) in fps and (1, 2) in fps:
        same = sum(fps[1, 8][a] == fps[1, 2][a] for a in fps[1, 8])
        say(f'  INFO full-size models: 8 threads equal 2 threads in {same} of {len(fps[1, 8])} arms')

    say(f'\nRESULT: {"ALL REQUIRED CHECKS PASS" if not FAILED else "FAILED: " + "; ".join(FAILED)}')
    with open(DRY / 'c2_t5_dryrun_report.txt', 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LINES) + '\n')
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
