"""Unit tests for ChromaVectorStore using a temporary (ephemeral) directory."""

import tempfile
from pathlib import Path

import pytest

from app.domain.models import Registro


def _make_registro(titulo: str = "test", codigo: str | None = None) -> Registro:
    return Registro(
        codigo=codigo,
        titulo=titulo,
        categoria="test_cat",
        mensaje_usuario="test msg",
        causas=["causa 1"],
        solucion=["solucion 1"],
        palabras_clave=["kw"],
        nivel_soporte="Nivel 1",
        source_file="test.json",
    )


def _zero_vector(dim: int = 4) -> list[float]:
    return [0.0] * dim


def _unit_vector(dim: int = 4, val: float = 1.0) -> list[float]:
    import math

    v = [val] + [0.0] * (dim - 1)
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v]


class TestChromaVectorStore:
    """Tests for ChromaVectorStore using a temp directory (persistent client)."""

    @pytest.fixture
    def store(self, tmp_path):
        from app.infrastructure.vector_store.chroma import ChromaVectorStore

        return ChromaVectorStore(str(tmp_path), "test_collection")

    def test_initial_count_is_zero(self, store):
        assert store.count() == 0

    def test_upsert_increases_count(self, store):
        registros = [_make_registro("rec 1", "CODE-001")]
        embeddings = [_unit_vector()]
        store.upsert(registros, embeddings)
        assert store.count() == 1

    def test_upsert_multiple_records(self, store):
        registros = [_make_registro(f"rec {i}", f"CODE-{i:03d}") for i in range(3)]
        embeddings = [_unit_vector() for _ in range(3)]
        store.upsert(registros, embeddings)
        assert store.count() == 3

    def test_upsert_is_idempotent(self, store):
        """Calling upsert twice with the same records should not duplicate them."""
        registros = [_make_registro("rec 1", "CODE-001")]
        embeddings = [_unit_vector()]
        store.upsert(registros, embeddings)
        store.upsert(registros, embeddings)
        assert store.count() == 1

    def test_query_returns_retrieved_chunks(self, store):
        from app.domain.ports import RetrievedChunk

        registros = [_make_registro("rec 1", "CODE-001")]
        embeddings = [_unit_vector()]
        store.upsert(registros, embeddings)

        results = store.query(_unit_vector(), top_k=1)
        assert len(results) == 1
        assert isinstance(results[0], RetrievedChunk)

    def test_query_score_between_zero_and_one(self, store):
        registros = [_make_registro("rec 1", "CODE-001")]
        embeddings = [_unit_vector()]
        store.upsert(registros, embeddings)

        results = store.query(_unit_vector(), top_k=1)
        score = results[0].score
        assert 0.0 <= score <= 1.0, f"Score {score} out of [0, 1]"

    def test_identical_vectors_score_near_one(self, store):
        """Querying with the same vector that was indexed should yield score ≥ 0.9."""
        registros = [_make_registro("rec 1", "CODE-001")]
        vec = _unit_vector()
        store.upsert(registros, [vec])

        results = store.query(vec, top_k=1)
        assert results[0].score >= 0.9, f"Expected score ≥ 0.9, got {results[0].score}"

    def test_query_returns_registro_with_titulo(self, store):
        registros = [_make_registro("My Test Record", "CODE-001")]
        store.upsert(registros, [_unit_vector()])

        results = store.query(_unit_vector(), top_k=1)
        assert results[0].registro.titulo == "My Test Record"

    def test_reset_clears_store(self, store):
        registros = [_make_registro("rec 1", "CODE-001")]
        store.upsert(registros, [_unit_vector()])
        assert store.count() == 1

        store.reset()
        assert store.count() == 0

    def test_upsert_record_without_codigo_uses_hash_id(self, store):
        """Records without a codigo should still be stored (using hash-based ID)."""
        registros = [_make_registro("No Code Record", codigo=None)]
        store.upsert(registros, [_unit_vector()])
        assert store.count() == 1

    def test_query_top_k_limits_results(self, store):
        registros = [_make_registro(f"rec {i}", f"CODE-{i:03d}") for i in range(5)]
        embeddings = [_unit_vector() for _ in range(5)]
        store.upsert(registros, embeddings)

        results = store.query(_unit_vector(), top_k=2)
        assert len(results) <= 2
