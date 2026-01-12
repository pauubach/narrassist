"""Test específico de la función _run_ner del pipeline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from narrative_assistant.pipelines.analysis_pipeline import _run_ner

text = """
María Sánchez es una mujer alta de Madrid. Sus ojos azules brillaban.
Juan Pérez es un hombre bajo de Barcelona. Tenía el cabello negro.
"""

print("=" * 70)
print("TEST _run_ner() DEL PIPELINE")
print("=" * 70)
print()
print(f"Texto: {text[:100]}...")
print()

# Crear proyecto temporal para el test
from narrative_assistant.persistence.project import ProjectManager

pm = ProjectManager()
try:
    create_result = pm.create_from_document(
        text="Test document",
        name="Test NER Pipeline",
        document_format="txt",
    )
    if create_result.is_success:
        project_id = create_result.value.id
        print(f"Proyecto de prueba creado: ID {project_id}")
        print()
    else:
        print(f"Error creando proyecto: {create_result.error}")
        sys.exit(1)
except Exception as e:
    print(f"Excepción creando proyecto: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Ejecutar _run_ner
result = _run_ner(text, project_id)

print(f"Resultado: {result.is_success}")
print()

if result.is_success:
    entities = result.value
    print(f"Entidades retornadas: {len(entities)}")

    for i, entity in enumerate(entities, 1):
        print(f"\n{i}. {entity.canonical_name}")
        print(f"   ID: {entity.id}")
        print(f"   Tipo: {entity.entity_type}")
        print(f"   Importancia: {entity.importance}")
        print(f"   Project ID: {entity.project_id}")
else:
    print(f"ERROR: {result.error.user_message if result.error else 'Unknown'}")
    if result.errors:
        for err in result.errors:
            print(f"  - {err}")

print()
print("=" * 70)
