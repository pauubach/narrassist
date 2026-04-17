"""
Test rápido para verificar integración de FillerDetector en pipeline.
"""

import sys
sys.path.insert(0, 'src')


def test_filler_detector_integration():
    """Verificar que FillerDetector se integra correctamente en pipeline."""
    from narrative_assistant.nlp.style.filler_detector import get_filler_detector

    # Texto con muletillas
    text = """
    O sea, la verdad es que básicamente pensé que, en realidad,
    el problema era muy complejo. Entonces, o sea, decidí que
    literalmente tenía que hacer algo. La verdad, es que o sea,
    no sabía qué hacer exactamente.
    """ * 10  # Repetir para tener suficiente texto

    detector = get_filler_detector()
    result = detector.detect(text, chapter_id=1)

    print("Test FillerDetector Integration:")
    print(f"  - Texto: {len(text)} caracteres, ~{len(text.split())} palabras")
    print(f"  - Result: {'SUCCESS' if result.is_success else 'FAILURE'}")

    if result.is_success:
        report = result.value
        print(f"  - Total muletillas detectadas: {report.total_fillers}")
        print(f"  - Muletillas excesivas: {report.excessive_fillers}")

        for filler in report.fillers[:5]:
            print(f"    * '{filler.phrase}': {filler.count} veces "
                  f"({filler.frequency_per_1000:.1f}/1k) - "
                  f"{'EXCESSIVE' if filler.is_excessive else 'OK'}")

        assert report.total_fillers > 0, "Debe detectar al menos una muletilla"
        assert report.excessive_fillers > 0, "Debe haber al menos una muletilla excesiva"

        print("  OK FillerDetector funciona correctamente")
    else:
        print(f"  FAIL: {result.error}")
        sys.exit(1)


def test_filler_in_pipeline_context():
    """Verificar que el método _run_filler_detection existe y es callable."""
    from narrative_assistant.pipelines.ua_quality import PipelineQualityMixin

    print("\nTest FillerDetector en Pipeline:")

    # Verificar que el método existe
    assert hasattr(PipelineQualityMixin, '_run_filler_detection'), \
        "PipelineQualityMixin debe tener método _run_filler_detection"

    method = getattr(PipelineQualityMixin, '_run_filler_detection')
    assert callable(method), "El método debe ser callable"

    print("  OK Método _run_filler_detection existe en pipeline")


if __name__ == "__main__":
    print("=" * 60)
    print("Test Integración FillerDetector")
    print("=" * 60)

    try:
        test_filler_detector_integration()
        test_filler_in_pipeline_context()

        print("\n" + "=" * 60)
        print("OK TODOS LOS TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\nFAIL TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nFAIL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
