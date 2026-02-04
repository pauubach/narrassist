"""
Tests para el modulo de focalizacion.
"""

import pytest

from narrative_assistant.focalization import (
    FocalizationDeclaration,
    FocalizationDeclarationService,
    FocalizationScope,
    FocalizationType,
    FocalizationViolation,
    FocalizationViolationDetector,
    ViolationSeverity,
    ViolationType,
)
from narrative_assistant.focalization.violations import detect_focalization_violations

# =============================================================================
# Tests de FocalizationDeclaration
# =============================================================================


class TestFocalizationDeclaration:
    """Tests para declaraciones de focalizacion."""

    def test_declaration_creation(self):
        """Creacion basica de declaracion."""
        dec = FocalizationDeclaration(
            id=1,
            project_id=1,
            chapter=1,
            focalization_type=FocalizationType.INTERNAL_FIXED,
            focalizer_ids=[1],
        )
        assert dec.id == 1
        assert dec.chapter == 1
        assert dec.focalization_type == FocalizationType.INTERNAL_FIXED
        assert dec.focalizer_ids == [1]

    def test_declaration_to_dict(self):
        """Conversion a diccionario."""
        dec = FocalizationDeclaration(
            id=1,
            project_id=1,
            chapter=2,
            focalization_type=FocalizationType.ZERO,
            focalizer_ids=[],
        )
        d = dec.to_dict()
        assert d["id"] == 1
        assert d["chapter"] == 2
        assert d["focalization_type"] == "zero"


class TestFocalizationScope:
    """Tests para alcance de focalizacion."""

    def test_scope_single_chapter(self):
        """Alcance de un solo capitulo."""
        scope = FocalizationScope(start_chapter=5)
        assert scope.contains(5)
        assert not scope.contains(4)
        assert not scope.contains(6)

    def test_scope_chapter_range(self):
        """Alcance de rango de capitulos."""
        scope = FocalizationScope(start_chapter=2, end_chapter=5)
        assert scope.contains(2)
        assert scope.contains(3)
        assert scope.contains(5)
        assert not scope.contains(1)
        assert not scope.contains(6)

    def test_scope_with_scenes(self):
        """Alcance con escenas."""
        scope = FocalizationScope(start_chapter=1, start_scene=2, end_chapter=1, end_scene=5)
        assert scope.contains(1, 2)
        assert scope.contains(1, 3)
        assert scope.contains(1, 5)
        assert not scope.contains(1, 1)
        assert not scope.contains(1, 6)


# =============================================================================
# Tests de FocalizationDeclarationService
# =============================================================================


