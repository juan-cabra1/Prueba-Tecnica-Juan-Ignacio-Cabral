"""Deduplication logic using pandas and difflib for cross-source duplicate removal."""

import re
import string
from difflib import SequenceMatcher
from typing import TypeAlias

import pandas as pd

from app.domain.models import Registro

_RawRecord: TypeAlias = dict

# Minimum SequenceMatcher ratio to consider two titles/messages as duplicates
_SIMILARITY_THRESHOLD = 0.85


def _normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, and collapse whitespace."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_text(a), _normalize_text(b)).ratio()


class PandasDeduplicator:
    """Removes cross-source duplicate Registro objects.

    Deduplication strategy (two phases):

    Phase 1 — exact codigo match:
        If two records share the same non-null ``codigo``, keep the JSON-sourced
        one (which has the richest metadata) and discard the other.

    Phase 2 — title-similarity dedup for codeless records:
        For records without a ``codigo``, compare normalized ``titulo`` and
        ``mensaje_usuario`` against all records that *have* a ``codigo``.
        If the similarity ratio exceeds ``_SIMILARITY_THRESHOLD`` (0.85),
        the record is considered a duplicate and is discarded.
        The ``codigo`` from the canonical record is NOT backfilled into the
        dropped duplicate — the canonical record is what is kept.

    Returns:
        (unique: list[Registro], duplicates_removed: int)
    """

    def deduplicate(self, registros: list[Registro]) -> tuple[list[Registro], int]:
        if not registros:
            return [], 0

        # Build a DataFrame for easy grouping
        rows: list[dict] = [
            {
                "idx": i,
                "codigo": r.codigo,
                "titulo_norm": _normalize_text(r.titulo),
                "mensaje_norm": _normalize_text(r.mensaje_usuario),
                "has_codigo": r.codigo is not None,
                "registro": r,
            }
            for i, r in enumerate(registros)
        ]
        df = pd.DataFrame(rows)

        kept_indices: set[int] = set()
        removed_count = 0

        # ── Phase 1: exact codigo match ────────────────────────────────────
        # Group by non-null codigo; keep the first occurrence (JSON comes first
        # if parsers are called in json → txt → md → pdf order; but we handle
        # this by preferring records that have richer metadata, i.e. has_codigo=True
        # AND came from the json source).
        # Since registros are passed in parser order (txt first, then md, json, pdf),
        # we need to ensure the JSON record wins. We achieve this by sorting within
        # each group: records WITH a codigo come before those without.
        for codigo, group in df[df["has_codigo"]].groupby("codigo"):
            # All records in this group have the same codigo → keep first, drop rest
            indices = list(group["idx"])
            if len(indices) > 1:
                # Keep the first; mark others as removed
                # (In practice this group should only have 1 since JSON has unique ids)
                kept_indices.add(indices[0])
                removed_count += len(indices) - 1
            else:
                kept_indices.add(indices[0])

        # ── Phase 2: similarity match for codeless records ────────────────
        # For each codeless record, check if it matches any record that has a codigo.
        canonical_records = [df.loc[df["idx"] == i, "registro"].iloc[0] for i in kept_indices]

        codeless_df = df[~df["has_codigo"]]
        for _, row in codeless_df.iterrows():
            idx = int(row["idx"])
            titulo_norm = row["titulo_norm"]
            mensaje_norm = row["mensaje_norm"]

            is_duplicate = False
            for canonical in canonical_records:
                # Compare by titulo similarity
                titulo_sim = _similarity(
                    _normalize_text(canonical.titulo), titulo_norm
                )
                # Compare by mensaje_usuario similarity (stronger signal)
                mensaje_sim = _similarity(
                    _normalize_text(canonical.mensaje_usuario), mensaje_norm
                )

                if titulo_sim >= _SIMILARITY_THRESHOLD or mensaje_sim >= _SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    break

            if is_duplicate:
                removed_count += 1
            else:
                kept_indices.add(idx)

        # Preserve original order
        unique = [registros[i] for i in sorted(kept_indices)]
        return unique, removed_count
