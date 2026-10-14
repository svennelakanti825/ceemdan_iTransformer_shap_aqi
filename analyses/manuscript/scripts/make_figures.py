"""Draw the main-text and supplementary figures of the revised manuscript from the stored result files.

Every plotted value is read from a result file of the revision (paths in SRC). Nothing is retrained or recomputed
beyond shares and means of stored values. Outputs go to ../figures/ as PDF and PNG (or to $FIG_OUT if set).

Figures are drawn at print size (6.5 in text width of arxiv.sty), so the type in every figure prints at the same
size. Each figure is checked before saving: no text may leave the figure, overlap other text or, in Figure 1,
leave its box; no legend may cover a data point.

Usage: python make_figures.py
"""
from __future__ import annotations

import os
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.text import Text
from matplotlib.transforms import blended_transform_factory
from scipy.cluster.hierarchy import leaves_list, linkage

HERE = Path(__file__).resolve().parent
FIG = Path(os.environ.get('FIG_OUT', HERE.parent / 'figures'))
REPO = Path(os.environ.get('REPO_ROOT', HERE.parents[2]))
R1 = REPO / 'analyses'
RES = REPO / 'results' / '02_r1_ext'
SRC = {
    'g1_matrix': REPO / 'results' / '04_followups' / 'reports' / 'shap' / 'g1_shap18_matrix_lb7.csv',
    'g1_summary': REPO / 'results' / '04_followups' / 'reports' / 'shap' / 'g1_shap18_summary_lb7.csv',
    'g2_shap': REPO / 'results' / '04_followups' / 'reports' / 'shap' / 'g2_shap_lb7.csv',
    'ablation': RES / 'reports' / 'shap' / 'shap_periods_ablation13ch_lb7.csv',
    'pm25': RES / 'reports' / 'shap' / 'shap_v2_pm25_attribution_lb7.csv',
    'e1_shares': R1 / 'x1_shap_recheck' / 'outputs' / 'e1_shares.csv',
    'e7_pooled': R1 / 'x1_shap_recheck' / 'outputs' / 'e7_d2_pooled.csv',
}
POLLUTANTS = ['PM2.5', 'PM10', 'NO', 'NO2', 'NOx', 'NH3', 'CO', 'SO2', 'O3', 'Benzene', 'Toluene', 'Xylene']
OSC = ['IMF1', 'IMF2', 'IMF3', 'IMF4']
SLOW = 'IMF5+ (slow)'
FOCUS = ['Delhi', 'Mumbai', 'Bengaluru']
TEX = {'PM2.5': 'PM$_{2.5}$', 'PM10': 'PM$_{10}$', 'NO2': 'NO$_2$', 'NOx': 'NO$_x$', 'NH3': 'NH$_3$',
       'SO2': 'SO$_2$', 'O3': 'O$_3$', SLOW: 'Slow'}
TEXTWIDTH = 6.5  # inches, \textwidth of arxiv.sty

# Colour-blind safe (Okabe-Ito) and perceptually uniform colour map, no rainbow maps (editorial requirement ED7).
C = {'pm25': '#0072B2', 'pm10': '#56B4E9', 'other': '#C4C4C4', 'slow': '#E69F00', 'osc': '#D55E00',
     'grey': '#4D4D4D', 'light': '#DADADA', 'causal': '#0072B2', 'leaky': '#D55E00', 'h1': '#0072B2',
     'h7': '#009E73', 'box_fc': '#F4F7FA', 'box_ec': '#5B7896'}


def _sans() -> str:
    names = {f.name for f in font_manager.fontManager.ttflist}
    return next(n for n in ('Arial', 'Liberation Sans', 'Helvetica', 'DejaVu Sans') if n in names)


SANS = _sans()
plt.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': [SANS, 'DejaVu Sans'],
    'mathtext.fontset': 'custom', 'mathtext.rm': SANS, 'mathtext.it': f'{SANS}:italic',
    'mathtext.bf': f'{SANS}:bold',
    'font.size': 7.5, 'axes.labelsize': 7.5, 'xtick.labelsize': 7, 'ytick.labelsize': 7, 'legend.fontsize': 7,
    'axes.linewidth': 0.6, 'xtick.major.width': 0.6, 'ytick.major.width': 0.6,
    'xtick.major.size': 2.5, 'ytick.major.size': 2.5, 'xtick.major.pad': 2, 'ytick.major.pad': 2,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': '#333333',
    'xtick.color': '#333333', 'ytick.color': '#333333', 'axes.labelcolor': '#1A1A1A', 'text.color': '#1A1A1A',
    'axes.labelpad': 3, 'legend.frameon': False, 'legend.handletextpad': 0.4, 'legend.borderaxespad': 0.3,
    'legend.labelspacing': 0.35, 'pdf.fonttype': 42, 'savefig.dpi': 400,
})


