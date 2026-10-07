from __future__ import annotations

import pandas as pd
import pytest

from mma_v4.identity import (
    apply_canonical_names,
    build_canonical_map,
    normalize_loose,
    scan_fuzzy_candidates,
    scan_suffix_candidates,
    token_set_key,
)


# ---------------------------------------------------------------------------
# normalize_loose / token_set_key unit behavior
# ---------------------------------------------------------------------------


def test_normalize_loose_strips_accents_punctuation_and_case() -> None:
    assert normalize_loose("Kauê Fernandes") == normalize_loose("Kaue Fernandes")
    assert normalize_loose("J.J. Aldrich") == normalize_loose("JJ Aldrich")
    assert normalize_loose("Chan-Mi Jeon") == normalize_loose("Chanmi Jeon")
    assert normalize_loose("Klaudia Syguła") == normalize_loose("Klaudia Sygula")


def test_normalize_loose_does_not_strip_generational_suffix() -> None:
    # Deliberate: suffix stripping is NOT part of the safe deterministic tier (see
    # scan_suffix_candidates) because "X" vs "X Jr." can denote two distinct real people.
    assert normalize_loose("Lance Gibson") != normalize_loose("Lance Gibson Jr.")


def test_token_set_key_is_order_independent() -> None:
    assert token_set_key("Song Yadong") == token_set_key("Yadong Song")
    assert token_set_key("Zhang Weili") == token_set_key("Weili Zhang")


def test_token_set_key_single_token_names_do_not_collide() -> None:
    assert token_set_key("Rongzhu") != token_set_key("Rong Zhu")


# ---------------------------------------------------------------------------
# build_canonical_map: known aliases resolve to the same canonical identity
# ---------------------------------------------------------------------------


