#!/usr/bin/env python3
"""Build roamingpigs.org from data/canon.json and src/templates.

    python3 scripts/build.py            # render site/
    python3 scripts/build.py --check    # exit 1 if canon or rendered output is stale

Every measured number on a page is read from data/canon.json, which
siteops/scripts/rp-canon.py derives from the research ledgers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path.home() / "projects/siteops/scripts"))
sys.path.insert(0, str(ROOT / "scripts"))

import charts  # noqa: E402
import rpsite_lib as lib  # noqa: E402
from jinja2 import Environment, FileSystemLoader, StrictUndefined  # noqa: E402

SITE = ROOT / "site"
BASE = "https://roamingpigs.org/"
MODIFIED = "2026-10-11"
MODIFIED_HUMAN = "11 October 2026"
FIRST_PUB = "11 October 2026"

NAV = [
    {"path": "/", "label": "Records"},
    {"path": "/results/", "label": "Results"},
    {"path": "/datasets/trcs/", "label": "TRCS audio"},
    {"path": "/studies/strix-halo-energy/", "label": "Energy study"},
    {"path": "/method/", "label": "Method"},
    {"path": "/reproduce/", "label": "Reproduce"},
    {"path": "/about/", "label": "About"},
]

PAGES = [
    {
        "path": "/",
        "template": "home.html",
        "title": "RoamingPigs Research Notes: Independent AI Systems Research",
        "description": "Small, self-run experiments on speech models, verifier ensembles and local inference hardware. Every figure shows its date, sample and limits.",
    },
    {
        "path": "/datasets/trcs/",
        "template": "dataset.html",
        "title": "TRCS Dataset Card: Synthetic Radio-Channel Speech Benchmark",
        "description": "1,050 synthetic audio files with a SHA-256 for each, built to test speech models on silence, noise and telephone codecs. Contents, checks and known limits.",
        "breadcrumb": [("Research Notes", "/"), ("TRCS dataset", "/datasets/trcs/")],
        "dataset": True,
    },
    {
        "path": "/studies/strix-halo-energy/",
        "template": "study.html",
        "title": "Energy and Speed per Token on One Mini PC: Vulkan Against ROCm",
        "description": "Four local models, four context lengths, three repeats on each of two software backends, measured at the wall plug and at the chip, with the plan and the expectations written first.",
        "breadcrumb": [("Research Notes", "/"), ("Energy study", "/studies/strix-halo-energy/")],
    },
    {
        "path": "/results/",
        "template": "results.html",
        "title": "Results Files: The Raw Numbers Behind Every Record",
        "description": "The five JSON results files behind the RoamingPigs records, with SHA-256 digests, a licence and a short script to reproduce a headline figure.",
        "breadcrumb": [("Research Notes", "/"), ("Results files", "/results/")],
        "og_image": "og/results.png",
        "results": True,
    },
    {
        "path": "/method/",
        "template": "method.html",
        "title": "Method: How a Number Gets onto RoamingPigs Notes",
        "description": "The four evidence classes (measured, modelled, simulated, proposed), what every record must show, and why nothing here is called verified.",
        "breadcrumb": [("Research Notes", "/"), ("Method", "/method/")],
    },
    {
        "path": "/reproduce/",
        "template": "reproduce.html",
        "title": "Reproduce a Result: Code, Pinned Data and Tolerances",
        "description": "Run the TRCS evaluation yourself on pinned data and models, check it against the published results, and report what you got. Failed reports are published too.",
        "breadcrumb": [("Research Notes", "/"), ("Reproduce", "/reproduce/")],
    },
    {
        "path": "/corrections/",
        "template": "corrections.html",
        "title": "Corrections Log: What Was Wrong and What Replaced It",
        "description": "A dated public log of figures, identifiers and labels removed or fixed on RoamingPigs Research Notes, and how corrections are handled.",
        "breadcrumb": [("Research Notes", "/"), ("Corrections", "/corrections/")],
    },
    {
        "path": "/cite/",
        "template": "cite.html",
        "title": "How to Cite RoamingPigs Research Notes and the TRCS Dataset",
        "description": "BibTeX for the TRCS dataset and these notes, and how to cite a single figure with its run date and evidence class. No DOI exists yet.",
        "breadcrumb": [("Research Notes", "/"), ("Cite", "/cite/")],
    },
    {
        "path": "/about/",
        "template": "about.html",
        "title": "About RoamingPigs Research Notes and Cisco Caceres",
        "description": "One person's small experiments, published with their limits. Who writes this, what I disclose, and how the RoamingPigs sites divide the work.",
        "breadcrumb": [("Research Notes", "/"), ("About", "/about/")],
        "ld_type": "AboutPage",
    },
]


def utc_label(s: str) -> str:
    m = re.match(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})", s)
    if not m and re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return f"{s} UTC date (time not recorded)"
    assert m, s
    return f"{m.group(1)} {m.group(2)} UTC"


LABELS_COND = {
    "digital_silence": "digital silence", "ambient_silence": "a quiet room", "squelch_burst": "radio squelch bursts",
    "noise_white": "white noise", "noise_pink": "pink noise", "noise_brown": "brown noise", "noise_engine": "engine noise", "noise_babble": "crowd babble",
}


def _join(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def pct(x: float, d: int = 0) -> str:
    return f"{x * 100:.{d}f}"


def span(r: tuple[float, float]) -> str:
    lo, hi = pct(r[0]), pct(r[1])
    return lo if lo == hi else f"{lo} to {hi}"


def v2_values(c: dict) -> dict:
    """Numbers and sentences for the full-grid run. Each claim is asserted so the copy cannot outrun the data."""
    v2 = c["trcs_v2"]
    A = v2["analysis"]
    n = A["e2"]["n_utterances"]
    norm = A["e2"]["normalised"]
    a1 = norm["A1_by_noise"]
    a3 = norm["A3_codec_minus_uncompressed_clean"]
    a4 = norm["A4_noise_effect"]
    for k, x in a4.items():
        assert x["lo"] > 0, f"noise effect {k} is not established (interval includes zero); rewrite the copy"
    worse = [k for k, x in a3.items() if x["lo"] > 0]
    better = [k for k, x in a3.items() if x["hi"] < 0]
    assert not better, "a narrowband path is better than uncompressed; rewrite the copy"
    inv = v2["batch_invariance"]
    inv_total = sum(x["checked"] for x in inv.values())
    inv_same = sum(x["identical"] for x in inv.values())
    e1 = A["e1"]
    arms = {"none": "No gate", "energy": "Energy gate", "neural": "Neural VAD gate"}
    per_model = e1["E1_1_rate_by_arm_and_model"]
    rng = {a: (min(x["rate"] for k, x in per_model.items() if k.startswith(a + "|")), max(x["rate"] for k, x in per_model.items() if k.startswith(a + "|"))) for a in arms}
    nd = next(x["n_distinct_clips"] for k, x in per_model.items() if k.startswith("none|"))
    # Strict variant of the plan's measure: an output counts only if it holds a letter or digit.
    # The plan's normaliser reduces an ellipsis to one full stop, so an ellipsis-only output counts under the plan.
    _clips = [json.loads(x) for x in (SITE / "results/trcs-full-grid-e1-per-clip.jsonl").read_text(encoding="utf-8").splitlines() if x]
    _strict: dict[str, dict[str, bool]] = {}
    _punct_only = 0
    for r in _clips:
        if r["is_speech"] or r["arm"] != "none":
            continue
        has = bool(re.search(r"[A-Za-z0-9]", r["hypothesis"]))
        _punct_only += 0 if has else 1
        _strict.setdefault(r["model"], {})[r["sha256"]] = has
    _strict_rates = [sum(v.values()) / len(v) for v in _strict.values()]
    assert len(_strict) == len(per_model) // 3 and all(len(v) == nd for v in _strict.values()), "strict-rate input does not match the plan's counts"
    cond = e1["E1_2_rate_by_arm_and_condition"]
    conds = [k.split("|")[1] for k in cond if k.startswith("none|")]

    def gate_sentence(arm: str, name: str) -> str:
        cleared = [LABELS_COND[x] for x in conds if cond[f"{arm}|{x}"]["rate"] <= 0.10]
        if len(cleared) == len(conds):
            return f"The {name} cleared every condition."
        stuck = [LABELS_COND[x] for x in conds if cond[f"{arm}|{x}"]["rate"] >= 0.90]
        part = [f"{LABELS_COND[x]} ({pct(cond[f'{arm}|{x}']['rate'])}%)" for x in conds if 0.10 < cond[f"{arm}|{x}"]["rate"] < 0.90]
        bits = []
        if cleared:
            bits.append("cleared " + _join(cleared))
        if part:
            bits.append("cut " + _join(part))
        if stuck:
            bits.append("left " + _join(stuck) + " untouched")
        return f"The {name} " + "; ".join(bits) + "."

    assert min(x["rate"] for k, x in per_model.items() if k.startswith("none|")) >= 0.5, "ungated models do not mostly write words on non-speech; rewrite the record title and headline"
    pts = [x["point"] for x in norm["A2_by_model_clean_uncompressed"].values()]
    if all(a > b for a, b in zip(pts, pts[1:])):
        size_sentence = "Error falls steadily as models get larger."
    elif pts[0] == max(pts):
        size_sentence = "The smallest model is worst, but error does not fall steadily with size."
    else:
        size_sentence = "Error does not fall steadily with model size."

    # Guards for the prose in "where my expectations were wrong": each sentence is true only while these hold.
    assert all(cond[f"neural|{x}"]["rate"] == 0 for x in conds), "neural gate no longer clears every non-speech clip; rewrite the expectations paragraph"
    assert cond["energy|squelch_burst"]["rate"] <= 0.10, "energy gate no longer clears squelch; rewrite the expectations paragraph"
    assert all(cond[f"energy|{x}"]["rate"] >= 0.90 for x in conds if x.startswith("noise_")), "energy gate now clears some noise; rewrite"
    sc = A["speech_cost"]
    assert abs(sc["delta_energy_minus_none"]["point"]) < 0.001 and sc["clips_skipped_neural"] == 0 and sc["clips_skipped_energy"] == 0, "speech-cost facts changed; rewrite"
    assert sc["delta_neural_minus_none"]["lo"] > 0, "neural gate cost is no longer established; rewrite"
    ident = c["trcs_v2"]["energy_gate_identical_transcripts"]
    def signed(x: float, d: int) -> str:
        s = f"{x * 100:+.{d}f}"
        return s.replace("-", "\u2212")

    def delta(arm: str) -> str:
        d = sc[f"delta_{arm}_minus_none"]
        tiny = abs(d["point"]) < 0.0005 and abs(d["lo"]) < 0.005 and abs(d["hi"]) < 0.005
        dp = 2 if tiny else 1
        point = "0.0" if tiny else signed(d["point"], 1)
        return f"{point} points (95% interval {signed(d['lo'], dp)} to {signed(d['hi'], dp)})"
    models = list(norm["A2_by_model_clean_uncompressed"])
    return {
        "n_utt": n,
        "n_transcripts": f"{len(models) * 960:,}",
        "w": {k: {"p": pct(x["point"]), "lo": pct(x["lo"]), "hi": pct(x["hi"])} for k, x in a1.items()},
        "codecs_worse": len(worse), "codecs_total": len(a3),
        "worse_list": worse,
        "any_over_100": any(x["point"] > 1 for x in a1.values()),
        "clean_by_model": {m: {"p": pct(x["point"]), "lo": pct(x["lo"]), "hi": pct(x["hi"])} for m, x in norm["A2_by_model_clean_uncompressed"].items()},
        "inv": f"{inv_same} of {inv_total}",
        "inv_ok": inv_same == inv_total,
        "e1_none": span(rng["none"]), "e1_energy": span(rng["energy"]), "e1_neural": span(rng["neural"]),
        "size_sentence": size_sentence,
        "e1_n_distinct": nd,
        "e1_strict_none": span((min(_strict_rates), max(_strict_rates))), "e1_punct_only": _punct_only,
        "gate_energy": gate_sentence("energy", "energy gate"),
        "gate_neural": gate_sentence("neural", "neural gate"),
        "cost_energy": delta("energy"), "cost_neural": delta("neural"),
        "skipped_energy": sc["clips_skipped_energy"], "skipped_neural": sc["clips_skipped_neural"],
        "energy_same": f'{ident["same"]} of {ident["of"]}', "speech_clips": f'{ident["of"]}',
        "cap_hits": f"{A['e2']['secondary']['outputs_hitting_token_cap']['count']:,}",
        "over_100_clips": f"{A['e2']['secondary']['clips_with_more_edits_than_reference_words']['count']:,}",
        "run_start": v2["run"]["started_utc"], "run_end": v2["run"]["finished_utc"],
        "plan": v2["plan"], "versions": v2["versions"],
    }


def derive(c: dict) -> dict:
    e1, e2, apu, vec, echo = c["e1"], c["e2"], c["apu"], c["vec"], c["echo"]
    runs = [r for r in apu["reported_runs"] if r["within_bandwidth_assumption"]]
    excluded = [r for r in apu["reported_runs"] if not r["within_bandwidth_assumption"]]
    assert len(excluded) <= 1 and len(runs) >= 2, "unexpected set of metered runs"
    words = {1: "one", 2: "two", 3: "three"}
    js = [r["power_rate_estimate_j_per_token"] for r in runs]
    assert len({r["generated_tokens"] for r in runs}) == 1, "runs differ in token count"
    assert c["trcs"]["rehash_mismatches"] == 0, "dataset re-hash found mismatches"
    assert echo["portfolio_agrees"], "portfolio headline disagrees with the E3 ledger"
    assert vec["generated_by_seeded_rng"], "VEC-SCR is no longer simulated; the evidence class must be rechecked"
    sizes = [m["params"] for m in e2["models"]]
    return {
        "v2": v2_values(c),
        "wer_clean": round(e2["mean_wer_by_snr"]["clean"] * 100),
        "wer_0": round(e2["mean_wer_by_snr"]["snr_0"] * 100),
        "e2_date": utc_label(e2["date_utc"]),
        "e2_sizes": f'{sizes[0]} to {sizes[-1]}',
        "e1_date": utc_label(e1["date_utc"]),
        "e1_wpm_cell": int(e1["ungated_wpm_cell_max"]),
        "apu_date": utc_label(apu["date_utc"]),
        "apu_mem": apu["unified_memory_gb"],
        "n_runs": words[len(runs)],
        "excl": excluded[0] if excluded else None,
        "peak_gbps": f'{apu["peak_gbps"]:.0f}',
        "j_min": f"{min(js):.2f}",
        "j_max": f"{max(js):.2f}",
        "j_first": f'{js[0]:.2f}',
        "j_peak_first": f'{runs[0]["peak_power_rate_estimate_j_per_token"]:.2f}',
        "j_reported_first": f'{runs[0]["reported_integrated_j_per_token"]:.4f}',
        "run_min": f'{min(r["run_seconds"] for r in runs):.0f}',
        "run_max": f'{max(r["run_seconds"] for r in runs):.0f}',
        "run_tokens": runs[0]["generated_tokens"],
        "vec_date": utc_label(vec["date_utc"]),
        "rho": f'{vec["error_correlation"]:.2f}',
        "cov": f'{vec["error_covariance"]:.3f}',
        "cands": f'{vec["candidates"]:,}',
        "ea": f'{vec["error_rate_a"]:.3f}',
        "eb": f'{vec["error_rate_b"]:.3f}',
        "echo_date": utc_label(echo["date_utc"]),
        "echo_tokens_x": f'{echo["tokens_per_attempt"]["echo"] / echo["tokens_per_attempt"]["single"]:.1f}',
        "snr_pooled": [(lab, f"{c['trcs_v2']['analysis']['e2']['normalised']['A1_by_noise'][k]['point'] * 100:.1f}") for lab, k in (("None", "clean"), ("20.0", "20 dB"), ("10.0", "10 dB"), ("0.0", "0 dB"))],
        "first_pub": FIRST_PUB,
        "verify_date": MODIFIED_HUMAN,
        "verify_bad": c["trcs"]["rehash_mismatches"],
    }


def site_ld() -> list[dict]:
    person = {
        "@type": "Person",
        "@id": BASE + "#author",
        "name": "Cisco Caceres",
        "url": "https://ciscocaceres.com/",
        "sameAs": ["https://orcid.org/0009-0005-7810-5077", "https://github.com/RoamingPigs", "https://huggingface.co/RoamingPigs"],
    }
    org = {
        "@type": "Organization",
        "@id": BASE + "#org",
        "name": "RoamingPigs",
        "url": BASE,
        "logo": BASE + "icon-512.png",
        "description": "An independent project publishing small AI systems experiments with their limits.",
        "founder": {"@id": BASE + "#author"},
        "sameAs": ["https://roamingpigs.ai/", "https://roamingpigs.com/", "https://github.com/RoamingPigs", "https://huggingface.co/RoamingPigs"],
    }
    website = {
        "@type": "WebSite",
        "@id": BASE + "#website",
        "url": BASE,
        "name": "RoamingPigs Research Notes",
        "inLanguage": "en",
        "publisher": {"@id": BASE + "#org"},
        "author": {"@id": BASE + "#author"},
    }
    return [website, org, person]


def dataset_ld(c: dict) -> dict:
    t = c["trcs"]
    return {
        "@type": "Dataset",
        "@id": BASE + "datasets/trcs/#dataset",
        "name": "TRCS: a synthetic radio-channel benchmark for speech recognition",
        "description": (
            f'{t["files"]:,} synthetic 16 kHz audio files in {t["conditions"]} conditions, with a SHA-256 for every file. '
            "Tests speech models on silence, noise and narrowband telephone codecs."
        ),
        "url": BASE + "datasets/trcs/",
        "sameAs": "https://huggingface.co/datasets/RoamingPigs/trcs-tactical-audio",
        "creator": {"@id": BASE + "#author"},
        "dateModified": t["generated_at"][:10],
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "isAccessibleForFree": True,
        "keywords": ["speech recognition", "hallucination", "telephone codecs", "benchmark", "synthetic speech"],
        "measurementTechnique": "Synthetic speech and noise passed through software codecs and mixed at fixed signal-to-noise ratios.",
        "distribution": [
            {
                "@type": "DataDownload",
                "encodingFormat": "audio/wav",
                "contentUrl": "https://huggingface.co/datasets/RoamingPigs/trcs-tactical-audio",
            }
        ],
    }


def results_ld(results: dict) -> dict:
    return {
        "@type": "Dataset",
        "@id": BASE + "results/#dataset",
        "name": "RoamingPigs research results files",
        "description": "Raw JSON results of the experiments reported on RoamingPigs Research Notes: speech-model transcripts, hallucination counts, agent diagnostics, wall-meter energy runs and a verifier simulation.",
        "url": BASE + "results/",
        "creator": {"@id": BASE + "#author"},
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "isAccessibleForFree": True,
        "dateModified": MODIFIED,
        "distribution": [
            {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": BASE + "results/" + f["file"], "sha256": f["sha256"], "contentSize": f"{f['bytes']} B"}
            for f in results["files"]
        ],
    }


STUDY = ROOT / "data/strix-halo-energy"
FIG_MAP = """
/* Maps the study figures' colour variables onto this site's tokens. The rules above come from the study repository. */
.fig-sh { --f-ink: var(--ink); --f-ink2: var(--ink-2); --f-mut: var(--ink-3); --f-rule: var(--rule); --f-rule2: var(--rule-strong);
  --f-bg: var(--surface); --f-a: #1a47c9; --f-b: #c2410c; --f-ok: var(--measured); --f-bad: #a32020; --f-chip: var(--measured-bg); --f-chipb: #f6dede;
  --f-sans: var(--sans); --f-mono: var(--mono); }
