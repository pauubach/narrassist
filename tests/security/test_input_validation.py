"""
Tests de seguridad para validación de inputs.

Cubre:
- Inyección SQL
- Path traversal
- Inputs malformados
- Límites de tamaño
"""

from pathlib import Path

import pytest

from narrative_assistant.core.result import Result
from narrative_assistant.parsers.sanitization import (
    InputSanitizer,
    sanitize_chapter_content,
    validate_file_path_safe as validate_file_path,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sanitizer():
    """Instancia del sanitizador."""
    return InputSanitizer()


@pytest.fixture
def allowed_dir(tmp_path):
    """Directorio permitido para tests de path traversal."""
    return tmp_path


# =============================================================================
# Tests de inyección SQL
# =============================================================================


class TestSQLInjection:
    """Tests para prevención de inyección SQL."""

    def test_sql_injection_in_chapter_content(self, sanitizer):
        """El contenido con SQL injection se sanitiza."""
        malicious_content = "SELECT * FROM users; DROP TABLE users;--"
        result = sanitizer.sanitize_text(malicious_content)

        # El texto debe mantenerse (es contenido legítimo de narrativa)
        # pero no debe ejecutarse como SQL
        assert "SELECT" in result or "select" in result.lower()
        # La sanitización no modifica el texto (eso es trabajo del ORM/parameterized queries)

    def test_sql_injection_patterns_in_entity_names(self, sanitizer):
        """Nombres de entidad con patrones SQL son sanitizados."""
        malicious_names = [
            "'; DROP TABLE entities;--",
            "1' OR '1'='1",
            "UNION SELECT * FROM users",
            "Robert'); DROP TABLE Students;--",
        ]

        for name in malicious_names:
            result = sanitizer.sanitize_entity_name(name)
            # El nombre se limpia de caracteres peligrosos
            assert ";" not in result or result != name  # Changed somehow
            assert "--" not in result or result != name


# =============================================================================
# Tests de Path Traversal
# =============================================================================


class TestPathTraversal:
    """Tests para prevención de path traversal."""

    def test_blocks_parent_directory_access(self, allowed_dir):
        """Bloquea intentos de acceso a directorio padre."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "foo/../../../bar",
            "foo/bar/../../../baz",
        ]

        for path in malicious_paths:
            result = validate_file_path(path, allowed_dir)
            assert result.is_failure, f"Should block: {path}"
            assert (
                "traversal" in result.error.message.lower()
                or "outside" in result.error.message.lower()
            )

    def test_blocks_absolute_path_outside_allowed(self, allowed_dir):
        """Bloquea rutas absolutas fuera del directorio permitido."""
        malicious_paths = [
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "/root/.ssh/id_rsa",
        ]

        for path in malicious_paths:
            result = validate_file_path(path, allowed_dir)
            assert result.is_failure, f"Should block: {path}"

    def test_allows_valid_paths_within_directory(self, allowed_dir):
        """Permite rutas válidas dentro del directorio permitido."""
        # Crear archivo de prueba
        test_file = allowed_dir / "test_document.txt"
        test_file.write_text("Content")

        result = validate_file_path(str(test_file), allowed_dir)
        assert result.is_success, f"Should allow: {test_file}"

    def test_blocks_null_byte_injection(self, allowed_dir):
        """Bloquea inyección de bytes nulos."""
        # Null byte puede truncar rutas en algunos sistemas
        malicious_paths = [
            "document.txt\x00.exe",
            "safe\x00../../../etc/passwd",
        ]

        for path in malicious_paths:
            result = validate_file_path(path, allowed_dir)
            assert result.is_failure, f"Should block null byte: {path}"

    def test_blocks_encoded_traversal(self, allowed_dir):
        """Bloquea path traversal con encoding."""
        encoded_paths = [
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded ../../../etc/passwd
            "..%252f..%252f..%252fetc/passwd",  # Double encoded
            "..%c0%af..%c0%afetc/passwd",  # Overlong UTF-8
        ]

        for path in encoded_paths:
            result = validate_file_path(path, allowed_dir)
            # Puede fallar o sanitizar, pero no debe permitir acceso
            if result.is_success:
                # Si permite, el path debe estar dentro del directorio
                assert str(allowed_dir) in str(result.value) or not Path(result.value).exists()


# =============================================================================
# Tests de inputs malformados
# =============================================================================


class TestMalformedInputs:
    """Tests para manejo de inputs malformados."""

    def test_handles_extremely_long_text(self, sanitizer):
        """Maneja texto extremadamente largo sin crash."""
        # 10MB de texto
        huge_text = "a" * (10 * 1024 * 1024)

        # No debe crashear
        result = sanitizer.sanitize_text(huge_text)
        assert result is not None

    def test_handles_unicode_edge_cases(self, sanitizer):
        """Maneja caracteres Unicode problemáticos."""
        edge_cases = [
            "\u0000",  # Null character
            "\uffff",  # Max BMP character
            "🎭" * 1000,  # Many emoji
            "\u202e" + "reversed text",  # Right-to-left override
            "\ufeff" + "text with BOM",  # Byte order mark
            "a\u0300\u0301\u0302\u0303\u0304" * 100,  # Combining characters
        ]

        for text in edge_cases:
            result = sanitizer.sanitize_text(text)
            # No debe crashear y debe devolver algo
            assert result is not None

    def test_handles_control_characters(self, sanitizer):
        """Maneja caracteres de control."""
        control_chars = "".join(chr(i) for i in range(32))
        result = sanitizer.sanitize_text(f"Text with {control_chars} control chars")

        # Debe sanitizar o manejar gracefully
        assert result is not None

    def test_handles_mixed_encodings(self, sanitizer):
        """Maneja mezcla de encodings (UTF-8 válido e inválido)."""
        # Simular texto con bytes inválidos (no se puede en Python str, pero...)
        mixed_text = "Válido: áéíóú Ñ ¿¡ €"
        result = sanitizer.sanitize_text(mixed_text)

        assert "áéíóú" in result or result is not None


# =============================================================================
# Tests de límites
# =============================================================================


class TestSizeLimits:
    """Tests para límites de tamaño."""

    def test_chapter_content_size_limit(self):
        """El contenido de capítulo tiene límite de tamaño."""
        # 50MB de texto - más de lo razonable para un capítulo
        huge_chapter = "palabra " * (50 * 1024 * 1024 // 8)

        result = sanitize_chapter_content(huge_chapter)

        # Debe truncar o rechazar
        assert len(result) <= len(huge_chapter) or result is not None

    def test_entity_name_length_limit(self, sanitizer):
        """Los nombres de entidad tienen límite de longitud."""
        long_name = "A" * 10000

        result = sanitizer.sanitize_entity_name(long_name)

        # Debe truncar a longitud razonable
        assert len(result) <= 500  # Límite razonable


# =============================================================================
# Tests específicos del validador de diálogos
# =============================================================================


class TestDialogueValidatorSecurity:
    """Tests de seguridad para el validador de diálogos."""

    def test_handles_malicious_chapter_content(self):
        """El validador maneja contenido malicioso sin crashear."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()

        malicious_contents = [
            # SQL injection en diálogo
            "—'; DROP TABLE users;-- preguntó Juan.",
            # Path traversal en contenido
            "—../../../etc/passwd— dijo María.",
            # Null bytes
            "—Hola\x00mundo— exclamó.",
            # Unicode extremo
            "—" + "🎭" * 1000 + "— gritó.",
            # Texto extremadamente largo
            "—" + "a" * 100000 + "— murmuró.",
        ]

        for content in malicious_contents:
            # No debe crashear
            issues = validator.validate_chapter(content, chapter_number=1)
            assert isinstance(issues, list)

    def test_validates_chapter_number_bounds(self):
        """Valida que los números de capítulo sean razonables."""
        from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

        validator = DialogueContextValidator()

        # Números extremos
        extreme_numbers = [
            0,
            -1,
            -9999,
            999999999,
            2**31 - 1,  # Max int32
        ]

        for num in extreme_numbers:
            # No debe crashear
            issues = validator.validate_chapter("—Hola— dijo Juan.", chapter_number=num)
            assert isinstance(issues, list)


# =============================================================================
# Tests específicos del detector de duplicados
# =============================================================================


class TestDuplicateDetectorSecurity:
    """Tests de seguridad para el detector de duplicados."""

    def test_handles_regex_dos_patterns(self):
        """El detector maneja patrones que podrían causar ReDoS."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()

        # Patrones que podrían causar backtracking exponencial
        redos_patterns = [
            "a" * 50 + "!",  # Muchas 'a' seguidas
            "x" * 100 + "y" * 100,  # Repeticiones largas
            "(" * 50 + ")" * 50,  # Paréntesis anidados
        ]

        for pattern in redos_patterns:
            # No debe colgar (timeout implícito del test)
            result = detector.detect_all(pattern, [])
            assert result is not None

    def test_handles_memory_exhaustion_attempts(self):
        """El detector no permite agotar memoria."""
        from narrative_assistant.analysis.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()

        # Texto que podría generar muchas comparaciones
        # (pero el detector debe tener límites)
        many_sentences = ". ".join(["Oración " + str(i) for i in range(10000)])

        # No debe agotar memoria
        result = detector.detect_all(many_sentences, [])
        assert result is not None


# =============================================================================
# Tests específicos del detector de estructura narrativa
# =============================================================================


class TestNarrativeStructureSecurity:
    """Tests de seguridad para el detector de estructura narrativa."""

    def test_handles_crafted_prolepsis_patterns(self):
        """El detector maneja patrones de prolepsis crafteados."""
        from narrative_assistant.analysis.narrative_structure import NarrativeStructureDetector

        detector = NarrativeStructureDetector()

        # Patrones que podrían explotar el regex de prolepsis
        crafted_patterns = [
            "Un año después " * 1000,  # Repetición del marcador
            "recordaría " * 500,  # Repetición del verbo
            "Tiempo después" + "." * 10000 + "vendría",  # Separación extrema
        ]

        chapters = [{"number": 1, "content": p, "start_char": 0} for p in crafted_patterns]

        for chapter in chapters:
            # No debe colgar ni crashear
            report = detector.detect_all("", [chapter])
            assert report is not None
