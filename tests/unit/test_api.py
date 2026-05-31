"""Integration tests for the FastAPI ingest endpoint using TestClient."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.domain.models import Registro
from app.domain.ports import RetrievedChunk

FIXTURES = Path(__file__).parent / "fixtures"


class FakeEmbedder:
    def embed_query(self, text: str) -> list[float]:
        return [0.0] * 4

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 4 for _ in texts]


class FakeVectorStore:
    def __init__(self):
        self.stored: list[Registro] = []

    def upsert(self, registros: list[Registro], embeddings: list[list[float]]) -> None:
        self.stored = registros

    def query(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        return []

    def count(self) -> int:
        return len(self.stored)

    def reset(self) -> None:
        self.stored = []


class TestIngestEndpoint:
    """Tests for POST /api/ingest."""

    @pytest.fixture
    def client(self):
        from app.application.ingest import IngestUseCase
        from app.infrastructure.dedup.pandas_dedup import PandasDeduplicator
        from app.infrastructure.parsers.json import JsonParser
        from app.infrastructure.parsers.md import MdParser
        from app.infrastructure.parsers.pdf import PdfParser
        from app.infrastructure.parsers.txt import TxtParser
        from app.interface.api import app, get_ingest_uc

        fake_embedder = FakeEmbedder()
        fake_store = FakeVectorStore()

        def fake_ingest_uc():
            parsers = {
                ".txt": TxtParser(),
                ".md": MdParser(),
                ".json": JsonParser(),
                ".pdf": PdfParser(),
            }
            return IngestUseCase(
                parsers=parsers,
                embedder=fake_embedder,
                store=fake_store,
                dedup=PandasDeduplicator(),
                docs_path=FIXTURES,
            )

        app.dependency_overrides[get_ingest_uc] = fake_ingest_uc
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    def test_ingest_returns_200(self, client):
        response = client.post("/api/ingest")
        assert response.status_code == 200

    def test_ingest_response_has_correct_shape(self, client):
        response = client.post("/api/ingest")
        body = response.json()
        assert "documentos" in body
        assert "chunks" in body
        assert "duplicados_removidos" in body

    def test_ingest_returns_twelve_chunks(self, client):
        response = client.post("/api/ingest")
        body = response.json()
        assert body["chunks"] == 12

    def test_ingest_returns_four_documentos(self, client):
        response = client.post("/api/ingest")
        body = response.json()
        assert body["documentos"] == 4

    def test_ingest_returns_two_duplicados_removidos(self, client):
        response = client.post("/api/ingest")
        body = response.json()
        assert body["duplicados_removidos"] == 2

    def test_ingest_is_idempotent(self, client):
        """Calling /api/ingest twice should still return chunks=12."""
        r1 = client.post("/api/ingest")
        r2 = client.post("/api/ingest")
        assert r1.json()["chunks"] == 12
        assert r2.json()["chunks"] == 12