# ---------------------------------------------------------------------------------------------------- checks
def _texts(fig: plt.Figure) -> list[Text]:
    """Visible texts that are drawn: tick labels count only for ticks inside the view limits."""
    ticks = {id(t) for ax in fig.axes for axis in (ax.xaxis, ax.yaxis) for tk in axis.get_major_ticks()
             for t in (tk.label1, tk.label2)}
    drawn = {id(t) for ax in fig.axes if ax.axison for axis in (ax.xaxis, ax.yaxis) for tk in axis._update_ticks()
             for t in (tk.label1, tk.label2) if t.get_visible()}
    return [t for t in fig.findobj(Text) if t.get_visible() and t.get_text().strip()
            and (id(t) not in ticks or id(t) in drawn)]


def check(fig: plt.Figure, name: str, boxes: list | None = None) -> None:
    """Fail if any text leaves the figure or a box, overlaps other text, or a legend covers a data point."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    fb = fig.bbox
    texts = [(t, t.get_window_extent(r)) for t in _texts(fig)]
    out = [t.get_text() for t, b in texts
           if b.x0 < fb.x0 - 0.5 or b.y0 < fb.y0 - 0.5 or b.x1 > fb.x1 + 0.5 or b.y1 > fb.y1 + 0.5]
    assert not out, f'{name}: text outside the figure: {out}'
    def collide(a: Text, ba, b: Text, bb) -> bool:
        if not (ba.overlaps(bb) and ba.intersection(ba, bb).width > 1 and ba.intersection(ba, bb).height > 1):
            return False
        th = np.deg2rad(a.get_rotation())
        if a.get_rotation() and a.get_rotation() == b.get_rotation():  # parallel rotated labels: test the gap
            (xa, ya), (xb, yb) = (t.get_transform().transform(t.get_position()) for t in (a, b))
            gap = abs(-np.sin(th) * (xb - xa) + np.cos(th) * (yb - ya))
            return gap < 1.05 * a.get_fontsize() * fig.dpi / 72
        return True
    clash = [(a.get_text(), b.get_text()) for (a, ba), (b, bb) in combinations(texts, 2) if collide(a, ba, b, bb)]
    assert not clash, f'{name}: overlapping text: {clash}'
    for box, members in boxes or []:
        bb = box.get_window_extent(r)
        loose = [t.get_text() for t in members
                 if not (bb.x0 <= t.get_window_extent(r).x0 and t.get_window_extent(r).x1 <= bb.x1
                         and bb.y0 <= t.get_window_extent(r).y0 and t.get_window_extent(r).y1 <= bb.y1)]
        assert not loose, f'{name}: text outside its box: {loose}'
    for ax in fig.axes:
        leg = ax.get_legend()
        if leg is None:
            continue
        lb = leg.get_window_extent(r)
        for coll in ax.collections:
            pts = coll.get_offset_transform().transform(coll.get_offsets())
            inside = ((pts[:, 0] > lb.x0) & (pts[:, 0] < lb.x1) & (pts[:, 1] > lb.y0) & (pts[:, 1] < lb.y1))
            assert not inside.any(), f'{name}: legend covers {int(inside.sum())} data points'


def save(fig: plt.Figure, name: str, boxes: list | None = None) -> None:
    check(fig, name, boxes)
    for ext in ('pdf', 'png'):
        fig.savefig(FIG / f'{name}.{ext}')
    plt.close(fig)
    print('written', name)


def panel_letters(fig: plt.Figure, axes, letters: str, dy: float = 0.06) -> None:
    """Place bold panel letters level with each other, flush with the left edge of each panel's labels."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    top = max(ax.get_position().y1 for ax in axes)
    for ax, lab in zip(axes, letters):
        x0 = fig.transFigure.inverted().transform(ax.get_tightbbox(r).p0)[0]
        fig.text(max(x0, 0.004), top + dy / fig.get_figheight(), lab, fontsize=9, fontweight='bold',
                 ha='left', va='bottom')


