"""Unit tests for domain ports (Protocols) structural compliance."""

import pytest

from app.domain.models import Registro
from app.domain.ports import Embedder, Parser, RetrievedChunk, VectorStore


class TestEmbedderProtocol:
    def test_import_succeeds(self):
        """Embedder can be imported from app.domain.ports."""
        assert Embedder is not None

    def test_compliant_class_satisfies_protocol(self):
        """A class that implements all required methods satisfies the Embedder Protocol."""

        class FakeEmbedder:
            def embed_query(self, text: str) -> list[float]:
                return [0.1, 0.2]

            def embed_documents(self, texts: list[str]) -> list[list[float]]:
                return [[0.1, 0.2]] * len(texts)

        assert isinstance(FakeEmbedder(), Embedder)

    def test_non_compliant_class_fails_protocol(self):
        """A class missing embed_query does NOT satisfy the Embedder Protocol."""

        class IncompleteEmbedder:
            def embed_documents(self, texts: list[str]) -> list[list[float]]:
                return []

        assert not isinstance(IncompleteEmbedder(), Embedder)

    def test_empty_class_fails_protocol(self):
        """An empty class does not satisfy the Embedder Protocol."""

        class EmptyClass:
            pass

        assert not isinstance(EmptyClass(), Embedder)


class TestVectorStoreProtocol:
    def test_import_succeeds(self):
        """VectorStore can be imported from app.domain.ports."""
        assert VectorStore is not None

    def test_compliant_class_satisfies_protocol(self):
        """A class that implements all required methods satisfies the VectorStore Protocol."""

        class FakeVectorStore:
            def upsert(self, registros: list[Registro], embeddings: list[list[float]]) -> None:
                pass

            def query(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
                return []

            def count(self) -> int:
                return 0

            def reset(self) -> None:
                pass

        assert isinstance(FakeVectorStore(), VectorStore)

    def test_non_compliant_class_fails_protocol(self):
        """A class missing upsert does NOT satisfy the VectorStore Protocol."""

        class IncompleteStore:
            def query(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
                return []

            def count(self) -> int:
                return 0

        assert not isinstance(IncompleteStore(), VectorStore)


class TestRetrievedChunkModel:
    def test_import_succeeds(self):
        """RetrievedChunk can be imported from app.domain.ports."""
        assert RetrievedChunk is not None

    def test_create_retrieved_chunk(self):
        """RetrievedChunk can be instantiated with a Registro and a score."""
        r = Registro(
            titulo="Error de prueba",
            categoria="Test",
            mensaje_usuario="Mensaje",
            causas=[],
            solucion=[],
            source_file="test.md",
        )
        chunk = RetrievedChunk(registro=r, score=0.95)
        assert chunk.registro == r
        assert chunk.score == 0.95


class TestParserProtocol:
    def test_import_succeeds(self):
        """Parser can be imported from app.domain.ports."""
        assert Parser is not None

    def test_compliant_class_satisfies_protocol(self):
        """A class that implements parse() satisfies the Parser Protocol."""
        from pathlib import Path

        class FakeParser:
            def parse(self, path: Path) -> list[Registro]:
                return []

        assert isinstance(FakeParser(), Parser)

    def test_non_compliant_class_fails_protocol(self):
        """A class without parse() does NOT satisfy the Parser Protocol."""

        class NoParser:
            pass

        assert not isinstance(NoParser(), Parser)
