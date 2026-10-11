# RoamingPigs Research Notes (roamingpigs.org)

The public record of small AI systems experiments: speech models, verifier ensembles, local inference energy. Every figure shows its date, sample, method, source file and limits. Self-published, not peer reviewed.

Papers stay canonical on ciscocaceres.com. This site holds the records, the TRCS dataset card, the method, the corrections log and citations. The instruments (calculators, explorers) live on roamingpigs.ai.

## How it is built

```bash
python3 scripts/build.py           # render site/ from data/canon.json and src/templates
python3 scripts/build.py --check   # fail if canon or the rendered output is stale
python3 ~/projects/siteops/scripts/rp-canon.py --out data/canon.json   # re-read the ledgers
```

- **No typed measurements.** `data/canon.json` is derived from the research ledgers in `~/projects/ciscocaceres.com` by `siteops/scripts/rp-canon.py`, which records the SHA-256 of every source file. Templates read it; the build asserts the claims they make (dataset re-hash has 0 mismatches, the verifier pool is still simulated, the energy runs are physically plausible).
- **Evidence classes** (measured, modelled, simulated, proposed) are defined on `/method/`. A figure without a date, sample and method does not ship.
- **Shared code** lives in siteops: `rpsite_lib.py` (head metadata, JSON-LD, sitemap), `rp-og.py` (social cards, icons), `rp-shoot.sh` (screenshots, axe, overflow, console and CSP check).
- **CSP is strict** (`_headers`): no inline script or style, nothing from other domains. Charts are inline SVG generated at build time. Fonts are self-hosted and OFL (Source Serif 4, Inter, JetBrains Mono).

## Gates before a deploy

```bash
python3 scripts/build.py --check
python3 ~/projects/siteops/scripts/seo-audit.py --domain roamingpigs.org --mode static
python3 ~/projects/siteops/scripts/llm-smell-audit.py --root site --auto --max-em-dashes 1
~/projects/siteops/scripts/rp-shoot.sh site /tmp/shots / /datasets/trcs/ /method/ /corrections/ /cite/ /about/
```

Deploy: `cf-deploy.py roamingpigs.org -y` (Pages project `roamingpigs-org`). Never `wrangler`.

## Rules for editing

- Do not add an identifier (DOI, ROR, anything) until it resolves. There is no DOI yet.
- Do not use proven, verified, cleared or validated for own results. Nothing here is reviewed.
- Models appear by size and kind, never by product name.
- A change to a published figure goes in `/corrections/` with its date.