def shares(row: pd.Series) -> pd.Series:
    return 100 * row / row.sum()


# ---------------------------------------------------------------------------------------------------- Figure 1
def _wrap(fig, text: str, width_px: float, **kw) -> list[str]:
    """Fewest lines that fit the width, then the most even split among them (no one-word last lines).
    A non-breaking space (\u00a0) keeps a number with its noun."""
    r = fig.canvas.get_renderer()

    def width(s: str) -> float:
        probe = fig.text(0, 0, s.replace('\u00a0', ' '), **kw)
        w = probe.get_window_extent(r).width
        probe.remove()
        return w

    words = text.split(' ')
    best = None
    for n in range(1, len(words) + 1):
        for cuts in combinations(range(1, len(words)), n - 1):
            idx = (0, *cuts, len(words))
            lines = [' '.join(words[a:b]) for a, b in zip(idx[:-1], idx[1:])]
            ws = [width(l) for l in lines]
            if max(ws) <= width_px and (best is None or max(ws) - min(ws) < best[0]):
                best = (max(ws) - min(ws), lines)
        if best:
            return [l.replace('\u00a0', ' ') for l in best[1]]
    return [text.replace('\u00a0', ' ')]


def fig1_pipeline() -> None:
    cards = [('a', 'City daily records', ['12\u00a0pollutant channels and\u00a0AQI', 'Common target-date partitions',
                                          'Scaling fitted on training data']),
             ('b', 'Historical decomposition', ['Last 180\u00a0to\u00a0365 available days', '30-step autoregressive extension',
                                                'IMF1 to IMF4 and one slow channel']),
             ('c', 'Forecast input', ['7 consecutive calendar days', '12\u00a0pollutants and 5\u00a0components',
                                      'Target is next-day\u00a0AQI']),
             ('d', 'Shared iTransformer', ['One token per channel', 'Attention across channels',
                                          'Scalar city bias']),
             ('e', 'Channel-level KernelSHAP', ['Whole channel histories replaced', '50\u00a0background windows',
                                               '100\u00a0explained test windows'])]
    W, margin, gap, pad = TEXTWIDTH, 0.03, 0.26, 0.085
    cw = (W - 2 * margin - (len(cards) - 1) * gap) / len(cards)
    fs_t, fs_b, fs_l = 7.5, 7, 9
    lh_t, lh_b, item_gap, bullet_in = fs_t * 1.22 / 72, fs_b * 1.25 / 72, 0.045, 0.085

    fig = plt.figure(figsize=(W, 2))  # height set below, once the wrapped text is known
    r = fig.canvas.get_renderer()
    probe = fig.text(0, 0, 'e', fontsize=fs_l, fontweight='bold')
    letter_w = probe.get_window_extent(r).width / fig.dpi + 0.06
    probe.remove()
    layout = []
    for lab, title, items in cards:
        t_lines = _wrap(fig, title, (cw - 2 * pad - letter_w) * fig.dpi, fontsize=fs_t, fontweight='bold')
        b_items = [_wrap(fig, it, (cw - 2 * pad - bullet_in) * fig.dpi, fontsize=fs_b) for it in items]
        layout.append((lab, t_lines, b_items))
    n_title = max(len(t) for _, t, _ in layout)
    head_h = pad + n_title * lh_t + 0.06
    body_h = max(sum(len(b) for b in bi) * lh_b + (len(bi) - 1) * item_gap for _, _, bi in layout)
    ch = head_h + 0.07 + body_h + pad
    H = ch + 2 * margin
    fig.set_size_inches(W, H)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W), ax.set_ylim(0, H), ax.axis('off')

    boxes = []
    for k, (lab, t_lines, b_items) in enumerate(layout):
        x, y = margin + k * (cw + gap), margin
        box = FancyBboxPatch((x, y), cw, ch, boxstyle='round,pad=0,rounding_size=0.045', fc=C['box_fc'],
                             ec=C['box_ec'], lw=0.7)
        ax.add_patch(box)
        members = [ax.text(x + pad, y + ch - pad, lab, fontsize=fs_l, fontweight='bold', va='top',
                           color=C['box_ec'])]
        for j, line in enumerate(t_lines):
            members.append(ax.text(x + pad + letter_w, y + ch - pad - j * lh_t + 0.004, line, fontsize=fs_t,
                                   fontweight='bold', va='top'))
        rule_y = y + ch - head_h
        ax.plot([x + pad, x + cw - pad], [rule_y, rule_y], color=C['box_ec'], lw=0.45, alpha=0.6)
        yy = rule_y - 0.07
        for lines in b_items:
            ax.plot(x + pad + 0.02, yy - 0.5 * lh_b + 0.005, 's', ms=1.8, color=C['box_ec'], mec='none')
            for line in lines:
                members.append(ax.text(x + pad + bullet_in, yy, line, fontsize=fs_b, va='top'))
                yy -= lh_b
            yy -= item_gap
        boxes.append((box, members))
        if k < len(cards) - 1:
            ax.add_patch(FancyArrowPatch((x + cw + 0.035, y + ch / 2), (x + cw + gap - 0.035, y + ch / 2),
                                         arrowstyle='-|>', mutation_scale=7, lw=0.8, color=C['box_ec']))
    save(fig, 'Figure1', boxes)


