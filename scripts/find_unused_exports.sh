#!/bin/bash
# Find potentially unused TypeScript/Vue exports
# Usage: bash scripts/find_unused_exports.sh

cd "$(dirname "$0")/.."

echo "Scanning for unused exports in frontend/src..."
echo "================================================"
echo

# Find all exported functions/constants/types
exports=$(grep -rh "export.*function\|export.*const\|export.*type\|export.*interface" frontend/src --include="*.ts" --exclude-dir=node_modules | \
  sed 's/.*export\s\+\(function\|const\|type\|interface\)\s\+\([a-zA-Z0-9_]\+\).*/\2/' | \
  sort | uniq)

unused_count=0

for export_name in $exports; do
  # Skip common false positives
  if [[ "$export_name" =~ ^(default|Props|Emits|State|Api|interface|type)$ ]]; then
    continue
  fi

  # Count usages (excluding the definition itself)
  usage_count=$(grep -r "$export_name" frontend/src --include="*.ts" --include="*.vue" | grep -v "export.*$export_name" | wc -l)

  # If used only once (the definition), it might be unused
  if [ "$usage_count" -eq 0 ]; then
    echo "Potentially unused: $export_name"
    unused_count=$((unused_count + 1))
  fi
done

echo
echo "Found $unused_count potentially unused exports"
echo "Note: Manual verification required (some may be used via dynamic imports)"
