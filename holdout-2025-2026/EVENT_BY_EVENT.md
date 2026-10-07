# Event-by-Event Performance (Part 15)

All 68 UFC events replayed, in chronological order, no cards excluded or cherry-picked.
Model and Elo accuracy are computed on every fight in the event (primary seed 1701);
market accuracy is computed only on the subset of that event's fights with a matched
odds record (`n/a` where no fight on that event had usable odds -- market/odds
coverage for this holdout stops matching after March 2026, see `LIMITATIONS.md`).
Cumulative columns are running totals over every event so far, in order.

## Summary

- **68 events**, 835 fights, 2025-01-11 through 2026-08-08 -- **the latest UFC event
  with complete, verified box-score data**, not August 15 or August 18. UFC 330
  (2026-08-15) was checked for inclusion and excluded because no box scores for it
  exist anywhere in the repository; see `LIMITATIONS.md` and `DATA_AUDIT.md`.
- Model accuracy beat market accuracy on **15 events**, lost on **28**, tied on **8**;
  the remaining **17** events had no matched-odds fights to compare against.
- Best event: **UFC Fight Night: Evloev vs. Murphy** (2026-03-21), 84.6% (11/13).
- Worst event: **UFC Fight Night: Song vs. Figueiredo** (2026-05-30), 25.0% (3/12).
- Final cumulative accuracy after all 68 events: 60.60% (primary seed); cumulative log
  loss 0.6545.
- No individual event is used as a performance claim -- 9-14 fights is too small a
  sample to be meaningful on its own; only the full 835-fight aggregate and
  year-level breakdowns are used that way.

## Full event-by-event table

