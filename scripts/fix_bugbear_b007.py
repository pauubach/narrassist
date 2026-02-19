#!/usr/bin/env python
"""Fix flake8-bugbear B007 issues: unused loop variables."""

import sys
from pathlib import Path

# Mapping of file:line to the fix to apply
FIXES = {
    "src/narrative_assistant/analysis/character_profiling.py:387": {
        "old": "for chapter_num in sorted",
        "new": "for _chapter_num in sorted",
    },
    "src/narrative_assistant/analysis/relationship_clustering.py:418": {
        "old": "for i in range(",
        "new": "for _ in range(",
    },
    "src/narrative_assistant/corrections/detectors/coherence.py:166": {
        "old": "for orig_idx in sorted(",
        "new": "for _orig_idx in sorted(",
    },
    "src/narrative_assistant/exporters/review_report_exporter.py:581": {
        "old": "for i in range(len(report",
        "new": "for _ in range(len(report",
    },
    "src/narrative_assistant/focalization/declaration.py:448": {
        "old": "for eid in entity_ids:",
        "new": "for _eid in entity_ids:",
    },
    "src/narrative_assistant/llm/expectation_inference.py:680": {
        "old": "for key in sorted(keys):",
        "new": "for _key in sorted(keys):",
    },
    "src/narrative_assistant/nlp/attr_voting.py:308": {
        "old": "for key in sorted(keys):",
        "new": "for _key in sorted(keys):",
    },
    "src/narrative_assistant/nlp/attributes.py:2790": {
        "old": "for start, end in matches:",
        "new": "for _start, _end in matches:",
    },
    "src/narrative_assistant/nlp/attributes.py:2807": {
        "old": "for start, end in matches:",
        "new": "for _start, _end in matches:",
    },
    "src/narrative_assistant/nlp/attributes.py:2825": {
        "old": "for start, end in all_m:",
        "new": "for _start, _end in all_m:",
    },
    "src/narrative_assistant/nlp/coreference_resolver.py:1559": {
        "old": "for antecedent, score in sorted_antecedents:",
        "new": "for _antecedent, _score in sorted_antecedents:",
    },
    "src/narrative_assistant/nlp/coreference_resolver.py:1609": {
        "old": "for _, score in antecedents:",
        "new": "for _, _score in antecedents:",
    },
    "src/narrative_assistant/nlp/extraction/extractors/llm_extractor.py:571": {
        "old": "for key in sorted(keys):",
        "new": "for _key in sorted(keys):",
    },
    "src/narrative_assistant/nlp/scope_resolver.py:531": {
        "old": "for name, start, end, etype in entity_mentions:",
        "new": "for name, _start, _end, etype in entity_mentions:",
    },
    "src/narrative_assistant/nlp/scope_resolver.py:646": {
        "old": "for name, start, end, etype in entity_mentions:",
        "new": "for name, start, _end, etype in entity_mentions:",
    },
    "src/narrative_assistant/nlp/scope_resolver.py:710": {
        "old": "for name, start, end, etype in entity_mentions:",
        "new": "for name, start, _end, etype in entity_mentions:",
    },
    "src/narrative_assistant/nlp/scope_resolver.py:749": {
        "old": "for name, start, end, etype in entity_mentions:",
        "new": "for name, start, _end, etype in entity_mentions:",
    },
    "src/narrative_assistant/nlp/scope_resolver.py:792": {
        "old": "for name, start, end, etype in entity_mentions:",
        "new": "for name, start, _end, etype in entity_mentions:",
    },
    "src/narrative_assistant/nlp/scope_resolver.py:843": {
        "old": "for name, start, end, etype in entity_mentions:",
        "new": "for name, start, _end, etype in entity_mentions:",
    },
    "src/narrative_assistant/nlp/scope_resolver.py:890": {
        "old": "for name, start, end, etype in entity_mentions:",
        "new": "for name, start, _end, etype in entity_mentions:",
    },
    "src/narrative_assistant/nlp/scope_resolver.py:1020": {
        "old": "for name, start, end, etype in candidates:",
        "new": "for name, start, _end, _etype in candidates:",
    },
    "src/narrative_assistant/nlp/scope_resolver.py:1033": {
        "old": "for name, start, end, etype in candidates:",
        "new": "for name, _start, _end, _etype in candidates:",
    },
    "src/narrative_assistant/pipelines/analysis_pipeline.py:1110": {
        "old": "for canonical_lower, _aliases in entity_variations:",
        "new": "for _canonical_lower, _aliases in entity_variations:",
    },
}


def fix_file(file_path: str, line_num: int, fix_data: dict):
    """Apply fix to specific line in file."""
    path = Path(file_path)
    lines = path.read_text(encoding='utf-8').splitlines()

    if line_num > len(lines):
        print(f"FAIL {file_path}:{line_num} - line out of range", file=sys.stderr)
        return False

    line = lines[line_num - 1]  # 0-indexed
    old = fix_data["old"]
    new = fix_data["new"]

    if old not in line:
        print(f"WARN {file_path}:{line_num} - pattern not found", file=sys.stderr)
        print(f"  Expected: {old}", file=sys.stderr)
        print(f"  Got: {line.strip()}", file=sys.stderr)
        return False

    lines[line_num - 1] = line.replace(old, new)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"OK {file_path}:{line_num}")
    return True


def main():
    fixed = 0
    failed = 0

    for location, fix_data in FIXES.items():
        file_path, line_num = location.rsplit(':', 1)
        if fix_file(file_path, int(line_num), fix_data):
            fixed += 1
        else:
            failed += 1

    print(f"\nFixed: {fixed}, Failed: {failed}")


if __name__ == '__main__':
    main()
