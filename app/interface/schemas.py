"""Pydantic request/response schemas for the API layer."""

from pydantic import BaseModel, field_validator


class IngestResponse(BaseModel):
    """Response schema for POST /api/ingest."""

    documentos: int
    chunks: int
    duplicados_removidos: int


class RetrieveRequest(BaseModel):
    """Request schema for POST /api/retrieve."""

    query: str

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        stripped = v.strip() if v else ""
        if not stripped:
            raise ValueError("query must not be empty")
        if not any(c.isalnum() for c in stripped):
            raise ValueError("query must contain at least one letter or digit")
        return stripped


class ResultItem(BaseModel):
    """A single retrieved result item."""

    codigo: str | None
    titulo: str
    context: str
    score: float
    source: str


class RetrieveResponse(BaseModel):
    """Response schema for POST /api/retrieve."""

    found: bool
    results: list[ResultItem] = []
    message: str | None = None
