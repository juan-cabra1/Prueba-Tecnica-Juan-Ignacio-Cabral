"""ChromaDB-backed vector store implementation."""

import hashlib
import re

import chromadb

from app.domain.models import Registro
from app.domain.ports import RetrievedChunk


def _make_id(registro: Registro) -> str:
    """Generate a stable ID for a Registro.

    Uses ``codigo`` if available, otherwise falls back to a SHA-256 hash of the
    normalized title so that repeated upserts are idempotent.
    """
    if registro.codigo:
        return registro.codigo
    normalized = re.sub(r"\s+", " ", registro.titulo.lower().strip())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _registro_to_metadata(r: Registro) -> dict:
    """Convert a Registro to a flat dict suitable for Chroma metadata storage.

    Chroma metadata values must be str | int | float | bool — lists are
    serialized as ``"|"``-separated strings.
    """
    return {
        "codigo": r.codigo or "",
        "titulo": r.titulo,
        "categoria": r.categoria,
        "mensaje_usuario": r.mensaje_usuario,
        "causas": "|".join(r.causas),
        "solucion": "|".join(r.solucion),
        "palabras_clave": "|".join(r.palabras_clave),
        "nivel_soporte": r.nivel_soporte or "",
        "source_file": r.source_file,
    }


def _metadata_to_registro(meta: dict) -> Registro:
    """Reconstruct a Registro from flattened Chroma metadata."""

    def split_pipe(value: str) -> list[str]:
        return [v for v in value.split("|") if v]

    return Registro(
        codigo=meta.get("codigo") or None,
        titulo=meta.get("titulo", ""),
        categoria=meta.get("categoria", ""),
        mensaje_usuario=meta.get("mensaje_usuario", ""),
        causas=split_pipe(meta.get("causas", "")),
        solucion=split_pipe(meta.get("solucion", "")),
        palabras_clave=split_pipe(meta.get("palabras_clave", "")),
        nivel_soporte=meta.get("nivel_soporte") or None,
        source_file=meta.get("source_file", ""),
    )


class ChromaVectorStore:
    """Vector store backed by ChromaDB with cosine similarity metric.

    Uses a PersistentClient for production use and a regular PersistentClient
    with a temp directory for testing (no special ephemeral client needed).

    Cosine distance in Chroma: ``distance = 1 - cosine_similarity``
    Therefore: ``score = 1.0 - distance``
    """

    def __init__(self, path: str, collection_name: str) -> None:
        self._path = path
        self._collection_name = collection_name
        self._client = chromadb.PersistentClient(path=path)
        self._col = self._get_or_create_collection()

    def _get_or_create_collection(self):
        return self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, registros: list[Registro], embeddings: list[list[float]]) -> None:
        """Insert or update records. Idempotent: re-running with same data is safe."""
        if not registros:
            return

        ids = [_make_id(r) for r in registros]
        metadatas = [_registro_to_metadata(r) for r in registros]
        documents = [r.embed_text() for r in registros]

        self._col.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

    def query(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        """Return the top_k most similar chunks for the given embedding.

        Converts Chroma cosine distance ``d`` to similarity score via
        ``score = 1.0 - d``.
        """
        results = self._col.query(
            query_embeddings=[embedding],
            n_results=min(top_k, self._col.count()),
            include=["metadatas", "distances"],
        )

        chunks: list[RetrievedChunk] = []
        distances = results["distances"][0]
        metadatas = results["metadatas"][0]

        for dist, meta in zip(distances, metadatas):
            score = max(0.0, min(1.0, 1.0 - dist))
            registro = _metadata_to_registro(meta)
            chunks.append(RetrievedChunk(registro=registro, score=score))

        return chunks

    def count(self) -> int:
        """Return the total number of records in the collection."""
        return self._col.count()

    def reset(self) -> None:
        """Delete and recreate the collection, effectively clearing all records."""
        self._client.delete_collection(self._collection_name)
        self._col = self._get_or_create_collection()