# ---------------------------------------------------------------------------------------------------- Figure 2
def g1_shares() -> tuple[pd.DataFrame, pd.DataFrame]:
    m = pd.read_csv(SRC['g1_matrix'], index_col=0)
    s = pd.read_csv(SRC['g1_summary']).set_index('city')
    return m.apply(shares, axis=1), s


def fig2_attribution() -> None:
    sh, s = g1_shares()
    cities = s.index[s.passes_completeness.astype(bool)]
    d = sh.loc[cities]
    g = pd.DataFrame({'PM$_{2.5}$': d['PM2.5'], 'PM$_{10}$': d['PM10'],
                      'Other pollutants': d[[p for p in POLLUTANTS if p not in ('PM2.5', 'PM10')]].sum(axis=1),
                      'Slow channel': d[SLOW], 'IMF1 to IMF4': d[OSC].sum(axis=1)})
    g = g.sort_values('PM$_{2.5}$')
    fig = plt.figure(figsize=(0.9 * TEXTWIDTH, 3.25))
    ax = fig.add_axes([0.215, 0.20, 0.70, 0.74])
    left = np.zeros(len(g))
    for col, colour in zip(g.columns, [C['pm25'], C['pm10'], C['other'], C['slow'], C['osc']]):
        ax.barh(g.index, g[col], left=left, color=colour, label=col, height=0.68, edgecolor='white', lw=0.5)
        left += g[col].to_numpy()
    tr = blended_transform_factory(ax.transAxes, ax.transData)
    for i, c in enumerate(g.index):
        ax.text(1.025, i, f'{s.at[c, "test_r2"]:.2f}', transform=tr, va='center', ha='left', fontsize=7,
                color=C['grey'])
    ax.text(1.025, len(g) - 0.45, 'Test $R^2$', transform=tr, fontsize=7, color=C['grey'], ha='left',
            va='bottom')
    ax.set_xlim(0, 100), ax.set_ylim(-0.6, len(g) - 0.45)
    ax.set_xticks(range(0, 101, 20))
    ax.set_xlabel('Share of total mean absolute channel attribution (%)')
    ax.tick_params(axis='y', length=0, pad=4)
    ax.spines['left'].set_visible(False)
    ax.legend(ncol=5, loc='upper center', bbox_to_anchor=(0.43, -0.135), handlelength=1.1, handleheight=0.9,
              columnspacing=1.1)
    save(fig, 'Figure2')