.fig-sh svg { display: block; width: 100%; height: auto; overflow: visible; }
"""


def figures_css() -> str:
    return (STUDY / "figures.css").read_text(encoding="utf-8") + FIG_MAP


def load_study() -> dict:
    """The study's exported files, each checked against the SHA-256 in PROVENANCE.json before anything is rendered from it."""
    prov = json.loads((STUDY / "PROVENANCE.json").read_text(encoding="utf-8"))
    for rel, want in prov["files"].items():
        got = hashlib.sha256((STUDY / rel).read_bytes()).hexdigest()
        if got != want:
            raise SystemExit(f"data/strix-halo-energy/{rel} does not match PROVENANCE.json; re-export it from the study repository")
    rd = lambda n: json.loads((STUDY / n).read_text(encoding="utf-8"))
    V, R, EV = rd("summary-vulkan.json"), rd("summary-rocm.json"), rd("evaluation.json")
    figs = {p.stem: p.read_text(encoding="utf-8") for p in sorted((STUDY / "figures").glob("*.svg"))}
    ratios = [R["cells"][k]["tok_per_s"]["mean"] / V["cells"][k]["tok_per_s"]["mean"] for k in V["cells"] if k in R["cells"]]
    jw = [x["wall_net_j_per_tok"]["mean"] for x in V["cells"].values()]
    idle = V["idle"].get("bare_idle_block") or next(iter(V["idle"].values()))
    held = [k for k, v in EV.items() if v["holds"]]
    return {
        "findings": rd("findings.json"), "table_v": rd("table-vulkan.json"), "table_r": rd("table-rocm.json"), "figs": figs, "ev": EV,
        "wrong": [k for k, v in EV.items() if not v["holds"]],
        "stats": {
            "cells": V["n_cells"] + R["n_cells"], "cells_v": V["n_cells"], "idle_w": f"{idle['wall_w_median']:g}", "ratio_lo": f"{min(ratios) * 100:.0f}", "ratio_hi": f"{max(ratios) * 100:.0f}",
            "j_lo": f"{min(jw):.1f}", "j_hi": f"{max(jw):.1f}", "held": len(held), "n_ex": len(EV), "counter_gap": f"{abs(V['crosscheck_total_counter']['diff_pct']):.1f}",
            "parse_errors": EV["P8"]["parse_error_requests"],
        },
        "prov": {"commit": prov["source_commit"][:7], "run": prov["run"], "source": prov["source"]},
    }


