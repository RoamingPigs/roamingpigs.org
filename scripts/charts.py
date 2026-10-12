"""Inline SVG charts for roamingpigs.org, drawn from data/canon.json at build time.

No JavaScript, no external library. Every chart has a <title> and <desc> so the
numbers are readable without the picture.
"""
from __future__ import annotations

from html import escape as e

LABELS_SNR = {
    "clean": "No added noise",
    "snr_20": "20 dB signal-to-noise",
    "snr_10": "10 dB",
    "snr_0": "0 dB",
    "snr_-6": "\u22126 dB",
}
LABELS_COND = {
    "digital_silence": "Digital silence",
    "ambient_silence": "Quiet room",
    "squelch_burst": "Radio squelch burst",
    "noise_white": "White noise",
    "noise_pink": "Pink noise",
    "noise_brown": "Brown noise",
    "noise_engine": "Engine noise",
    "noise_babble": "Crowd babble",
}


def _svg(w: int, h: int, uid: str, title: str, desc: str, body: str) -> str:
    return (
        f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-labelledby="{uid}-t {uid}-d">'
        f'<title id="{uid}-t">{e(title)}</title><desc id="{uid}-d">{e(desc)}</desc>{body}</svg>'
    )


def wer_by_snr(e2: dict) -> str:
    """Mean word error rate by noise level. 100% line marked."""
    rows = [(LABELS_SNR[k], e2["mean_wer_by_snr"][k]) for k in LABELS_SNR]
    x0, x1, vmax = 150, 610, 1.75
    sc = (x1 - x0) / vmax
    row_h, top = 40, 34
    h = top + row_h * len(rows) + 30
    out = []
    for g in (0, 0.5, 1.0, 1.5):
        x = x0 + g * sc
        out.append(f'<line class="grid" x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{h - 28}"/>')
        out.append(f'<text class="mut" x="{x:.1f}" y="{h - 10}" text-anchor="middle">{int(g * 100)}%</text>')
    for i, (label, v) in enumerate(rows):
        y = top + i * row_h
        w = v * sc
        cls = "bar-over" if v > 1 else "bar-m"
        out.append(f'<text class="lbl" x="{x0 - 12}" y="{y + 17}" text-anchor="end">{e(label)}</text>')
        out.append(f'<rect class="{cls}" x="{x0}" y="{y + 4}" width="{w:.1f}" height="22" rx="2"/>')
        out.append(f'<text class="val" x="{x0 + w + 8:.1f}" y="{y + 20}">{v * 100:.0f}%</text>')
    xr = x0 + 1.0 * sc
    out.append(f'<line class="ref" x1="{xr:.1f}" y1="{top - 14}" x2="{xr:.1f}" y2="{h - 28}"/>')
    out.append(f'<text class="lbl" x="{xr - 8:.1f}" y="{top - 18}" text-anchor="end">100% = as many wrong words as words spoken</text>')
    desc = "; ".join(f"{l}: {v * 100:.1f}%" for l, v in rows)
    return _svg(660, h, "c-wer", "Mean word error rate by noise level", "Mean word error rate across six models and six audio paths. " + desc, "".join(out))


def hallucination_by_condition(e1: dict) -> str:
    """Hallucinated clips with and without the energy gate, per non-speech condition."""
    conds = list(LABELS_COND)
    x0, x1 = 160, 560
    row_h, top = 44, 40
    h = top + row_h * len(conds) + 12
    out = []
    lx = x0
    out.append(f'<rect class="bar-gray" x="{lx}" y="8" width="12" height="12" rx="2"/><text x="{lx + 18}" y="19">No gate</text>')
    out.append(f'<rect class="bar-ink" x="{lx + 96}" y="8" width="12" height="12" rx="2"/><text x="{lx + 114}" y="19">With energy gate</text>')
    desc_parts = []
    for i, c in enumerate(conds):
        row = e1["by_condition"][c]
        y = top + i * row_h
        n = row["clips"]
        sc = (x1 - x0) / n
        out.append(f'<text class="lbl" x="{x0 - 12}" y="{y + 20}" text-anchor="end">{e(LABELS_COND[c])}</text>')
        out.append(f'<rect class="bar-bg" x="{x0}" y="{y + 3}" width="{n * sc:.1f}" height="13" rx="2"/>')
        out.append(f'<rect class="bar-gray" x="{x0}" y="{y + 3}" width="{row["ungated"] * sc:.1f}" height="13" rx="2"/>')
        out.append(f'<text class="val" x="{x1 + 10}" y="{y + 14}">{row["ungated"]}/{n}</text>')
        out.append(f'<rect class="bar-bg" x="{x0}" y="{y + 20}" width="{n * sc:.1f}" height="13" rx="2"/>')
        if row["gated"]:
            out.append(f'<rect class="bar-ink" x="{x0}" y="{y + 20}" width="{row["gated"] * sc:.1f}" height="13" rx="2"/>')
        out.append(f'<text class="val" x="{x1 + 10}" y="{y + 31}">{row["gated"]}/{n}</text>')
        desc_parts.append(f"{LABELS_COND[c]}: {row['ungated']} of {n} without the gate, {row['gated']} of {n} with it")
    return _svg(
        640,
        h,
        "c-hal",
        "Clips where a model wrote words that were not spoken",
        "Per condition, across six models and three seeds each. " + "; ".join(desc_parts),
        "".join(out),
    )


