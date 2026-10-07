# Data Audit: 2025-2026 Box-Score Integration

## Source

- User-supplied file `ufcstats_box_scores_2025-01-01_through_2026-04-03.csv`, covering 2025-01-11 through 2026-03-28 (51 events, 636 fights).
- **Provenance (verbatim from the user):** "This file was reconstructed from the public `Greco1899/scrape_ufc_stats` UFCStats mirror rather than downloaded directly from ufcstats.com during your session." This investigation did not independently scrape ufcstats.com for this data. Every converted row's `source_dataset` column is stamped `"ufcstats.com (via Greco1899/scrape_ufc_stats mirror, user-supplied)"` so the provenance is explicit in the data itself, not just in this document.
- Combined with the pre-existing, independently-verified `data/updates/ufcstats_2026-04-04_through_2026-08-08.csv` (17 events, 210 fights, `source_dataset == "ufcstats.com"`, imported in a prior session and documented in `data/updates/UFCSTATS_2026-08-09_UPDATE_AUDIT.md`).

## Corruption found and fixed

1. **Primary gap** (2025-01-11 through 2026-03-28): the repo's pre-existing data for this window came from three third-party datasets (`jossilva3110/ufc-dataset-1994-2026`, `jerzyszocik/ufc-betting-odds-daily-dataset`, `mdabbert/ultimate-ufc-dataset`) with **no event name or event ID on any row**, and fight-date clustering as high as 44 fights on a single date (a real UFC card is 9-16 fights) -- identified in an earlier internal investigation. Fixed by unconditionally superseding every row in this window with the verified box-score data.
2. **Secondary, previously-undetected corruption** inside the window the project had already labeled "verified" (2026-04-04 through 2026-08-08): the prior session's ufcstats.com import only removed placeholder rows that exact-string-matched an official row by `(date, fighter_a_name, fighter_b_name)`. Any placeholder row that didn't exact-match (name variants, mis-ordered pairs) was silently left in place, inflating some event dates to up to 39 rows instead of the real 12-14. Found only by checking post-merge date-cluster plausibility, not by trusting the prior audit's own "verified" label.

## Fix applied

`scripts/holdout_2025_2026_rebuild_state.py` rebuilds `canonical_fights.csv`/`fights_chronological.csv` from scratch (V3 raw source + every `data/updates/ufcstats_*.csv` patch via the existing `merge_official` exact-match dedup), then applies one additional, stricter rule: for both verified windows above, **unconditionally drop every row whose `fight_id` does not start with `ufcstats_`** (i.e. every row not sourced from a verified ufcstats.com-derived patch), regardless of whether it happened to string-match an official row. Verified data supersedes its entire covered date range unconditionally, not just the rows it happens to pattern-match.

- `merge_official` exact-match passes removed **924** rows (across all `data/updates/*.csv` patches applied during this rebuild).
- The additional unconditional-supersession rule removed a further **743** leftover rows that exact-matching missed.
- Post-identity-canonicalization dedup removed **0** more rows (duplicates revealed only after fighter-name canonicalization).

## Result

- Final 2025-2026 span: **848** fights across **68** events (51 from the new box-score file, 17 from the prior verified import), max **14** fights on any single date.
- Total fighters after full rebuild: 2820. Total fights, all history: 9130.
- No duplicate `fight_id` values remain anywhere in the dataset.
- Data strictly before 2025-01-11 was not touched by this integration.

## Imported events (2025-2026 span)

