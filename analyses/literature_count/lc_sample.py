"""Literature count, step 3: fix the coding order of the accessible included records (protocol section 5).

Output: outputs/coding_order.csv (rank, rid, doi, year, venue, title, oa_status, oa_urls). Usage: python lc_sample.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / 'outputs'


def main() -> None:
    u = pd.read_csv(OUT / 'screening_set.csv', dtype=str).fillna('')
    d = pd.read_csv(OUT / 'screening_decisions.csv', dtype=str).fillna('')
    m = u.merge(d[['rid', 'decision']], on='rid')
    frame = m[(m.decision == 'include') & (m.is_oa == 'True')].sort_values('doi').reset_index(drop=True)
    order = np.random.default_rng(20261013).permutation(len(frame))
    out = frame.iloc[order][['rid', 'doi', 'year', 'venue', 'title', 'oa_status', 'oa_urls']].reset_index(drop=True)
    out.insert(0, 'rank', range(1, len(out) + 1))
    out.to_csv(OUT / 'coding_order.csv', index=False)
    print(f'{len(frame)} accessible included records; coding order written')


if __name__ == '__main__':
    main()
