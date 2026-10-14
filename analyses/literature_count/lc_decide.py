"""Append title/abstract screening decisions from stdin to outputs/screening_decisions.csv.

Each line: <rid> INC [note]  or  <rid> EXC <CODE> <reason>. Codes: TOPIC (not a surface air-quality variable or not air
quality), NOFC (no out-of-sample time forecast), NODEC (no decomposition of a series feeding the model), REV (review or
survey), DESC (decomposition only descriptive), NOTPR (not peer reviewed), NONEN (not English), RETR (retracted),
DUP (duplicate missed by DOI/title matching). A correction: <rid> FIX <decision line without rid>; it replaces the
earlier decision and keeps it in the column 'previous'.
Uncertain records are INC (protocol section 3). A rid already decided is refused.
"""
import sys
from pathlib import Path
import pandas as pd
OUT = Path(__file__).resolve().parent / 'outputs' / 'screening_decisions.csv'
CODES = {'TOPIC', 'NOFC', 'NODEC', 'REV', 'DESC', 'NOTPR', 'NONEN', 'RETR', 'DUP'}
old = pd.read_csv(OUT, dtype=str).fillna('') if OUT.exists() else pd.DataFrame(columns=['rid', 'decision', 'code', 'reason'])
if 'previous' not in old.columns:
    old['previous'] = ''
rows = []
for ln in sys.stdin.read().splitlines():
    ln = ln.strip()
    if not ln:
        continue
    fix = ln.split(maxsplit=2)[1] == 'FIX'
    if fix:
        rid0, _, rest = ln.split(maxsplit=2)
        ln = f'{rid0} {rest}'
    parts = ln.split(maxsplit=3)
    rid, dec = parts[0], parts[1]
    if fix:
        i = old.index[old.rid == rid]
        assert len(i) == 1, f'{rid}: nothing to correct'
        prev = old.loc[i[0]]
        old = old.drop(i)
        prev_txt = f"{prev['decision']} {prev['code']} {prev['reason']}".strip()
    else:
        assert rid not in set(old.rid) and rid not in {r['rid'] for r in rows}, f'{rid} already decided'
        prev_txt = ''
    if dec == 'INC':
        rows.append({'rid': rid, 'decision': 'include', 'code': '', 'reason': ' '.join(parts[2:]), 'previous': prev_txt})
    else:
        assert dec == 'EXC' and parts[2] in CODES and len(parts) == 4, ln
        rows.append({'rid': rid, 'decision': 'exclude', 'code': parts[2], 'reason': parts[3], 'previous': prev_txt})
new = pd.concat([old, pd.DataFrame(rows)], ignore_index=True)
new = new.sort_values('rid').reset_index(drop=True)
new.to_csv(OUT, index=False)
print(f'+{len(rows)} decisions, total {len(new)} (include {int((new.decision == "include").sum())}, exclude {int((new.decision == "exclude").sum())})')
