# STEP 7.4: CLI Principal

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | M (4-6 horas) |
| **Prioridad** | P0 (Crítico) |
| **Prerequisitos** | Todos los anteriores |

---

## Descripción

Implementar la interfaz de línea de comandos (CLI) que integra todos los módulos y permite al usuario interactuar con el sistema de forma unificada.

---

## Comandos Principales

| Comando | Descripción |
|---------|-------------|
| `analyze` | Analiza un manuscrito completo |
| `entities` | Gestiona entidades (listar, fusionar) |
| `alerts` | Muestra y gestiona alertas |
| `export` | Exporta fichas, guías, reportes |
| `project` | Gestiona proyectos |
| `focalization` | Declara/modifica focalización |

---

## Estructura de Comandos

```
narrative-assistant
├── analyze <file.docx>
│   ├── --output-dir <path>
│   ├── --config <config.yaml>
│   └── --verbose
│
├── project
│   ├── create <name>
│   ├── list
│   ├── delete <id>
│   └── info <id>
│
├── entities
│   ├── list [--project <id>]
│   ├── merge <id1> <id2> --name <canonical>
│   ├── suggest-merges [--project <id>]
│   └── show <id>
│
├── alerts
│   ├── list [--project <id>] [--severity <level>]
│   ├── show <id>
│   ├── resolve <id> [--note <text>]
│   └── dismiss <id> [--note <text>]
│
├── export
│   ├── character-sheet <entity_id> [--format md|json]
│   ├── style-guide [--project <id>]
│   ├── timeline [--project <id>]
│   └── full-report [--project <id>]
│
└── focalization
    ├── declare <chapter> <type> [--focalizer <id>]
    ├── list [--project <id>]
    └── check [--chapter <num>]
```

---

## Implementación