def asset(path: str) -> str:
    h = hashlib.sha256((SITE / path.lstrip("/")).read_bytes()).hexdigest()[:8]
    return f"{path}?v={h}"


def render() -> dict[str, str]:
    c = json.loads((ROOT / "data/canon.json").read_text(encoding="utf-8"))
    v = derive(c)
    results = json.loads((SITE / "results/index.json").read_text(encoding="utf-8"))
    for f in results["files"]:
        f["kb"] = f"{f['bytes'] / 1000:,.0f}"
    echo = c["echo"]
    A = c["trcs_v2"]["analysis"]
    norm = A["e2"]["normalised"]
    a1 = norm["A1_by_noise"]
    vmax = max(1.0, max(x["hi"] for x in a1.values()) * 1.12)
    vmax = float(int(vmax * 4 + 0.999)) / 4
    ch = {
        "wer": charts.wer_ci_bars([(lab, a1[k]) for k, lab in charts.NOISE_V2], "c-wer", "Corpus word error rate by noise level, with 95% intervals", vmax),
        "model_clean": charts.wer_ci_bars(list(norm["A2_by_model_clean_uncompressed"].items()), "c-model", "Corpus word error rate on clean uncompressed audio, by model", max(0.5, max(x["hi"] for x in norm["A2_by_model_clean_uncompressed"].values()) * 1.15), ref100=False, label_w=210),
        "hal": charts.hallucination_arms(A["e1"]),
        "joules": charts.joules_per_token(c["apu"]),
        "echo": charts.unit_chart(
            [
                ("Single agent", echo["accepted"]["single"]),
                ("Two-worker messaging", echo["accepted"]["plain"]),
                ("Echo", echo["accepted"]["echo"]),
            ],
            echo["attempts_per_arm"],
            "c-echo",
            "Accepted solutions out of 16 attempts, by arm",
        ),
    }
    env = Environment(loader=FileSystemLoader(ROOT / "src/templates"), undefined=StrictUndefined, autoescape=False, trim_blocks=True, lstrip_blocks=True)
    env.globals["asset"] = asset
    site_meta = {
        "base": BASE,
        "name": "RoamingPigs Research Notes",
        "locale": "en_US",
        "theme_color": "#f6f3ec",
        "color_scheme": "light",
        "author": "Cisco Caceres",
        "og_image": "og/default.png",
        "og_alt": "RoamingPigs Research Notes: research notes with the limits printed next to the numbers",
        "person_id": BASE + "#author",
        "ld": site_ld(),
    }
    st = load_study()
    out: dict[str, str] = {}
    for p in PAGES:
        page = dict(p, modified=MODIFIED)
        if p.get("og_image"):
            page["og_alt"] = p["title"]
        if p["path"] == "/datasets/trcs/":
            page["og_image"] = "og/dataset.png"
            page["og_alt"] = "TRCS dataset card: 1,050 synthetic audio files, each with a SHA-256"
        extra = [dataset_ld(c)] if p.get("dataset") else []
        if p.get("results"):
            extra = [results_ld(results)]
        head = lib.head_meta(site_meta, page, extra)
        ctx = {
            "c": c,
            "v": v,
            "results": results,
            "ch": ch,
            "st": st,
            "head": head,
            "nav": NAV,
            "page": page,
            "site": {"modified": MODIFIED, "modified_human": MODIFIED_HUMAN},
        }
        html = env.get_template(p["template"]).render(**ctx)
        rel = "index.html" if p["path"] == "/" else p["path"].strip("/") + "/index.html"
        out[rel] = html
    nf = dict(path="/404.html", title="Page not found | RoamingPigs Research Notes", description="This page does not exist.", modified=MODIFIED, noindex=True)
    head = lib.head_meta(site_meta, nf)
    out["404.html"] = env.get_template("404.html").render(
        c=c, v=v, results=results, ch=ch, st=st, head=head, nav=NAV, page=nf, site={"modified": MODIFIED, "modified_human": MODIFIED_HUMAN}
    )
    return out


