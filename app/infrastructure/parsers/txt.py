"""Parser for plain-text error documentation (Documentación 2.txt)."""

import re
from pathlib import Path

from app.domain.models import Registro

_SECTION_PATTERN = re.compile(r"\d+\.\d+\s+Error:", re.IGNORECASE)

# Synonyms for field labels in the txt format
_LABEL_TITULO = re.compile(r"^\d+\.\d+\s+Error:\s*", re.IGNORECASE)
_LABEL_MENSAJE = re.compile(r"^Mensaje\s+mostrado\s*$", re.IGNORECASE)
_LABEL_CAUSAS = re.compile(r"^Causas\s+posibles\s*$", re.IGNORECASE)
_LABEL_SOLUCION = re.compile(r"^Solución\s*$", re.IGNORECASE | re.UNICODE)


def _parse_block(block: str, section_header: str) -> Registro:
    """Parse a single section block into a Registro.

    Args:
        block: the lines AFTER the section header (causas, solucion, etc.)
        section_header: the raw section header line (e.g. "3.2 Error: ...")
    """
    titulo = _LABEL_TITULO.sub("", section_header).strip()

    lines = [line.rstrip() for line in block.splitlines()]

    mensaje_usuario = ""
    causas: list[str] = []
    solucion_text = ""

    state = "init"

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if _LABEL_MENSAJE.match(stripped):
            state = "mensaje"
            continue
        if _LABEL_CAUSAS.match(stripped):
            state = "causas"
            continue
        if _LABEL_SOLUCION.match(stripped):
            state = "solucion"
            continue

        if state == "mensaje":
            mensaje_usuario = stripped
            state = "after_mensaje"
        elif state == "after_mensaje":
            # Next non-empty line after mensaje before another label — still mensaje if
            # we haven't hit causas yet; but the txt format only has one sentence there.
            pass
        elif state == "causas":
            causas.append(stripped.rstrip("."))
        elif state == "solucion":
            if solucion_text:
                solucion_text += " " + stripped
            else:
                solucion_text = stripped

    solucion: list[str] = [solucion_text] if solucion_text else []

    return Registro(
        codigo=None,
        titulo=titulo,
        categoria="",
        mensaje_usuario=mensaje_usuario,
        causas=causas,
        solucion=solucion,
        palabras_clave=[],
        nivel_soporte=None,
        source_file="Documentación 2.txt",
    )


class TxtParser:
    """Parses the plain-text error documentation file into Registro objects.

    Splits on numeric section headers (``\\d+.\\d+ Error:``), maps:
    - ``Mensaje mostrado`` → ``mensaje_usuario``
    - ``Causas posibles`` → ``causas`` (list of strings, one per line)
    - ``Solución`` → ``solucion`` (single paragraph, returned as a one-element list)
    """

    def parse(self, path: Path) -> list[Registro]:
        """Parse the file at *path* and return one Registro per section."""
        text = path.read_text(encoding="utf-8")
        return self._split_and_parse(text)

    def _split_and_parse(self, text: str) -> list[Registro]:
        lines = text.splitlines()
        # Find indices of section header lines
        header_indices: list[int] = []
        for i, line in enumerate(lines):
            if _SECTION_PATTERN.match(line.strip()):
                header_indices.append(i)

        registros: list[Registro] = []
        for idx, header_line_idx in enumerate(header_indices):
            header_line = lines[header_line_idx].strip()
            # The block is from the line AFTER the header to before the next header
            start = header_line_idx + 1
            end = header_indices[idx + 1] if idx + 1 < len(header_indices) else len(lines)
            block = "\n".join(lines[start:end])
            registros.append(_parse_block(block, header_line))

        return registros
