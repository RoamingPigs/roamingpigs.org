# Work Tracker, roamingpigs.org

Durable backlog. Update at every milestone and pause.

**Updated:** 2026-10-11

## Done

- [x] 2026-10-11: Rebuilt as "Research Notes". Withdrew the first version, which carried a placeholder DOI, a ROR link that does not exist, a "Merkle root" that was one file's hash, codec error rates with no source, an agent-swarm panel with no source, and "proven / verified / cleared" labels. Every figure now comes from `data/canon.json`, derived from the ledgers, with an evidence class, date, sample and limits. Corrections are public at `/corrections/`.
- [x] Gates green on 7 pages x 3 viewports: axe WCAG 2.2 AA, no overflow, no console or CSP errors; SEO audit 9 of 9; copy audit clean; pre-deploy clean.

- [x] 2026-10-11: Published the five results files at `/results/` (scrubbed: model names to size and kind, local paths, hosts and IPs removed, every number checked unchanged), with SHA-256 digests, `index.json`, CORS, Dataset JSON-LD and a script that reproduces the headline figure. Live hashes verified against the index.

- [x] 2026-10-12: Full-grid speech run on the released 1,050 files (6 models, 5,760 transcripts; E1 with a neural-VAD arm; speech-cost check), with a plan pushed first, cluster-bootstrap intervals, a completeness check and per-clip results. Code, plan, tolerances and reproduction rules are public at github.com/RoamingPigs/trcs. The pilot is superseded and its files are marked so. Records, results page, reproduce page and the explorer on roamingpigs.ai use the new data.
- [x] Hugging Face dataset card rewritten (synthetic speech stated, CC BY 4.0 to match the manifest, how the audio was made, known limits).
- [x] `build.py --check` is in `pre_build` for this site (claude-code `cf-sites.json`), and the Abundera-only `well-known` SEO dimension is skipped for it.

## Open

Only the operator can do these:
- [ ] **Zenodo DOI for the evaluation repo.** Sign in to Zenodo with GitHub, switch on RoamingPigs/trcs, then publish a GitHub release (suggested tag `v2.0.0`; `.zenodo.json` and `CITATION.cff` are ready). Then add the DOI to `/cite/`, the Dataset JSON-LD and the README. Do not create the release before Zenodo is switched on, or it will not be archived.
- [ ] **Hugging Face DOI** (optional): the "Generate DOI" button in the dataset's settings. It is permanent and the docs do not say it freezes the files, so decide after the Zenodo DOI.
- [ ] **Cloudflare Web Analytics.** Cloudflare injects its beacon on production; the CSP blocks it (so the "no analytics" line holds) but it logs a console error. Turn off automatic setup for roamingpigs.org and .ai in the dashboard, or supply a token with Account Settings Write.
- [ ] **ciscocaceres.com.** Apply `docs/HANDOFF-roamingpigs-sites-2026-10-11.md` (in that repo), run its gates and deploy. Another session has uncommitted edits there, so I did not.
- [ ] **arXiv preprint** (optional). Account `cisco801`. I can prepare a bundle on request; submission is yours.

Next work:
- [ ] Invite outside reproduction (post the /reproduce/ page where speech and ASR engineers will see it). Count stays at none until a report arrives.
- [ ] Publish the scripts behind the energy, agent-coordination and verifier records. Today only the speech experiments are fully public.
- [ ] A second dataset with recorded (not synthetic) speech, so claims can leave the synthetic regime. This is the main thing the current results cannot show.
- [ ] Confirm the CC BY 4.0 licence on the results files.
- [ ] Core Web Vitals field data once there is traffic.
