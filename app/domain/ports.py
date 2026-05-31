"""Domain ports: Protocols that infrastructure implementations must satisfy."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from app.domain.models import Registro


class RetrievedChunk(BaseModel):
    """A record retrieved from the vector store together with its similarity score."""

    registro: Registro
    score: float


@runtime_checkable
class Embedder(Protocol):
    """Contract for any embedding model implementation.

    Separates query embedding (with 'query:' prefix) from document embedding
    (with 'passage:' prefix) so the e5 prefix requirement cannot be forgotten.
    """

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of document strings."""


@runtime_checkable
class VectorStore(Protocol):
    """Contract for any vector store implementation."""

    def upsert(self, registros: list[Registro], embeddings: list[list[float]]) -> None:
        """Insert or update records in the store. Idempotent on re-run."""

    def query(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        """Return the top_k most similar chunks for the given embedding."""

    def count(self) -> int:
        """Return the total number of records currently stored."""

    def reset(self) -> None:
        """Drop all records and recreate the collection (idempotent re-index)."""


@runtime_checkable
class Deduplicator(Protocol):
    """Contract for cross-source deduplication strategies."""

    def deduplicate(self, registros: list[Registro]) -> tuple[list[Registro], int]:
        """Return unique records and the count of duplicates removed."""


@runtime_checkable
class Parser(Protocol):
    """Contract for document parsers. Each source format gets one implementation."""

    def parse(self, path: Path) -> list[Registro]:
        """Parse a file and return a list of normalized Registro objects."""
