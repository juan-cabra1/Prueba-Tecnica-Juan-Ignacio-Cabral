"""Domain model: canonical error/incident record."""

from pydantic import BaseModel


class Registro(BaseModel):
    codigo: str | None = None
    titulo: str
    categoria: str
    mensaje_usuario: str
    causas: list[str]
    solucion: list[str]
    palabras_clave: list[str] = []
    nivel_soporte: str | None = None
    source_file: str

    def embed_text(self) -> str:
        """Compose the text that will be embedded for vector indexing.

        Joins titulo + mensaje_usuario + causas + solucion + palabras_clave,
        filtering out empty strings so no phantom spaces are introduced.
        """
        parts = [self.titulo, self.mensaje_usuario]
        parts.extend(self.causas)
        parts.extend(self.solucion)
        parts.extend(self.palabras_clave)
        return " ".join(p for p in parts if p)

    def context_payload(self) -> str:
        """Return a structured, human-readable block used for LLM grounding.

        Includes the record identifier and all relevant fields so the LLM
        can cite the source and provide an accurate answer.
        """
        lines: list[str] = []

        if self.codigo:
            lines.append(f"Código: {self.codigo}")

        lines.append(f"Título: {self.titulo}")
        lines.append(f"Categoría: {self.categoria}")
        lines.append(f"Mensaje al usuario: {self.mensaje_usuario}")

        if self.causas:
            lines.append("Causas:")
            for causa in self.causas:
                lines.append(f"  - {causa}")

        if self.solucion:
            lines.append("Solución:")
            for paso in self.solucion:
                lines.append(f"  - {paso}")

        if self.nivel_soporte:
            lines.append(f"Nivel de soporte: {self.nivel_soporte}")

        lines.append(f"Fuente: {self.source_file}")

        return "\n".join(lines)
