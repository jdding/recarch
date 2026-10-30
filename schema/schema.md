# RecArch card schema (v0.1)

One YAML file per system in `data/systems/<id>.yaml`. `build.py` validates every card and fails the build on errors.
Rule: every claim must come from a listed source. If a source does not say, use `null` and list the field in `unknown_fields`. Never guess.

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string (slug) | yes | Must equal the file name without `.yaml` |
| `name` | string | yes | System / paper name |
| `company` | string | yes | Organisation that built it |
| `surface` | string | yes | Product surface, or what the source actually evaluates |
| `year` | int | yes | Year of first public disclosure (arXiv v1, blog date, or venue date if no preprint). See "Year and era rules" |
| `system_type` | enum | yes | `recommendation`, `search`, `ads`, `training_infrastructure`, `reference_architecture`, `research` |
| `evidence_level` | enum | yes | `production_described` (source says it is deployed), `open_source_reference` (code released, not a live-system guarantee), `research_only` (not described as deployed) |
| `summary` | string | yes | 1-3 factual sentences |
| `paradigms` | list of enum | yes | `two-tower`, `dlrm`, `sequential-transformer`, `generative-retrieval`, `semantic-id`, `llm-based`, `foundation-model`, `graph-neural-network`, `random-walk`, `attention-ctr`, `learning-to-rank`, `gbdt`, `item-cf`, `embedding-based-retrieval`, `multi-task`, `online-training`, `rl-alignment` |
| `stages` | list | yes | Items: `stage` (`retrieval`, `pre-rank`, `rank`, `re-rank`, `single-stage`, `other`), `model_family`, `details` |
| `id_tokenization` | map | yes | `approach`, `details` - how items/users are represented (ID embeddings, Semantic IDs, ...) |
| `features_signals` | list of strings | yes | Features and real-time signals the source names |
| `training` | map | yes | `mode` (offline / online / ...), `objectives` (list), `notes` |
| `serving_infra` | string or null | yes | Serving / infra notes |
| `scale` | list | yes | Items: `metric`, `value`, `note`. Only numbers stated by the source |
| `results_reported` | string or null | yes | Reported outcome, with attribution |
| `caveats` | list of strings | yes | Anything a reader could misread (e.g. not production, unnamed platform) |
| `unknown_fields` | list of strings | yes | Things the sources do not say |
| `sources` | list (>= 1) | yes | Items: `title`, `url` (https), `type` (`paper`, `engineering_blog`, `documentation`, `source_code`, `press`) |
| `code` | map | yes (added round 6) | Open-source code status: `status`, `checked_on`, `repos`, optional `note`. See below |


## Draft-only fields
Cards in `data/drafts/` carry `needs_fulltext: true` and `fulltext_note` (which paper PDF is needed). They are not built or published.


## Full-text provenance (added round 3)
Cards upgraded from drafts carry `needs_fulltext: false` and `fulltext: {pdf_url, local_pdf, sections_read, verified_on}`. `local_pdf` is the box path of the PDF, or a note that the text was read through a fetch tool. These fields are optional and not validated by `build.py`.

## Code field (added round 6)
```yaml
code:
  status: official_full | official_partial | third_party_only | none
  checked_on: '2026-10-30'
  repos:            # empty list when status is none
  - url: https://github.com/...   # must exist; verified by HTTP 200 on the check date
    owner: who publishes it
    official: true | false
    note: what it contains and what it lacks
  note: optional, used when status is none
```
Status definitions:
- `official_full`: the paper's authors or the company released code implementing the paper's main model or system. Production data, weights and surrounding infrastructure may be absent; the note says what is missing.
- `official_partial`: official but incomplete. Only one component, a framework or reference implementation by the company, a related-but-different release, or a deliberately minimal or snapshot version.
- `third_party_only`: no official code found; only community reimplementations exist. One representative repo is listed with `official: false`.
- `none`: no official code and no notable third-party implementation found. This records a search result (paper text, company GitHub organisation, GitHub and web search), not proof that no code exists.

Validation (`build.py`): `official_*` needs at least one repo with `official: true`; `third_party_only` needs repos that are all `official: false`; `none` has no repos; every repo needs an https://github.com URL, owner, note and a boolean `official`.

The home page chip "Has official code" selects `official_full` plus `official_partial`. Third-party-only cards do not count as having code.

## Year and era rules (added round 7)

**`year`** is the year of first public disclosure of the system: arXiv v1 date, engineering-blog date, or the venue date when there is no preprint. It is not the venue year and not the deployment year. The id suffix is a stable slug and may differ from `year`.

New required fields (all validated by `build.py`):

