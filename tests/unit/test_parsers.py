"""Parser unit tests — one class per parser, fixtures from tests/unit/fixtures/."""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


class TestTxtParser:
    """Tests for TxtParser against Documentación 2.txt."""

    def test_returns_six_registros(self):
        from app.infrastructure.parsers.txt import TxtParser

        records = TxtParser().parse(FIXTURES / "Documentación 2.txt")
        assert len(records) == 6

    def test_all_have_none_codigo(self):
        from app.infrastructure.parsers.txt import TxtParser

        records = TxtParser().parse(FIXTURES / "Documentación 2.txt")
        for r in records:
            assert r.codigo is None

    def test_each_has_non_empty_titulo(self):
        from app.infrastructure.parsers.txt import TxtParser

        records = TxtParser().parse(FIXTURES / "Documentación 2.txt")
        for r in records:
            assert r.titulo.strip() != ""

    def test_each_has_causas_list(self):
        from app.infrastructure.parsers.txt import TxtParser

        records = TxtParser().parse(FIXTURES / "Documentación 2.txt")
        for r in records:
            assert isinstance(r.causas, list)
            assert len(r.causas) > 0

    def test_each_has_solucion_list(self):
        from app.infrastructure.parsers.txt import TxtParser

        records = TxtParser().parse(FIXTURES / "Documentación 2.txt")
        for r in records:
            assert isinstance(r.solucion, list)
            assert len(r.solucion) > 0

    def test_source_file_is_set(self):
        from app.infrastructure.parsers.txt import TxtParser

        records = TxtParser().parse(FIXTURES / "Documentación 2.txt")
        for r in records:
            assert r.source_file == "Documentación 2.txt"

    def test_first_record_titulo_contains_base_de_datos(self):
        from app.infrastructure.parsers.txt import TxtParser

        records = TxtParser().parse(FIXTURES / "Documentación 2.txt")
        assert "base de datos" in records[0].titulo.lower()

    def test_mensaje_usuario_is_set(self):
        from app.infrastructure.parsers.txt import TxtParser

        records = TxtParser().parse(FIXTURES / "Documentación 2.txt")
        for r in records:
            assert r.mensaje_usuario.strip() != ""


class TestMdParser:
    """Tests for MdParser against Documentación 3.md."""

    def test_returns_one_registro(self):
        from app.infrastructure.parsers.md import MdParser

        records = MdParser().parse(FIXTURES / "Documentación 3.md")
        assert len(records) == 1

    def test_codigo_is_err_auth_001(self):
        from app.infrastructure.parsers.md import MdParser

        records = MdParser().parse(FIXTURES / "Documentación 3.md")
        assert records[0].codigo == "ERR-AUTH-001"

    def test_titulo_is_non_empty(self):
        from app.infrastructure.parsers.md import MdParser

        records = MdParser().parse(FIXTURES / "Documentación 3.md")
        assert records[0].titulo.strip() != ""

    def test_causas_is_list_with_items(self):
        from app.infrastructure.parsers.md import MdParser

        records = MdParser().parse(FIXTURES / "Documentación 3.md")
        assert isinstance(records[0].causas, list)
        assert len(records[0].causas) > 0

    def test_solucion_is_list_with_items(self):
        from app.infrastructure.parsers.md import MdParser

        records = MdParser().parse(FIXTURES / "Documentación 3.md")
        assert isinstance(records[0].solucion, list)
        assert len(records[0].solucion) > 0

    def test_palabras_clave_parsed(self):
        from app.infrastructure.parsers.md import MdParser

        records = MdParser().parse(FIXTURES / "Documentación 3.md")
        assert isinstance(records[0].palabras_clave, list)
        assert len(records[0].palabras_clave) > 0

    def test_source_file_is_set(self):
        from app.infrastructure.parsers.md import MdParser

        records = MdParser().parse(FIXTURES / "Documentación 3.md")
        assert records[0].source_file == "Documentación 3.md"


class TestJsonParser:
    """Tests for JsonParser against Documentación 4.json."""

    def test_returns_two_registros(self):
        from app.infrastructure.parsers.json import JsonParser

        records = JsonParser().parse(FIXTURES / "Documentación 4.json")
        assert len(records) == 2

    def test_codes_are_correct(self):
        from app.infrastructure.parsers.json import JsonParser

        records = JsonParser().parse(FIXTURES / "Documentación 4.json")
        codes = {r.codigo for r in records}
        assert codes == {"ERR-DB-001", "ERR-CAT-001"}

    def test_both_have_nivel_soporte(self):
        from app.infrastructure.parsers.json import JsonParser

        records = JsonParser().parse(FIXTURES / "Documentación 4.json")
        for r in records:
            assert r.nivel_soporte is not None

    def test_causas_and_solucion_are_lists(self):
        from app.infrastructure.parsers.json import JsonParser

        records = JsonParser().parse(FIXTURES / "Documentación 4.json")
        for r in records:
            assert isinstance(r.causas, list)
            assert len(r.causas) > 0
            assert isinstance(r.solucion, list)
            assert len(r.solucion) > 0

    def test_palabras_clave_propagated(self):
        from app.infrastructure.parsers.json import JsonParser

        records = JsonParser().parse(FIXTURES / "Documentación 4.json")
        for r in records:
            assert isinstance(r.palabras_clave, list)
            assert len(r.palabras_clave) > 0

    def test_source_file_is_set(self):
        from app.infrastructure.parsers.json import JsonParser

        records = JsonParser().parse(FIXTURES / "Documentación 4.json")
        for r in records:
            assert r.source_file == "Documentación 4.json"


class TestPdfParser:
    """Tests for PdfParser against Documentación 1.pdf."""

    def test_returns_five_registros(self):
        from app.infrastructure.parsers.pdf import PdfParser

        records = PdfParser().parse(FIXTURES / "Documentación 1.pdf")
        assert len(records) == 5

    def test_first_record_titulo_contains_catalogo(self):
        from app.infrastructure.parsers.pdf import PdfParser

        records = PdfParser().parse(FIXTURES / "Documentación 1.pdf")
        assert "catálogo" in records[0].titulo.lower() or "catalogo" in records[0].titulo.lower()

    def test_no_contacto_de_soporte_record(self):
        from app.infrastructure.parsers.pdf import PdfParser

        records = PdfParser().parse(FIXTURES / "Documentación 1.pdf")
        for r in records:
            assert "contacto" not in r.titulo.lower()

    def test_all_have_non_empty_causas(self):
        from app.infrastructure.parsers.pdf import PdfParser

        records = PdfParser().parse(FIXTURES / "Documentación 1.pdf")
        for r in records:
            assert isinstance(r.causas, list)
            assert len(r.causas) > 0, f"Record '{r.titulo}' has empty causas"

    def test_all_have_non_empty_solucion(self):
        from app.infrastructure.parsers.pdf import PdfParser

        records = PdfParser().parse(FIXTURES / "Documentación 1.pdf")
        for r in records:
            assert isinstance(r.solucion, list)
            assert len(r.solucion) > 0, f"Record '{r.titulo}' has empty solucion"

    def test_source_file_is_set(self):
        from app.infrastructure.parsers.pdf import PdfParser

        records = PdfParser().parse(FIXTURES / "Documentación 1.pdf")
        for r in records:
            assert r.source_file == "Documentación 1.pdf"

    def test_all_have_none_codigo(self):
        from app.infrastructure.parsers.pdf import PdfParser

        records = PdfParser().parse(FIXTURES / "Documentación 1.pdf")
        for r in records:
            assert r.codigo is None
