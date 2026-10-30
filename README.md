# RecArch v0.1
Structured, sourced database of industrial recsys/search/ranking architectures. Static site, no backend.

- Cards: `data/systems/*.yaml` (schema: `schema/schema.md`). Build validates them.
- Build: `python3 build.py` (set `SITE_URL=https://yourdomain` for canonical URLs and sitemap) -> `dist/`
- Serve: `cd dist && python3 -m http.server 8080`
- Refresh candidates: `python3 scripts/refresh.py` -> `review_queue.jsonl` (pending only; never auto-publishes)
- Placeholders (TODO): newsletter signup, sponsor page contact/pricing, SITE_URL domain.


## Round 2
Card counts are computed, never typed here: run `python3 scripts/stats.py`. See `coverage_plan.md` for what is in and what was dropped. Home page has an Era filter (classic / deep-learning / generative-LLM-scaling); since round 7 it uses the explicit `era` field, not the year.
Admission audit: `python3 scripts/admission_audit.py`. Judged per system; merged cards use the summed citations of all versions (docs/admission.md section 4).

## Publication rule (owner, round 2b)
A card is published only if it is based on the full text of its sources. Cards whose sources were read only at abstract / search-snippet level live in `data/drafts/` (not built) with `needs_fulltext: true` and a `fulltext_note`. See `drafts_needing_pdf.md`. Counts: `python3 scripts/stats.py`. Full-text status of drafted cards: `needs_zotero.md`.

## Code coverage (round 6, checked 2026-10-30)
Every card has a `code` block (schema/schema.md). Per-status counts: `python3 scripts/stats.py`. Home page chip "Has official code" = full + partial. Every listed repo URL returned HTTP 200 on 2026-10-30. "none" records a search result, not proof that no code exists.

## Round 7: year and era audit
See `era_audit.md` (rules, per-card table, borderline cases) and `needs_published_pdf.md` (published versions not yet read). `year` = first public disclosure; `era` = dominant paradigm (explicit, validated). 2 wrong years fixed (Pixie 2017, Lattice 2023). `linkedin-ligr-2025` moved to `data/withdrawn/` (authors withdrew the paper). Published (venue) version is `primary_source` where one exists.

## Round 8: update signals and subscribing (no external accounts)

- Home page strip "Recently added & updated" with a this-week counter, `/changelog/` (all events by date), `/feed.xml` (Atom; cards added, updated, newsletter issues; `<link rel="alternate">` on every page).
- Every card page shows Added / Last verified and a History list. Fields: see `schema/schema.md` ("Update signals"). Backfilled `added_on` dates are approximate.
- `/newsletter/` archive and `/newsletter/<slug>/` issue pages are built from `data/newsletter/*.yaml` (template: `templates/newsletter_issue.example.yaml`). No issues exist yet, so the archive says so.
- Home: hero sentence + Beehiiv embed, search box, Era / Stage / Paradigm-family chips, two toggles (production-deployed, official code), collapsed "More filters", List | Timeline view, filter state in the URL query (`?era=deep&prod=1&view=timeline`). Families/stage groups: `data/taxonomy.yaml` (validated by `build.py`). Card pages open with the `tldr` line plus Paper / Code buttons.
- Subscribe boxes (home hero, every card, compare, changelog, newsletter, each issue) are the real Beehiiv embed: `newsletter.form_id`, `public_url`, `publication_id` and the loader `embed_url` come from `data/site.yaml`; every page also loads Beehiiv's `attribution.js` so UTM params are forwarded. Without JS the box falls back to a link to `https://recarch.beehiiv.com/subscribe`. The old stub `static/subscribe.js` was removed. Never test by submitting an address: it creates a real subscriber.
- Workflow per release: add card or edit -> add `updates` entry + bump `last_verified` -> `python3 build.py` -> the strip, changelog, feed and sitemap update automatically.
- `needs_published_pdf.md` has three sections: A (in Zotero but cloud-only in Google Drive), B (Zotero has only an arXiv copy), C (not in Zotero).

## Round 9: citation counts, redrawn diagrams, home carousel (nothing deployed)

- **Citations** (`scripts/citations.py` -> `data/citations.json`, generated, committed). Lookup order per card: Semantic Scholar Graph API by DOI, then arXiv id, then a title search accepted only if title similarity >= 0.92 and year within 1; OpenAlex (`cited_by_count`) is the fallback. Google Scholar is never scraped. If S2 splits one work into a venue record and an arXiv record, the counts are summed and the entry carries a `note`. A second arXiv id that is a different paper (e.g. TransAct V2) is ignored and listed in `ignored_other_papers`. Cards with no paper (blog/code only), or whose only paper is related work, get no entry: the card page shows nothing (never "0"). Refresh weekly: `python3 scripts/citations.py` (`--only id1,id2`, `--dry`); a failed lookup keeps the previous value. Then `python3 build.py`.
- **"Most cited" sort** on the home list view (`?sort=cites`); cards without a count go last in default order.
- **Diagrams** (`data/diagrams/<id>.yaml`, pilot: youtube-dnn-2016, din-alibaba-2017, tiger-google-2023). Our own simplified redraw, rendered by `build.py` to inline SVG below the TL;DR. Format in `schema/schema.md`. `build.py` fails if the caption link is not one of the card's `sources[].url`.
- **Home carousel** replaces the text strip: `carousel_size` (default 6) and `carousel_window_days` (default 7) in `data/site.yaml`. Tests: `python3 tests/carousel_fixture.py /tmp/car-fixtures && NODE_PATH=/tmp/jt/node_modules node tests/carousel.test.js /tmp/car-fixtures dist/static`, and `node tests/sort.test.js`.
- Style lint: build.py warns (never fails) when a card name contains parentheses, or a displayed string has more than one parenthetical or one longer than 40 chars. Keep names to the bare method name; put company, year and venue in their own fields.

## Round 10: admission standard adopted, status lifecycle, one system = one card (nothing deployed)

- `docs/admission.md` is the adopted admission and scheduling standard (Chinese). Lane rule by venue year, 5 new + 1 upgrade a week with a trigger to 4 + 2, thresholds, cap 120.
- `status` active / superseded / retired (`schema/schema.md`, "Status"). Six cards retired, listed in `docs/admission.md`. Their files and URLs stay.
- `version` / `versions` fields and the merge procedure (`schema/schema.md`, "Versions"). Merged: DCN + DCN V2 into `dcn-google` (presents DCN V2), OneRec + OneRec-V2 + OneRec-Think into `onerec-kuaishou` (presents OneRec-V2 by owner decision; the latest version is OneRec-Think). Old URLs are static redirect pages, old YAMLs are `superseded`. DCNv3 is a third-party paper, not merged.
- Tests: `tests/retired.test.js` (non-active cards, redirects, merged cards). `tests/v2_order.test.js` skips redirect pages and checks their count.

## Deploy

Pushing to `main` runs `.github/workflows/pages.yml`: it builds with `SITE_URL=https://jdding.github.io/recarch`, runs the tests and deploys `dist/` to GitHub Pages. To go live, make the repo public, then set Settings > Pages > Source to GitHub Actions.