| Event | Date | Fights | Model correct | Model accuracy | Elo accuracy | Market accuracy | Cumulative accuracy | Cumulative log loss |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| UFC Fight Night: Dern vs. Ribas 2 | 2025-01-11 | 14 | 6 | 42.9% | 50.0% | 64.3% | 42.86% | 0.7475 |
| UFC 311: Makhachev vs. Moicano | 2025-01-18 | 13 | 8 | 61.5% | 46.2% | 53.8% | 51.85% | 0.6901 |
| UFC Fight Night: Adesanya vs. Imavov | 2025-02-01 | 11 | 7 | 63.6% | 54.5% | 54.5% | 55.26% | 0.6690 |
| UFC 312: Du Plessis vs. Strickland 2 | 2025-02-08 | 11 | 6 | 54.5% | 45.5% | 60.0% | 55.10% | 0.6706 |
| UFC Fight Night: Cannonier vs. Rodrigues | 2025-02-15 | 12 | 9 | 75.0% | 66.7% | 75.0% | 59.02% | 0.6652 |
| UFC Fight Night: Cejudo vs. Song | 2025-02-22 | 12 | 9 | 75.0% | 66.7% | 60.0% | 61.64% | 0.6524 |
| UFC Fight Night: Kape vs. Almabayev | 2025-03-01 | 10 | 4 | 40.0% | 60.0% | 60.0% | 59.04% | 0.6633 |
| UFC 313: Pereira vs. Ankalaev | 2025-03-08 | 10 | 8 | 80.0% | 70.0% | 55.6% | 61.29% | 0.6596 |
| UFC Fight Night: Vettori vs. Dolidze 2 | 2025-03-15 | 13 | 8 | 61.5% | 53.8% | 50.0% | 61.32% | 0.6629 |
| UFC Fight Night: Edwards vs. Brady | 2025-03-22 | 13 | 8 | 61.5% | 46.2% | 46.2% | 61.34% | 0.6645 |
| UFC Fight Night: Moreno vs. Erceg | 2025-03-29 | 12 | 8 | 66.7% | 66.7% | 83.3% | 61.83% | 0.6623 |
| UFC Fight Night: Emmett vs. Murphy | 2025-04-05 | 12 | 10 | 83.3% | 66.7% | 66.7% | 63.64% | 0.6574 |
| UFC 314: Volkanovski vs. Lopes | 2025-04-12 | 13 | 9 | 69.2% | 38.5% | 84.6% | 64.10% | 0.6555 |
| UFC Fight Night: Machado Garry vs. Prates | 2025-04-26 | 14 | 6 | 42.9% | 42.9% | 92.9% | 62.35% | 0.6607 |
| UFC Fight Night: Sandhagen vs. Figueiredo | 2025-05-03 | 12 | 8 | 66.7% | 41.7% | 58.3% | 62.64% | 0.6573 |
| UFC 315: Muhammad vs. Della Maddalena | 2025-05-10 | 12 | 7 | 58.3% | 58.3% | 58.3% | 62.37% | 0.6595 |
| UFC Fight Night: Burns vs. Morales | 2025-05-17 | 11 | 9 | 81.8% | 45.5% | 90.0% | 63.41% | 0.6551 |
| UFC Fight Night: Blanchfield vs. Barber | 2025-05-31 | 9 | 5 | 55.6% | 55.6% | 66.7% | 63.08% | 0.6578 |
| UFC 316: Dvalishvili vs. O'Malley 2 | 2025-06-07 | 13 | 9 | 69.2% | 61.5% | 83.3% | 63.44% | 0.6541 |
| UFC Fight Night: Usman vs. Buckley | 2025-06-14 | 11 | 6 | 54.5% | 63.6% | 72.7% | 63.03% | 0.6516 |
| UFC Fight Night: Hill vs. Rountree Jr. | 2025-06-21 | 12 | 6 | 50.0% | 50.0% | 50.0% | 62.40% | 0.6537 |
| UFC 317: Topuria vs. Oliveira | 2025-06-28 | 11 | 7 | 63.6% | 63.6% | 90.9% | 62.45% | 0.6525 |
| UFC Fight Night: Lewis vs. Teixeira | 2025-07-12 | 12 | 8 | 66.7% | 58.3% | 66.7% | 62.64% | 0.6504 |
| UFC 318: Holloway vs. Poirier 3 | 2025-07-19 | 14 | 10 | 71.4% | 64.3% | 100.0% | 63.07% | 0.6511 |
| UFC Fight Night: Whittaker vs. De Ridder | 2025-07-26 | 12 | 9 | 75.0% | 66.7% | 41.7% | 63.55% | 0.6495 |
| UFC Fight Night: Taira vs. Park | 2025-08-02 | 12 | 6 | 50.0% | 66.7% | 83.3% | 63.02% | 0.6521 |
| UFC Fight Night: Dolidze vs. Hernandez | 2025-08-09 | 12 | 10 | 83.3% | 75.0% | 81.8% | 63.78% | 0.6502 |
| UFC 319: Du Plessis vs. Chimaev | 2025-08-16 | 12 | 8 | 66.7% | 41.7% | 58.3% | 63.88% | 0.6497 |
| UFC Fight Night: Walker vs. Zhang | 2025-08-23 | 12 | 6 | 50.0% | 58.3% | 63.6% | 63.40% | 0.6512 |
| UFC Fight Night: Imavov vs. Borralho | 2025-09-06 | 13 | 10 | 76.9% | 61.5% | 53.8% | 63.89% | 0.6485 |
| Noche UFC: Lopes vs. Silva | 2025-09-13 | 13 | 5 | 38.5% | 30.8% | 46.2% | 63.00% | 0.6517 |
| UFC Fight Night: Ulberg vs. Reyes | 2025-09-27 | 12 | 6 | 50.0% | 66.7% | 75.0% | 62.60% | 0.6532 |
| UFC 320: Ankalaev vs. Pereira 2 | 2025-10-04 | 14 | 10 | 71.4% | 64.3% | 71.4% | 62.91% | 0.6511 |
| UFC Fight Night: Oliveira vs. Gamrot | 2025-10-11 | 12 | 5 | 41.7% | 41.7% | 66.7% | 62.29% | 0.6537 |
| UFC Fight Night: De Ridder vs. Allen | 2025-10-18 | 13 | 5 | 38.5% | 46.2% | 53.8% | 61.56% | 0.6563 |
| UFC 321: Aspinall vs. Gane | 2025-10-25 | 12 | 4 | 33.3% | 50.0% | 58.3% | 60.78% | 0.6597 |
| UFC Fight Night: Garcia vs. Onama | 2025-11-01 | 13 | 7 | 53.8% | 69.2% | 83.3% | 60.58% | 0.6588 |
| UFC Fight Night: Bonfim vs. Brown | 2025-11-08 | 12 | 10 | 83.3% | 58.3% | 75.0% | 61.17% | 0.6565 |
| UFC 322: Della Maddalena vs. Makhachev | 2025-11-15 | 14 | 8 | 57.1% | 57.1% | 85.7% | 61.05% | 0.6562 |
| UFC Fight Night: Tsarukyan vs. Hooker | 2025-11-22 | 14 | 9 | 64.3% | 64.3% | 84.6% | 61.15% | 0.6547 |
| UFC 323: Dvalishvili vs. Yan 2 | 2025-12-06 | 13 | 7 | 53.8% | 38.5% | 69.2% | 60.96% | 0.6565 |
| UFC Fight Night: Royval vs. Kape | 2025-12-13 | 11 | 3 | 27.3% | 54.5% | 90.0% | 60.23% | 0.6579 |
| UFC 324: Gaethje vs. Pimblett | 2026-01-24 | 11 | 8 | 72.7% | 36.4% | 70.0% | 60.50% | 0.6574 |
| UFC 325: Volkanovski vs. Lopes 2 | 2026-01-31 | 13 | 9 | 69.2% | 53.8% | 69.2% | 60.71% | 0.6558 |
| UFC Fight Night: Bautista vs. Oliveira | 2026-02-07 | 13 | 6 | 46.2% | 61.5% | 84.6% | 60.36% | 0.6572 |
| UFC Fight Night: Strickland vs. Hernandez | 2026-02-21 | 14 | 11 | 78.6% | 64.3% | 71.4% | 60.82% | 0.6557 |
| UFC Fight Night: Moreno vs. Kavanagh | 2026-02-28 | 13 | 9 | 69.2% | 69.2% | 76.9% | 61.01% | 0.6543 |
| UFC 326: Holloway vs. Oliveira 2 | 2026-03-07 | 12 | 7 | 58.3% | 66.7% | 72.7% | 60.95% | 0.6537 |
| UFC Fight Night: Emmett vs. Vallejos | 2026-03-14 | 14 | 10 | 71.4% | 57.1% | 92.9% | 61.19% | 0.6525 |
| UFC Fight Night: Evloev vs. Murphy | 2026-03-21 | 13 | 11 | 84.6% | 76.9% | 84.6% | 61.69% | 0.6490 |
| UFC Fight Night: Adesanya vs. Pyfer | 2026-03-28 | 12 | 7 | 58.3% | 41.7% | 58.3% | 61.62% | 0.6498 |
| UFC Fight Night: Moicano vs. Duncan | 2026-04-04 | 13 | 8 | 61.5% | 53.8% | n/a | 61.62% | 0.6510 |
| UFC 327: Prochazka vs. Ulberg | 2026-04-11 | 11 | 7 | 63.6% | 63.6% | n/a | 61.66% | 0.6504 |
| UFC Fight Night: Burns vs. Malott | 2026-04-18 | 11 | 4 | 36.4% | 45.5% | n/a | 61.24% | 0.6519 |
| UFC Fight Night: Sterling vs. Zalal | 2026-04-25 | 13 | 9 | 69.2% | 38.5% | n/a | 61.39% | 0.6522 |
| UFC Fight Night: Della Maddalena vs. Prates | 2026-05-02 | 13 | 5 | 38.5% | 46.2% | n/a | 60.96% | 0.6534 |
| UFC 328: Chimaev vs. Strickland | 2026-05-09 | 13 | 8 | 61.5% | 76.9% | n/a | 60.97% | 0.6537 |
| UFC Fight Night: Allen vs. Costa | 2026-05-16 | 13 | 6 | 46.2% | 38.5% | n/a | 60.70% | 0.6561 |
| UFC Fight Night: Song vs. Figueiredo | 2026-05-30 | 12 | 3 | 25.0% | 41.7% | n/a | 60.11% | 0.6577 |
| UFC Fight Night: Muhammad vs. Bonfim | 2026-06-06 | 12 | 10 | 83.3% | 83.3% | n/a | 60.49% | 0.6561 |
| UFC Freedom 250 | 2026-06-14 | 7 | 3 | 42.9% | 57.1% | n/a | 60.32% | 0.6561 |
| UFC Fight Night: Kape vs. Horiguchi | 2026-06-20 | 12 | 6 | 50.0% | 58.3% | n/a | 60.16% | 0.6572 |
| UFC Fight Night: Fiziev vs. Torres | 2026-06-27 | 13 | 9 | 69.2% | 61.5% | n/a | 60.31% | 0.6567 |
| UFC 329: McGregor vs. Holloway 2 | 2026-07-11 | 14 | 8 | 57.1% | 71.4% | n/a | 60.25% | 0.6568 |
| UFC Fight Night: Du Plessis vs. Usman | 2026-07-18 | 12 | 8 | 66.7% | 66.7% | n/a | 60.35% | 0.6562 |
| UFC Fight Night: Ankalaev vs. Guskov | 2026-07-25 | 12 | 7 | 58.3% | 58.3% | n/a | 60.32% | 0.6567 |
| UFC Fight Night: Medic vs. Rodriguez | 2026-08-01 | 14 | 9 | 64.3% | 50.0% | n/a | 60.39% | 0.6559 |
| UFC Fight Night: Gamrot vs. Salkilld | 2026-08-08 | 12 | 9 | 75.0% | 58.3% | n/a | 60.60% | 0.6545 |