def static_files() -> dict[str, str]:
    base = BASE
    manifest = {
        "name": "RoamingPigs Research Notes",
        "short_name": "RP Notes",
        "start_url": "/",
        "display": "browser",
        "background_color": "#f6f3ec",
        "theme_color": "#f6f3ec",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }
    headers = """/*
  Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; manifest-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; upgrade-insecure-requests
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Cross-Origin-Opener-Policy: same-origin
  Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
  Permissions-Policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), microphone=(), payment=(), usb=()
  Cache-Control: public, max-age=0, must-revalidate, no-transform

/fonts/*
  Cache-Control: public, max-age=31536000, immutable

/css/*
  Cache-Control: public, max-age=31536000, immutable

/js/*
  Cache-Control: public, max-age=31536000, immutable

/results/*
  Access-Control-Allow-Origin: *
  Cache-Control: public, max-age=3600

/og/*
  Cache-Control: public, max-age=86400

/*.png
  Cache-Control: public, max-age=86400
"""
    sec = f"Contact: https://ciscocaceres.com/contact/\nExpires: 2027-10-11T00:00:00.000Z\nPreferred-Languages: en\nCanonical: {base}.well-known/security.txt\n"
    gpc = json.dumps({"gpc": True, "lastUpdate": MODIFIED}) + "\n"
    return {
        "site.webmanifest": json.dumps(manifest, indent=2) + "\n",
        "_headers": headers,
        "_redirects": RETIRED_REDIRECTS,
        ".well-known/security.txt": sec,
        ".well-known/gpc.json": gpc,
    }


