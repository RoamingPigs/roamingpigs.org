# Session handoff, roamingpigs.org

## Last session ended
2026-10-11

## Last big thing accomplished
2026-10-12: ran and published the full-grid speech study (plan first, 5,760 transcripts, intervals), added /reproduce/ and a results folder, and fixed the dataset card. Earlier the same day:
Rebuilt the site from scratch as RoamingPigs Research Notes: a light, serif-set research record where every figure carries an evidence class (measured, modelled, simulated, proposed), a run date, a sample and what it does not show. Pages: `/`, `/datasets/trcs/`, `/method/`, `/corrections/`, `/cite/`, `/about/`, 404. Built by `scripts/build.py` from `data/canon.json` (derived from the ledgers by `siteops/scripts/rp-canon.py`) and `src/templates`.

## First action next session
Run `python3 scripts/build.py --check`. If it reports stale canon, a ledger changed upstream: re-run `rp-canon.py`, read the diff, and check whether any sentence on a page still holds.

## Read before editing
- Papers are canonical on ciscocaceres.com. Do not copy their text here.
- Nothing typed: add numbers to `rp-canon.py`, not to a template.
- The first version's false claims are listed on `/corrections/`. Do not bring any back.

## Open items
See `docs/WORK_TRACKER.md`.
