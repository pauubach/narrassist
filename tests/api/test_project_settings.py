"""
Tests de contrato para endpoints de settings de proyecto (CR-03).

Verifica:
- GET /api/projects/{id} incluye settings.analysis_features en envelope data
- PATCH /api/projects/{id}/settings con merge profundo
- Validación de métodos contra schema conocido
- Defaults cuando proyecto sin settings
- Runtime warnings en respuesta
"""

import pytest


class TestProjectSettingsContract:
    """Tests de contrato API para settings de proyecto."""

    def test_get_project_includes_settings_in_data_envelope(self, test_client, sample_project):
        """GET proyecto incluye settings.analysis_features en envelope data."""
        response = test_client.get(f"/api/projects/{sample_project.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "data" in data

        project = data["data"]
        assert "settings" in project
        assert "analysis_features" in project["settings"]

        features = project["settings"]["analysis_features"]
        assert "schema_version" in features
        assert features["schema_version"] == 1
        assert "pipeline_flags" in features
        assert "nlp_methods" in features
        assert "updated_at" in features
        assert "updated_by" in features

    def test_get_project_returns_defaults_when_no_settings(self, test_client, sample_project):
        """GET proyecto sin settings devuelve defaults calculados (sin escribir DB)."""
        response = test_client.get(f"/api/projects/{sample_project.id}")
        assert response.status_code == 200

        project = response.json()["data"]
        features = project["settings"]["analysis_features"]

        # Defaults: 11 pipeline_flags = true
        flags = features["pipeline_flags"]
        assert flags["character_profiling"] is True
        assert flags["network_analysis"] is True
        assert flags["anachronism_detection"] is True
        assert flags["ooc_detection"] is True
        assert flags["classical_spanish"] is True
        assert flags["name_variants"] is True
        assert flags["multi_model_voting"] is True
        assert flags["spelling"] is True
        assert flags["grammar"] is True
        assert flags["consistency"] is True
        assert flags["speech_tracking"] is True

        # Defaults: nlp_methods con métodos básicos
        methods = features["nlp_methods"]
        assert "coreference" in methods
        assert "ner" in methods
        assert "grammar" in methods
        assert "spelling" in methods
        assert "character_knowledge" in methods

        # Defaults de umbrales de votación
        thresholds = features["voting_thresholds"]
        assert thresholds["inferenceMinConfidence"] == 55
        assert thresholds["inferenceMinConsensus"] == 60

    def test_patch_settings_with_partial_update(self, test_client, sample_project):
        """PATCH settings con actualización parcial (merge profundo)."""
        # Actualización parcial: solo deshabilitar grammar
        response = test_client.patch(
            f"/api/projects/{sample_project.id}/settings",
            json={
                "analysis_features": {
                    "schema_version": 1,
                    "pipeline_flags": {"grammar": False},
                }
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "data" in data

        result = data["data"]
        assert "settings" in result

        features = result["settings"]["analysis_features"]

        # grammar debe estar en false
        assert features["pipeline_flags"]["grammar"] is False

        # Otros flags deben preservarse (merge profundo)
        assert features["pipeline_flags"]["spelling"] is True
        assert features["pipeline_flags"]["consistency"] is True

        # nlp_methods debe preservarse
        assert "coreference" in features["nlp_methods"]

    def test_patch_settings_nlp_methods_replaces_category(self, test_client, sample_project):
        """PATCH con nlp_methods: reemplazo completo por categoría."""
        # Actualizar solo coreference (debe reemplazar completo)
        response = test_client.patch(
            f"/api/projects/{sample_project.id}/settings",
            json={
                "analysis_features": {
                    "schema_version": 1,
                    "nlp_methods": {
                        "coreference": ["morpho", "heuristics"],  # Solo 2 métodos
                    },
                }
            },
        )
        assert response.status_code == 200

        features = response.json()["data"]["settings"]["analysis_features"]

        # coreference debe tener SOLO los 2 métodos especificados
        assert set(features["nlp_methods"]["coreference"]) == {"morpho", "heuristics"}

        # Otras categorías deben preservarse
        assert "ner" in features["nlp_methods"]
        assert "grammar" in features["nlp_methods"]

    def test_patch_settings_persists_voting_thresholds(self, test_client, sample_project):
        """PATCH persiste voting_thresholds y GET posterior los refleja."""
        response = test_client.patch(
            f"/api/projects/{sample_project.id}/settings",
            json={
                "analysis_features": {
                    "voting_thresholds": {
                        "inferenceMinConfidence": 72,
                        "inferenceMinConsensus": 81,
                    }
                }
            },
        )
        assert response.status_code == 200

        features = response.json()["data"]["settings"]["analysis_features"]
        assert features["voting_thresholds"]["inferenceMinConfidence"] == 72
        assert features["voting_thresholds"]["inferenceMinConsensus"] == 81

        get_response = test_client.get(f"/api/projects/{sample_project.id}")
        assert get_response.status_code == 200
        persisted = get_response.json()["data"]["settings"]["analysis_features"]["voting_thresholds"]
        assert persisted["inferenceMinConfidence"] == 72
        assert persisted["inferenceMinConsensus"] == 81

    def test_patch_settings_voting_thresholds_supports_partial_merge(
        self, test_client, sample_project
    ):
        """PATCH parcial de voting_thresholds solo modifica la clave enviada."""
        test_client.patch(
            f"/api/projects/{sample_project.id}/settings",
            json={
                "analysis_features": {
                    "voting_thresholds": {
                        "inferenceMinConfidence": 70,
                        "inferenceMinConsensus": 80,
                    }
                }
            },
        )

        response = test_client.patch(
            f"/api/projects/{sample_project.id}/settings",
            json={
                "analysis_features": {
                    "voting_thresholds": {
                        "inferenceMinConsensus": 68,
                    }
                }
            },
        )
        assert response.status_code == 200
        thresholds = response.json()["data"]["settings"]["analysis_features"]["voting_thresholds"]
        assert thresholds["inferenceMinConfidence"] == 70
        assert thresholds["inferenceMinConsensus"] == 68

    def test_patch_settings_validates_unknown_methods(self, test_client, sample_project):
        """PATCH con métodos desconocidos: sanitiza y reporta warning."""
        # Enviar método inventado
        response = test_client.patch(
            f"/api/projects/{sample_project.id}/settings",
            json={
                "analysis_features": {
                    "schema_version": 1,
                    "nlp_methods": {
                        "coreference": ["embeddings", "invented_method", "llm"],
                    },
                }
            },
        )
        assert response.status_code == 200

        data = response.json()["data"]

        # Método inventado debe eliminarse
        methods = data["settings"]["analysis_features"]["nlp_methods"]["coreference"]
        assert "invented_method" not in methods
        assert "embeddings" in methods
        assert "llm" in methods

        # Debe reportar warning
        assert "runtime_warnings" in data
        warnings = data["runtime_warnings"]
        assert any("desconocido" in w.lower() or "unknown" in w.lower() for w in warnings)

    def test_patch_settings_preserves_other_settings_branches(self, test_client, sample_project):
        """PATCH preserva otras ramas de settings no incluidas en el request."""
        # Primero, establecer settings completos
        test_client.patch(
            f"/api/projects/{sample_project.id}/settings",
            json={
                "analysis_features": {
                    "schema_version": 1,
                    "pipeline_flags": {"grammar": False},
                    "nlp_methods": {"coreference": ["morpho"]},
                }
            },
        )

        # Actualizar solo pipeline_flags
        response = test_client.patch(
            f"/api/projects/{sample_project.id}/settings",
            json={
                "analysis_features": {
                    "pipeline_flags": {"spelling": False},
                }
            },
        )
        assert response.status_code == 200

        features = response.json()["data"]["settings"]["analysis_features"]

        # Ambos flags deben estar actualizados
        assert features["pipeline_flags"]["grammar"] is False  # Preservado
        assert features["pipeline_flags"]["spelling"] is False  # Nuevo

        # nlp_methods debe preservarse
        assert features["nlp_methods"]["coreference"] == ["morpho"]

    def test_patch_settings_invalid_project_id(self, test_client):
        """PATCH con ID de proyecto inválido retorna 404."""
        response = test_client.patch(
            "/api/projects/99999/settings",
            json={
                "analysis_features": {
                    "pipeline_flags": {"grammar": False},
                }
            },
        )
        assert response.status_code == 404

    def test_patch_settings_updates_metadata(self, test_client, sample_project):
        """PATCH actualiza metadata (updated_at, updated_by)."""
        response = test_client.patch(
            f"/api/projects/{sample_project.id}/settings",
            json={
                "analysis_features": {
                    "pipeline_flags": {"grammar": False},
                }
            },
        )
        assert response.status_code == 200

        features = response.json()["data"]["settings"]["analysis_features"]

        assert "updated_at" in features
        assert features["updated_at"] is not None
        assert "updated_by" in features
        assert features["updated_by"] == "api"

    def test_patch_settings_rejects_non_boolean_pipeline_flag(self, test_client, sample_project):
        """PATCH con flag no booleano retorna 400 (validación estricta)."""
        response = test_client.patch(
            f"/api/projects/{sample_project.id}/settings",
            json={
                "analysis_features": {
                    "pipeline_flags": {"grammar": "false"},
                }
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "boolean" in data["detail"].lower()

    def test_patch_settings_rejects_invalid_voting_threshold_type(
        self, test_client, sample_project
    ):
        """PATCH con umbral no numérico retorna 400."""
        response = test_client.patch(
            f"/api/projects/{sample_project.id}/settings",
            json={
                "analysis_features": {
                    "voting_thresholds": {
                        "inferenceMinConfidence": "alto",
                    }
                }
            },
        )
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "numérico" in detail

    def test_patch_settings_rejects_voting_threshold_out_of_range(
        self, test_client, sample_project
    ):
        """PATCH con umbral fuera de rango (0-100) retorna 400."""
        response = test_client.patch(
            f"/api/projects/{sample_project.id}/settings",
            json={
                "analysis_features": {
                    "voting_thresholds": {
                        "inferenceMinConsensus": 140,
                    }
                }
            },
        )
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "fuera de rango" in detail

    def test_get_project_after_patch_reflects_changes(self, test_client, sample_project):
        """GET después de PATCH refleja los cambios persistidos."""
        # PATCH
        test_client.patch(
            f"/api/projects/{sample_project.id}/settings",
            json={
                "analysis_features": {
                    "pipeline_flags": {"grammar": False, "spelling": False},
                    "nlp_methods": {"coreference": ["heuristics"]},
                }
            },
        )

        # GET
        response = test_client.get(f"/api/projects/{sample_project.id}")
        assert response.status_code == 200

        features = response.json()["data"]["settings"]["analysis_features"]

        # Verificar persistencia
        assert features["pipeline_flags"]["grammar"] is False
        assert features["pipeline_flags"]["spelling"] is False
        assert features["nlp_methods"]["coreference"] == ["heuristics"]