# Files from the withdrawn first design. Pages kept serving them after they left the deployment, so they redirect.
RETIRED_REDIRECTS = "/css/style.css /css/site.css 301\n/js/provenance.js /js/site.js 301\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    canon_cmd = [sys.executable, str(Path.home() / "projects/siteops/scripts/rp-canon.py"), "--out", str(ROOT / "data/canon.json"), "--results-dir", str(SITE / "results")]
    if a.check:
        r = subprocess.run(canon_cmd + ["--check"])
        if r.returncode:
            return 1
    css_path = SITE / "css/figures.css"
    if a.check:
        if not css_path.exists() or css_path.read_text(encoding="utf-8") != figures_css():
            print("STALE output: css/figures.css", file=sys.stderr)
            return 1
    else:
        css_path.write_text(figures_css(), encoding="utf-8")
    out = render()
    out.update(static_files())
    stale = []
    for rel, text in out.items():
        path = SITE / rel
        if a.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(rel)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    if a.check:
        if stale:
            print("STALE output:", ", ".join(stale), file=sys.stderr)
            return 1
        print(f"ok: {len(out)} files match the templates and canon")
        return 0
    pages = [dict(p, modified=MODIFIED) for p in PAGES]
    lib.write_sitemap(SITE, BASE, pages)
    lib.write_robots(SITE, BASE)
    print(f"built {len(out)} files + sitemap.xml, robots.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
