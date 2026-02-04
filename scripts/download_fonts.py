#!/usr/bin/env python3
"""
Script para descargar fuentes de Google Fonts para uso offline.

Las fuentes se descargan en formato WOFF2 (formato moderno, comprimido)
y se guardan en frontend/src/assets/fonts/files/

Ejecutar: python scripts/download_fonts.py
"""

import os
import re
import urllib.request
from pathlib import Path

# Directorio de destino
FONTS_DIR = Path(__file__).parent.parent / "frontend" / "src" / "assets" / "fonts" / "files"

# User-Agent de Chrome moderno para obtener WOFF2 (formato moderno)
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Fuentes a descargar con sus pesos
FONTS = {
    # Generales (sans-serif)
    "Inter": [300, 400, 500, 600, 700],
    "Source+Sans+3": [300, 400, 500, 600, 700],
    "Nunito": [300, 400, 500, 600, 700],

    # Lectura (serif modernas)
    "Literata": [300, 400, 500, 600, 700],
    "Merriweather": [300, 400, 700],
    "Source+Serif+4": [300, 400, 500, 600, 700],
    "Lora": [400, 500, 600, 700],

    # Clásicas (estilo Word)
    "EB+Garamond": [400, 500, 600, 700],
    "Libre+Baskerville": [400, 700],
    "Crimson+Pro": [300, 400, 500, 600, 700],
    "Playfair+Display": [400, 500, 600, 700],
    "PT+Serif": [400, 700],
    "Cormorant+Garamond": [400, 500, 600, 700],
    "IBM+Plex+Serif": [300, 400, 500, 600, 700],
    "Spectral": [300, 400, 500, 600, 700],

    # Accesibles y especializadas
    "Atkinson+Hyperlegible": [400, 700],
    "Roboto+Serif": [300, 400, 500, 600, 700],
    "Noto+Serif": [300, 400, 500, 600, 700],
    "Libre+Caslon+Text": [400, 700],
}


def get_google_fonts_css(font_name: str, weights: list[int]) -> str:
    """Obtiene el CSS de Google Fonts para una fuente."""
    weights_str = ";".join(str(w) for w in weights)
    url = f"https://fonts.googleapis.com/css2?family={font_name}:wght@{weights_str}&display=swap"

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as response:
        return response.read().decode("utf-8")


def parse_font_urls(css: str) -> list[dict]:
    """Extrae URLs de fuentes y metadatos del CSS de Google Fonts."""
    fonts = []

    # Buscar bloques @font-face
    pattern = r"@font-face\s*\{([^}]+)\}"
    for match in re.finditer(pattern, css):
        block = match.group(1)

        # Extraer font-family
        family_match = re.search(r"font-family:\s*['\"]?([^;'\"]+)['\"]?", block)
        family = family_match.group(1).strip() if family_match else None

        # Extraer font-weight
        weight_match = re.search(r"font-weight:\s*(\d+)", block)
        weight = int(weight_match.group(1)) if weight_match else 400

        # Extraer URL del woff2
        url_match = re.search(r"src:\s*url\(([^)]+\.woff2)\)", block)
        url = url_match.group(1) if url_match else None

        # Extraer unicode-range si existe
        range_match = re.search(r"unicode-range:\s*([^;]+)", block)
        unicode_range = range_match.group(1).strip() if range_match else None

        if family and url:
            fonts.append({
                "family": family,
                "weight": weight,
                "url": url,
                "unicode_range": unicode_range
            })

    return fonts