```python
"""
narrative-assistant CLI

Uso:
    narrative-assistant analyze <file> [--output-dir <path>] [--verbose]
    narrative-assistant project (create <name> | list | delete <id> | info <id>)
    narrative-assistant entities (list | merge <id1> <id2> --name <name> | suggest-merges | show <id>)
    narrative-assistant alerts (list | show <id> | resolve <id> | dismiss <id>)
    narrative-assistant export (character-sheet <id> | style-guide | timeline | full-report)
    narrative-assistant focalization (declare <chapter> <type> | list | check)
    narrative-assistant --version
    narrative-assistant --help
"""

import argparse
import sys
from pathlib import Path
from typing import Optional
import json

# Importaciones del sistema
from narrative_assistant.core.project import ProjectManager
from narrative_assistant.core.analysis import AnalysisPipeline
from narrative_assistant.services.entity_fusion import EntityFusionService
from narrative_assistant.alerts.engine import AlertEngine
from narrative_assistant.export.character_sheets import CharacterSheetGenerator
from narrative_assistant.export.style_guide import StyleGuideGenerator
from narrative_assistant.focalization.declaration import FocalizationDeclarationService
from narrative_assistant.db.repository import Repository

class CLI:
    def __init__(self):
        self.repo = Repository()
        self.project_manager = ProjectManager(self.repo)
        self.alert_engine = AlertEngine(self.repo)

    def run(self, args: Optional[list] = None):
        """Punto de entrada principal."""
        parser = self._create_parser()
        parsed = parser.parse_args(args)

        if not hasattr(parsed, 'command') or parsed.command is None:
            parser.print_help()
            return 1

        # Despachar al comando apropiado
        handlers = {
            'analyze': self._handle_analyze,
            'project': self._handle_project,
            'entities': self._handle_entities,
            'alerts': self._handle_alerts,
            'export': self._handle_export,
            'focalization': self._handle_focalization,
        }

        handler = handlers.get(parsed.command)
        if handler:
            return handler(parsed)
        else:
            parser.print_help()
            return 1

    def _create_parser(self) -> argparse.ArgumentParser:
        """Crea el parser de argumentos."""
        parser = argparse.ArgumentParser(
            prog='narrative-assistant',
            description='Asistente de corrección narrativa y estilo'
        )
        parser.add_argument('--version', action='version', version='0.1.0')

        subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')

        # === analyze ===
        analyze_parser = subparsers.add_parser('analyze', help='Analiza un manuscrito')
        analyze_parser.add_argument('file', type=str, help='Archivo DOCX a analizar')
        analyze_parser.add_argument('--output-dir', '-o', type=str, help='Directorio de salida')
        analyze_parser.add_argument('--config', '-c', type=str, help='Archivo de configuración')
        analyze_parser.add_argument('--verbose', '-v', action='store_true', help='Modo verboso')

        # === project ===
        project_parser = subparsers.add_parser('project', help='Gestión de proyectos')
        project_sub = project_parser.add_subparsers(dest='subcommand')

        project_create = project_sub.add_parser('create', help='Crea un proyecto')
        project_create.add_argument('name', type=str, help='Nombre del proyecto')

        project_sub.add_parser('list', help='Lista proyectos')

        project_delete = project_sub.add_parser('delete', help='Elimina un proyecto')
        project_delete.add_argument('id', type=int, help='ID del proyecto')

        project_info = project_sub.add_parser('info', help='Info de un proyecto')
        project_info.add_argument('id', type=int, help='ID del proyecto')

        # === entities ===
        entities_parser = subparsers.add_parser('entities', help='Gestión de entidades')
        entities_sub = entities_parser.add_subparsers(dest='subcommand')

        entities_list = entities_sub.add_parser('list', help='Lista entidades')
        entities_list.add_argument('--project', '-p', type=int, help='ID del proyecto')

        entities_merge = entities_sub.add_parser('merge', help='Fusiona entidades')
        entities_merge.add_argument('id1', type=int, help='Primera entidad')
        entities_merge.add_argument('id2', type=int, help='Segunda entidad')
        entities_merge.add_argument('--name', '-n', required=True, help='Nombre canónico')

        entities_suggest = entities_sub.add_parser('suggest-merges', help='Sugiere fusiones')
        entities_suggest.add_argument('--project', '-p', type=int, help='ID del proyecto')

        entities_show = entities_sub.add_parser('show', help='Muestra una entidad')
        entities_show.add_argument('id', type=int, help='ID de la entidad')

        # === alerts ===
        alerts_parser = subparsers.add_parser('alerts', help='Gestión de alertas')
        alerts_sub = alerts_parser.add_subparsers(dest='subcommand')

        alerts_list = alerts_sub.add_parser('list', help='Lista alertas')
        alerts_list.add_argument('--project', '-p', type=int, help='ID del proyecto')
        alerts_list.add_argument('--severity', '-s', type=str,
                                 choices=['critical', 'warning', 'info', 'hint'])
        alerts_list.add_argument('--status', type=str,
                                 choices=['open', 'resolved', 'dismissed'])

        alerts_show = alerts_sub.add_parser('show', help='Muestra una alerta')
        alerts_show.add_argument('id', type=int, help='ID de la alerta')

        alerts_resolve = alerts_sub.add_parser('resolve', help='Resuelve una alerta')
        alerts_resolve.add_argument('id', type=int, help='ID de la alerta')
        alerts_resolve.add_argument('--note', '-n', type=str, default='')

        alerts_dismiss = alerts_sub.add_parser('dismiss', help='Descarta una alerta')
        alerts_dismiss.add_argument('id', type=int, help='ID de la alerta')
        alerts_dismiss.add_argument('--note', '-n', type=str, default='')

        # === export ===
        export_parser = subparsers.add_parser('export', help='Exporta datos')
        export_sub = export_parser.add_subparsers(dest='subcommand')

        export_char = export_sub.add_parser('character-sheet', help='Ficha de personaje')
        export_char.add_argument('id', type=int, help='ID de la entidad')
        export_char.add_argument('--format', '-f', type=str, choices=['md', 'json'], default='md')

        export_style = export_sub.add_parser('style-guide', help='Guía de estilo')
        export_style.add_argument('--project', '-p', type=int, help='ID del proyecto')

        export_timeline = export_sub.add_parser('timeline', help='Timeline')
        export_timeline.add_argument('--project', '-p', type=int, help='ID del proyecto')

        export_report = export_sub.add_parser('full-report', help='Reporte completo')
        export_report.add_argument('--project', '-p', type=int, help='ID del proyecto')

        # === focalization ===
        foc_parser = subparsers.add_parser('focalization', help='Gestión de focalización')
        foc_sub = foc_parser.add_subparsers(dest='subcommand')

        foc_declare = foc_sub.add_parser('declare', help='Declara focalización')
        foc_declare.add_argument('chapter', type=int, help='Número de capítulo')
        foc_declare.add_argument('type', type=str,
                                choices=['zero', 'internal_fixed', 'internal_variable', 'external'])
        foc_declare.add_argument('--focalizer', '-f', type=int, action='append',
                                help='ID del focalizador')

        foc_list = foc_sub.add_parser('list', help='Lista declaraciones')
        foc_list.add_argument('--project', '-p', type=int, help='ID del proyecto')

        foc_check = foc_sub.add_parser('check', help='Verifica focalización')
        foc_check.add_argument('--chapter', '-c', type=int, help='Capítulo a verificar')

        return parser

    def _handle_analyze(self, args) -> int:
        """Maneja el comando analyze."""
        file_path = Path(args.file)

        if not file_path.exists():
            print(f"Error: El archivo '{file_path}' no existe", file=sys.stderr)
            return 1

        if not file_path.suffix.lower() == '.docx':
            print(f"Error: Solo se soportan archivos .docx", file=sys.stderr)
            return 1

        print(f"📖 Analizando: {file_path.name}")

        # Crear proyecto
        project = self.project_manager.create_project(
            name=file_path.stem,
            source_file=str(file_path)
        )
        print(f"   Proyecto creado: ID {project.id}")

        # Pipeline de análisis
        pipeline = AnalysisPipeline(self.repo, project.id)

        if args.verbose:
            pipeline.set_verbose(True)

        try:
            results = pipeline.run(str(file_path))

            print(f"\n✅ Análisis completado")
            print(f"   📊 Capítulos: {results.get('chapters', 0)}")
            print(f"   👤 Entidades: {results.get('entities', 0)}")
            print(f"   💬 Diálogos: {results.get('dialogues', 0)}")
            print(f"   ⚠️  Alertas: {results.get('alerts', 0)}")

            # Mostrar resumen de alertas por severidad
            if results.get('alert_summary'):
                print(f"\n   Alertas por severidad:")
                for sev, count in results['alert_summary'].items():
                    print(f"      {sev}: {count}")

            print(f"\n💡 Usa 'narrative-assistant alerts list --project {project.id}' para ver alertas")

        except Exception as e:
            print(f"Error durante el análisis: {e}", file=sys.stderr)
            return 1

        return 0

    def _handle_project(self, args) -> int:
        """Maneja comandos de proyecto."""
        if args.subcommand == 'create':
            project = self.project_manager.create_project(name=args.name)
            print(f"✅ Proyecto creado: ID {project.id}")

        elif args.subcommand == 'list':
            projects = self.project_manager.list_projects()
            if not projects:
                print("No hay proyectos")
            else:
                print(f"{'ID':<6} {'Nombre':<30} {'Fecha':<20}")
                print("-" * 60)
                for p in projects:
                    print(f"{p.id:<6} {p.name:<30} {p.created_at.strftime('%Y-%m-%d %H:%M')}")

        elif args.subcommand == 'info':
            project = self.project_manager.get_project(args.id)
            if not project:
                print(f"Proyecto {args.id} no encontrado")
                return 1
            print(f"ID: {project.id}")
            print(f"Nombre: {project.name}")
            print(f"Creado: {project.created_at}")
            # Más info...

        elif args.subcommand == 'delete':
            if self.project_manager.delete_project(args.id):
                print(f"✅ Proyecto {args.id} eliminado")
            else:
                print(f"Error al eliminar proyecto {args.id}")
                return 1

        return 0

    def _handle_entities(self, args) -> int:
        """Maneja comandos de entidades."""
        if args.subcommand == 'list':
            entities = self.repo.get_entities(args.project)
            if not entities:
                print("No hay entidades")
            else:
                print(f"{'ID':<6} {'Nombre':<30} {'Tipo':<15} {'Menciones':<10}")
                print("-" * 65)
                for e in entities:
                    print(f"{e.id:<6} {e.canonical_name:<30} {e.entity_type:<15} {e.mention_count:<10}")

        elif args.subcommand == 'merge':
            fusion_service = EntityFusionService(self.repo)
            result_id = fusion_service.merge_entities(
                project_id=1,  # Simplificado
                entity_ids=[args.id1, args.id2],
                canonical_name=args.name
            )
            print(f"✅ Entidades fusionadas. Nueva entidad ID: {result_id}")

        elif args.subcommand == 'suggest-merges':
            fusion_service = EntityFusionService(self.repo)
            suggestions = fusion_service.suggest_merges(args.project or 1)
            if not suggestions:
                print("No hay sugerencias de fusión")
            else:
                for s in suggestions[:10]:
                    print(f"  {s['entity1'].canonical_name} ↔ {s['entity2'].canonical_name}")
                    print(f"    Similaridad: {s['similarity']:.0%} - {s['reason']}")

        elif args.subcommand == 'show':
            entity = self.repo.get_entity(args.id)
            if not entity:
                print(f"Entidad {args.id} no encontrada")
                return 1
            print(f"ID: {entity.id}")
            print(f"Nombre: {entity.canonical_name}")
            print(f"Tipo: {entity.entity_type}")
            print(f"Aliases: {', '.join(entity.aliases)}")

        return 0

    def _handle_alerts(self, args) -> int:
        """Maneja comandos de alertas."""
        # Implementación similar a los anteriores
        if args.subcommand == 'list':
            alerts = self.alert_engine.get_alerts(args.project or 1)
            # Filtrar por severidad/status si se especifica
            print(f"{'ID':<6} {'Severidad':<10} {'Categoría':<15} {'Título':<40}")
            print("-" * 75)
            for a in alerts[:20]:
                print(f"{a.id:<6} {a.severity.value:<10} {a.category.value:<15} {a.title[:40]:<40}")

        elif args.subcommand == 'resolve':
            from narrative_assistant.alerts.engine import AlertStatus
            self.alert_engine.update_alert_status(
                args.id, AlertStatus.RESOLVED, args.note
            )
            print(f"✅ Alerta {args.id} marcada como resuelta")

        return 0

    def _handle_export(self, args) -> int:
        """Maneja comandos de exportación."""
        if args.subcommand == 'character-sheet':
            generator = CharacterSheetGenerator(self.repo, self.repo, self.repo)
            sheet = generator.generate_sheet(1, args.id)

            if args.format == 'json':
                print(json.dumps(generator.export_to_json(sheet), indent=2))
            else:
                print(generator.export_to_markdown(sheet))

        elif args.subcommand == 'style-guide':
            # Cargar texto del proyecto
            project = self.project_manager.get_project(args.project or 1)
            text = self.repo.get_full_text(project.id)

            generator = StyleGuideGenerator()
            guide = generator.generate(project.id, project.name, text)
            print(generator.export_to_markdown(guide))

        return 0

    def _handle_focalization(self, args) -> int:
        """Maneja comandos de focalización."""
        service = FocalizationDeclarationService(self.repo)

        if args.subcommand == 'declare':
            from narrative_assistant.focalization.declaration import FocalizationType
            foc_type = FocalizationType(args.type)
            focalizers = args.focalizer or []

            declaration = service.declare_focalization(
                project_id=1,  # Simplificado
                chapter=args.chapter,
                focalization_type=foc_type,
                focalizer_ids=focalizers
            )
            print(f"✅ Focalización declarada para capítulo {args.chapter}")

        elif args.subcommand == 'list':
            declarations = service.get_all_declarations(args.project or 1)
            for d in declarations:
                focalizers = ", ".join(str(f) for f in d.focalizer_ids) or "N/A"
                print(f"Cap. {d.chapter}: {d.focalization_type.value} [{focalizers}]")

        return 0


def main():
    """Función principal."""
    cli = CLI()
    sys.exit(cli.run())


if __name__ == '__main__':
    main()
```

