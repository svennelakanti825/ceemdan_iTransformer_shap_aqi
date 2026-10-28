"""E7 D2: causal CEEMDAN (r1_ext settings) of bulletin AQI at the selected origins, one cached npz per city."""
from __future__ import annotations

import json
import sys
import time

import numpy as np


def _job(args):
    from e7_common import EXTENSION, NS
    history, seed = args
    comps = NS['c5_decompose'](history, seed, extension=EXTENSION)
    keep = NS['C5_KEEP']
    tail = np.full((NS['C5_MAX_COMPONENTS'], keep), np.nan)
    tail[:len(comps)] = comps[:, -keep:]
    periods = (np.array([NS['c5_period'](ch) for ch in NS['c5_channels'](comps)]) if len(comps) >= 5
               else np.full(5, np.nan))
    return tail, len(comps), periods, len(history)


def main(n_jobs: int = 8) -> None:
    from multiprocessing import Pool
    from e7_common import D2_CITIES, DECOMP, EXTENSION, NS, city_calendar, load_bulletin, origins
    b = load_bulletin()
    plan = {c: origins(city_calendar(b, c)) for c in D2_CITIES}
    total = sum(len(v) for v in plan.values())
    print('origins per city:', {c: len(v) for c, v in plan.items()}, 'total', total, flush=True)
    params = NS['c5_params'](extension=EXTENSION)
    with Pool(n_jobs) as pool:
        for c in D2_CITIES:
            f = DECOMP / f'e7_{c}.npz'
            info = city_calendar(b, c)
            fp = NS['c5_fingerprint'](info['cal']['Date'], info['y'], info['available'], info['seed'])
            if f.exists():
                meta = json.loads(str(np.load(f)['meta']))
                if meta['fingerprint'] == fp and meta['params'] == params and meta['n'] == len(plan[c]):
                    print(c, 'cached', flush=True)
                    continue
            t0 = time.time()
            jobs = [(NS['c5_history'](info['y'], info['available'], int(t)), info['seed']) for t in plan[c]]
            out = pool.map(_job, jobs, chunksize=4)
            np.savez_compressed(f, days=plan[c].astype(np.int64), tail=np.stack([o[0] for o in out]),
                                n_components=np.array([o[1] for o in out]), periods=np.stack([o[2] for o in out]),
                                history_len=np.array([o[3] for o in out]),
                                meta=json.dumps({'fingerprint': fp, 'params': params, 'n': len(plan[c]),
                                                 'seed': info['seed']}))
            print(f'{c}: {len(jobs)} decompositions in {time.time() - t0:.0f} s', flush=True)
    print('E7 decomposition DONE', flush=True)


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
