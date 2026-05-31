"""Parser for JSON error documentation (Documentación 4.json)."""

import json
from pathlib import Path

from app.domain.models import Registro


class JsonParser:
    """Parses JSON error documentation into Registro objects.

    The JSON structure has top-level metadata (``software``, ``modulo``) that
    is propagated into each record, and a ``contenido`` array where each item
    maps directly to the canonical schema.

    Field mapping:
    - ``id`` → ``codigo``
    - ``causas_posibles`` → ``causas``
    - ``palabras_clave`` → ``palabras_clave``
    - all other fields map by name
    - ``software`` and ``modulo`` from top-level are stored in ``categoria``
      if ``categoria`` is absent from the item, or appended as context.
    """

    def parse(self, path: Path) -> list[Registro]:
        """Parse the JSON file at *path* and return one Registro per ``contenido`` item."""
        data = json.loads(path.read_text(encoding="utf-8"))
        source_file = path.name

        software: str = data.get("software", "")
        modulo: str = data.get("modulo", "")

        registros: list[Registro] = []
        for item in data.get("contenido", []):
            registro = self._map_item(item, software, modulo, source_file)
            registros.append(registro)

        return registros

    def _map_item(
        self, item: dict, software: str, modulo: str, source_file: str
    ) -> Registro:
        codigo: str | None = item.get("id") or None
        titulo: str = item.get("titulo", "")
        categoria: str = item.get("categoria", "")

        # Enrich categoria with top-level metadata if available
        if software and modulo:
            categoria = f"{categoria} | {software} / {modulo}" if categoria else f"{software} / {modulo}"

        mensaje_usuario: str = item.get("mensaje_usuario", "")
        causas: list[str] = item.get("causas_posibles", [])
        solucion: list[str] = item.get("solucion", [])
        palabras_clave: list[str] = item.get("palabras_clave", [])
        nivel_soporte: str | None = item.get("nivel_soporte") or None

        return Registro(
            codigo=codigo,
            titulo=titulo,
            categoria=categoria,
            mensaje_usuario=mensaje_usuario,
            causas=causas,
            solucion=solucion,
            palabras_clave=palabras_clave,
            nivel_soporte=nivel_soporte,
            source_file=source_file,
        )
