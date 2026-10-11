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
    {"path": "/method/", "label": "Method"},
    {"path": "/cite/", "label": "Cite"},
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
    assert m, s
    return f"{m.group(1)} {m.group(2)} UTC"


def derive(c: dict) -> dict:
    e1, e2, apu, vec, echo = c["e1"], c["e2"], c["apu"], c["vec"], c["echo"]
    runs = [r for r in apu["metered_runs"] if r["plausible"]]
    excluded = [r for r in apu["metered_runs"] if not r["plausible"]]
    assert len(excluded) <= 1 and len(runs) >= 2, "unexpected set of metered runs"
    words = {1: "one", 2: "two", 3: "three"}
    js = [r["j_per_token_mean_power"] for r in runs]
    assert len({r["generated_tokens"] for r in runs}) == 1, "runs differ in token count"
    assert c["trcs"]["rehash_mismatches"] == 0, "dataset re-hash found mismatches"
    assert echo["portfolio_agrees"], "portfolio headline disagrees with the E3 ledger"
    assert vec["generated_by_seeded_rng"], "VEC-SCR is no longer simulated; the evidence class must be rechecked"
    sizes = [m["params"] for m in e2["models"]]
    return {
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
        "j_peak_first": f'{runs[0]["j_per_token_peak_power"]:.2f}',
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
        "snr_list": [(k, f'{e2["mean_wer_by_snr"][k] * 100:.1f}') for k in ("clean", "snr_20", "snr_10", "snr_0", "snr_-6")],
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
    ch = {
        "wer": charts.wer_by_snr(c["e2"]),
        "hal": charts.hallucination_by_condition(c["e1"]),
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
        c=c, v=v, results=results, ch=ch, head=head, nav=NAV, page=nf, site={"modified": MODIFIED, "modified_human": MODIFIED_HUMAN}
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
  Cache-Control: public, max-age=0, must-revalidate

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
        ".well-known/security.txt": sec,
        ".well-known/gpc.json": gpc,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    canon_cmd = [sys.executable, str(Path.home() / "projects/siteops/scripts/rp-canon.py"), "--out", str(ROOT / "data/canon.json"), "--results-dir", str(SITE / "results")]
    if a.check:
        r = subprocess.run(canon_cmd + ["--check"])
        if r.returncode:
            return 1
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
