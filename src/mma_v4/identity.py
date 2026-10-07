from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd


# Characters NFKD does not decompose (a distinct base letter + stroke/ligature, not a
# combining accent) -- verified empirically: unicodedata.normalize("NFKD", "ł") == "ł".
_EXTRA_CHAR_MAP = {
    "ł": "l", "Ł": "L",
    "ø": "o", "Ø": "O",
    "đ": "d", "Đ": "D",
    "æ": "ae", "Æ": "AE",
    "œ": "oe", "Œ": "OE",
    "ß": "ss",
}

_SUFFIX_RE = re.compile(r"[,\s]+(jr|sr|ii|iii|iv)\.?\s*$", re.IGNORECASE)


def strip_accents(value: str) -> str:
    for src, dst in _EXTRA_CHAR_MAP.items():
        value = value.replace(src, dst)
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


def normalize_loose(name: Any) -> str:
    """Deterministic identity key: strips diacritics, punctuation, and whitespace, then
    lowercases. Two raw names sharing this key are treated as the same person -- an EXACT
    match after a documented, reversible, information-preserving transformation, never a
    similarity score. Catches accent variants (Kaue/Kauê) and punctuation variants (J.J./JJ).

    Deliberately does NOT strip generational suffixes (Jr./Sr./II/III/IV): father-and-son
    pairs who are both real, distinct fighters are a genuine phenomenon in combat sports, so
    "X" vs "X Jr." is NOT treated as a safe deterministic match -- it requires the same
    individual-verification-and-alias-table process as a transliteration variant (see
    `scan_suffix_candidates`), not a blanket auto-merge."""
    s = strip_accents(str(name).strip()).lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def token_set_key(name: Any) -> tuple[str, ...]:
    """Order-independent identity key: same normalization as `normalize_loose` (suffix NOT
    stripped -- see its docstring), tokenized and sorted. Catches family-name-first vs.
    given-name-first recording inconsistency (e.g. "Song Yadong" vs "Yadong Song").
    Single-token names return a 1-tuple and are not eligible for order-swap matching (nothing
    to reorder)."""
    s = strip_accents(str(name).strip()).lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return tuple(sorted(t for t in s.split() if t))


def scan_suffix_candidates(names: list[str]) -> pd.DataFrame:
    """Candidate pairs differing only by a generational suffix (Jr./Sr./II/III/IV) after
    `normalize_loose`. Like `scan_fuzzy_candidates`, this is a review list, not an auto-merge:
    it is left to individual verification (and the alias table) because the suffix can denote
    a genuinely different second person (father/son), not just an inconsistently-recorded
    name."""
    keyed: dict[str, list[str]] = {}
    for n in names:
        base = _SUFFIX_RE.sub("", str(n).strip())
        keyed.setdefault(normalize_loose(base), []).append(n)
    rows = []
    for base_key, members in keyed.items():
        if len(members) > 1:
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    rows.append({"name_a": members[i], "name_b": members[j]})
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["name_a", "name_b"])


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1]


def scan_fuzzy_candidates(
    ghost_names: list[str], real_names: list[str], max_distance: int = 2
) -> pd.DataFrame:
    """Restricted fuzzy scan: only pairs a zero-history "ghost" name against a real
    (fight_count > 0) name, edit distance <= max_distance on the `normalize_loose` key,
    excluding pairs already resolved by `normalize_loose`/`token_set_key` exact matching.
    This is a CANDIDATE list for manual review -- nothing here is auto-merged. Restricting to
    ghost-vs-real pairs is a deliberate safety gate: it prevents two distinct real people
    (each with their own genuine fight history) from ever being fuzzy-matched together, which
    is the failure mode that would actually corrupt a real fighter's record."""
    from collections import defaultdict

    buckets: dict[str, list[str]] = defaultdict(list)
    for name in real_names:
        key = normalize_loose(name)
        buckets[key[:2] if len(key) >= 2 else key].append(name)

    rows = []
    for gname in ghost_names:
        gkey = normalize_loose(gname)
        prefix = gkey[:2] if len(gkey) >= 2 else gkey
        for rname in buckets.get(prefix, []):
            rkey = normalize_loose(rname)
            if rkey == gkey or abs(len(rkey) - len(gkey)) > max_distance:
                continue
            distance = levenshtein(gkey, rkey)
            if distance <= max_distance:
                rows.append({"ghost_name": gname, "real_name": rname, "edit_distance": distance})
    return pd.DataFrame(rows).sort_values("edit_distance") if rows else pd.DataFrame(
        columns=["ghost_name", "real_name", "edit_distance"]
    )


def load_alias_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["raw_name", "canonical_name", "reason"])
    return pd.read_csv(path)


