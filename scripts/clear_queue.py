#!/usr/bin/env python3
"""
Script temporal para limpiar la cola heavy y permitir que el proyecto 7 continúe.
"""

import sys

# Add parent directory to path
sys.path.insert(0, "d:/repos/tfm")
sys.path.insert(0, "d:/repos/tfm/api-server")

def main():
    try:
        import deps

        with deps._progress_lock:
            # Ver estado actual
            print(f"Heavy queue antes: {len(deps._heavy_analysis_queue)} items")
            for item in deps._heavy_analysis_queue:
                print(f"  - Project {item['project_id']}")

            # Limpiar proyecto 7
            deps._heavy_analysis_queue[:] = [
                q for q in deps._heavy_analysis_queue if q["project_id"] != 7
            ]

            print(f"\nHeavy queue después: {len(deps._heavy_analysis_queue)} items")

            # Ver progress storage
            if 7 in deps.analysis_progress_storage:
                storage = deps.analysis_progress_storage[7]
                print(f"\nProgress storage proyecto 7:")
                print(f"  Status: {storage.get('status')}")
                print(f"  Progress: {storage.get('progress')}")
                print(f"  Phase: {storage.get('current_phase')}")
            else:
                print("\nNo hay progress storage para proyecto 7")

        print("\n✅ Cola limpiada")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