# ---------------------------------------------------------------------------------------------------- Figure 3
def fig3_dependence() -> None:
    sh, _ = g1_shares()
    aqi_dec = sh.loc[FOCUS, OSC + [SLOW]].sum(axis=1)
    ab = pd.read_csv(SRC['ablation'])
    ab = ab[(ab.period == 'all') & (ab.lookback == 7)].set_index('city')
    raw_cols = POLLUTANTS + ['AQI_lag']
    raw = (100 * ab['AQI_lag'] / ab[raw_cols].sum(axis=1)).loc[FOCUS]
    pm = pd.read_csv(SRC['pm25'], index_col=0)
    pm_dec = (100 * pm[OSC + [SLOW]].sum(axis=1) / pm.sum(axis=1)).loc[FOCUS]
    g2 = pd.read_csv(SRC['g2_shap'])
    g2 = g2[g2.period == 'all']

    fig, axes = plt.subplots(1, 2, figsize=(TEXTWIDTH, 2.75), gridspec_kw={'width_ratios': [1, 1.75]})
    fig.subplots_adjust(left=0.085, right=0.995, top=0.92, bottom=0.265, wspace=0.27)
    ax = axes[0]
    x = np.arange(len(FOCUS))
    for k, (vals, lab, col, mk) in enumerate([
            (aqi_dec, 'AQI target, decomposed AQI history', C['slow'], 'o'),
            (raw, 'AQI target, one raw AQI channel', C['grey'], 's'),
            (pm_dec, 'PM$_{2.5}$ target, decomposed PM$_{2.5}$ history', C['pm25'], 'D')]):
        ax.scatter(x + (k - 1) * 0.2, vals, color=col, marker=mk, s=22, label=lab, zorder=3, lw=0)
    ax.set_xticks(x, FOCUS), ax.set_xlim(-0.55, len(FOCUS) - 0.45)
    ax.set_ylim(0, 100), ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel('Target-history share\nof attribution (%)')
    ax.tick_params(axis='x', length=0, pad=4)
    ax.legend(loc='upper left', bbox_to_anchor=(-0.22, -0.115), handlelength=1.0, borderaxespad=0)

    ax = axes[1]
    bases = [123, 42, 2024, 7]
    for ci, city in enumerate(FOCUS):
        if ci:
            ax.axvline(ci * 5 - 1, color=C['light'], lw=0.6, zorder=0)
        for bi, b in enumerate(bases):
            v = g2[(g2.city == city) & (g2.decomposition_seed_base == b)].decomposition_share_pct.to_numpy()
            xs = ci * 5 + bi + np.linspace(-0.2, 0.2, len(v))
            ax.scatter(xs, v, s=11, color=C['h1'], zorder=3, lw=0, alpha=0.9)
            ax.hlines(v.mean(), ci * 5 + bi - 0.34, ci * 5 + bi + 0.34, color='#1A1A1A', lw=1.1, zorder=4)
        ax.text(ci * 5 + 1.5, 39.5, city, ha='center', va='top', fontsize=7.5)
    ax.set_xticks([ci * 5 + bi for ci in range(3) for bi in range(4)], [str(b) for _ in FOCUS for b in bases])
    ax.set_xlim(-0.7, 13.7)
    ax.tick_params(axis='x', length=0, pad=4)
    ax.set_xlabel('Decomposition realisation (seed base), five model seeds each')
    ax.set_ylabel('Decomposition share\nof attribution (%)'), ax.set_ylim(0, 40)
    panel_letters(fig, axes, 'ab')
    save(fig, 'Figure3')


