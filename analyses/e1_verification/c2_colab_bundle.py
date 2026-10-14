"""C2-T5 platform test (decision C2-12): pack what the runner needs into one zip for Google Colab.

The zip keeps repository-relative paths, so c2x_features finds every pinned input where Appendix A says. It
contains:
- the 30 pinned inputs;
- the approved pre-registration and addenda A1 and A2;
- the C2 code and the three C2 test files, which are hashed into every verdict;
- c2_requirements.txt, the exact package versions (Colab builds a clean Python 3.13.0 environment from it);
- the laptop references from c2_t5_dryrun.py:
  - dry runs A (8 threads) and C (2 threads);
  - the full-size model fingerprints of the timing runs at 8 and 2 threads;
  - the feature-build summary (digests of BASE and every weather block);
  - the timing lines;
- the Colab Linux references of the platform test (outputs/dryrun/colab_linux, 10 Oct): the 2-thread dry run and
  full-size fingerprints of the CPU runtime (AMD EPYC; identical on the Intel Xeon of the GPU runtime), and both
  runtimes' feature summaries. The real-run notebook's pre-flight check compares with them;
- C2_FREEZE_SHA256.txt, once the code is frozen. Every file it lists must match it, or no bundle is built;
- bundle_manifest.json, with the raw-byte SHA-256 of every file.

The notebooks c2_colab_dryrun.ipynb (platform test) and c2_colab_run.ipynb (real run and rerun, addendum A2) check the
manifest after unpacking, so a damaged upload cannot pass silently. c2_colab_run.ipynb runs a real run only from a
frozen bundle.
Usage: python c2_colab_bundle.py  -> outputs/c2_colab_bundle.zip (git-ignored); upload it to My Drive.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
import platform
import zipfile

import c2_xgb_confirm as rn
import c2x_features as cx

PYTHON = '3.13.0'                                    # pre-registration section 2
CODE = [cx.HERE / n for n in ('common.py', 'e1_leakage_contrast.py', 'e5_driver_band_precheck.py', 'fetch_era5.py',
                               'fetch_era5_pool.py', 'c2x_features.py', 'c2x_verdict.py', 'c2_xgb_confirm.py')]
DOCS = [cx.PREREG, cx.ADDENDUM_A1, cx.ADDENDUM_A2]
REQUIREMENTS = cx.HERE / 'c2_requirements.txt'
DRY = cx.OUT / 'dryrun'
REF_RUNS = {'8': 'A', '2': 'C'}                      # XGBoost threads -> laptop dry run with that thread count
REFERENCE = [DRY / run / n for run in REF_RUNS.values()
             for n in ('dry_pooled.csv', 'dry_city.csv', 'dry_predictions.npz', 'dry_verdict.json', 'dry_verdict.txt')]
FINGERPRINTS = {t: rn.fingerprint_path(DRY / 'timing', 'cpu', 1, int(t)) for t in REF_RUNS}
FEATURES_SUMMARY = cx.OUT / 'c2_t2_features_summary.txt'
REPORT = DRY / 'c2_t5_dryrun_report.txt'
LINUX = DRY / 'colab_linux'
LINUX_DRY = LINUX / 'cpu_runtime' / 'dry_cpu_t2'
LINUX_REFERENCE = [LINUX_DRY / n for n in ('dry_pooled.csv', 'dry_city.csv', 'dry_predictions.npz', 'dry_verdict.json',
                                           'dry_verdict.txt')]
LINUX_FINGERPRINTS = LINUX / 'cpu_runtime' / 'timing' / 'fingerprints_cpu_p1_t2.json'
LINUX_SUMMARIES = {'AMD EPYC 7B12 (Colab CPU runtime)': LINUX / 'cpu_runtime' / 'c2_t2_features_summary_colab.txt',
                   'Intel Xeon @ 2.00GHz (Colab GPU runtime)': LINUX / 'gpu_runtime' / 'c2_t2_features_summary_colab.txt'}
FREEZE = cx.HERE / 'C2_FREEZE_SHA256.txt'


def frozen_files() -> dict[str, str]:
    """The freeze record: repository-relative path -> SHA-256 (pre-registration hash rule). Empty before the freeze."""
    if not FREEZE.is_file():
        return {}
    rows = [l.split() for l in FREEZE.read_text(encoding='utf-8').splitlines() if l.strip() and not l.startswith('#')]
    return {path: sha for sha, path in rows}


def rel(p) -> str:
    return p.relative_to(cx.REPO).as_posix()


def pinned() -> dict[str, str]:
    lines = REQUIREMENTS.read_text(encoding='utf-8').splitlines()
    return dict(x.strip().split('==') for x in lines if x.strip() and not x.startswith('#'))


def main() -> None:
    freeze = frozen_files()
    changed = [f for f, want in freeze.items() if not (cx.REPO / f).is_file() or cx.sha256_rule(cx.REPO / f) != want]
    if changed:
        raise SystemExit('frozen files changed since the freeze (a new, labelled run would be needed): ' + ', '.join(changed))
    files = sorted({*(p for _, p, _ in cx.appendix_a()), *CODE, *DOCS, *rn.SCRIPTS, *REFERENCE, *FINGERPRINTS.values(),
                    FEATURES_SUMMARY, REQUIREMENTS, *LINUX_REFERENCE, LINUX_FINGERPRINTS, *LINUX_SUMMARIES.values(),
                    *([FREEZE] if freeze else [])}, key=str)
    missing = [str(p) for p in files if not p.is_file()]
    if missing:
        raise SystemExit('missing (run c2_t5_dryrun.py first for the references): ' + ', '.join(missing))
    if 'ALL REQUIRED CHECKS PASS' not in REPORT.read_text(encoding='utf-8'):
        raise SystemExit('the T5 dry-run checks have not all passed; no bundle')
    differ = {n: (md.version(n), v) for n, v in pinned().items() if md.version(n) != v}
    if platform.python_version() != PYTHON or differ:
        raise SystemExit(f'this environment is not the pinned one: python {platform.python_version()}, {differ}')
    manifest = {'files': {rel(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                'python': PYTHON, 'requirements': rel(REQUIREMENTS),
                'laptop_references': {t: rel(DRY / run) for t, run in REF_RUNS.items()},
                'laptop_fingerprints': {t: rel(p) for t, p in FINGERPRINTS.items()},
                'laptop_features_summary': rel(FEATURES_SUMMARY),
                'laptop_timing': [l.strip() for l in REPORT.read_text(encoding='utf-8').splitlines()
                                  if l.strip().startswith('TIMING')],
                'linux_reference': {'dry': rel(LINUX_DRY), 'fingerprints': rel(LINUX_FINGERPRINTS), 'threads': 2},
                'linux_features_summaries': {k: rel(v) for k, v in LINUX_SUMMARIES.items()},
                'frozen': bool(freeze), 'freeze_file': rel(FREEZE) if freeze else None}
    out = cx.OUT / 'c2_colab_bundle.zip'
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, rel(p))
        zf.writestr('bundle_manifest.json', json.dumps(manifest, indent=1))
    size = out.stat().st_size / 1e6
    print(f'{out} ({size:.1f} MB): {len(files)} files + manifest; '
          + (f'frozen code ({len(freeze)} files match the freeze record)' if freeze
             else 'NOT FROZEN: a real run will refuse this bundle (rehearsal only)'))


if __name__ == '__main__':
    main()
