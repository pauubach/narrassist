# Documentation Build Process

## Overview

The user manual is written in **Markdown** (in `docs_site/`) and built to **static HTML** using **MkDocs Material**.

The generated HTML is automatically copied to `frontend/public/docs/` during the build process, making it available offline in the Tauri app at `/docs/`.

---

## Directory Structure

```
tfm/
├── docs_site/               # Source Markdown files
│   ├── index.md            # Landing page
│   ├── user-manual/        # Manual chapters
│   │   ├── introduction.md
│   │   ├── first-analysis.md
│   │   ├── entities.md
│   │   ├── alerts.md
│   │   ├── timeline-events.md
│   │   ├── collections-sagas.md
│   │   ├── settings.md
│   │   └── use-cases.md
│   └── api-reference/      # API docs (planned)
│
├── mkdocs.yml              # MkDocs configuration
│
├── site/                   # Generated HTML (gitignored)
│
└── frontend/
    └── public/
        └── docs/           # Copied HTML (gitignored)
            └── index.html
```

---

## Automated Build

### During Development

**Edit docs**:
```bash
# Serve live preview at http://localhost:8000
scripts/serve_docs.bat    # Windows
# or
mkdocs serve              # Any OS
```

Changes are reflected instantly in the browser.

### During App Build

**Automatic** - runs before Vite build:

```bash
npm run build
```

This executes:
1. `npm run build:docs` → Runs `frontend/scripts/build-docs.js`
2. `build-docs.js` → Executes `mkdocs build --clean`
3. Copies `site/` → `frontend/public/docs/`
4. Cleans up `site/` directory
5. Continues with Vite build

### Manual Build

If you need to rebuild docs without full app build:

```bash
# Windows
scripts\build_docs.bat

# Linux/macOS
./scripts/build_docs.sh

# Or via npm
cd frontend
npm run build:docs
```

---

## Accessing in the App

From Vue components:

```typescript
import { openManual, openManualChapter } from '@/utils/openManual'

// Open manual home
openManual()

// Open specific chapter
openManualChapter('alerts')
openManualChapter('entities')
```

The manual opens in a **new window/tab** within the Tauri webview.

---

## Technologies

- **MkDocs**: Static site generator (Python)
- **Material for MkDocs**: Professional theme
- **Markdown extensions**:
  - Admonitions (callouts)
  - Tabs
  - Code highlighting
  - Mermaid diagrams
  - Emoji support

---

## Why This Approach?

### Pros
✅ **Single source of truth**: Docs in `docs_site/`, HTML generated
✅ **Offline-first**: Works without internet in the app
✅ **Easy to edit**: Markdown is simple, non-technical
✅ **Professional look**: Material theme, responsive
✅ **Versioned**: Docs tracked in git
✅ **No duplication**: Generated HTML is gitignored

### Cons
⚠️ **Requires Python**: MkDocs needs Python + pip
⚠️ **Build step**: Must run before each release
⚠️ **Size**: Adds ~2-3 MB to app bundle

---

## Deployment

### GitHub Pages (Optional)

To host the manual publicly:

```bash
# Build and deploy to gh-pages branch
mkdocs gh-deploy

# Available at: https://pauubach.github.io/narrassist/
```

This is **optional** - the app always bundles its own copy.

---

## Maintenance

### Adding a New Chapter

1. Create `docs_site/user-manual/new-chapter.md`
2. Add to `mkdocs.yml` nav section:
   ```yaml
   nav:
     - Manual de Usuario:
       - ...
       - New Chapter: user-manual/new-chapter.md
   ```
3. Build: `npm run build:docs`
4. Test: Open app → Help → Manual

### Updating Existing Content

1. Edit Markdown file in `docs_site/`
2. Preview: `mkdocs serve`
3. Commit changes
4. Next `npm run build` will auto-include updates

---

## Troubleshooting

### "mkdocs: command not found"

**Solution**: Install MkDocs
```bash
pip install mkdocs mkdocs-material
```

### Build fails during `npm run build`

**Quick fix**: Skip docs build temporarily
```bash
# Edit package.json, change:
"build": "vue-tsc && vite build"  # Remove build:docs call

# Or build manually before npm run build:
scripts/build_docs.bat
```

### Docs not showing in app

1. Check `frontend/public/docs/index.html` exists
2. Rebuild: `npm run build:docs`
3. Clear Tauri cache and rebuild app

---

## Future Improvements

- [ ] Add search index pre-building
- [ ] Versioned docs (v0.6, v0.7, etc.)
- [ ] Screenshots/GIFs in manual
- [ ] API reference auto-generation from OpenAPI
- [ ] Translations (English, Catalan)