class TestFocalizationDeclarationService:
    """Tests para el servicio de declaraciones."""

    @pytest.fixture
    def service(self):
        """Servicio con repositorio en memoria."""
        return FocalizationDeclarationService()

    def test_declare_internal_fixed(self, service):
        """Declarar focalizacion interna fija."""
        dec = service.declare_focalization(
            project_id=1,
            chapter=1,
            focalization_type=FocalizationType.INTERNAL_FIXED,
            focalizer_ids=[1],
            notes="Desde el punto de vista de Juan",
        )
        assert dec.id == 1
        assert dec.focalization_type == FocalizationType.INTERNAL_FIXED
        assert dec.focalizer_ids == [1]

    def test_declare_zero(self, service):
        """Declarar focalizacion omnisciente."""
        dec = service.declare_focalization(
            project_id=1, chapter=2, focalization_type=FocalizationType.ZERO, focalizer_ids=[]
        )
        assert dec.focalization_type == FocalizationType.ZERO
        assert dec.focalizer_ids == []

    def test_declare_external(self, service):
        """Declarar focalizacion externa."""
        dec = service.declare_focalization(
            project_id=1, chapter=3, focalization_type=FocalizationType.EXTERNAL, focalizer_ids=[]
        )
        assert dec.focalization_type == FocalizationType.EXTERNAL

    def test_declare_internal_variable(self, service):
        """Declarar focalizacion interna variable."""
        dec = service.declare_focalization(
            project_id=1,
            chapter=4,
            focalization_type=FocalizationType.INTERNAL_VARIABLE,
            focalizer_ids=[1, 2],
        )
        assert dec.focalization_type == FocalizationType.INTERNAL_VARIABLE
        assert len(dec.focalizer_ids) == 2

    def test_declare_internal_multiple(self, service):
        """Declarar focalizacion interna multiple."""
        dec = service.declare_focalization(
            project_id=1,
            chapter=5,
            focalization_type=FocalizationType.INTERNAL_MULTIPLE,
            focalizer_ids=[1, 2, 3],
        )
        assert dec.focalization_type == FocalizationType.INTERNAL_MULTIPLE
        assert len(dec.focalizer_ids) == 3

    def test_invalid_internal_fixed_multiple_focalizers(self, service):
        """Focalizacion interna fija requiere exactamente un focalizador."""
        with pytest.raises(ValueError, match="exactly 1 focalizer"):
            service.declare_focalization(
                project_id=1,
                chapter=1,
                focalization_type=FocalizationType.INTERNAL_FIXED,
                focalizer_ids=[1, 2],
            )

    def test_invalid_external_with_focalizers(self, service):
        """Focalizacion externa no debe tener focalizadores."""
        with pytest.raises(ValueError, match="should not have focalizers"):
            service.declare_focalization(
                project_id=1,
                chapter=1,
                focalization_type=FocalizationType.EXTERNAL,
                focalizer_ids=[1],
            )

    def test_invalid_internal_multiple_one_focalizer(self, service):
        """Focalizacion interna multiple requiere al menos 2 focalizadores."""
        with pytest.raises(ValueError, match="at least 2 focalizers"):
            service.declare_focalization(
                project_id=1,
                chapter=1,
                focalization_type=FocalizationType.INTERNAL_MULTIPLE,
                focalizer_ids=[1],
            )

    def test_get_focalization(self, service):
        """Obtener focalizacion por capitulo."""
        service.declare_focalization(
            project_id=1,
            chapter=1,
            focalization_type=FocalizationType.INTERNAL_FIXED,
            focalizer_ids=[1],
        )
        foc = service.get_focalization(project_id=1, chapter=1)
        assert foc is not None
        assert foc.focalization_type == FocalizationType.INTERNAL_FIXED

    def test_get_focalization_not_found(self, service):
        """Obtener focalizacion inexistente."""
        foc = service.get_focalization(project_id=1, chapter=99)
        assert foc is None

    def test_get_all_declarations(self, service):
        """Obtener todas las declaraciones."""
        service.declare_focalization(
            project_id=1,
            chapter=1,
            focalization_type=FocalizationType.INTERNAL_FIXED,
            focalizer_ids=[1],
        )
        service.declare_focalization(
            project_id=1, chapter=2, focalization_type=FocalizationType.ZERO, focalizer_ids=[]
        )
        service.declare_focalization(
            project_id=2,
            chapter=1,  # Otro proyecto
            focalization_type=FocalizationType.EXTERNAL,
            focalizer_ids=[],
        )

        decs = service.get_all_declarations(project_id=1)
        assert len(decs) == 2

    def test_update_focalization(self, service):
        """Actualizar declaracion existente."""
        dec = service.declare_focalization(
            project_id=1,
            chapter=1,
            focalization_type=FocalizationType.INTERNAL_FIXED,
            focalizer_ids=[1],
        )

        updated = service.update_focalization(
            declaration_id=dec.id, focalizer_ids=[2], notes="Cambiado a Maria"
        )

        assert updated.focalizer_ids == [2]
        assert updated.notes == "Cambiado a Maria"
        assert updated.is_validated == False

    def test_delete_focalization(self, service):
        """Eliminar declaracion."""
        dec = service.declare_focalization(
            project_id=1, chapter=1, focalization_type=FocalizationType.ZERO, focalizer_ids=[]
        )

        result = service.delete_focalization(dec.id)
        assert result == True

        foc = service.get_focalization(project_id=1, chapter=1)
        assert foc is None

    def test_generate_summary(self, service):
        """Generar resumen de focalizacion."""
        service.declare_focalization(
            project_id=1,
            chapter=1,
            focalization_type=FocalizationType.INTERNAL_FIXED,
            focalizer_ids=[1],
        )
        service.declare_focalization(
            project_id=1, chapter=2, focalization_type=FocalizationType.ZERO, focalizer_ids=[]
        )

        summary = service.generate_summary(project_id=1)
        assert "internal_fixed" in summary
        assert "zero" in summary
        assert "Total de declaraciones: 2" in summary


