"""Unit tests for the Registro domain model."""

import pytest

from app.domain.models import Registro


class TestRegistroModel:
    def test_create_with_minimal_fields(self):
        """Registro can be created with only the required fields; optional ones default correctly."""
        r = Registro(
            titulo="Error de conexión",
            categoria="Base de datos",
            mensaje_usuario="No se pudo conectar",
            causas=[],
            solucion=[],
            palabras_clave=[],
            source_file="f.md",
        )
        assert r.codigo is None
        assert r.nivel_soporte is None

    def test_create_with_all_fields(self):
        """Registro accepts all fields when provided."""
        r = Registro(
            codigo="ERR-DB-001",
            titulo="Error de base de datos",
            categoria="Base de datos",
            mensaje_usuario="Error al conectar a la base de datos",
            causas=["Credenciales incorrectas", "BD apagada"],
            solucion=["Verificar credenciales", "Revisar servicio"],
            palabras_clave=["base de datos", "conexión"],
            nivel_soporte="N2",
            source_file="Documentación 4.json",
        )
        assert r.codigo == "ERR-DB-001"
        assert r.nivel_soporte == "N2"
        assert len(r.causas) == 2
        assert len(r.solucion) == 2

    def test_embed_text_composite(self):
        """embed_text() returns titulo + mensaje_usuario + causas + solucion + palabras_clave joined by space."""
        r = Registro(
            titulo="Error X",
            categoria="Cat",
            mensaje_usuario="Mensaje del error",
            causas=["Causa uno", "Causa dos"],
            solucion=["Paso uno", "Paso dos"],
            palabras_clave=["kw1", "kw2"],
            source_file="test.md",
        )
        text = r.embed_text()
        assert "Error X" in text
        assert "Mensaje del error" in text
        assert "Causa uno" in text
        assert "Causa dos" in text
        assert "Paso uno" in text
        assert "Paso dos" in text
        assert "kw1" in text
        assert "kw2" in text

    def test_embed_text_strips_empty_parts(self):
        """embed_text() does not include empty strings in the composite."""
        r = Registro(
            titulo="Solo titulo",
            categoria="Cat",
            mensaje_usuario="",
            causas=[],
            solucion=[],
            palabras_clave=[],
            source_file="test.md",
        )
        text = r.embed_text()
        assert text == "Solo titulo"
        assert "  " not in text  # no double spaces from empty join

    def test_embed_text_all_empty_except_titulo(self):
        """embed_text() works when only titulo has content."""
        r = Registro(
            titulo="Único campo",
            categoria="Cat",
            mensaje_usuario="",
            causas=[],
            solucion=[],
            source_file="test.md",
        )
        assert r.embed_text() == "Único campo"

    def test_context_payload_returns_non_empty_string(self):
        """context_payload() returns a non-empty string containing key information."""
        r = Registro(
            codigo="ERR-001",
            titulo="Error importante",
            categoria="Sistema",
            mensaje_usuario="Ocurrió un error",
            causas=["Causa 1"],
            solucion=["Solución 1"],
            palabras_clave=["error"],
            nivel_soporte="N1",
            source_file="doc.md",
        )
        payload = r.context_payload()
        assert isinstance(payload, str)
        assert len(payload) > 0
        assert "ERR-001" in payload
        assert "Error importante" in payload

    def test_context_payload_without_codigo(self):
        """context_payload() works correctly when codigo is None."""
        r = Registro(
            titulo="Error sin código",
            categoria="Sistema",
            mensaje_usuario="Mensaje",
            causas=["Causa"],
            solucion=["Solución"],
            source_file="doc.txt",
        )
        payload = r.context_payload()
        assert isinstance(payload, str)
        assert len(payload) > 0