def build_canonical_map(
    fighter_a_names: pd.Series,
    fighter_b_names: pd.Series,
    fight_dates: pd.Series,
    alias_path: Path | None = None,
) -> tuple[dict[str, str], pd.DataFrame]:
    """Build a raw-name -> canonical-name map from the full name universe in the raw fight
    data, using ONLY deterministic rules (`normalize_loose`, `token_set_key`) plus an explicit,
    human-reviewed alias table -- never a live fuzzy/edit-distance auto-merge. Returns the map
    and an audit DataFrame (one row per raw name) recording each name's canonical resolution,
    the merge reason, and the size of its identity group.
    """
    names = pd.concat([fighter_a_names, fighter_b_names], ignore_index=True).map(lambda v: str(v).strip())
    dates = pd.concat([fight_dates, fight_dates], ignore_index=True)
    distinct = sorted(n for n in names.unique() if n)

    appearance_count = names.value_counts().to_dict()
    last_seen = pd.DataFrame({"name": names, "date": dates}).groupby("name")["date"].max().to_dict()

    uf = _UnionFind()
    for n in distinct:
        uf.find(n)

    merge_reason: dict[str, str] = {}

    loose_groups: dict[str, list[str]] = {}
    token_groups: dict[tuple[str, ...], list[str]] = {}
    for n in distinct:
        loose_groups.setdefault(normalize_loose(n), []).append(n)
        tok = token_set_key(n)
        if len(tok) > 1:
            token_groups.setdefault(tok, []).append(n)

    for members in loose_groups.values():
        if len(members) > 1:
            for m in members[1:]:
                uf.union(members[0], m)
                merge_reason[m] = merge_reason.get(m, "accent_or_punctuation_normalization")
                merge_reason[members[0]] = merge_reason.get(members[0], "accent_or_punctuation_normalization")

    for members in token_groups.values():
        if len(members) > 1:
            for m in members[1:]:
                uf.union(members[0], m)
                merge_reason[m] = merge_reason.get(m, "token_order_swap")
                merge_reason[members[0]] = merge_reason.get(members[0], "token_order_swap")

    alias_df = load_alias_table(alias_path) if alias_path else pd.DataFrame(columns=["raw_name", "canonical_name", "reason"])
    for _, row in alias_df.iterrows():
        raw, canon = str(row["raw_name"]).strip(), str(row["canonical_name"]).strip()
        if raw not in distinct and canon not in distinct:
            continue
        uf.find(raw)
        uf.find(canon)
        uf.union(raw, canon)
        merge_reason[raw] = f"manual_alias: {row.get('reason', '')}"
        merge_reason[canon] = merge_reason.get(canon, f"manual_alias: {row.get('reason', '')}")

    groups: dict[str, list[str]] = {}
    for n in distinct:
        root = uf.find(n)
        groups.setdefault(root, []).append(n)

    canonical_map: dict[str, str] = {}
    audit_rows: list[dict[str, Any]] = []
    alias_canonical_override = {str(r["raw_name"]).strip(): str(r["canonical_name"]).strip() for _, r in alias_df.iterrows()}
    for root, members in groups.items():
        forced = next((alias_canonical_override[m] for m in members if m in alias_canonical_override), None)
        if forced is not None and forced in members:
            canonical = forced
        else:
            canonical = max(
                members,
                key=lambda m: (appearance_count.get(m, 0), str(last_seen.get(m, "")), any(ord(c) > 127 for c in m)),
            )
        for m in members:
            canonical_map[m] = canonical
            audit_rows.append(
                {
                    "raw_name": m,
                    "canonical_name": canonical,
                    "group_size": len(members),
                    "merged": len(members) > 1,
                    "reason": merge_reason.get(m, "no_merge_needed") if len(members) > 1 else "",
                    "appearance_count": appearance_count.get(m, 0),
                    "last_seen_date": last_seen.get(m, ""),
                }
            )
    audit = pd.DataFrame(audit_rows).sort_values(["group_size", "canonical_name", "raw_name"], ascending=[False, True, True])
    return canonical_map, audit


def apply_canonical_names(fights: pd.DataFrame, canonical_map: dict[str, str]) -> pd.DataFrame:
    """Rewrite fighter_a_name/fighter_b_name/winner_name to canonical identities. winner_name
    is remapped too since `core.winner_score` compares it against fighter_a_name/fighter_b_name
    by string equality -- leaving it unmapped would silently break winner detection for any
    fight whose winner was recorded under a non-canonical name spelling."""
    out = fights.copy()

    def resolve(value: Any) -> Any:
        if pd.isna(value):
            return value
        key = str(value).strip()
        return canonical_map.get(key, key)

    for col in ["fighter_a_name", "fighter_b_name", "winner_name"]:
        if col in out.columns:
            out[col] = out[col].map(resolve)
    return out
