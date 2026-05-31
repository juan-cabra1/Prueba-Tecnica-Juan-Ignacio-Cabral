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


class TestRetrieveEndpoint:
    """Tests for POST /api/retrieve."""

    THRESHOLD = 0.80

    def _make_registro(self, titulo: str = "test titulo", codigo: str | None = "ERR-001") -> Registro:
        return Registro(
            codigo=codigo,
            titulo=titulo,
            categoria="cat",
            mensaje_usuario="mensaje",
            causas=["causa 1"],
            solucion=["paso 1"],
            source_file="test.txt",
        )

    @pytest.fixture
    def client_found(self):
        """Client configured so /api/retrieve returns a found result."""
        from app.application.retrieve import RetrieveResult, RetrieveUseCase, RetrievedResult
        from app.interface.api import app, get_embedder, get_store

        registro = self._make_registro()
        chunk = RetrievedChunk(registro=registro, score=0.90)

        fake_store = FakeVectorStore()
        fake_store.query = MagicMock(return_value=[chunk])

        fake_embedder = FakeEmbedder()

        app.dependency_overrides[get_embedder] = lambda: fake_embedder
        app.dependency_overrides[get_store] = lambda: fake_store

        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    @pytest.fixture
    def client_not_found(self):
        """Client configured so /api/retrieve returns a not-found result (score below threshold)."""
        from app.interface.api import app, get_embedder, get_store

        registro = self._make_registro()
        chunk = RetrievedChunk(registro=registro, score=0.40)

        fake_store = FakeVectorStore()
        fake_store.query = MagicMock(return_value=[chunk])

        fake_embedder = FakeEmbedder()

        app.dependency_overrides[get_embedder] = lambda: fake_embedder
        app.dependency_overrides[get_store] = lambda: fake_store

        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    def test_retrieve_endpoint_found(self, client_found):
        """Score >= threshold → 200 + found: true."""
        response = client_found.post("/api/retrieve", json={"query": "error de conexion"})
        assert response.status_code == 200
        body = response.json()
        assert body["found"] is True
        assert len(body["results"]) == 1

    def test_retrieve_endpoint_found_result_shape(self, client_found):
        """Result items contain all required fields."""
        response = client_found.post("/api/retrieve", json={"query": "error de conexion"})
        item = response.json()["results"][0]
        assert "codigo" in item
        assert "titulo" in item
        assert "context" in item
        assert "score" in item
        assert "source" in item

    def test_retrieve_endpoint_not_found(self, client_not_found):
        """Score below threshold → 200 + found: false."""
        response = client_not_found.post("/api/retrieve", json={"query": "algo inexistente"})
        assert response.status_code == 200
        body = response.json()
        assert body["found"] is False
        assert body["results"] == []
        assert body["message"] is not None

    def test_retrieve_endpoint_empty_query(self):
        """POST with empty query string → 422 validation error."""
        from app.interface.api import app

        client = TestClient(app)
        response = client.post("/api/retrieve", json={"query": ""})
        assert response.status_code == 422

    def test_retrieve_endpoint_whitespace_query(self):
        """POST with whitespace-only query → 422 validation error."""
        from app.interface.api import app

        client = TestClient(app)
        response = client.post("/api/retrieve", json={"query": "   "})
        assert response.status_code == 422

    def test_retrieve_endpoint_missing_query_field(self):
        """POST with empty body (missing query field) → 422 validation error."""
        from app.interface.api import app

        client = TestClient(app)
        response = client.post("/api/retrieve", json={})
        assert response.status_code == 422
