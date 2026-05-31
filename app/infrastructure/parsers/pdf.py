"""Parser for PDF error documentation (Documentación 1.pdf)."""

import re
from pathlib import Path

import pdfplumber

from app.domain.models import Registro

# Matches numbered section headers like "4.3 No se guardan..."
_SECTION_PATTERN = re.compile(r"^(\d+\.\d+)\s+(.+)$")

# Labels for causas field (multiple synonyms in this document)
_CAUSAS_LABELS = re.compile(
    r"^(Posibles\s+causas|Causas\s+posibles|Verificaciones\s+b[aá]sicas)\s*$",
    re.IGNORECASE | re.UNICODE,
)

# Labels for solucion field (multiple synonyms in this document)
_SOLUCION_LABELS = re.compile(
    r"^(Acciones?\s+recomendadas?|Acci[oó]n\s+recomendada)\s*$",
    re.IGNORECASE | re.UNICODE,
)

# Marks the "Contacto de soporte" block — everything from here is metadata, not a record
_CONTACTO_PATTERN = re.compile(r"Contacto\s+de\s+soporte", re.IGNORECASE)

# Bullet point markers used in this PDF
_BULLET_RE = re.compile(r"^[•\-\*]\s+")
_NUMBERED_RE = re.compile(r"^\d+\.\s+")


def _extract_text(path: Path) -> str:
    """Extract all text from a PDF file using pdfplumber, joining pages with newline."""
    with pdfplumber.open(str(path)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages)


def _clean_line(line: str) -> str:
    return line.strip()


def _parse_record_lines(lines: list[str], titulo: str, source_file: str) -> Registro:
    """Parse a list of body lines into a Registro given the titulo."""
    causas: list[str] = []
    solucion: list[str] = []
    state = "init"

    for line in lines:
        stripped = _clean_line(line)
        if not stripped:
            continue

        if _CAUSAS_LABELS.match(stripped):
            state = "causas"
            continue
        if _SOLUCION_LABELS.match(stripped):
            state = "solucion"
            continue

        if state == "causas":
            if _BULLET_RE.match(stripped):
                item = _BULLET_RE.sub("", stripped).rstrip(".")
                if item:
                    causas.append(item)
            else:
                # Non-bullet line in causas section — could still be content
                # (shouldn't happen in this doc, but be safe)
                pass
        elif state == "solucion":
            # Both bullet and numbered lists appear in solucion
            if _BULLET_RE.match(stripped):
                item = _BULLET_RE.sub("", stripped).rstrip(".")
                if item:
                    solucion.append(item)
            elif _NUMBERED_RE.match(stripped):
                item = _NUMBERED_RE.sub("", stripped).rstrip(".")
                if item:
                    solucion.append(item)
            else:
                # Free-form solucion paragraph (e.g. "Revisar el estado de la muestra...")
                # Append as a single item if it looks like an action sentence
                if not _CAUSAS_LABELS.match(stripped) and not _SOLUCION_LABELS.match(stripped):
                    solucion.append(stripped)

    return Registro(
        codigo=None,
        titulo=titulo,
        categoria="",
        mensaje_usuario="",
        causas=causas,
        solucion=solucion,
        palabras_clave=[],
        nivel_soporte=None,
        source_file=source_file,
    )


def _split_into_blocks(text: str) -> list[tuple[str, list[str]]]:
    """Split the full PDF text into (titulo, body_lines) tuples.

    Handles the headerless leading block before the first numbered section.
    Discards the "Contacto de soporte técnico" block.

    Returns:
        List of (titulo, body_lines) tuples — one per logical record.
    """
    lines = text.splitlines()

    # Truncate at the "Contacto de soporte" line — everything after is metadata
    cutoff = len(lines)
    for i, line in enumerate(lines):
        if _CONTACTO_PATTERN.search(line):
            cutoff = i
            break
    lines = lines[:cutoff]

    # Find all numbered section header positions
    header_positions: list[tuple[int, str]] = []  # (line_idx, titulo)
    for i, line in enumerate(lines):
        m = _SECTION_PATTERN.match(line.strip())
        if m:
            header_positions.append((i, m.group(2).strip()))

    blocks: list[tuple[str, list[str]]] = []

    if header_positions:
        first_header_idx = header_positions[0][0]

        # Leading block: lines 0 .. first_header_idx - 1
        leading_lines = lines[:first_header_idx]
        # The first non-empty line in the leading block is the titulo
        leading_content = [l for l in leading_lines if l.strip()]
        if leading_content:
            leading_titulo = leading_content[0].strip()
            leading_body = leading_content[1:]
            blocks.append((leading_titulo, leading_body))

        # Numbered sections
        for idx, (header_line_idx, titulo) in enumerate(header_positions):
            body_start = header_line_idx + 1
            body_end = (
                header_positions[idx + 1][0]
                if idx + 1 < len(header_positions)
                else len(lines)
            )
            body_lines = lines[body_start:body_end]
            blocks.append((titulo, body_lines))

    return blocks


class PdfParser:
    """Parses PDF error documentation into Registro objects.

    Uses ``pdfplumber`` for text extraction.  The PDF has a headerless leading
    block that must be captured before the first numbered section (``4.3``).
    The final "Contacto de soporte técnico" block is discarded.

    Label synonyms handled:
    - ``Posibles causas`` / ``Verificaciones básicas`` → ``causas``
    - ``Acciones recomendadas`` / ``Acción recomendada`` → ``solucion``
    """

    def parse(self, path: Path) -> list[Registro]:
        """Parse the PDF file at *path* and return one Registro per section."""
        text = _extract_text(path)
        source_file = path.name
        blocks = _split_into_blocks(text)
        return [_parse_record_lines(body, titulo, source_file) for titulo, body in blocks]
