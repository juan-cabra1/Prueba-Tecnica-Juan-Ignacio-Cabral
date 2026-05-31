"""Tests for PandasDeduplicator — 14 raw records → 12 unique, 2 removed."""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _load_all_records():
    """Load all records from all 4 fixture files (mirrors IngestUseCase behavior)."""
    from app.infrastructure.parsers.json import JsonParser
    from app.infrastructure.parsers.md import MdParser
    from app.infrastructure.parsers.pdf import PdfParser
    from app.infrastructure.parsers.txt import TxtParser

    records = []
    records.extend(TxtParser().parse(FIXTURES / "Documentación 2.txt"))   # 6 records
    records.extend(MdParser().parse(FIXTURES / "Documentación 3.md"))      # 1 record
    records.extend(JsonParser().parse(FIXTURES / "Documentación 4.json"))  # 2 records
    records.extend(PdfParser().parse(FIXTURES / "Documentación 1.pdf"))    # 5 records
    return records


class TestPandasDeduplicator:
    """Tests for deduplication logic across all 4 source files."""

    def test_returns_twelve_unique_records(self):
        from app.infrastructure.dedup.pandas_dedup import PandasDeduplicator

        records = _load_all_records()
        assert len(records) == 14, f"Expected 14 raw records, got {len(records)}"

        unique, removed = PandasDeduplicator().deduplicate(records)
        assert len(unique) == 12, f"Expected 12 unique, got {len(unique)}"

    def test_removed_count_is_two(self):
        from app.infrastructure.dedup.pandas_dedup import PandasDeduplicator

        records = _load_all_records()
        unique, removed = PandasDeduplicator().deduplicate(records)
        assert removed == 2, f"Expected 2 duplicates removed, got {removed}"

    def test_err_db_001_backfilled(self):
        """ERR-DB-001 from JSON must be propagated to the txt duplicate."""
        from app.infrastructure.dedup.pandas_dedup import PandasDeduplicator

        records = _load_all_records()
        unique, _ = PandasDeduplicator().deduplicate(records)

        db_records = [r for r in unique if r.codigo == "ERR-DB-001"]
        assert len(db_records) == 1, "ERR-DB-001 should appear exactly once after dedup"

    def test_err_cat_001_backfilled(self):
        """ERR-CAT-001 from JSON must be propagated to the txt duplicate."""
        from app.infrastructure.dedup.pandas_dedup import PandasDeduplicator

        records = _load_all_records()
        unique, _ = PandasDeduplicator().deduplicate(records)

        cat_records = [r for r in unique if r.codigo == "ERR-CAT-001"]
        assert len(cat_records) == 1, "ERR-CAT-001 should appear exactly once after dedup"

    def test_no_duplicate_codigos(self):
        """No two records in the unique list should share the same non-null codigo."""
        from app.infrastructure.dedup.pandas_dedup import PandasDeduplicator

        records = _load_all_records()
        unique, _ = PandasDeduplicator().deduplicate(records)

        codigos = [r.codigo for r in unique if r.codigo is not None]
        assert len(codigos) == len(set(codigos)), "Duplicate codigos found after dedup"

    def test_err_auth_001_preserved(self):
        """ERR-AUTH-001 from MD should be present in unique records."""
        from app.infrastructure.dedup.pandas_dedup import PandasDeduplicator

        records = _load_all_records()
        unique, _ = PandasDeduplicator().deduplicate(records)

        auth_records = [r for r in unique if r.codigo == "ERR-AUTH-001"]
        assert len(auth_records) == 1

    def test_dedup_returns_tuple(self):
        """deduplicate must return a tuple (list[Registro], int)."""
        from app.infrastructure.dedup.pandas_dedup import PandasDeduplicator

        records = _load_all_records()
        result = PandasDeduplicator().deduplicate(records)
        assert isinstance(result, tuple)
        assert len(result) == 2
        unique, removed = result
        assert isinstance(unique, list)
        assert isinstance(removed, int)
