"""Ingest use case: parse all docs, deduplicate, embed, and index."""

from pathlib import Path

from pydantic import BaseModel

from app.domain.models import Registro
from app.domain.ports import Deduplicator, Embedder, Parser, VectorStore

_SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".pdf"}


class IngestResult(BaseModel):
    """Result returned by IngestUseCase.execute()."""

    documentos: int
    chunks: int
    duplicados_removidos: int


class IngestUseCase:
    """Orchestrates the full ingest pipeline.

    1. Discovers supported files in ``docs_path``
    2. Parses each file with the matching Parser
    3. Deduplicates all records across sources
    4. Embeds the unique records
    5. Upserts into the vector store (idempotent)
    6. Returns an IngestResult summary

    Args:
        parsers: mapping of file extension → Parser instance
        embedder: Embedder to use for document embedding
        store: VectorStore to write to
        dedup: callable/instance with ``deduplicate(list[Registro]) → (list, int)``
        docs_path: directory to scan for documentation files
    """

    def __init__(
        self,
        parsers: dict[str, Parser],
        embedder: Embedder,
        store: VectorStore,
        dedup: Deduplicator,
        docs_path: Path,
    ) -> None:
        self._parsers = parsers
        self._embedder = embedder
        self._store = store
        self._dedup = dedup
        self._docs_path = docs_path

    def execute(self) -> IngestResult:
        """Run the full ingest pipeline and return a summary."""
        all_registros: list[Registro] = []
        docs_found: int = 0

        for file_path in sorted(self._docs_path.iterdir()):
            ext = file_path.suffix.lower()
            if ext not in _SUPPORTED_EXTENSIONS:
                continue
            parser = self._parsers.get(ext)
            if parser is None:
                continue

            records = parser.parse(file_path)
            all_registros.extend(records)
            docs_found += 1

        unique, duplicados_removidos = self._dedup.deduplicate(all_registros)

        embeddings = self._embedder.embed_documents([r.embed_text() for r in unique])
        self._store.upsert(unique, embeddings)

        return IngestResult(
            documentos=docs_found,
            chunks=len(unique),
            duplicados_removidos=duplicados_removidos,
        )
