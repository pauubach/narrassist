#!/usr/bin/env python3
"""
Genera iconos para la aplicación Tauri.

Crea iconos en todos los tamaños necesarios para Windows, macOS y Linux.
"""

import struct
import zlib
from pathlib import Path


def create_png(width: int, height: int) -> bytes:
    """
    Crea un PNG simple con el logo de Narrative Assistant.

    El icono representa una pluma estilizada (símbolo de escritura/edición)
    con colores profesionales: azul oscuro (#1e3a5f) y dorado (#d4a84b).
    """
    # Colores en RGB
    bg_color = (30, 58, 95)  # Azul oscuro #1e3a5f
    accent_color = (212, 168, 75)  # Dorado #d4a84b
    white = (255, 255, 255)

    # Crear matriz de píxeles
    pixels = []
    center_x = width // 2
    center_y = height // 2

    for y in range(height):
        row = []
        for x in range(width):
            # Calcular distancia al centro
            dx = x - center_x
            dy = y - center_y
            dist = (dx * dx + dy * dy) ** 0.5

            # Radio del círculo principal (80% del tamaño)
            radius = min(width, height) * 0.4
            inner_radius = radius * 0.7

            if dist <= radius:
                # Dentro del círculo principal
                if dist <= inner_radius:
                    # Centro con gradiente
                    # Dibujar una "N" estilizada
                    rel_x = (x - (center_x - inner_radius)) / (inner_radius * 2)
                    rel_y = (y - (center_y - inner_radius)) / (inner_radius * 2)

                    # Letra N estilizada
                    in_n = False

                    # Barra izquierda de la N
                    if 0.2 <= rel_x <= 0.35 and 0.2 <= rel_y <= 0.8:
                        in_n = True
                    # Barra derecha de la N
                    elif 0.65 <= rel_x <= 0.8 and 0.2 <= rel_y <= 0.8:
                        in_n = True
                    # Diagonal de la N
                    elif 0.2 <= rel_x <= 0.8 and 0.2 <= rel_y <= 0.8:
                        # Diagonal desde arriba-izquierda a abajo-derecha
                        diag_y = 0.2 + (rel_x - 0.2) * (0.8 - 0.2) / (0.8 - 0.2)
                        if abs(rel_y - diag_y) < 0.12:
                            in_n = True

                    if in_n:
                        row.append(white)
                    else:
                        row.append(bg_color)
                else:
                    # Borde dorado
                    row.append(accent_color)
            else:
                # Fondo transparente (usamos un color distintivo)
                row.append((0, 0, 0, 0))  # Transparente
        pixels.append(row)

    # Convertir a bytes PNG
    return encode_png(width, height, pixels)


def encode_png(width: int, height: int, pixels: list) -> bytes:
    """Codifica una imagen como PNG."""
    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        """Crea un chunk PNG."""
        chunk_len = struct.pack(">I", len(data))
        chunk_crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xffffffff)
        return chunk_len + chunk_type + data + chunk_crc

    # Cabecera PNG
    signature = b'\x89PNG\r\n\x1a\n'

    # IHDR chunk
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    ihdr = png_chunk(b'IHDR', ihdr_data)

    # IDAT chunk (datos de imagen comprimidos)
    raw_data = b''
    for row in pixels:
        raw_data += b'\x00'  # Filter byte
        for pixel in row:
            if len(pixel) == 4:
                raw_data += bytes(pixel)
            else:
                raw_data += bytes(pixel) + b'\xff'  # Añadir alpha opaco

    compressed = zlib.compress(raw_data, 9)
    idat = png_chunk(b'IDAT', compressed)

    # IEND chunk
    iend = png_chunk(b'IEND', b'')

    return signature + ihdr + idat + iend


def create_ico(sizes: list[tuple[int, int]], png_creator) -> bytes:
    """Crea un archivo ICO con múltiples tamaños."""
    images = []
    for size in sizes:
        png_data = png_creator(size[0], size[1])
        images.append((size[0], size[1], png_data))

    # Cabecera ICO
    header = struct.pack("<HHH", 0, 1, len(images))  # Reserved, Type (1=ICO), Count

    # Calcular offsets
    entries_size = 16 * len(images)
    offset = 6 + entries_size

    entries = b''
    image_data = b''

    for width, height, png_data in images:
        # Entrada del directorio
        w = 0 if width >= 256 else width
        h = 0 if height >= 256 else height
        entries += struct.pack(
            "<BBBBHHII",
            w, h,  # Width, Height (0 = 256)
            0,  # Color palette
            0,  # Reserved
            1,  # Color planes
            32,  # Bits per pixel
            len(png_data),  # Size of image data
            offset  # Offset to image data
        )
        image_data += png_data
        offset += len(png_data)

    return header + entries + image_data


def create_icns(png_creator) -> bytes:
    """
    Crea un archivo ICNS para macOS.

    Formato simplificado con tamanos pequenos para evitar timeouts.
    """
    # Tipos de iconos ICNS (solo tamanos pequenos para velocidad)
    icon_types = [
        (b'ic07', 128),   # 128x128
        (b'ic08', 256),   # 256x256
    ]

    data = b''
    for icon_type, size in icon_types:
        png_data = png_creator(size, size)
        # Cada entrada: tipo (4 bytes) + longitud (4 bytes) + datos
        entry = icon_type + struct.pack(">I", len(png_data) + 8) + png_data
        data += entry

    # Cabecera ICNS
    header = b'icns' + struct.pack(">I", len(data) + 8)

    return header + data


def main():
    """Genera todos los iconos necesarios para Tauri."""
    icons_dir = Path(__file__).parent.parent / "src-tauri" / "icons"
    icons_dir.mkdir(exist_ok=True)

    print("Generando iconos para Narrative Assistant...")

    # PNG en varios tamaños
    png_sizes = [
        (32, "32x32.png"),
        (128, "128x128.png"),
        (256, "128x128@2x.png"),  # Retina
    ]

    for size, filename in png_sizes:
        png_data = create_png(size, size)
        path = icons_dir / filename
        path.write_bytes(png_data)
        print(f"  [OK] {filename} ({size}x{size})")

    # ICO para Windows (multiples tamanos)
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_data = create_ico(ico_sizes, create_png)
    (icons_dir / "icon.ico").write_bytes(ico_data)
    print(f"  [OK] icon.ico (multiples tamanos)")

    # ICNS para macOS
    icns_data = create_icns(create_png)
    (icons_dir / "icon.icns").write_bytes(icns_data)
    print(f"  [OK] icon.icns (macOS)")

    # Tambien crear un icon.png de 512x512 como referencia
    icon_512 = create_png(512, 512)
    (icons_dir / "icon.png").write_bytes(icon_512)
    print(f"  [OK] icon.png (512x512)")

    print(f"\nIconos guardados en: {icons_dir}")


if __name__ == "__main__":
    main()
