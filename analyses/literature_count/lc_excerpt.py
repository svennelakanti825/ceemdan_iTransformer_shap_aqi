"""Print coding evidence sentences: python lc_excerpt.py <rid> [...]  (from outputs/fulltext_text/<rid>.txt)."""
import re
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
T = Path(__file__).resolve().parent / 'outputs' / 'fulltext_text'
GROUPS = [('SPLIT', r'training (?:set|data|sample)|test(?:ing)? (?:set|data|sample)|train(?:ing)? and test|divided into|split|partition|first \d+ ?%|last \d+ ?%|train(?:ed|ing).{0,60}(?:\d{4}|data|samples)|\d+ ?% (?:of|for)|\bdays? (?:were|was) used|out[- ]of[- ]sample|validation set'),
          ('LEAK', r'look-?ahead|future (?:information|data|values)|leak|rolling|recursive|real-?time decomposition|end effect|boundary|endpoint|online decomposition|sliding window'),
          ('DECOMP', r'(?:is|are|was|were|be) (?:first )?decomposed|decompos(?:e|es|ing) the (?:original|raw|whole|entire)|original (?:\w+ ){0,3}series'),
          ('BASE', r'persisten|na[iï]ve|random walk|without decomposition|(?:single|individual) model|compar\w+ (?:with|to|against) (?:the )?(?:\w+ ){0,3}(?:model|method)s?|benchmark|baseline'),
          ('INTERP', r'(?:imf|component|mode|residual|trend)\w*\W+(?:\w+\W+){0,8}(?:reflect|represent|correspond|caused by|attribut|driven|due to)|policy|interpretab|shap'),
          ('CODE', r'github|code (?:is|are) available|data availability|available (?:at|from|upon)')]
for rid in sys.argv[1:]:
    t = re.sub(r'\s+', ' ', (T / f'{rid}.txt').read_text(encoding='utf-8', errors='replace'))
    m = re.search(r'(?i)\b(references|bibliography)\b', t[int(len(t) * 0.6):])
    if m:
        t = t[:int(len(t) * 0.6) + m.start()]
    sents = re.split(r'(?<=[.!?])\s+(?=[A-Z(])', t)
    print(f'===== {rid} ({len(t)} chars, {len(sents)} sentences)')
    seen, total = set(), 0
    for name, pat in GROUPS:
        hits = [s for s in sents if re.search(pat, s, re.I) and s not in seen and not re.search(r'et al\.|\[\d+(?:[,–-]\d+)*\]\s*(?:proposed|used|applied)', s)]
        out = []
        for s in hits[:8]:
            s = s[:450]
            if total + len(s) > 5200:
                break
            out.append(s); seen.add(s); total += len(s)
        if out:
            print(f'[{name}] ' + ' ‖ '.join(out))
    print()
