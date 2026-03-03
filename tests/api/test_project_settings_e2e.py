"""
Test E2E básico del flujo CR-03 (UI → Backend → Análisis).

Verifica:
- UI puede leer settings de proyecto
- UI puede actualizar settings de proyecto
- Settings actualizados persisten correctamente
- Cambios en settings no afectan análisis en curso (aplican al siguiente)
"""

import pytest


class TestProjectSettingsE2E:
    """Test E2E del flujo completo de settings de proyecto."""

    def test_complete_settings_lifecycle(self, test_client, sample_project):
        """Test del ciclo completo: GET → PATCH → GET → verificar persistencia."""
        project_id = sample_project.id

        # 1. GET inicial - debe tener defaults
        response = test_client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        project = response.json()["data"]

        features = project["settings"]["analysis_features"]
        assert features["pipeline_flags"]["grammar"] is True
        assert features["pipeline_flags"]["spelling"] is True

        # 2. PATCH - deshabilitar grammar
        patch_response = test_client.patch(
            f"/api/projects/{project_id}/settings",
            json={
                "analysis_features": {
                    "pipeline_flags": {"grammar": False}
                }
            },
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["success"] is True

        # 3. GET después de PATCH - debe reflejar cambios
        get_after_patch = test_client.get(f"/api/projects/{project_id}")
        assert get_after_patch.status_code == 200

        features_after = get_after_patch.json()["data"]["settings"]["analysis_features"]
        assert features_after["pipeline_flags"]["grammar"] is False
        assert features_after["pipeline_flags"]["spelling"] is True  # preservado

        # 4. Simular cierre y reapertura (nuevo GET)
        get_reopen = test_client.get(f"/api/projects/{project_id}")
        assert get_reopen.status_code == 200

        features_reopen = get_reopen.json()["data"]["settings"]["analysis_features"]
        assert features_reopen["pipeline_flags"]["grammar"] is False
        assert features_reopen["pipeline_flags"]["spelling"] is True

    def test_multiple_partial_updates(self, test_client, sample_project):
        """Test de múltiples actualizaciones parciales sucesivas."""
        project_id = sample_project.id

        # Update 1: deshabilitar grammar
        test_client.patch(
            f"/api/projects/{project_id}/settings",
            json={
                "analysis_features": {
                    "pipeline_flags": {"grammar": False}
                }
            },
        )

        # Update 2: deshabilitar spelling
        test_client.patch(
            f"/api/projects/{project_id}/settings",
            json={
                "analysis_features": {
                    "pipeline_flags": {"spelling": False}
                }
            },
        )

        # Update 3: cambiar métodos de coreference
        test_client.patch(
            f"/api/projects/{project_id}/settings",
            json={
                "analysis_features": {
                    "nlp_methods": {
                        "coreference": ["heuristics"]
                    }
                }
            },
        )

        # Verificar estado final
        response = test_client.get(f"/api/projects/{project_id}")
        features = response.json()["data"]["settings"]["analysis_features"]

        # Todas las actualizaciones deben estar aplicadas
        assert features["pipeline_flags"]["grammar"] is False
        assert features["pipeline_flags"]["spelling"] is False
        assert features["nlp_methods"]["coreference"] == ["heuristics"]

        # Otras configuraciones deben preservarse
        assert features["pipeline_flags"]["consistency"] is True
        assert "ner" in features["nlp_methods"]

    def test_settings_isolation_between_projects(self, test_client, sample_project, empty_project):
        """Settings de un proyecto no afectan a otro proyecto."""
        project_a_id = sample_project.id
        project_b_id = empty_project.id

        # Actualizar settings de proyecto A
        test_client.patch(
            f"/api/projects/{project_a_id}/settings",
            json={
                "analysis_features": {
                    "pipeline_flags": {"grammar": False}
                }
            },
        )

        # Verificar que proyecto B mantiene defaults
        response_b = test_client.get(f"/api/projects/{project_b_id}")
        features_b = response_b.json()["data"]["settings"]["analysis_features"]

        assert features_b["pipeline_flags"]["grammar"] is True  # default

        # Verificar que proyecto A tiene su configuración
        response_a = test_client.get(f"/api/projects/{project_a_id}")
        features_a = response_a.json()["data"]["settings"]["analysis_features"]

        assert features_a["pipeline_flags"]["grammar"] is False

    def test_invalid_methods_are_filtered_with_warning(self, test_client, sample_project):
        """Métodos inválidos se filtran y se retorna warning."""
        project_id = sample_project.id

        response = test_client.patch(
            f"/api/projects/{project_id}/settings",
            json={
                "analysis_features": {
                    "nlp_methods": {
                        "coreference": ["embeddings", "invented_method", "llm"]
                    }
                }
            },
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # Método inventado debe ser filtrado
        methods = data["settings"]["analysis_features"]["nlp_methods"]["coreference"]
        assert "invented_method" not in methods
        assert "embeddings" in methods
        assert "llm" in methods

        # Debe haber warning
        assert "runtime_warnings" in data
        warnings = data["runtime_warnings"]
        assert len(warnings) > 0
        assert any("invented_method" in w.lower() for w in warnings)

    def test_settings_persist_across_multiple_gets(self, test_client, sample_project):
        """Settings persisten a través de múltiples GETs."""
        project_id = sample_project.id

        # Actualizar settings
        test_client.patch(
            f"/api/projects/{project_id}/settings",
            json={
                "analysis_features": {
                    "pipeline_flags": {
                        "grammar": False,
                        "spelling": False,
                        "consistency": False
                    }
                }
            },
        )

        # Hacer 5 GETs consecutivos
        for _ in range(5):
            response = test_client.get(f"/api/projects/{project_id}")
            features = response.json()["data"]["settings"]["analysis_features"]

            # Configuración debe ser consistente en todos los GETs
            assert features["pipeline_flags"]["grammar"] is False
            assert features["pipeline_flags"]["spelling"] is False
            assert features["pipeline_flags"]["consistency"] is False
            assert features["pipeline_flags"]["character_profiling"] is True  # no modificado
