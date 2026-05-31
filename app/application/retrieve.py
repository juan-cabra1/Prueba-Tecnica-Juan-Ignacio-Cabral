"""Retrieve use case: embed query, search vector store, apply abstention threshold."""

from pydantic import BaseModel

from app.domain.ports import Embedder, VectorStore


class RetrievedResult(BaseModel):
    """A single result item returned to the caller."""

    codigo: str | None
    titulo: str
    context: str
    score: float
    source: str


class RetrieveResult(BaseModel):
    """Full response from RetrieveUseCase.execute()."""

    found: bool
    results: list[RetrievedResult] = []
    message: str | None = None


class RetrieveUseCase:
    """Retrieves relevant documentation chunks for a given query.

    Applies a similarity threshold: if the top-1 score is below the threshold,
    the result is ``found: False`` (abstention) and no LLM call is needed.

    Args:
        embedder: Embedder used to embed the query (``embed_query`` path).
        store: VectorStore to search against.
        threshold: Minimum cosine similarity score required to return results.
        top_k: Maximum number of chunks to retrieve.
    """

    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        threshold: float,
        top_k: int,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._threshold = threshold
        self._top_k = top_k

    def execute(self, query: str) -> RetrieveResult:
        """Embed the query, retrieve top-k chunks, and apply abstention logic.

        Returns:
            ``RetrieveResult`` with ``found=True`` and populated results when
            the top-1 score meets the threshold, or ``found=False`` otherwise.
        """
        embedding = self._embedder.embed_query(query)
        chunks = self._store.query(embedding, self._top_k)

        if not chunks or chunks[0].score < self._threshold:
            return RetrieveResult(
                found=False,
                results=[],
                message="No se encontró información relevante en la documentación.",
            )

        return RetrieveResult(
            found=True,
            results=[
                RetrievedResult(
                    codigo=chunk.registro.codigo,
                    titulo=chunk.registro.titulo,
                    context=chunk.registro.context_payload(),
                    score=chunk.score,
                    source=chunk.registro.source_file,
                )
                for chunk in chunks
            ],
        )