| Field | Type | Meaning |
|---|---|---|
| `first_public` | string `YYYY-MM` | Month of first public disclosure; its year must equal `year` |
| `venue` | string or null | Formal venue of the published version, e.g. `KDD 2018`; null when preprint/blog only |
| `venue_year` | int or null | Year of that venue; null iff `venue` is null |
| `published_version_checked` | bool or null | true = card numbers checked against the published full text; false = published version exists but was not readable (card based on arXiv); null iff `venue` is null |
| `primary_source` | URL | Must equal one `sources[].url`: the venue/DOI link when a published version exists, otherwise the latest arXiv version or the blog/repo |
| `era` | `classic` / `deep` / `generative` | Dominant modelling paradigm, see below |
| `tldr` | string | One plain-English sentence (<= 200 chars) shown at the top of the card page and on home cards. Must restate only facts already in `summary` / `results_reported`; no new claims |
| `era_reason` | string | One line justifying `era` |

Optional: `deployed_year` (int; only when a source states it), `version_note` (string; shown with caveats, e.g. withdrawn or removed arXiv versions).

**Era definitions** (by dominant paradigm; year is only a sanity bound: classic <= 2017, deep >= 2016, generative >= 2023):

- `classic`: CF / MF, linear, GLM, FTRL, GBDT pipelines, non-learned graph walks.
- `deep`: central model is a discriminative neural network (embedding+MLP, attention-CTR, two-tower, GNN, multi-task, sequence transformer as encoder/feature), including 2023+ systems that did not change paradigm.
- `generative`: autoregressive / generative recommendation (semantic IDs, next-action tokens), LLM-based, or scaling-law / foundation-model scale as the central claim.

Withdrawn sources: cards whose source was withdrawn by its authors move to `data/withdrawn/` and are not built.

## Update signals (added round 8)

| field | type | rule |
|---|---|---|
| `added_on` | quoted `YYYY-MM-DD` | required; day the card was first published on RecArch. Shown on the card page, drives "Added" events |
| `last_verified` | quoted `YYYY-MM-DD` | required; last day the card was checked against its sources; must be >= `added_on`. Shown on the card page, used as sitemap `lastmod` and JSON-LD `dateModified` |
| `updates` | optional list of `{date, note}` | one entry per material change after publishing (correction, re-verification against the published PDF). Each becomes an "Updated" event in the home strip, `/changelog/` and `/feed.xml` |

Backfill note: rounds 1-7 had no dates on cards, so `added_on` for the 62 existing cards is an approximation (2026-10-29 or 2026-10-30, by build round). From now on set it when the card is created and add an `updates` entry for every later edit.

`data/site.yaml`: `newsletter` (provider, `publication_id`, `embed_url`) and site-level `events` (title, date, note). `data/newsletter/<slug>.yaml`: one file per issue, see `templates/newsletter_issue.example.yaml`.

## Home taxonomy (`data/taxonomy.yaml`)
Home filters show six paradigm *families* instead of the 17 raw tags; the raw tags and evidence levels live in a collapsed "More filters" panel. `taxonomy.yaml` maps every paradigm tag to exactly one family and every pipeline stage to exactly one stage group; `build.py` fails if a tag or stage is unmapped, mapped twice, or unknown. When adding a paradigm tag, add it to `PARADIGMS` in `build.py`, here, and to a family.
`random-walk` = random-walk / personalized-PageRank systems with no learned GNN (Pixie, Twitter WTF). `graph-neural-network` is only for learned GNNs (PinSage, LiGNN, OmniSage).

## Citations (`data/citations.json`, generated by `scripts/citations.py`)

`{card_id: {count, source: "Semantic Scholar"|"OpenAlex", source_url, fetched_on, matched_title, matched_year, ids, papers, note?, ignored_other_papers?, shared_papers?}}`. No entry = no paper counted; the page shows nothing. `build.py` rejects unknown card ids or malformed entries.

`count` is the total for the whole system and is what the card shows and what admission checks use. `papers` is required and uniform: `[{name, count, source, source_url, matched_title, matched_year, ids}]`. A card with `versions` has one row per version, named like the version, and `count` is the sum of those rows. Every other card has one row and `count` equals that row. A Semantic Scholar record is counted once per card, so two versions that resolve to the same record never double count; the version whose paper was already counted is listed in `shared_papers`. `source`, `source_url`, `matched_title` and `matched_year` at the top level describe the presented version. `build.py` fails when `count` is not the sum of `papers` or when a merged card lacks a row for one of its versions. On a merged card the version list on the card page shows each version's own count in small type. See `docs/admission.md` section 4.

## Diagrams (`data/diagrams/<id>.yaml`)

```yaml
alt: "text alternative (required)"
caption: {fig: "Fig. 3", work: "Paper title (Venue Year)", url: "<must equal one of the card's sources[].url>", note: "optional: what is not drawn"}
columns:                       # left to right: inputs -> core module(s) -> outputs
  - label: Inputs
    boxes:
      - {id: a, kind: input|module|output, text: ["Bold title", "small description", ...]}
edges: [[a, b], ...]           # arrows; same column = vertical arrow
```
Boxes in a column stack top to bottom; the SVG is at least 640px wide and scrolls horizontally on phones. Always our own redraw; never copy the paper's artwork.