def joules_per_token(apu: dict) -> str:
    runs = [r for r in apu["reported_runs"] if r["within_bandwidth_assumption"]]
    names = [
        f'{r["params_b"]:g}B dense' if r["kind"].startswith("Dense") else f'{r["params_b"]:g}B mixture, {r["active_b"]:g}B active'
        for r in runs
    ]
    x0, x1, vmax = 190, 560, 5.0
    sc = (x1 - x0) / vmax
    row_h, top = 54, 22
    h = top + row_h * len(runs) + 34
    out = []
    for g in (0, 1, 2, 3, 4, 5):
        x = x0 + g * sc
        out.append(f'<line class="grid" x1="{x:.1f}" y1="{top - 10}" x2="{x:.1f}" y2="{h - 30}"/>')
        out.append(f'<text class="mut" x="{x:.1f}" y="{h - 12}" text-anchor="middle">{g}</text>')
    out.append(f'<text class="mut" x="{x1 + 8}" y="{h - 12}">joules per token</text>')
    cal = apu["calculated_9b"]["j_per_token"]
    for i, (r, nm) in enumerate(zip(runs, names)):
        y = top + i * row_h
        v = r["power_rate_estimate_j_per_token"]
        out.append(f'<text class="lbl" x="{x0 - 12}" y="{y + 18}" text-anchor="end">{e(nm)}</text>')
        out.append(f'<text class="mut" x="{x0 - 12}" y="{y + 34}" text-anchor="end">{r["tokens_per_sec"]:g} tok/s, {r["wall_w_mean"]:.0f} W</text>')
        out.append(f'<rect class="bar-m" x="{x0}" y="{y + 4}" width="{v * sc:.1f}" height="24" rx="2"/>')
        out.append(f'<text class="val" x="{x0 + v * sc + 8:.1f}" y="{y + 21}">{v:.2f}</text>')
        if i == 0:
            cx = x0 + cal * sc
            out.append(f'<circle class="dot-mod" cx="{cx:.1f}" cy="{y + 16}" r="6"/>')
            out.append(f'<text class="mut" x="{cx:.1f}" y="{y + 46}" text-anchor="middle">calculated scenario {cal:.2f}</text>')
    desc = "; ".join(f"{n}: {r['power_rate_estimate_j_per_token']:.2f} J per token at {r['wall_w_mean']:.0f} W and {r['tokens_per_sec']:g} tokens per second" for n, r in zip(names, runs))
    return _svg(660, h, "c-j", "Derived mean-power/decode-speed estimates", f"{len(runs)} historical summaries on one machine. " + desc + f". Separate calculated scenario: {cal:.2f}; raw energy traces are absent.", "".join(out))


def unit_chart(rows: list[tuple[str, int]], total: int, uid: str, title: str) -> str:
    """Rows of `total` squares, `n` filled."""
    sq, gap, x0, row_h, top = 15, 4, 190, 34, 6
    h = top + row_h * len(rows) + 6
    out = []
    for i, (label, n) in enumerate(rows):
        y = top + i * row_h
        out.append(f'<text class="lbl" x="{x0 - 14}" y="{y + 15}" text-anchor="end">{e(label)}</text>')
        for k in range(total):
            cls = "bar-ink" if k < n else "bar-bg"
            out.append(f'<rect class="{cls}" x="{x0 + k * (sq + gap)}" y="{y + 2}" width="{sq}" height="{sq + 2}" rx="2"/>')
        out.append(f'<text class="val" x="{x0 + total * (sq + gap) + 6}" y="{y + 16}">{n} of {total}</text>')
    desc = "; ".join(f"{l}: {n} of {total}" for l, n in rows)
    return _svg(x0 + total * (sq + gap) + 70, h, uid, title, desc, "".join(out))


# ---------------------------------------------------------------------------
# Full-grid charts (intervals shown)
# ---------------------------------------------------------------------------
NOISE_V2 = [("clean", "No added noise"), ("20 dB", "20 dB signal-to-noise"), ("10 dB", "10 dB"), ("0 dB", "0 dB")]