# =============================================================================
# Tests de FocalizationViolationDetector
# =============================================================================


class MockEntity:
    """Entidad mock para tests."""

    def __init__(self, id, name, aliases=None):
        self.id = id
        self.canonical_name = name
        self.name = name
        self.aliases = aliases or []
        self.entity_type = "person"


class TestFocalizationViolationDetector:
    """Tests para el detector de violaciones."""

    @pytest.fixture
    def entities(self):
        """Entidades de ejemplo."""
        return [
            MockEntity(1, "Juan"),
            MockEntity(2, "Maria"),
            MockEntity(3, "Pedro"),
        ]

    @pytest.fixture
    def service_internal_fixed(self):
        """Servicio con focalizacion interna fija en Juan."""
        service = FocalizationDeclarationService()
        service.declare_focalization(
            project_id=1,
            chapter=1,
            focalization_type=FocalizationType.INTERNAL_FIXED,
            focalizer_ids=[1],  # Juan
        )
        return service

    @pytest.fixture
    def service_external(self):
        """Servicio con focalizacion externa."""
        service = FocalizationDeclarationService()
        service.declare_focalization(
            project_id=1, chapter=1, focalization_type=FocalizationType.EXTERNAL, focalizer_ids=[]
        )
        return service

    @pytest.fixture
    def service_zero(self):
        """Servicio con focalizacion omnisciente."""
        service = FocalizationDeclarationService()
        service.declare_focalization(
            project_id=1, chapter=1, focalization_type=FocalizationType.ZERO, focalizer_ids=[]
        )
        return service

    def test_internal_fixed_no_violation(self, service_internal_fixed, entities):
        """Sin violacion cuando el focalizador piensa."""
        detector = FocalizationViolationDetector(service_internal_fixed, entities)

        text = "Juan penso que todo saldria bien."
        violations = detector.detect_violations(project_id=1, text=text, chapter=1)

        assert len(violations) == 0

    def test_internal_fixed_violation_other_mind(self, service_internal_fixed, entities):
        """Violacion al acceder a mente de otro personaje."""
        detector = FocalizationViolationDetector(service_internal_fixed, entities)

        text = "Maria sintio una punzada de tristeza."
        violations = detector.detect_violations(project_id=1, text=text, chapter=1)

        assert len(violations) >= 1
        assert violations[0].violation_type == ViolationType.FORBIDDEN_MIND_ACCESS
        assert violations[0].entity_name == "Maria"

    def test_internal_fixed_multiple_violations(self, service_internal_fixed, entities):
        """Multiples violaciones en un texto."""
        detector = FocalizationViolationDetector(service_internal_fixed, entities)

        text = """
        Juan caminaba por la calle pensando en sus problemas.
        Maria penso que algo no iba bien.
        Pedro sabia que algo andaba mal.
        """
        violations = detector.detect_violations(project_id=1, text=text, chapter=1)

        # Deberia detectar acceso a Maria y Pedro
        assert len(violations) >= 2
        names = {v.entity_name for v in violations}
        assert "Maria" in names
        assert "Pedro" in names

    def test_external_violation_any_thought(self, service_external, entities):
        """Violacion en focalizacion externa al acceder a cualquier pensamiento."""
        detector = FocalizationViolationDetector(service_external, entities)

        text = "Juan penso que era hora de actuar."
        violations = detector.detect_violations(project_id=1, text=text, chapter=1)

        assert len(violations) >= 1
        assert violations[0].violation_type == ViolationType.THOUGHT_IN_EXTERNAL

    def test_external_no_violation_observable(self, service_external, entities):
        """Sin violacion en focalizacion externa con acciones observables."""
        detector = FocalizationViolationDetector(service_external, entities)

        text = "Juan camino hacia la puerta y la abrio."
        violations = detector.detect_violations(project_id=1, text=text, chapter=1)

        assert len(violations) == 0

    def test_zero_no_violations(self, service_zero, entities):
        """Focalizacion omnisciente no tiene violaciones."""
        detector = FocalizationViolationDetector(service_zero, entities)

        text = """
        Juan penso que Maria era hermosa.
        Maria sintio que Juan la miraba.
        Pedro sabia que ambos se gustaban.
        """
        violations = detector.detect_violations(project_id=1, text=text, chapter=1)

        # En focalizacion omnisciente no hay violaciones
        assert len(violations) == 0

    def test_no_declaration_no_violations(self, entities):
        """Sin declaracion no se detectan violaciones."""
        service = FocalizationDeclarationService()  # Sin declaraciones
        detector = FocalizationViolationDetector(service, entities)

        text = "Maria penso en Juan."
        violations = detector.detect_violations(project_id=1, text=text, chapter=1)

        assert len(violations) == 0

    def test_validate_chapter(self, service_internal_fixed, entities):
        """Validar capitulo completo."""
        detector = FocalizationViolationDetector(service_internal_fixed, entities)

        text = """
        Juan penso que todo saldria bien.
        Maria sintio miedo al verlo.
        """
        result = detector.validate_chapter(project_id=1, chapter=1, text=text)

        assert result["chapter"] == 1
        assert result["total_violations"] >= 1
        assert "by_type" in result
        assert "by_severity" in result

    def test_violation_to_dict(self, service_internal_fixed, entities):
        """Conversion de violacion a diccionario."""
        detector = FocalizationViolationDetector(service_internal_fixed, entities)

        text = "Maria sabia que algo andaba mal."
        violations = detector.detect_violations(project_id=1, text=text, chapter=1)

        if violations:
            d = violations[0].to_dict()
            assert "violation_type" in d
            assert "severity" in d
            assert "explanation" in d


