# Fighter Identity Audit

## Method

Deterministic-only auto-merge (`src/mma_v4/identity.py`): two raw name strings are merged iff
they share the same accent/punctuation-normalized key (`normalize_loose`) or the same
order-independent token set (`token_set_key`) -- both exact matches after a named,
reversible transformation, never a similarity score. A small, individually-verified manual
alias table (`reviewed_alias_table.csv`) handles transliteration variants that change actual
letters (not just accents/order), each entry justified by either direct internal evidence
(shared opponent + date) or a well-established transliteration pattern -- see the `reason`
column. **No blind fuzzy/edit-distance auto-merging was performed.**

## Results (base pass, before official-results patches; `identity_merge_audit_base.csv`)

| metric | value |
| --- | ---: |
| Raw name variants seen | 3,603 |
| Distinct canonical identities after merge | 3,545 |
| Merged groups (2+ raw names -> 1 canonical identity) | 56 |
| Raw names absorbed into a merge | 114 |
| — via accent/punctuation normalization | 30 |
| — via token-order-swap matching | 11 |
| — via reviewed manual alias | 16 |

A second pass (`identity_merge_audit_final.csv`) re-canonicalizes after official-results
patches are merged in (patch files carry their own raw name spellings); this pass found 6
additional groups introduced only by patch data.

Final fighter count in `data/v4_fighter_latest_state.csv`: **3,571** (down from 3,621 before
this fix -- a net reduction of 50 phantom/duplicate identities after accounting for
patch-introduced duplicates too).

## The 5 originally-reported examples

All 5 confirmed and fixed: `Kauê Fernandes`/`Kaue Fernandes` and `Yadong Song`/`Song Yadong`
resolved automatically (accent and token-order rules respectively); `Sergey Pavlovich`/`Sergei
Pavlovich`, `Asu Almabaev`/`Asu Almabayev`, and `Elves Brenner`/`Elves Brener` required the
manual alias table (transliteration variants that change actual letters).

## Worse than reported: split-history duplicates

Several merges were not "one real fighter + one empty ghost" but two *nonzero* partial
histories under different name spellings -- the fighter's real career was fragmented across two
divergent, incomplete Elo trajectories, not just shadowed by an inert duplicate. Most notably
**`Weili Zhang`/`Zhang Weili`** (7 vs. 14 recorded appearances before merge) -- a former UFC
strawweight champion whose real record was split by a Western-order/family-name-first
transliteration inconsistency. Also `Batgerel Danaa`/`Danaa Batgerel` (15 vs. 3),
`Bibulatov Magomed`/`Magomed Bibulatov`, and others -- see `identity_merge_audit_base.csv`
(`reason = token_order_swap`) for the full list.

## Candidates found but intentionally NOT merged

`fuzzy_candidates_reviewed_not_all_merged.csv` (restricted scan: edit distance <=2 on the
normalized key, one side a zero-history "ghost" -- a safety gate that prevents two people with
their own real, distinct fight histories from ever being fuzzy-matched) and
`suffix_candidates_reviewed.csv` (generational-suffix pairs, `X` vs `X Jr./Sr./II/III/IV`,
deliberately excluded from automatic matching -- see below) list every candidate considered.
Notable rejections, with the internal evidence that ruled them out:

| candidate pair | why rejected |
| --- | --- |
| `Aldo Pereira` / `Alex Pereira` | Contradicting evidence: the champion Alex Pereira's real fight schedule does not include "vs. Leon Hill" on the ghost's recorded date -- confirmed different people. |
| `Lance Gibson` / `Lance Gibson Jr.` | 25-year gap between the two name groups (2000 vs. 2025-2026) -- the generational-suffix pattern almost certainly denotes an actual father/son pair, not one person recorded twice. |
| `Ger Harris` / `Gerry Harris` | 31-year gap (1995 vs. 2026) -- implausible single career span. |
| `Thyago Silva` / `Thiago Silva` | 13-19 year gap with zero corroborating evidence; `Thiago Silva` is a common enough name that a coincidental match is plausible. |
| `Mike Kena` / `Mike King` | Different surname entirely (not a transliteration variant), coincidental low edit distance only. |
| `Jose Sandoval` / `Joseph Sandoval` | Different given names (not a spelling variant of the same name) plus a 14-year gap. |
| `Aline Pereira` / `Alice Pereira` | Different given names. |
| `Levi Rodrigues` / `Levi Rodrigues Jr.` | No corroborating evidence (different dates/opponents); generational suffix could denote a real second person. |
| `Sang Won Kim` / `Sangwook Kim`, `Seok Hyun Ko` / `Seokhyeon Ko`, `Jeongyoung Lee` / `JeongYeong Lee` | Korean-name-transliteration ambiguity with no direct corroborating evidence and meaningful risk of collision on a common surname (`Lee`); left for future manual research rather than guessed. |

## Why the blanket "strip generational suffixes" idea was rejected during development

An earlier draft of `normalize_loose` stripped Jr./Sr./II/III/IV before comparing, which would
have auto-merged every `X`/`X Jr.` pair — including `Lance Gibson`/`Lance Gibson Jr.`, which the
25-year gap shows is almost certainly a real father-and-son pair. This was caught by a
regression test (`tests/test_v4_identity.py::test_generational_suffix_pair_does_not_auto_merge_without_verification`)
before it reached production data. Suffix-only pairs now go through the same
individual-verification-and-alias-table process as transliteration variants (`Carlo Pedersoli`/
`Carlo Pedersoli Jr.` and `Kai Kamaka`/`Kai Kamaka III` were verified this way, via direct
internal evidence of a single continuous career, and added to the alias table).
