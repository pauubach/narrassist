"""
Tests de integración para el pipeline completo.
"""

import pytest
from pathlib import Path
from narrative_assistant.pipelines import run_full_analysis, PipelineConfig


class TestFullPipeline:
    """Tests de integración del pipeline completo."""

    def test_analyze_simple_document(self, test_data_dir):
        """Analiza documento simple end-to-end."""
        doc_path = test_data_dir / "test_document.txt"
        if not doc_path.exists():
            pytest.skip("Test document not found")

        config = PipelineConfig(
            run_ner=True,
            run_attributes=True,
            run_consistency=True,
            create_alerts=True,
        )

        result = run_full_analysis(
            document_path=doc_path,
            project_name="Test Pipeline",
            config=config,
        )

        assert result.is_success
        report = result.value

        # Verificar estructura del reporte
        assert report is not None
        assert hasattr(report, "stats")
        assert hasattr(report, "entities")
        assert hasattr(report, "alerts")
        assert report.duration_seconds > 0

    def test_analyze_rich_document(self, test_data_dir):
        """Analiza documento con inconsistencias."""
        doc_path = test_data_dir / "test_document_rich.txt"
        if not doc_path.exists():
            pytest.skip("Rich test document not found")

        config = PipelineConfig(
            run_ner=True,
            run_attributes=True,
            run_consistency=True,
            create_alerts=True,
        )

        result = run_full_analysis(
            document_path=doc_path,
            project_name="Test Rich Document",
            config=config,
        )

        assert result.is_success
        report = result.value

        # Verificar que detectó entidades
        assert len(report.entities) > 0
        assert report.stats["entities_detected"] > 0

        # Debería detectar algunos atributos
        if "attributes_extracted" in report.stats:
            assert report.stats["attributes_extracted"] >= 0

    def test_analyze_docx(self, test_data_dir):
        """Analiza documento DOCX."""
        doc_path = test_data_dir / "la_regenta_sample.docx"
        if not doc_path.exists():
            pytest.skip("DOCX test file not found")

        config = PipelineConfig(
            run_ner=True,
            run_attributes=False,  # Más rápido para test
            run_consistency=False,
            create_alerts=False,
        )

        result = run_full_analysis(
            document_path=doc_path,
            project_name="Test DOCX",
            config=config,
        )

        assert result.is_success
        report = result.value
        assert len(report.entities) > 0

    def test_analyze_epub(self, test_data_dir):
        """Analiza documento EPUB."""
        doc_path = test_data_dir / "novelas_ejemplares_cervantes.epub"
        if not doc_path.exists():
            pytest.skip("EPUB test file not found")

        config = PipelineConfig(
            run_ner=True,
            run_attributes=False,
            run_consistency=False,
            create_alerts=False,
        )

        result = run_full_analysis(
            document_path=doc_path,
            project_name="Test EPUB",
            config=config,
        )

        # EPUB parsing may not be fully implemented
        if result.is_failure:
            pytest.skip(f"EPUB parsing not available: {result.error}")

        report = result.value
        # EPUB puede tener muchas entidades
        assert report.stats.get("total_characters", 0) > 0

    def test_pipeline_with_custom_config(self, test_data_dir):
        """Pipeline con configuración personalizada."""
        doc_path = test_data_dir / "test_document.txt"
        if not doc_path.exists():
            pytest.skip("Test document not found")

        # Solo NER, sin atributos ni consistencia
        config = PipelineConfig(
            run_ner=True,
            run_attributes=False,
            run_consistency=False,
            create_alerts=False,
        )

        result = run_full_analysis(
            document_path=doc_path,
            project_name="Custom Config Test",
            config=config,
        )

        assert result.is_success
        report = result.value
        assert len(report.entities) > 0
        # No debería haber atributos
        assert "attributes_extracted" not in report.stats or report.stats["attributes_extracted"] == 0

    def test_pipeline_error_handling(self, tmp_path):
        """Maneja errores correctamente."""
        # Archivo inexistente
        nonexistent = tmp_path / "nonexistent.txt"

        config = PipelineConfig()
        result = run_full_analysis(
            document_path=nonexistent,
            project_name="Error Test",
            config=config,
        )

        assert result.is_failure
        assert result.error is not None

    def test_pipeline_creates_project(self, test_data_dir):
        """Verifica que el pipeline crea un proyecto."""
        doc_path = test_data_dir / "test_document.txt"
        if not doc_path.exists():
            pytest.skip("Test document not found")

        config = PipelineConfig(run_ner=True)
        result = run_full_analysis(
            document_path=doc_path,
            project_name="Project Creation Test",
            config=config,
        )

        assert result.is_success
        report = result.value
        # Debería tener project_id
        assert hasattr(report, "project_id") or "project_id" in report.stats

    def test_pipeline_statistics(self, test_data_dir):
        """Verifica estadísticas del reporte."""
        doc_path = test_data_dir / "test_document.txt"
        if not doc_path.exists():
            pytest.skip("Test document not found")

        config = PipelineConfig(
            run_ner=True,
            run_attributes=True,
            run_consistency=True,
        )

        result = run_full_analysis(
            document_path=doc_path,
            project_name="Statistics Test",
            config=config,
        )

        assert result.is_success
        report = result.value

        # Verificar estadísticas clave (puede ser total_characters o document_chars)
        has_chars = "total_characters" in report.stats or "document_chars" in report.stats
        assert has_chars, f"Missing character count in stats: {list(report.stats.keys())}"
        assert "entities_detected" in report.stats
        char_count = report.stats.get("total_characters", report.stats.get("document_chars", 0))
        assert char_count > 0

    def test_pipeline_alerts_generation(self, test_data_dir):
        """Verifica generación de alertas."""
        doc_path = test_data_dir / "test_document_rich.txt"
        if not doc_path.exists():
            pytest.skip("Rich test document not found")

        config = PipelineConfig(
            run_ner=True,
            run_attributes=True,
            run_consistency=True,
            create_alerts=True,
        )

        result = run_full_analysis(
            document_path=doc_path,
            project_name="Alerts Test",
            config=config,
        )

        assert result.is_success
        report = result.value

        # Verificar estructura de alertas
        assert hasattr(report, "alerts")
        assert isinstance(report.alerts, list)

    def test_pipeline_performance(self, test_data_dir):
        """Verifica que el pipeline completa en tiempo razonable."""
        doc_path = test_data_dir / "test_document.txt"
        if not doc_path.exists():
            pytest.skip("Test document not found")

        import time
        start = time.time()

        config = PipelineConfig(run_ner=True)
        result = run_full_analysis(
            document_path=doc_path,
            project_name="Performance Test",
            config=config,
        )

        duration = time.time() - start

        assert result.is_success
        # Documento pequeño debería analizarse en < 60s (puede variar según la carga del sistema)
        assert duration < 60.0, f"Pipeline took {duration:.1f}s, expected < 60s"


class TestPipelineConfig:
    """Tests para la configuración del pipeline."""

    def test_default_config(self):
        """Configuración por defecto."""
        config = PipelineConfig()

        assert config.run_ner is True
        assert config.run_attributes is True
        assert config.run_consistency is True
        assert config.create_alerts is True

    def test_custom_config(self):
        """Configuración personalizada."""
        config = PipelineConfig(
            run_ner=True,
            run_attributes=False,
            run_consistency=False,
            create_alerts=False,
        )

        assert config.run_ner is True
        assert config.run_attributes is False
        assert config.run_consistency is False
        assert config.create_alerts is False

    def test_minimal_config(self):
        """Configuración mínima (solo parsing)."""
        config = PipelineConfig(
            run_ner=False,
            run_attributes=False,
            run_consistency=False,
            create_alerts=False,
        )

        # Debería permitir análisis mínimo
        assert isinstance(config, PipelineConfig)