def _whisker(x_lo: float, x_hi: float, y: float, h: float = 8) -> str:
    return (
        f'<line class="whisk" x1="{x_lo:.1f}" y1="{y:.1f}" x2="{x_hi:.1f}" y2="{y:.1f}"/>'
        f'<line class="whisk" x1="{x_lo:.1f}" y1="{y - h / 2:.1f}" x2="{x_lo:.1f}" y2="{y + h / 2:.1f}"/>'
        f'<line class="whisk" x1="{x_hi:.1f}" y1="{y - h / 2:.1f}" x2="{x_hi:.1f}" y2="{y + h / 2:.1f}"/>'
    )


def _fmt_pct(v: float) -> str:
    return f"{v * 100:.0f}%"


def wer_ci_bars(items: list[tuple[str, dict]], uid: str, title: str, vmax: float, ref100: bool = True, label_w: int = 190) -> str:
    """Horizontal bars with 95% interval whiskers. items: (label, {point, lo, hi}) as fractions."""
    x0, x1 = label_w, 600
    sc = (x1 - x0) / vmax
    row_h, top = 42, 36
    h = top + row_h * len(items) + 34
    out = []
    step = 0.25 if vmax <= 1.6 else 0.5
    g = 0.0
    while g <= vmax + 1e-9:
        x = x0 + g * sc
        out.append(f'<line class="grid" x1="{x:.1f}" y1="{top - 10}" x2="{x:.1f}" y2="{h - 30}"/>')
        out.append(f'<text class="mut" x="{x:.1f}" y="{h - 12}" text-anchor="middle">{int(round(g * 100))}%</text>')
        g += step
    for i, (label, v) in enumerate(items):
        y = top + i * row_h
        cls = "bar-over" if v["point"] > 1 else "bar-m"
        out.append(f'<text class="lbl" x="{x0 - 12}" y="{y + 18}" text-anchor="end">{e(label)}</text>')
        out.append(f'<rect class="{cls}" x="{x0}" y="{y + 4}" width="{v["point"] * sc:.1f}" height="22" rx="2"/>')
        out.append(_whisker(x0 + v["lo"] * sc, x0 + v["hi"] * sc, y + 15))
        out.append(f'<text class="val" x="{x0 + v["hi"] * sc + 10:.1f}" y="{y + 19}">{_fmt_pct(v["point"])}</text>')
    if ref100 and vmax >= 1.0:
        xr = x0 + 1.0 * sc
        out.append(f'<line class="ref" x1="{xr:.1f}" y1="{top - 16}" x2="{xr:.1f}" y2="{h - 30}"/>')
        out.append(f'<text class="lbl" x="{xr - 8:.1f}" y="{top - 20}" text-anchor="end">100% = as many wrong words as words spoken</text>')
    desc = "; ".join(f"{l}: {v['point'] * 100:.1f}% (95% interval {v['lo'] * 100:.1f} to {v['hi'] * 100:.1f})" for l, v in items)
    return _svg(660, h, uid, title, desc, "".join(out))


def hallucination_arms(e1: dict) -> str:
    """Pooled hallucination rate by condition for the three arms."""
    conds = [c for c in LABELS_COND if f"none|{c}" in e1["E1_2_rate_by_arm_and_condition"]]
    arms = [("none", "No gate", "bar-gray"), ("energy", "Energy gate", "bar-ink"), ("neural", "Neural VAD gate", "bar-m")]
    x0, x1 = 160, 540
    row_h, top = 58, 40
    h = top + row_h * len(conds) + 8
    out = []
    lx = x0
    for k, (_, name, cls) in enumerate(arms):
        out.append(f'<rect class="{cls}" x="{lx}" y="8" width="12" height="12" rx="2"/><text x="{lx + 18}" y="19">{name}</text>')
        lx += 130
    desc = []
    for i, c in enumerate(conds):
        y = top + i * row_h
        out.append(f'<text class="lbl" x="{x0 - 12}" y="{y + 28}" text-anchor="end">{e(LABELS_COND[c])}</text>')
        for k, (arm, name, cls) in enumerate(arms):
            v = e1["E1_2_rate_by_arm_and_condition"][f"{arm}|{c}"]
            yy = y + k * 17
            out.append(f'<rect class="bar-bg" x="{x0}" y="{yy + 2}" width="{x1 - x0}" height="12" rx="2"/>')
            if v["rate"] > 0:
                out.append(f'<rect class="{cls}" x="{x0}" y="{yy + 2}" width="{v["rate"] * (x1 - x0):.1f}" height="12" rx="2"/>')
            out.append(f'<text class="val" x="{x1 + 10}" y="{yy + 13}">{v["rate"] * 100:.0f}%</text>')
            desc.append(f"{LABELS_COND[c]}, {name}: {v['rate'] * 100:.0f}%")
    return _svg(640, h, "c-hal2", "Share of non-speech clips where a model wrote words, by condition and gate", "Pooled over six models. " + "; ".join(desc), "".join(out))
