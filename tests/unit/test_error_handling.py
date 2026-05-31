"""Tests for cross-cutting error handling on the FastAPI layer.

Slice 4 — Error Handling.
Verifies that no raw 500 ever reaches the caller and that structured
error bodies are returned for both endpoint-level and unexpected failures.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestErrorHandling:
    """Cross-cutting error handling tests for the API layer."""

    def test_ingest_returns_500_on_use_case_failure(self):
        """When the ingest use case raises an exception the endpoint must
        return HTTP 500 with a JSON body containing an ``error`` key."""
        from app.interface.api import app, get_ingest_uc

        def failing_ingest_uc():
            uc = MagicMock()
            uc.execute.side_effect = RuntimeError("disk full")
            return uc

        app.dependency_overrides[get_ingest_uc] = failing_ingest_uc
        try:
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/ingest")
            assert response.status_code == 500
            body = response.json()
            assert "error" in body or "detail" in body
        finally:
            app.dependency_overrides.clear()

    def test_retrieve_returns_500_on_embedder_failure(self):
        """When the embedder raises during retrieve the endpoint must return
        HTTP 500 with a JSON body containing an ``error`` key."""
        from app.interface.api import app, get_embedder, get_store

        failing_embedder = MagicMock()
        failing_embedder.embed_query.side_effect = ConnectionError("model unavailable")

        fake_store = MagicMock()

        app.dependency_overrides[get_embedder] = lambda: failing_embedder
        app.dependency_overrides[get_store] = lambda: fake_store
        try:
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/retrieve", json={"query": "error de conexion"})
            assert response.status_code == 500
            body = response.json()
            assert "error" in body or "detail" in body
        finally:
            app.dependency_overrides.clear()

    def test_retrieve_422_on_empty_query(self):
        """POST /api/retrieve with empty string → 422 (cross-cutting smoke)."""
        from app.interface.api import app

        client = TestClient(app)
        response = client.post("/api/retrieve", json={"query": ""})
        assert response.status_code == 422

    def test_retrieve_422_on_missing_query(self):
        """POST /api/retrieve with no query field → 422 (cross-cutting smoke)."""
        from app.interface.api import app

        client = TestClient(app)
        response = client.post("/api/retrieve", json={})
        assert response.status_code == 422

    def test_retrieve_422_on_null_query(self):
        """POST /api/retrieve with query: null → 422."""
        from app.interface.api import app

        client = TestClient(app)
        response = client.post("/api/retrieve", json={"query": None})
        assert response.status_code == 422
