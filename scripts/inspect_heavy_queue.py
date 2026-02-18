#!/usr/bin/env python3
"""
Script para inspeccionar el estado de la cola heavy.
"""

import sys

# Add parent directory to path
sys.path.insert(0, "d:/repos/tfm")
sys.path.insert(0, "d:/repos/tfm/api-server")

def main():
    try:
        import deps

        with deps._progress_lock:
            print(f"=== HEAVY ANALYSIS STATE ===\n")

            # Queue
            print(f"Heavy queue: {len(deps._heavy_analysis_queue)} items")
            for item in deps._heavy_analysis_queue:
                print(f"  - Project {item['project_id']}")

            # Slot
            print(f"\nHeavy slot project ID: {deps._heavy_analysis_project_id}")
            print(f"Heavy slot claimed at: {deps._heavy_analysis_claimed_at}")

            # Flags
            print(f"\nCancellation flags: {len(deps.analysis_cancellation_flags)} projects")
            for project_id, cancelled in deps.analysis_cancellation_flags.items():
                print(f"  - Project {project_id}: cancelled={cancelled}")

            # Storage
            print(f"\nProgress storage: {len(deps.analysis_progress_storage)} projects")
            for project_id, storage in deps.analysis_progress_storage.items():
                status = storage.get('status', 'unknown')
                phase = storage.get('current_phase', 'unknown')
                print(f"  - Project {project_id}: status={status}, phase={phase}")

        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
