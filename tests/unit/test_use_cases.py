"""Unit tests for IngestUseCase with faked dependencies."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.domain.models import Registro
from app.domain.ports import RetrievedChunk

FIXTURES = Path(__file__).parent / "fixtures"


def _make_registro(titulo: str = "test", codigo: str | None = "TST-001") -> Registro:
    return Registro(
        codigo=codigo,
        titulo=titulo,
        categoria="cat",
        mensaje_usuario="msg",
        causas=["c1"],
        solucion=["s1"],
        source_file="test.txt",
    )


class FakeEmbedder:
    """Returns zero vectors for any input."""

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * 4

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 4 for _ in texts]


class FakeVectorStore:
    """In-memory store that tracks calls."""

    def __init__(self):
        self.stored: list[Registro] = []
        self.upsert_calls: int = 0

    def upsert(self, registros: list[Registro], embeddings: list[list[float]]) -> None:
        self.stored = registros
        self.upsert_calls += 1

    def query(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        return []

    def count(self) -> int:
        return len(self.stored)

    def reset(self) -> None:
        self.stored = []


class TestIngestUseCase:
    """Tests for IngestUseCase orchestration."""

    def _make_use_case(self, embedder=None, store=None):
        from app.application.ingest import IngestUseCase
        from app.infrastructure.dedup.pandas_dedup import PandasDeduplicator
        from app.infrastructure.parsers.json import JsonParser
        from app.infrastructure.parsers.md import MdParser
        from app.infrastructure.parsers.pdf import PdfParser
        from app.infrastructure.parsers.txt import TxtParser

        parsers = {
            ".txt": TxtParser(),
            ".md": MdParser(),
            ".json": JsonParser(),
            ".pdf": PdfParser(),
        }
        dedup = PandasDeduplicator()
        return IngestUseCase(
            parsers=parsers,
            embedder=embedder or FakeEmbedder(),
            store=store or FakeVectorStore(),
            dedup=dedup,
            docs_path=FIXTURES,
        )

    def test_returns_ingest_result(self):
        from app.application.ingest import IngestResult

        uc = self._make_use_case()
        result = uc.execute()
        assert isinstance(result, IngestResult)

    def test_documents_count_is_four(self):
        uc = self._make_use_case()
        result = uc.execute()
        # 4 source files (txt, md, json, pdf)
        assert result.documentos == 4

    def test_chunks_count_is_twelve(self):
        uc = self._make_use_case()
        result = uc.execute()
        assert result.chunks == 12

    def test_duplicados_removidos_is_two(self):
        uc = self._make_use_case()
        result = uc.execute()
        assert result.duplicados_removidos == 2

    def test_embed_documents_called_once_with_12_texts(self):
        from unittest.mock import MagicMock

        embedder = FakeEmbedder()
        embedder.embed_documents = MagicMock(return_value=[[0.0] * 4 for _ in range(12)])

        uc = self._make_use_case(embedder=embedder)
        uc.execute()

        assert embedder.embed_documents.call_count == 1
        call_args = embedder.embed_documents.call_args[0][0]
        assert len(call_args) == 12

    def test_store_upsert_called_once_with_12_records(self):
        store = FakeVectorStore()
        store.upsert = MagicMock(wraps=store.upsert)

        uc = self._make_use_case(store=store)
        uc.execute()

        assert store.upsert.call_count == 1
        upsert_registros = store.upsert.call_args[0][0]
        assert len(upsert_registros) == 12

    def test_execute_is_idempotent(self):
        """Calling execute() twice should still yield chunks=12."""
        store = FakeVectorStore()
        uc = self._make_use_case(store=store)

        result1 = uc.execute()
        result2 = uc.execute()
        assert result1.chunks == 12
        assert result2.chunks == 12