def download_font(url: str, dest_path: Path) -> bool:
    """Descarga un archivo de fuente."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req) as response:
            dest_path.write_bytes(response.read())
        return True
    except Exception as e:
        print(f"  Error descargando {url}: {e}")
        return False


def sanitize_filename(name: str) -> str:
    """Convierte nombre de fuente a nombre de archivo válido."""
    return name.lower().replace(" ", "-").replace("+", "-")


def main():
    """Descarga todas las fuentes."""
    print("=" * 60)
    print("Descargando fuentes de Google Fonts para uso offline")
    print("=" * 60)

    # Crear directorio si no existe
    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    all_font_faces = []
    total_fonts = 0

    for font_name, weights in FONTS.items():
        display_name = font_name.replace("+", " ")
        print(f"\n📥 {display_name}...")

        try:
            # Obtener CSS de Google Fonts
            css = get_google_fonts_css(font_name, weights)
            fonts_data = parse_font_urls(css)

            if not fonts_data:
                print(f"  ⚠️  No se encontraron fuentes para {display_name}")
                continue

            # Agrupar por peso para solo descargar una variante por peso (latin)
            fonts_by_weight = {}
            for font in fonts_data:
                weight = font["weight"]
                # Preferir latin (sin unicode-range) o latin extended
                if weight not in fonts_by_weight:
                    fonts_by_weight[weight] = font
                elif font["unicode_range"] is None:
                    fonts_by_weight[weight] = font
                elif "latin" in (font.get("unicode_range") or "").lower():
                    if fonts_by_weight[weight].get("unicode_range") is not None:
                        fonts_by_weight[weight] = font

            # Descargar cada peso
            font_slug = sanitize_filename(display_name)
            downloaded = 0

            for weight, font in sorted(fonts_by_weight.items()):
                filename = f"{font_slug}-{weight}.woff2"
                dest_path = FONTS_DIR / filename

                if dest_path.exists():
                    print(f"  ✓ {filename} (ya existe)")
                    downloaded += 1
                elif download_font(font["url"], dest_path):
                    print(f"  ✓ {filename}")
                    downloaded += 1

                # Guardar info para generar CSS
                all_font_faces.append({
                    "family": font["family"],
                    "weight": weight,
                    "filename": filename
                })

            total_fonts += downloaded

        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Generar archivo CSS con @font-face
    generate_css(all_font_faces)

    print("\n" + "=" * 60)
    print(f"✅ Descargadas {total_fonts} fuentes en {FONTS_DIR}")
    print("=" * 60)


def generate_css(font_faces: list[dict]):
    """Genera el archivo CSS con las definiciones @font-face."""
    css_path = FONTS_DIR.parent / "fonts-local.css"

    # Agrupar por familia
    families = {}
    for face in font_faces:
        family = face["family"]
        if family not in families:
            families[family] = []
        families[family].append(face)

    css_lines = [
        "/**",
        " * Font Definitions - Narrative Assistant (LOCAL)",
        " *",
        " * Fuentes descargadas localmente para funcionamiento 100% offline.",
        " * Generado automáticamente por scripts/download_fonts.py",
        " */",
        "",
    ]

    for family, faces in sorted(families.items()):
        css_lines.append(f"/* {family} */")
        for face in sorted(faces, key=lambda x: x["weight"]):
            css_lines.extend([
                "@font-face {",
                f"  font-family: '{face['family']}';",
                f"  font-style: normal;",
                f"  font-weight: {face['weight']};",
                f"  font-display: swap;",
                f"  src: url('./files/{face['filename']}') format('woff2');",
                "}",
                "",
            ])

    # Añadir las variables CSS
    css_lines.extend([
        "/* =============================================================================",
        "   CSS VARIABLES POR FUENTE",
        "   ============================================================================= */",
        "",
        ":root {",
        "  /* Fuentes del sistema como fallback */",
        "  --font-system: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;",
        "  --font-system-serif: Georgia, 'Times New Roman', Times, serif;",
        "  --font-mono: 'SF Mono', 'Fira Code', 'Fira Mono', 'Roboto Mono', Consolas, monospace;",
        "",
        "  /* Fuentes sans-serif */",
        "  --font-inter: 'Inter', var(--font-system);",
        "  --font-source-sans: 'Source Sans 3', var(--font-system);",
        "  --font-nunito: 'Nunito', var(--font-system);",
        "",
        "  /* Fuentes serif (lectura) */",
        "  --font-literata: 'Literata', var(--font-system-serif);",
        "  --font-merriweather: 'Merriweather', var(--font-system-serif);",
        "  --font-source-serif: 'Source Serif 4', var(--font-system-serif);",
        "  --font-lora: 'Lora', var(--font-system-serif);",
        "",
        "  /* Fuentes clásicas (estilo Word) */",
        "  --font-garamond: 'EB Garamond', Garamond, var(--font-system-serif);",
        "  --font-baskerville: 'Libre Baskerville', Baskerville, var(--font-system-serif);",
        "  --font-crimson: 'Crimson Pro', var(--font-system-serif);",
        "  --font-playfair: 'Playfair Display', var(--font-system-serif);",
        "  --font-pt-serif: 'PT Serif', var(--font-system-serif);",
        "  --font-cormorant: 'Cormorant Garamond', Garamond, var(--font-system-serif);",
        "  --font-ibm-plex-serif: 'IBM Plex Serif', var(--font-system-serif);",
        "  --font-spectral: 'Spectral', var(--font-system-serif);",
        "",
        "  /* Fuentes accesibles y especializadas */",
        "  --font-atkinson: 'Atkinson Hyperlegible', var(--font-system);",
        "  --font-roboto-serif: 'Roboto Serif', var(--font-system-serif);",
        "  --font-noto-serif: 'Noto Serif', var(--font-system-serif);",
        "  --font-caslon: 'Libre Caslon Text', var(--font-system-serif);",
        "",
        "  /* Fuente activa (se cambia dinámicamente) */",
        "  --font-family-active: var(--font-inter);",
        "  --font-family-reading: var(--font-literata);",
        "}",
        "",
        "/* =============================================================================",
        "   CLASES DE FUENTE",
        "   ============================================================================= */",
        "",
        "/* Aplicar fuente activa globalmente */",
        ".font-active {",
        "  font-family: var(--font-family-active);",
        "}",
        "",
        "/* Clase para áreas de lectura de documentos */",
        ".reading-area {",
        "  font-family: var(--font-family-reading);",
        "}",
        "",
    ])

    css_path.write_text("\n".join(css_lines), encoding="utf-8")
    print(f"\n📄 Generado {css_path}")


if __name__ == "__main__":
    main()
