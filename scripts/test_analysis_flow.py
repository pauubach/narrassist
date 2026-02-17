"""
Script de prueba E2E del flujo de análisis completo.

Prueba:
1. Crear proyecto
2. Subir documento
3. Iniciar análisis
4. Monitorear progreso y fases
5. Verificar resultados
"""

import sys
import time
import requests
from pathlib import Path
from typing import Optional

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"


class AnalysisFlowTester:
    def __init__(self):
        self.session = requests.Session()
        self.project_id: Optional[int] = None

    def check_backend(self) -> bool:
        """Verifica que el backend está corriendo."""
        try:
            response = self.session.get(f"{API_BASE}/health")
            if response.status_code == 200:
                print("✓ Backend conectado")
                return True
            else:
                print(f"✗ Backend respondió con status {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("✗ Backend no está corriendo")
            print("  Iniciar con: cd api-server && uvicorn main:app --reload")
            return False

    def create_project(self, name: str) -> Optional[int]:
        """Crea un nuevo proyecto."""
        print(f"\n📁 Creando proyecto '{name}'...")

        response = self.session.post(
            f"{API_BASE}/projects",
            data={"name": name, "is_demo": False}
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                project_id = data["data"]["id"]
                print(f"✓ Proyecto creado con ID: {project_id}")
                return project_id
            else:
                print(f"✗ Error: {data.get('error')}")
                return None
        else:
            print(f"✗ Error HTTP {response.status_code}: {response.text}")
            return None

    def create_project_with_file(self, name: str, doc_path: Path) -> Optional[int]:
        """Crea proyecto y sube documento en un solo paso."""
        print(f"\n📁 Creando proyecto '{name}' con documento {doc_path.name}...")

        if not doc_path.exists():
            print(f"✗ Archivo no existe: {doc_path}")
            return None

        with open(doc_path, 'rb') as f:
            files = {'file': (doc_path.name, f, 'text/plain')}
            data = {'name': name, 'is_demo': False}
            response = self.session.post(
                f"{API_BASE}/projects",
                data=data,
                files=files
            )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                project_id = data["data"]["id"]
                print(f"✓ Proyecto creado con ID: {project_id}, análisis iniciado")
                return project_id
            else:
                print(f"✗ Error: {data.get('error')}")
                return None
        else:
            print(f"✗ Error HTTP {response.status_code}: {response.text}")
            return None

    def start_analysis(self, project_id: int) -> bool:
        """Inicia el análisis de un proyecto."""
        print(f"\n▶️  Iniciando análisis del proyecto {project_id}...")

        response = self.session.post(f"{API_BASE}/projects/{project_id}/analyze")

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"✓ Análisis iniciado")
                return True
            else:
                print(f"✗ Error: {data.get('error')}")
                return False
        else:
            print(f"✗ Error HTTP {response.status_code}: {response.text}")
            return False

    def get_progress(self, project_id: int) -> Optional[dict]:
        """Obtiene el progreso del análisis."""
        response = self.session.get(f"{API_BASE}/projects/{project_id}/analysis/progress")

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data["data"]
            else:
                return None
        else:
            return None

    def monitor_analysis(self, project_id: int, max_wait: int = 300) -> bool:
        """Monitorea el progreso del análisis."""
        print(f"\n⏳ Monitoreando análisis (max {max_wait}s)...")
        print("=" * 80)

        start_time = time.time()
        last_phase = None
        last_progress = -1

        while time.time() - start_time < max_wait:
            progress_data = self.get_progress(project_id)

            if not progress_data:
                print("✗ No se pudo obtener progreso")
                time.sleep(2)
                continue

            status = progress_data.get("status")
            progress = progress_data.get("progress", 0)
            current_phase = progress_data.get("current_phase", "")
            phases = progress_data.get("phases", [])

            # Mostrar cambios de fase
            if current_phase != last_phase:
                print(f"\n🔄 {current_phase}")
                last_phase = current_phase

            # Mostrar progreso cada 5%
            if progress // 5 > last_progress // 5:
                completed_phases = [p["id"] for p in phases if p.get("completed")]
                print(f"   [{progress:3.0f}%] Fases completadas: {len(completed_phases)}/13")
                last_progress = progress

            # Estados terminales
            if status == "completed":
                print("\n" + "=" * 80)
                print("✓ Análisis completado")
                self._print_phase_summary(phases)
                return True
            elif status in ["error", "failed", "cancelled"]:
                print("\n" + "=" * 80)
                print(f"✗ Análisis terminó con estado: {status}")
                error = progress_data.get("error", "Sin detalles")
                print(f"  Error: {error}")
                return False

            time.sleep(2)

        print("\n" + "=" * 80)
        print(f"✗ Timeout después de {max_wait}s")
        return False

    def _print_phase_summary(self, phases: list):
        """Imprime resumen de fases completadas."""
        print("\n📊 Resumen de fases:")
        for i, phase in enumerate(phases, 1):
            status = "✓" if phase.get("completed") else "○"
            name = phase.get("name", phase.get("id"))
            print(f"  {i:2d}. {status} {name}")

    def get_results(self, project_id: int):
        """Obtiene los resultados del análisis."""
        print(f"\n📈 Obteniendo resultados...")

        # Obtener proyecto
        response = self.session.get(f"{API_BASE}/projects/{project_id}")
        if response.status_code != 200:
            print("✗ No se pudo obtener proyecto")
            return

        project = response.json()["data"]
        print(f"✓ Proyecto: {project['name']}")
        print(f"  - Palabras: {project.get('wordCount', 0):,}")
        print(f"  - Capítulos: {project.get('chapterCount', 0)}")

        # Obtener entidades
        response = self.session.get(f"{API_BASE}/projects/{project_id}/entities")
        if response.status_code == 200:
            entities = response.json()["data"]
            print(f"  - Entidades: {len(entities)}")

            # Top 5 entidades por menciones
            if entities:
                top_entities = sorted(entities, key=lambda e: e.get('mentionCount', 0), reverse=True)[:5]
                print("    Top 5 entidades:")
                for e in top_entities:
                    print(f"      • {e['name']} ({e.get('entityType', 'unknown')}): {e.get('mentionCount', 0)} menciones")

        # Obtener alertas
        response = self.session.get(f"{API_BASE}/projects/{project_id}/alerts")
        if response.status_code == 200:
            alerts = response.json()["data"]
            print(f"  - Alertas: {len(alerts)}")

            # Alertas por severidad
            by_severity = {}
            for alert in alerts:
                severity = alert.get('severity', 'unknown')
                by_severity[severity] = by_severity.get(severity, 0) + 1

            if by_severity:
                print("    Por severidad:")
                for severity in ['critical', 'high', 'medium', 'low', 'info']:
                    if severity in by_severity:
                        print(f"      • {severity}: {by_severity[severity]}")

    def cleanup(self, project_id: int):
        """Elimina el proyecto de prueba."""
        print(f"\n🗑️  Limpiando proyecto {project_id}...")
        response = self.session.delete(f"{API_BASE}/projects/{project_id}")
        if response.status_code == 200:
            print("✓ Proyecto eliminado")
        else:
            print(f"⚠ No se pudo eliminar proyecto (status {response.status_code})")


def main():
    """Ejecuta el test completo."""
    tester = AnalysisFlowTester()

    print("=" * 80)
    print("TEST E2E - Flujo de Análisis Completo")
    print("=" * 80)

    # 1. Verificar backend
    if not tester.check_backend():
        return 1

    # 2. Crear proyecto y subir documento
    doc_path = Path("test_books/test_documents/test_document_rich.txt")
    project_id = tester.create_project_with_file("Test E2E - Rich", doc_path)
    if not project_id:
        return 1

    tester.project_id = project_id

    try:
        # 3. Iniciar análisis
        if not tester.start_analysis(project_id):
            return 1

        # 4. Monitorear análisis
        success = tester.monitor_analysis(project_id, max_wait=300)

        if success:
            # 5. Obtener resultados
            tester.get_results(project_id)

            print("\n" + "=" * 80)
            print("✓ TEST COMPLETADO EXITOSAMENTE")
            print("=" * 80)
            return 0
        else:
            print("\n" + "=" * 80)
            print("✗ TEST FALLÓ")
            print("=" * 80)
            return 1

    finally:
        # Cleanup (opcional, comentar si quieres inspeccionar el proyecto)
        # tester.cleanup(project_id)
        print(f"\n💡 Proyecto ID {project_id} disponible para inspección en:")
        print(f"   {BASE_URL}/projects/{project_id}")


if __name__ == "__main__":
    exit(main())