# ---------------------------------------------------------------------------------------------------- Figure 4
def fig4_leakage_skill() -> None:
    e1 = pd.read_csv(SRC['e1_shares'])
    e1 = e1[e1.arm.isin(['CAUSAL', 'LEAKY']) & e1.city.isin(FOCUS)].copy()
    e1['osc_share'] = pd.to_numeric(e1.osc_share)
    e7 = pd.read_csv(SRC['e7_pooled'])
    e7 = e7[e7['hist'] == 'long']

    fig, axes = plt.subplots(1, 3, figsize=(TEXTWIDTH, 2.6), gridspec_kw={'width_ratios': [1.1, 1.2, 1.2]})
    fig.subplots_adjust(left=0.075, right=0.995, top=0.91, bottom=0.24, wspace=0.42)
    ax = axes[0]
    for ci, city in enumerate(FOCUS):
        for k, (arm, col, lab) in enumerate([('CAUSAL', C['causal'], 'Past data only'),
                                             ('LEAKY', C['leaky'], 'Whole record')]):
            v = e1[(e1.city == city) & (e1.arm == arm)].osc_share.to_numpy()
            ax.scatter(np.full(len(v), ci + (k - 0.5) * 0.32), v, color=col, s=16, zorder=3, lw=0.4,
                       edgecolor='white', label=lab if ci == 0 else None)
    ax.set_xticks(range(3), FOCUS), ax.set_xlim(-0.6, 2.6)
    ax.tick_params(axis='x', length=0, pad=4)
    ax.set_ylabel('IMF1 to IMF4 share\nof attribution (%)')
    ax.set_ylim(0, 40)
    ax.legend(loc='upper right', title='Decomposition of', title_fontsize=7, handlelength=0.8,
              bbox_to_anchor=(1.02, 1.02))

    years = sorted(e7.year.unique())
    for panel, ax in enumerate(axes[1:]):
        for h, col, mk in [(1, C['h1'], 'o'), (7, C['h7'], 's')]:
            d = e7[e7.h == h]
            base = d[d.arm == 'RAW+MAL'].set_index(['year', 'seed']).mae
            osc = d[d.arm == 'RAW+MAL+OSC'].set_index(['year', 'seed'])
            off = -0.16 if h == 1 else 0.16
            lab = f'{h} day{"s" if h > 1 else ""} ahead'
            if panel == 0:
                gain = 100 * (base - osc.mae) / base
                ax.scatter(gain.index.get_level_values(0) + off, gain, color=col, marker=mk, s=11, zorder=3,
                           lw=0, label=lab)
            else:
                v = 100 * osc.osc_share if osc.osc_share.max() <= 1 else osc.osc_share
                ax.scatter(v.index.get_level_values(0) + off, v, color=col, marker=mk, s=11, zorder=3, lw=0,
                           label=lab)
        ax.set_xticks(years, [str(y) for y in years], rotation=45, ha='right', rotation_mode='anchor')
        ax.set_xlim(years[0] - 0.6, years[-1] + 0.6)
        ax.set_xlabel('Evaluation year')
    axes[1].axhline(0, color=C['grey'], lw=0.6, zorder=1)
    axes[1].set_ylim(-4.8, 4.8), axes[1].set_yticks(range(-4, 5, 2))
    axes[1].set_ylabel('MAE reduction when IMF1\nto IMF4 are added (%)')
    axes[1].legend(loc='upper right', handlelength=0.8, bbox_to_anchor=(1.02, 1.02))
    axes[2].set_ylabel('IMF1 to IMF4 share\nof attribution (%)'), axes[2].set_ylim(0, 30)
    panel_letters(fig, axes, 'abc')
    save(fig, 'Figure4')


# ---------------------------------------------------------------------------------------------------- Figure S1
def figS1_heatmap() -> None:
    sh, s = g1_shares()
    cols = POLLUTANTS + OSC + [SLOW]
    d = sh[cols]
    order = leaves_list(linkage(d.to_numpy(), method='average', metric='euclidean'))
    d = d.iloc[order]
    labels = [c + ('' if s.at[c, 'passes_completeness'] else ' (limited data)') for c in d.index]
    fig = plt.figure(figsize=(TEXTWIDTH, 4.5))
    ax = fig.add_axes([0.235, 0.135, 0.665, 0.80])
    cax = fig.add_axes([0.915, 0.135, 0.016, 0.80])
    im = ax.imshow(d.to_numpy(), cmap='cividis', aspect='auto', vmin=0)
    ax.set_xticks(range(len(cols)), [TEX.get(c, c) for c in cols], rotation=45, ha='right',
                  rotation_mode='anchor')
    ax.set_yticks(range(len(d)), labels)
    ax.tick_params(length=0, pad=3)
    for sp in ax.spines.values():
        sp.set_visible(False)
    split = len(POLLUTANTS) - 0.5
    ax.axvline(split, color='white', lw=2.2)
    tr = blended_transform_factory(ax.transData, ax.transAxes)
    for x0, x1, lab in [(-0.4, split - 0.15, 'Pollutant channels'),
                        (split + 0.15, len(cols) - 0.6, 'AQI decomposition channels')]:
        ax.plot([x0, x1], [1.012, 1.012], transform=tr, color=C['grey'], lw=0.6, clip_on=False)
        ax.text((x0 + x1) / 2, 1.022, lab, transform=tr, ha='center', va='bottom', fontsize=7, color=C['grey'])
    cb = fig.colorbar(im, cax=cax)
    cb.outline.set_linewidth(0.5)
    cb.ax.tick_params(width=0.5, length=2)
    cb.set_label('Share of attribution (%)')
    save(fig, 'FigureS1')


if __name__ == '__main__':
    FIG.mkdir(exist_ok=True, parents=True)
    for p in SRC.values():
        assert p.exists(), p
    fig1_pipeline()
    fig2_attribution()
    fig3_dependence()
    fig4_leakage_skill()
    figS1_heatmap()
