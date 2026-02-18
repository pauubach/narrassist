#!/bin/bash
# Build MkDocs static HTML and copy to Tauri public folder

set -e

echo "[1/3] Building MkDocs static site..."
cd "$(dirname "$0")/.."
python3 -m mkdocs build --clean

echo "[2/3] Copying to frontend public/docs..."
rm -rf frontend/public/docs
cp -r site frontend/public/docs

echo "[3/3] Cleaning up build artifacts..."
rm -rf site

echo ""
echo "✅ Documentation built and copied successfully!"
echo "   Location: frontend/public/docs/index.html"
echo "   Accessible in app at: /docs/index.html"
echo ""
