"""
Test script para verificar por qué el cache DB no está escribiendo snapshots.

Simula el flujo de SpeechMetrics.calculate() con los parámetros que recibe
desde speech_tracker.py cuando se llama desde ua_consistency.py.
"""

import sys
sys.path.insert(0, "src")

from narrative_assistant.analysis.speech_tracking.metrics import SpeechMetrics
from narrative_assistant.analysis.speech_tracking.db_cache import get_db_cache

# Simular llamada a SpeechMetrics.calculate
dialogues = [
    "Hola, ¿cómo estás?",
    "Muy bien, gracias por preguntar.",
    "Perfecto, nos vemos luego."
]

print("=" * 60)
print("TEST: SpeechMetrics.calculate() con cache DB")
print("=" * 60)

# Test 1: Sin fingerprint (debería NO usar cache)
print("\n[TEST 1] Sin document_fingerprint (string vacío)")
metrics1 = SpeechMetrics.calculate(
    dialogues=dialogues,
    use_cache=True,
    character_id=1,
    window_start_chapter=1,
    window_end_chapter=3,
    document_fingerprint="",  # STRING VACÍO
)
print(f"Metrics calculated: {metrics1}")

# Verificar cache
cache = get_db_cache()
stats = cache.get_stats()
print(f"Cache stats: {stats}")
print(f"  Esperado: 0 hits, 0 misses, 0 snapshots (cache deshabilitado por fp vacio)")

# Test 2: Con fingerprint válido (debería usar cache)
print("\n[TEST 2] Con document_fingerprint válido")
test_fp = "5972ab3939ee78c2fb3856c6d5f658c7abc123def456"  # Similar al de Rich
metrics2 = SpeechMetrics.calculate(
    dialogues=dialogues,
    use_cache=True,
    character_id=1,
    window_start_chapter=1,
    window_end_chapter=3,
    document_fingerprint=test_fp,
)
print(f"Metrics calculated: {metrics2}")

# Verificar cache
stats = cache.get_stats()
print(f"Cache stats: {stats}")
print(f"  -> Esperado: 0 hits, 1 miss, 1 snapshot (first write)")

# Test 3: Segunda llamada con mismo fingerprint (debería ser cache HIT)
print("\n[TEST 3] Segunda llamada con mismo fingerprint (debería ser HIT)")
metrics3 = SpeechMetrics.calculate(
    dialogues=dialogues,
    use_cache=True,
    character_id=1,
    window_start_chapter=1,
    window_end_chapter=3,
    document_fingerprint=test_fp,
)
print(f"Metrics from cache: {metrics3}")

# Verificar cache
stats = cache.get_stats()
print(f"Cache stats: {stats}")
print(f"  -> Esperado: 1 hit, 1 miss, 1 snapshot (cache HIT)")

# Test 4: Con fingerprint None (debería NO usar cache)
print("\n[TEST 4] Con document_fingerprint=None")
metrics4 = SpeechMetrics.calculate(
    dialogues=dialogues,
    use_cache=True,
    character_id=1,
    window_start_chapter=1,
    window_end_chapter=3,
    document_fingerprint=None,
)
print(f"Metrics calculated: {metrics4}")

# Verificar cache
stats = cache.get_stats()
print(f"Cache stats: {stats}")
print(f"  -> Esperado: 1 hit, 1 miss, 1 snapshot (NO cambió)")

print("\n" + "=" * 60)
print("FIN DEL TEST")
print("=" * 60)