| date | event | bouts |
| --- | --- | ---: |
| 2025-01-11 00:00:00 | UFC Fight Night: Dern vs. Ribas 2 | 14 |
| 2025-01-18 00:00:00 | UFC 311: Makhachev vs. Moicano | 13 |
| 2025-02-01 00:00:00 | UFC Fight Night: Adesanya vs. Imavov | 11 |
| 2025-02-08 00:00:00 | UFC 312: Du Plessis vs. Strickland 2 | 12 |
| 2025-02-15 00:00:00 | UFC Fight Night: Cannonier vs. Rodrigues | 12 |
| 2025-02-22 00:00:00 | UFC Fight Night: Cejudo vs. Song | 12 |
| 2025-03-01 00:00:00 | UFC Fight Night: Kape vs. Almabayev | 10 |
| 2025-03-08 00:00:00 | UFC 313: Pereira vs. Ankalaev | 10 |
| 2025-03-15 00:00:00 | UFC Fight Night: Vettori vs. Dolidze 2 | 13 |
| 2025-03-22 00:00:00 | UFC Fight Night: Edwards vs. Brady | 13 |
| 2025-03-29 00:00:00 | UFC Fight Night: Moreno vs. Erceg | 12 |
| 2025-04-05 00:00:00 | UFC Fight Night: Emmett vs. Murphy | 12 |
| 2025-04-12 00:00:00 | UFC 314: Volkanovski vs. Lopes | 13 |
| 2025-04-26 00:00:00 | UFC Fight Night: Machado Garry vs. Prates | 14 |
| 2025-05-03 00:00:00 | UFC Fight Night: Sandhagen vs. Figueiredo | 12 |
| 2025-05-10 00:00:00 | UFC 315: Muhammad vs. Della Maddalena | 12 |
| 2025-05-17 00:00:00 | UFC Fight Night: Burns vs. Morales | 11 |
| 2025-05-31 00:00:00 | UFC Fight Night: Blanchfield vs. Barber | 9 |
| 2025-06-07 00:00:00 | UFC 316: Dvalishvili vs. O'Malley 2 | 13 |
| 2025-06-14 00:00:00 | UFC Fight Night: Usman vs. Buckley | 13 |
| 2025-06-21 00:00:00 | UFC Fight Night: Hill vs. Rountree Jr. | 12 |
| 2025-06-28 00:00:00 | UFC 317: Topuria vs. Oliveira | 11 |
| 2025-07-12 00:00:00 | UFC Fight Night: Lewis vs. Teixeira | 12 |
| 2025-07-19 00:00:00 | UFC 318: Holloway vs. Poirier 3 | 14 |
| 2025-07-26 00:00:00 | UFC Fight Night: Whittaker vs. De Ridder | 12 |
| 2025-08-02 00:00:00 | UFC Fight Night: Taira vs. Park | 12 |
| 2025-08-09 00:00:00 | UFC Fight Night: Dolidze vs. Hernandez | 12 |
| 2025-08-16 00:00:00 | UFC 319: Du Plessis vs. Chimaev | 12 |
| 2025-08-23 00:00:00 | UFC Fight Night: Walker vs. Zhang | 12 |
| 2025-09-06 00:00:00 | UFC Fight Night: Imavov vs. Borralho | 13 |
| 2025-09-13 00:00:00 | Noche UFC: Lopes vs. Silva | 14 |
| 2025-09-27 00:00:00 | UFC Fight Night: Ulberg vs. Reyes | 12 |
| 2025-10-04 00:00:00 | UFC 320: Ankalaev vs. Pereira 2 | 14 |
| 2025-10-11 00:00:00 | UFC Fight Night: Oliveira vs. Gamrot | 12 |
| 2025-10-18 00:00:00 | UFC Fight Night: De Ridder vs. Allen | 13 |
| 2025-10-25 00:00:00 | UFC 321: Aspinall vs. Gane | 13 |
| 2025-11-01 00:00:00 | UFC Fight Night: Garcia vs. Onama | 13 |
| 2025-11-08 00:00:00 | UFC Fight Night: Bonfim vs. Brown | 12 |
| 2025-11-15 00:00:00 | UFC 322: Della Maddalena vs. Makhachev | 14 |
| 2025-11-22 00:00:00 | UFC Fight Night: Tsarukyan vs. Hooker | 14 |
| 2025-12-06 00:00:00 | UFC 323: Dvalishvili vs. Yan 2 | 14 |
| 2025-12-13 00:00:00 | UFC Fight Night: Royval vs. Kape | 12 |
| 2026-01-24 00:00:00 | UFC 324: Gaethje vs. Pimblett | 11 |
| 2026-01-31 00:00:00 | UFC 325: Volkanovski vs. Lopes 2 | 13 |
| 2026-02-07 00:00:00 | UFC Fight Night: Bautista vs. Oliveira | 13 |
| 2026-02-21 00:00:00 | UFC Fight Night: Strickland vs. Hernandez | 14 |
| 2026-02-28 00:00:00 | UFC Fight Night: Moreno vs. Kavanagh | 13 |
| 2026-03-07 00:00:00 | UFC 326: Holloway vs. Oliveira 2 | 12 |
| 2026-03-14 00:00:00 | UFC Fight Night: Emmett vs. Vallejos | 14 |
| 2026-03-21 00:00:00 | UFC Fight Night: Evloev vs. Murphy | 13 |
| 2026-03-28 00:00:00 | UFC Fight Night: Adesanya vs. Pyfer | 13 |
| 2026-03-29 00:00:00 | NaT | 0 |
| 2026-04-04 00:00:00 | UFC Fight Night: Moicano vs. Duncan | 13 |
| 2026-04-11 00:00:00 | UFC 327: Prochazka vs. Ulberg | 12 |
| 2026-04-18 00:00:00 | UFC Fight Night: Burns vs. Malott | 12 |
| 2026-04-25 00:00:00 | UFC Fight Night: Sterling vs. Zalal | 13 |
| 2026-05-02 00:00:00 | UFC Fight Night: Della Maddalena vs. Prates | 13 |
| 2026-05-09 00:00:00 | UFC 328: Chimaev vs. Strickland | 13 |
| 2026-05-16 00:00:00 | UFC Fight Night: Allen vs. Costa | 13 |
| 2026-05-30 00:00:00 | UFC Fight Night: Song vs. Figueiredo | 13 |
| 2026-06-06 00:00:00 | UFC Fight Night: Muhammad vs. Bonfim | 12 |
| 2026-06-14 00:00:00 | UFC Freedom 250 | 7 |
| 2026-06-20 00:00:00 | UFC Fight Night: Kape vs. Horiguchi | 12 |
| 2026-06-27 00:00:00 | UFC Fight Night: Fiziev vs. Torres | 13 |
| 2026-07-11 00:00:00 | UFC 329: McGregor vs. Holloway 2 | 14 |
| 2026-07-18 00:00:00 | UFC Fight Night: Du Plessis vs. Usman | 12 |
| 2026-07-25 00:00:00 | UFC Fight Night: Ankalaev vs. Guskov | 12 |
| 2026-08-01 00:00:00 | UFC Fight Night: Medic vs. Rodriguez | 14 |
| 2026-08-08 00:00:00 | UFC Fight Night: Gamrot vs. Salkilld | 12 |
