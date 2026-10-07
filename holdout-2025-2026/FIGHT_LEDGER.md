# Fight Ledger (2025-2026)

Every completed UFC fight from 2025-01-11 through 2026-08-08 used in this holdout: **835 fights across 68 events** (513 in 2025, 322 in 2026). No scheduled/future fights are included -- this ledger contains only fights with a completed, known result.

- 603 of 835 fights (72.2%) have a matched historical moneyline odds record; the rest have no usable odds match and are excluded from every market-comparison and betting metric (but are still included in the model/Elo accuracy numbers).
- Box-score data provenance: fights through 2026-03-28 come from a user-supplied file reconstructed from the public `Greco1899/scrape_ufc_stats` UFCStats mirror (not scraped directly from ufcstats.com by this session); fights from 2026-04-04 onward come from a prior session's direct ufcstats.com scrape, independently verified. See `DATA_AUDIT.md` for the full reconciliation and corruption-fix accounting.
- Odds timing (opening/closing/snapshot) is **UNKNOWN** -- see `LIMITATIONS.md`. Every betting number in this deliverable is a historical backtest, not a claim of deployable, real-time executable ROI.

## Events

| date | event | fights |
| --- | --- | ---: |
| 2025-01-11 | UFC Fight Night: Dern vs. Ribas 2 | 14 |
| 2025-01-18 | UFC 311: Makhachev vs. Moicano | 13 |
| 2025-02-01 | UFC Fight Night: Adesanya vs. Imavov | 11 |
| 2025-02-08 | UFC 312: Du Plessis vs. Strickland 2 | 11 |
| 2025-02-15 | UFC Fight Night: Cannonier vs. Rodrigues | 12 |
| 2025-02-22 | UFC Fight Night: Cejudo vs. Song | 12 |
| 2025-03-01 | UFC Fight Night: Kape vs. Almabayev | 10 |
| 2025-03-08 | UFC 313: Pereira vs. Ankalaev | 10 |
| 2025-03-15 | UFC Fight Night: Vettori vs. Dolidze 2 | 13 |
| 2025-03-22 | UFC Fight Night: Edwards vs. Brady | 13 |
| 2025-03-29 | UFC Fight Night: Moreno vs. Erceg | 12 |
| 2025-04-05 | UFC Fight Night: Emmett vs. Murphy | 12 |
| 2025-04-12 | UFC 314: Volkanovski vs. Lopes | 13 |
| 2025-04-26 | UFC Fight Night: Machado Garry vs. Prates | 14 |
| 2025-05-03 | UFC Fight Night: Sandhagen vs. Figueiredo | 12 |
| 2025-05-10 | UFC 315: Muhammad vs. Della Maddalena | 12 |
| 2025-05-17 | UFC Fight Night: Burns vs. Morales | 11 |
| 2025-05-31 | UFC Fight Night: Blanchfield vs. Barber | 9 |
| 2025-06-07 | UFC 316: Dvalishvili vs. O'Malley 2 | 13 |
| 2025-06-14 | UFC Fight Night: Usman vs. Buckley | 11 |
| 2025-06-21 | UFC Fight Night: Hill vs. Rountree Jr. | 12 |
| 2025-06-28 | UFC 317: Topuria vs. Oliveira | 11 |
| 2025-07-12 | UFC Fight Night: Lewis vs. Teixeira | 12 |
| 2025-07-19 | UFC 318: Holloway vs. Poirier 3 | 14 |
| 2025-07-26 | UFC Fight Night: Whittaker vs. De Ridder | 12 |
| 2025-08-02 | UFC Fight Night: Taira vs. Park | 12 |
| 2025-08-09 | UFC Fight Night: Dolidze vs. Hernandez | 12 |
| 2025-08-16 | UFC 319: Du Plessis vs. Chimaev | 12 |
| 2025-08-23 | UFC Fight Night: Walker vs. Zhang | 12 |
| 2025-09-06 | UFC Fight Night: Imavov vs. Borralho | 13 |
| 2025-09-13 | Noche UFC: Lopes vs. Silva | 13 |
| 2025-09-27 | UFC Fight Night: Ulberg vs. Reyes | 12 |
| 2025-10-04 | UFC 320: Ankalaev vs. Pereira 2 | 14 |
| 2025-10-11 | UFC Fight Night: Oliveira vs. Gamrot | 12 |
| 2025-10-18 | UFC Fight Night: De Ridder vs. Allen | 13 |
| 2025-10-25 | UFC 321: Aspinall vs. Gane | 12 |
| 2025-11-01 | UFC Fight Night: Garcia vs. Onama | 13 |
| 2025-11-08 | UFC Fight Night: Bonfim vs. Brown | 12 |
| 2025-11-15 | UFC 322: Della Maddalena vs. Makhachev | 14 |
| 2025-11-22 | UFC Fight Night: Tsarukyan vs. Hooker | 14 |
| 2025-12-06 | UFC 323: Dvalishvili vs. Yan 2 | 13 |
| 2025-12-13 | UFC Fight Night: Royval vs. Kape | 11 |
| 2026-01-24 | UFC 324: Gaethje vs. Pimblett | 11 |
| 2026-01-31 | UFC 325: Volkanovski vs. Lopes 2 | 13 |
| 2026-02-07 | UFC Fight Night: Bautista vs. Oliveira | 13 |
| 2026-02-21 | UFC Fight Night: Strickland vs. Hernandez | 14 |
| 2026-02-28 | UFC Fight Night: Moreno vs. Kavanagh | 13 |
| 2026-03-07 | UFC 326: Holloway vs. Oliveira 2 | 12 |
| 2026-03-14 | UFC Fight Night: Emmett vs. Vallejos | 14 |
| 2026-03-21 | UFC Fight Night: Evloev vs. Murphy | 13 |
| 2026-03-28 | UFC Fight Night: Adesanya vs. Pyfer | 12 |
| 2026-04-04 | UFC Fight Night: Moicano vs. Duncan | 13 |
| 2026-04-11 | UFC 327: Prochazka vs. Ulberg | 11 |
| 2026-04-18 | UFC Fight Night: Burns vs. Malott | 11 |
| 2026-04-25 | UFC Fight Night: Sterling vs. Zalal | 13 |
| 2026-05-02 | UFC Fight Night: Della Maddalena vs. Prates | 13 |
| 2026-05-09 | UFC 328: Chimaev vs. Strickland | 13 |
| 2026-05-16 | UFC Fight Night: Allen vs. Costa | 13 |
| 2026-05-30 | UFC Fight Night: Song vs. Figueiredo | 12 |
| 2026-06-06 | UFC Fight Night: Muhammad vs. Bonfim | 12 |
| 2026-06-14 | UFC Freedom 250 | 7 |
| 2026-06-20 | UFC Fight Night: Kape vs. Horiguchi | 12 |
| 2026-06-27 | UFC Fight Night: Fiziev vs. Torres | 13 |
| 2026-07-11 | UFC 329: McGregor vs. Holloway 2 | 14 |
| 2026-07-18 | UFC Fight Night: Du Plessis vs. Usman | 12 |
| 2026-07-25 | UFC Fight Night: Ankalaev vs. Guskov | 12 |
| 2026-08-01 | UFC Fight Night: Medic vs. Rodriguez | 14 |
| 2026-08-08 | UFC Fight Night: Gamrot vs. Salkilld | 12 |