def _fights_frame(rows: list[tuple[str, str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["fight_date", "fighter_a_name", "fighter_b_name", "winner_name"])


@pytest.mark.parametrize(
    "name_a,name_b",
    [
        ("Kauê Fernandes", "Kaue Fernandes"),
        ("Yadong Song", "Song Yadong"),
        ("J.J. Aldrich", "JJ Aldrich"),
        ("Zhang Weili", "Weili Zhang"),
    ],
)
def test_known_deterministic_aliases_resolve_to_same_canonical_id(name_a: str, name_b: str) -> None:
    fights = _fights_frame(
        [
            ("2020-01-01", name_a, "Opponent One", name_a),
            ("2021-01-01", name_b, "Opponent Two", "Opponent Two"),
        ]
    )
    canonical_map, _ = build_canonical_map(fights["fighter_a_name"], fights["fighter_b_name"], fights["fight_date"])
    assert canonical_map[name_a] == canonical_map[name_b]


def test_project_alias_table_resolves_transliteration_variants() -> None:
    # Uses the actual reviewed alias table shipped in the repo (data/identity_aliases.csv),
    # not a synthetic one -- this is the real config used by build_v4_fighter_state.py.
    from mma_v4.paths import DATA_DIR

    alias_path = DATA_DIR / "identity_aliases.csv"
    assert alias_path.exists(), "data/identity_aliases.csv must exist"
    fights = _fights_frame(
        [
            ("2020-01-01", "Sergey Pavlovich", "Ghost Opponent", ""),
            ("2020-06-01", "Sergei Pavlovich", "Real Opponent", "Sergei Pavlovich"),
            ("2021-01-01", "Asu Almabaev", "Ghost Opponent", ""),
            ("2021-06-01", "Asu Almabayev", "Real Opponent", "Asu Almabayev"),
            ("2022-01-01", "Elves Brenner", "Ghost Opponent", ""),
            ("2022-06-01", "Elves Brener", "Real Opponent", "Elves Brener"),
        ]
    )
    canonical_map, _ = build_canonical_map(fights["fighter_a_name"], fights["fighter_b_name"], fights["fight_date"], alias_path=alias_path)
    assert canonical_map["Sergey Pavlovich"] == canonical_map["Sergei Pavlovich"]
    assert canonical_map["Asu Almabaev"] == canonical_map["Asu Almabayev"]
    assert canonical_map["Elves Brenner"] == canonical_map["Elves Brener"]


def test_sergey_sergei_requires_alias_table(tmp_path) -> None:
    fights = _fights_frame(
        [
            ("2020-01-01", "Sergey Pavlovich", "Ghost Opponent", ""),
            ("2020-06-01", "Sergei Pavlovich", "Real Opponent", "Sergei Pavlovich"),
        ]
    )
    # Without the alias table, these do NOT merge (not caught by deterministic rules alone).
    canonical_map_no_alias, _ = build_canonical_map(fights["fighter_a_name"], fights["fighter_b_name"], fights["fight_date"])
    assert canonical_map_no_alias["Sergey Pavlovich"] != canonical_map_no_alias["Sergei Pavlovich"]

    alias_path = tmp_path / "aliases.csv"
    pd.DataFrame([{"raw_name": "Sergey Pavlovich", "canonical_name": "Sergei Pavlovich", "reason": "test"}]).to_csv(alias_path, index=False)
    canonical_map, _ = build_canonical_map(fights["fighter_a_name"], fights["fighter_b_name"], fights["fight_date"], alias_path=alias_path)
    assert canonical_map["Sergey Pavlovich"] == canonical_map["Sergei Pavlovich"]


# ---------------------------------------------------------------------------
# Safety: do not merge genuinely different people
# ---------------------------------------------------------------------------


def test_similar_but_distinct_names_do_not_auto_merge() -> None:
    # Synthetic adversarial pair: two edit-distance-2-close names with no shared evidence.
    # A famous, well-documented real-world instance of this exact risk: "Aldo Pereira" vs
    # "Alex Pereira" (the UFC champion) -- confirmed via this repo's own fight log to be two
    # different people (their fight dates/opponents do not overlap or corroborate).
    fights = _fights_frame(
        [
            ("2010-01-01", "Firstname Lastname", "Opponent A", "Firstname Lastname"),
            ("2022-01-01", "Firstnam Lastname", "Opponent B", "Opponent B"),
        ]
    )
    canonical_map, _ = build_canonical_map(fights["fighter_a_name"], fights["fighter_b_name"], fights["fight_date"])
    assert canonical_map["Firstname Lastname"] != canonical_map["Firstnam Lastname"]


def test_generational_suffix_pair_does_not_auto_merge_without_verification() -> None:
    # A large date gap between "X" and "X Jr." (e.g. 25 years) is exactly the father/son
    # pattern that must NOT be silently merged by a blanket suffix-stripping rule.
    fights = _fights_frame(
        [
            ("2000-03-10", "Lance Gibson", "Opponent A", "Lance Gibson"),
            ("2025-12-14", "Lance Gibson Jr.", "Opponent B", "Opponent B"),
        ]
    )
    canonical_map, _ = build_canonical_map(fights["fighter_a_name"], fights["fighter_b_name"], fights["fight_date"])
    assert canonical_map["Lance Gibson"] != canonical_map["Lance Gibson Jr."]


# ---------------------------------------------------------------------------
# Split-history merge: canonical name/id resolution and downstream fight-count union
# ---------------------------------------------------------------------------


def test_split_history_duplicate_merges_to_one_continuous_identity() -> None:
    # Both spellings have real, nonzero fight history (the "Weili Zhang"/"Zhang Weili" pattern)
    # -- the fix must unify them, not just discard the smaller side.
    fights = _fights_frame(
        [
            ("2018-01-01", "Weili Zhang", "Opp 1", "Weili Zhang"),
            ("2019-01-01", "Weili Zhang", "Opp 2", "Weili Zhang"),
            ("2020-01-01", "Zhang Weili", "Opp 3", "Zhang Weili"),
            ("2021-01-01", "Zhang Weili", "Opp 4", "Zhang Weili"),
            ("2022-01-01", "Zhang Weili", "Opp 5", "Zhang Weili"),
        ]
    )
    canonical_map, audit = build_canonical_map(fights["fighter_a_name"], fights["fighter_b_name"], fights["fight_date"])
    canonical = canonical_map["Weili Zhang"]
    assert canonical == canonical_map["Zhang Weili"]
    # Canonical name preference: more appearances wins (3 "Zhang Weili" > 2 "Weili Zhang").
    assert canonical == "Zhang Weili"
    resolved = apply_canonical_names(fights, canonical_map)
    total_appearances = (resolved["fighter_a_name"] == canonical).sum() + (resolved["fighter_b_name"] == canonical).sum()
    assert total_appearances == 5


def test_apply_canonical_names_also_remaps_winner_name() -> None:
    fights = _fights_frame([("2020-01-01", "Kauê Fernandes", "Opponent", "Kauê Fernandes")])
    canonical_map, _ = build_canonical_map(fights["fighter_a_name"], fights["fighter_b_name"], fights["fight_date"])
    resolved = apply_canonical_names(fights, canonical_map)
    assert resolved.loc[0, "winner_name"] == resolved.loc[0, "fighter_a_name"]


# ---------------------------------------------------------------------------
# Candidate scanners (review-only, never auto-applied)
# ---------------------------------------------------------------------------


def test_scan_fuzzy_candidates_only_pairs_ghosts_against_reals() -> None:
    candidates = scan_fuzzy_candidates(
        ghost_names=["Sergey Pavlovich"], real_names=["Sergei Pavlovich", "Unrelated Fighter"], max_distance=2
    )
    assert list(candidates["ghost_name"]) == ["Sergey Pavlovich"]
    assert list(candidates["real_name"]) == ["Sergei Pavlovich"]


def test_scan_suffix_candidates_finds_unresolved_suffix_pairs() -> None:
    candidates = scan_suffix_candidates(["Levi Rodrigues", "Levi Rodrigues Jr.", "Unrelated Fighter"])
    pairs = set(zip(candidates["name_a"], candidates["name_b"]))
    assert ("Levi Rodrigues", "Levi Rodrigues Jr.") in pairs
