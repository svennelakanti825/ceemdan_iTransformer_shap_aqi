"""Append full-text coding to outputs/coding_sheet.csv from stdin, one record per line, fields separated by ' | ':
rid | status | T1 | T2 | T3 | T3_explicit | T4 | T5 | T6 | T7 | T8 | T9 | T10 | evidence
status: CODED, or SKIP-<CODE> (protocol exclusion code at full text) or SKIP-NOACCESS. For SKIP lines only rid, status
and evidence are needed (other fields '-'). T3 values i, ii, iii, iv, v (protocol section 4)."""
import sys
from pathlib import Path
import pandas as pd
OUT = Path(__file__).resolve().parent / 'outputs' / 'coding_sheet.csv'
COLS = ['rid', 'status', 'T1_target', 'T2_method', 'T3_timing', 'T3_explicit', 'T4_boundary', 'T5_nodec_model', 'T6_persistence',
        'T7_gain', 'T8_interpretation', 'T9_explanation', 'T10_code_data', 'evidence']
old = pd.read_csv(OUT, dtype=str).fillna('') if OUT.exists() else pd.DataFrame(columns=COLS)
rows = []
for ln in sys.stdin.read().splitlines():
    if not ln.strip():
        continue
    f = [x.strip() for x in ln.split(' | ')]
    assert len(f) == 14, (len(f), ln[:80])
    assert f[0] not in set(old.rid), f'{f[0]} already coded'
    assert f[1] == 'CODED' or f[1].startswith('SKIP-'), f[1]
    if f[1] == 'CODED':
        assert f[4] in {'i', 'ii', 'iii', 'iv', 'v'}, f[4]
        assert all(f[k] in {'yes', 'no'} for k in (5, 6, 7, 8, 10)), ln[:80]
    rows.append(dict(zip(COLS, f)))
new = pd.concat([old, pd.DataFrame(rows)], ignore_index=True)
new.to_csv(OUT, index=False)
c = new[new.status == 'CODED']
print(f'+{len(rows)}; coded {len(c)}, skipped {len(new) - len(c)}; T3 {c.T3_timing.value_counts().to_dict()}')