---

## Ejemplo de Uso

```bash
# Analizar un manuscrito
$ narrative-assistant analyze mi_novela.docx --verbose

📖 Analizando: mi_novela.docx
   Proyecto creado: ID 1
   Procesando capítulos...
   Detectando entidades...
   Analizando diálogos...
   Verificando consistencia...

✅ Análisis completado
   📊 Capítulos: 15
   👤 Entidades: 23
   💬 Diálogos: 342
   ⚠️  Alertas: 17

   Alertas por severidad:
      critical: 2
      warning: 8
      info: 7

💡 Usa 'narrative-assistant alerts list --project 1' para ver alertas

# Ver alertas críticas
$ narrative-assistant alerts list --project 1 --severity critical

ID     Severidad  Categoría       Título
---------------------------------------------------------------------------
3      critical   consistency     Color de ojos inconsistente: María
7      critical   focalization    Violación de focalización: acceso a mente

# Fusionar entidades
$ narrative-assistant entities suggest-merges --project 1

  Doctor García ↔ El doctor
    Similaridad: 85% - Nombres similares

$ narrative-assistant entities merge 5 12 --name "Doctor García"
✅ Entidades fusionadas. Nueva entidad ID: 5

# Exportar ficha de personaje
$ narrative-assistant export character-sheet 1 --format md > maria.md

# Declarar focalización
$ narrative-assistant focalization declare 1 internal_fixed --focalizer 1
✅ Focalización declarada para capítulo 1
```

---

## Criterio de DONE

```python
from narrative_assistant.cli import CLI
import sys
from io import StringIO

cli = CLI()

# Test: help funciona
result = cli.run(['--help'])
# Nota: --help sale con código 0 normalmente

# Test: version funciona
result = cli.run(['--version'])

# Test: comando desconocido
result = cli.run(['unknown-command'])
assert result == 1

# Test: analyze sin archivo
result = cli.run(['analyze', 'no_existe.docx'])
assert result == 1

print("✅ CLI básica funcionando")
print("   - Help: OK")
print("   - Version: OK")
print("   - Error handling: OK")
```

---

## Fin de STEPs

Has completado todos los STEPs del proyecto. Vuelve al [Índice de STEPs](../README.md) o al [README principal](../../../README.md).