class TestFocalizationInternalVariable:
    """Tests para focalizacion interna variable."""

    @pytest.fixture
    def entities(self):
        return [
            MockEntity(1, "Juan"),
            MockEntity(2, "Maria"),
            MockEntity(3, "Pedro"),
        ]

    @pytest.fixture
    def service_variable(self):
        """Servicio con focalizacion variable (Juan y Maria)."""
        service = FocalizationDeclarationService()
        service.declare_focalization(
            project_id=1,
            chapter=1,
            focalization_type=FocalizationType.INTERNAL_VARIABLE,
            focalizer_ids=[1, 2],  # Juan y Maria
        )
        return service

    def test_variable_allowed_focalizers(self, service_variable, entities):
        """Sin violacion para focalizadores permitidos."""
        detector = FocalizationViolationDetector(service_variable, entities)

        text = """
        Juan penso en Maria.
        Maria sintio que Juan la miraba.
        """
        violations = detector.detect_violations(project_id=1, text=text, chapter=1)

        assert len(violations) == 0

    def test_variable_forbidden_focalizer(self, service_variable, entities):
        """Violacion para focalizador no permitido."""
        detector = FocalizationViolationDetector(service_variable, entities)

        text = "Pedro sabia que Juan y Maria se gustaban."
        violations = detector.detect_violations(project_id=1, text=text, chapter=1)

        assert len(violations) >= 1
        assert violations[0].entity_name == "Pedro"


# =============================================================================
# Tests de integracion
# =============================================================================


class TestFocalizationIntegration:
    """Tests de integracion del modulo."""

    def test_detect_focalization_violations_helper(self):
        """Funcion helper de deteccion."""
        chapters = [{"number": 1, "project_id": 1, "content": "Maria penso en Juan."}]

        entities = [
            MockEntity(1, "Juan"),
            MockEntity(2, "Maria"),
        ]

        declarations = [
            {
                "project_id": 1,
                "chapter": 1,
                "focalization_type": "internal_fixed",
                "focalizer_ids": [1],  # Juan
            }
        ]

        service, violations = detect_focalization_violations(chapters, entities, declarations)

        assert service is not None
        assert len(violations) >= 1
        assert violations[0].entity_name == "Maria"

    def test_suggest_focalization(self):
        """Sugerencia de focalizacion."""
        service = FocalizationDeclarationService()

        entities = [
            MockEntity(1, "Juan"),
            MockEntity(2, "Maria"),
        ]

        text = "Juan penso que Maria era hermosa."

        suggestion = service.suggest_focalization(
            project_id=1, chapter=1, text=text, entities=entities
        )

        assert suggestion["suggested_type"] is not None
        assert suggestion["confidence"] > 0