## Site settings for the home carousel (`data/site.yaml`)

`carousel_size: 6`, `carousel_window_days: 7`. Selection: activity date = max(`added_on`, latest `updates[].date`); cards active within the window come first (newest first; ties: updated before added, then id descending), the rest backfill by most recent activity until `carousel_size`.

## Card layout v2 (default for all cards)

Every card page uses the v2 layout. Section order: header, key facts, architecture (only when the card has a diagram under `data/diagrams/`, otherwise the block and its TOC link are skipped), how it works, results, subscribe, technical details (collapsed), limitations (only when the card has limits), sources, history. There is no per-card switch. `build.py` fails if a card is missing one of these fields:

- `core_idea`: one short line, no parentheses.
- `deployed_in`: product or surface.
- `scale_short`: one short scale statement taken from `scale` or `results_reported`.
- `key_result`: one online A/B or production result. With no online result, the strongest offline result labelled "Offline:". With none, say what is reported, for example "No metrics reported".
- `results_table`: lists `online`, `offline` and `other` of rows with `setting`, `method`, `metric`, `result`, `versus`. `other` holds reported results whose type the source does not state and renders as "Reported, type not stated". An optional `note` renders as a paragraph after the table. A card needs at least one row or a `note`.

Number checks run in `build.py`. Every number in `key_result` and in `results_table` must appear in `results_reported`. Every number in `core_idea`, `deployed_in` and `scale_short` must appear in the card's own `results_reported`, `summary`, `surface`, `tldr` or `scale`. Digits inside names count as numbers, so use a generic method name such as "The proposed model" when the real name contains digits and the digits are not in `results_reported`.

## Status (added 2026-10-30, owner decision)

`status`: `active` (default when absent), `superseded` or `retired`. Validated by `build.py`.

| field | type | rule |
|---|---|---|
| `status` | `active` / `superseded` / `retired` | optional; absent means `active` |
| `status_date` | quoted `YYYY-MM-DD` | required when not active; between `added_on` and today |
| `status_reason` | string | required when not active; shown to readers on the card page, so keep it factual and without parentheses |
| `superseded_by` | card id | required when `superseded`; must be an existing card |

Meaning. `retired`: the card no longer meets the admission standard (`docs/admission.md`). `superseded`: the card was merged into another card, one card per system lineage; `superseded_by` is that card.

Behaviour of a `retired` card, and of a `superseded` card where noted:

- A `superseded` card's page is a static redirect page: `meta refresh` to `../<superseded_by>/`, `canonical` to the merged card, `noindex`, and a link. It has no card layout. The card file is never deleted.
- A `retired` card keeps its file forever and its page is still built at `/systems/<id>/`, with a notice that carries the date and the reason, a `noindex` meta tag, the title prefix "Retired:" or "Superseded:", and no "Compare this system" button.
- It is left out of the home list, the timeline, the "N systems" count, the carousel, `data/systems.json` (compare picker), the sitemap, and the feed and changelog events for "Added" and "Updated". The changelog and feed carry one "Retired" or "Superseded" event on `status_date`.
- The home page ends with a collapsed "Archive" list of these cards with their reasons.
- `status_reason`, `status_date` and `superseded_by` are rejected on an active card. `superseded_by` may not point at the card itself.

Lane note. Scheduling lanes use the venue year, and `year` stays the year of first public disclosure. A paper first posted in 2025 and published at a 2026 venue is scheduled in the 2026 lane and its card still shows 2025. See `docs/admission.md`.


## Versions (added 2026-10-30, owner decision: one system = one card)

A card for a system with several published versions presents one version in all main fields (the latest by default; the owner may designate another) and lists the other versions only as sources and in a version list. Two optional fields, valid on every card, both present or both absent. A single-version card writes neither.

| field | type | rule |
|---|---|---|
| `version` | string | name of the version this card presents; must equal one `versions[].name` |
| `versions` | list, at least 2, oldest first | items: `name`, `first_public` (`YYYY-MM`), `source` (must equal one `sources[].url`), `note` (one factual line, no new numbers) |

`build.py` checks: `version` equals the `name` of one `versions` item; the list is sorted by `first_public`; the first item's `first_public` equals the card's `first_public` (so `year` is the first public year of the whole lineage); `primary_source` equals the presented version's `source`.

Rendering: a "Presents <version>, latest of N versions" badge (or "Presents <version>, one of N versions, latest is <other>" when the presented version is not the newest) under the title, a "Versions" list at the top of the History section, and an "other version" tag on the other versions' sources. The merged card's `version_note` says which version it presents.

Merging procedure. Create the merged card with a new id from the presented version's card. Keep `added_on` as the earliest of the merged cards and add an `updates` entry. Set every old card (including the presented version's old card) to `status: superseded` with `superseded_by`, `status_date` and `status_reason`. Add an entry to `data/citations.json` for the new id, with one `papers` row per version; `count` is their sum (run `scripts/citations.py --only <id>`). See `docs/admission.md` section 4.
