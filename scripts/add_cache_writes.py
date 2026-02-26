"""Script para añadir escritura de caché a todos los endpoints de prose.py"""

import re

# Mapeo de enrichment_type -> phase
ENRICHMENT_PHASES = {
    "sticky_sentences": 12,
    "sentence_energy": 12,
    "echo_report": 12,
    "narrative_structure": 12,
    "dialogue_validation": 12,
    "sentence_variation": 12,
    "pacing_analysis": 12,
    "tension_curve": 12,
    "sensory_report": 12,
    "age_readability": 12,
}

CACHE_TEMPLATE = """
        # Guardar en caché
        from routers._enrichment_phases import _cache_result
        _cache_result(
            db_session=deps.get_database(),
            project_id=project_id,
            enrichment_type="{enrichment_type}",
            result=result,
            phase={phase},
        )
"""

def add_cache_writes():
    """Añade escritura de caché a todos los endpoints que la necesitan."""

    with open("api-server/routers/prose.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Para cada enrichment type, buscar el endpoint y añadir escritura de caché
    for enrichment_type, phase in ENRICHMENT_PHASES.items():
        # Buscar el patrón: get_cached_enrichment(..., "enrichment_type")
        # seguido de return ApiResponse(success=True, data=...)

        pattern = (
            rf'get_cached_enrichment\([^,]+,\s*project_id,\s*"{enrichment_type}"[^)]*\)\s+'
            r'if cached:\s+'
            r'return ApiResponse\(success=True, data=cached\)'
        )

        # Buscar el siguiente "return ApiResponse(success=True, data=...)"
        # que no sea el cached
        matches = list(re.finditer(pattern, content, re.MULTILINE))

        if not matches:
            print(f"[SKIP] No se encontró endpoint para {enrichment_type}")
            continue

        print(f"[INFO] Procesando {enrichment_type}...")

        # Para cada match, buscar el próximo return ApiResponse que sea el resultado computado
        for match in matches:
            start_pos = match.end()

            # Buscar el próximo return ApiResponse(success=True, data=...) después de la caché
            next_return_pattern = r'return ApiResponse\(success=True,\s*data=([^)]+)\)'
            next_returns = list(re.finditer(next_return_pattern, content[start_pos:]))

            if not next_returns:
                print(f"  [WARN] No se encontró return después de caché para {enrichment_type}")
                continue

            # Tomar el primer return (el que devuelve el resultado computado)
            first_return = next_returns[0]
            result_var = first_return.group(1).strip()

            # Verificar si ya tiene _cache_result
            section = content[start_pos:start_pos + first_return.start()]
            if "_cache_result" in section:
                print(f"  [SKIP] Ya tiene caché escrito")
                continue

            # Insertar el código de caché ANTES del return
            insert_pos = start_pos + first_return.start()
            cache_code = CACHE_TEMPLATE.format(
                enrichment_type=enrichment_type,
                phase=phase
            ).replace("result=result", f"result={result_var}")

            content = content[:insert_pos] + cache_code + "\n" + content[insert_pos:]
            print(f"  [OK] Añadido cache_result antes de return {result_var}")

    # Escribir el archivo modificado
    with open("api-server/routers/prose.py", "w", encoding="utf-8") as f:
        f.write(content)

    print("\n[DONE] Script completado")


if __name__ == "__main__":
    add_cache_writes()
