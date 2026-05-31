"""Parser for Markdown error documentation (Documentación 3.md)."""

import re
from pathlib import Path

from app.domain.models import Registro

# H1 separates records; H2 declares field sections
_H1_PATTERN = re.compile(r"^# (.+)$", re.MULTILINE)
_H2_PATTERN = re.compile(r"^## (.+)$", re.MULTILINE)

# Normalized H2 header → schema field mapping
_FIELD_MAP: dict[str, str] = {
    "código": "codigo",
    "categoría": "categoria",
    "mensaje mostrado al usuario": "mensaje_usuario",
    "causas posibles": "causas",
    "solución recomendada": "solucion",
    "palabras clave": "palabras_clave",
    "nivel de soporte": "nivel_soporte",
}


def _normalize_header(header: str) -> str:
    return header.strip().lower()


def _extract_list_items(text: str) -> list[str]:
    """Extract bullet/numbered list items from a block of text."""
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        # Strip bullet markers (-, *, •) and numbering (1. 2. etc.)
        if stripped.startswith(("-", "*", "•")):
            item = stripped[1:].strip()
            if item:
                items.append(item)
        elif re.match(r"^\d+\.\s+", stripped):
            item = re.sub(r"^\d+\.\s+", "", stripped).strip()
            if item:
                items.append(item)
    return items


def _parse_record(h1_title: str, body: str, source_file: str) -> Registro:
    """Parse an H1 block into a Registro."""
    # Split body into H2 sections
    h2_positions: list[tuple[str, int]] = []
    for m in _H2_PATTERN.finditer(body):
        h2_positions.append((m.group(1), m.start(), m.end()))

    sections: dict[str, str] = {}
    for i, (header, _, end) in enumerate(h2_positions):
        next_start = h2_positions[i + 1][1] if i + 1 < len(h2_positions) else len(body)
        section_body = body[end:next_start].strip()
        key = _normalize_header(header)
        sections[key] = section_body

    def get(field_label: str) -> str:
        return sections.get(field_label, "").strip()

    codigo_raw = get("código")
    codigo = codigo_raw if codigo_raw else None

    categoria = get("categoría")
    mensaje_usuario = get("mensaje mostrado al usuario").strip('"').strip("\"")

    causas_raw = get("causas posibles")
    causas = _extract_list_items(causas_raw)

    solucion_raw = get("solución recomendada")
    solucion = _extract_list_items(solucion_raw)

    palabras_clave_raw = get("palabras clave")
    palabras_clave = [w.strip() for w in palabras_clave_raw.split(",") if w.strip()]

    nivel_soporte_raw = get("nivel de soporte")
    nivel_soporte = nivel_soporte_raw if nivel_soporte_raw else None

    return Registro(
        codigo=codigo,
        titulo=h1_title.strip(),
        categoria=categoria,
        mensaje_usuario=mensaje_usuario,
        causas=causas,
        solucion=solucion,
        palabras_clave=palabras_clave,
        nivel_soporte=nivel_soporte,
        source_file=source_file,
    )


class MdParser:
    """Parses Markdown error documentation into Registro objects.

    Splits on H1 headers (``# Title``).  Within each H1 block the H2
    sub-headers map to canonical schema fields via ``_FIELD_MAP``.
    """

    def parse(self, path: Path) -> list[Registro]:
        """Parse the Markdown file at *path* and return one Registro per H1 block."""
        text = path.read_text(encoding="utf-8")
        source_file = path.name
        return self._parse_text(text, source_file)

    def _parse_text(self, text: str, source_file: str) -> list[Registro]:
        # Find all H1 positions
        h1_matches = list(_H1_PATTERN.finditer(text))
        if not h1_matches:
            return []

        registros: list[Registro] = []
        for i, match in enumerate(h1_matches):
            h1_title = match.group(1)
            body_start = match.end()
            body_end = h1_matches[i + 1].start() if i + 1 < len(h1_matches) else len(text)
            body = text[body_start:body_end]
            registros.append(_parse_record(h1_title, body, source_file))

        return registros
