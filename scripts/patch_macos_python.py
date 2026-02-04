#!/usr/bin/env python3
"""
Script para parchear las rutas absolutas del Python.framework embebido en macOS
para usar rutas relativas (@executable_path, @loader_path, @rpath)

Este script debe ejecutarse después de extraer el Python.framework del .pkg oficial.
"""
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def run_command(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Ejecuta un comando y retorna el resultado"""
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        print(f"Error ejecutando: {' '.join(cmd)}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        sys.exit(1)
    return result


def get_dependencies(binary_path: Path) -> List[str]:
    """Obtiene las dependencias de un binario usando otool -L"""
    result = run_command(["otool", "-L", str(binary_path)], check=False)
    if result.returncode != 0:
        return []

    deps = []
    for line in result.stdout.splitlines()[1:]:  # Skip first line (binary name)
        line = line.strip()
        if line:
            # Extract just the path (before the version info in parentheses)
            dep_path = line.split(" (")[0].strip()
            deps.append(dep_path)
    return deps


def patch_binary_dependency(binary_path: Path, old_path: str, new_path: str) -> bool:
    """Parchea una dependencia en un binario usando install_name_tool"""
    try:
        run_command([
            "install_name_tool",
            "-change",
            old_path,
            new_path,
            str(binary_path)
        ])
        return True
    except Exception as e:
        print(f"  ⚠️  Error parcheando {binary_path.name}: {e}")
        return False


def patch_binary_id(binary_path: Path, new_id: str) -> bool:
    """Cambia el install_name ID de una librería"""
    try:
        run_command([
            "install_name_tool",
            "-id",
            new_id,
            str(binary_path)
        ])
        return True
    except Exception as e:
        print(f"  ⚠️  Error cambiando ID de {binary_path.name}: {e}")
        return False


def add_rpath(binary_path: Path, rpath: str) -> bool:
    """Añade un RPATH a un binario"""
    try:
        # Check if rpath already exists
        result = run_command(["otool", "-l", str(binary_path)], check=False)
        if f"path {rpath}" in result.stdout:
            return True  # Already has this rpath

        run_command([
            "install_name_tool",
            "-add_rpath",
            rpath,
            str(binary_path)
        ])
        return True
    except Exception as e:
        print(f"  ⚠️  Error añadiendo rpath a {binary_path.name}: {e}")
        return False


def adhoc_sign(binary_path: Path) -> bool:
    """Re-firma un binario con ad-hoc signing después de modificarlo"""
    try:
        run_command([
            "codesign",
            "--force",
            "--sign",
            "-",
            str(binary_path)
        ], check=False)
        return True
    except Exception as e:
        # No es crítico si falla
        return False


def patch_python_framework(framework_dir: Path) -> bool:
    """
    Parchea el Python.framework para usar rutas relativas

    Args:
        framework_dir: Ruta al directorio que contiene Python.framework
    """
    python_framework = framework_dir / "Python.framework"
    if not python_framework.exists():
        print(f"❌ Python.framework no encontrado en {framework_dir}")
        return False

    versions_dir = python_framework / "Versions" / "3.12"
    if not versions_dir.exists():
        print(f"❌ Versions/3.12 no encontrado en framework")
        return False

    print(f"\n{'='*80}")
    print(f"🔧 Parcheando Python.framework en {framework_dir}")
    print(f"{'='*80}\n")

    # 1. Parchear el binario Python (la librería del framework)
    python_lib = versions_dir / "Python"
    if python_lib.exists():
        print(f"📦 Parcheando librería Python del framework...")
        # Cambiar el install_name ID para que sea relativo
        new_id = "@rpath/Python.framework/Versions/3.12/Python"
        if patch_binary_id(python_lib, new_id):
            print(f"  ✅ ID cambiado a: {new_id}")
        else:
            print(f"  ⚠️  No se pudo cambiar ID")

    # 2. Parchear TODOS los ejecutables python en bin/
    bin_dir = versions_dir / "bin"
    python_executables = []

    # Buscar python3 y python3.12 (ambos si existen)
    for python_name in ["python3", "python3.12"]:
        python_exe = bin_dir / python_name
        if python_exe.exists() and not python_exe.is_symlink():
            python_executables.append(python_exe)

    if python_executables:
        print(f"\n🐍 Parcheando {len(python_executables)} ejecutable(s) python en framework...")

        for python3_exe in python_executables:
            print(f"  Parcheando {python3_exe.name}...")

            # Añadir RPATHs
            add_rpath(python3_exe, "@executable_path/..")

            # Obtener dependencias
            deps = get_dependencies(python3_exe)
            for dep in deps:
                if "/Library/Frameworks/Python.framework" in dep:
                    # python3 está en bin/, Python está en ../Python
                    # /Library/Frameworks/Python.framework/Versions/3.12/Python -> @executable_path/../Python
                    new_dep = dep.replace(
                        "/Library/Frameworks/Python.framework/Versions/3.12/Python",
                        "@executable_path/../Python"
                    )
                    if patch_binary_dependency(python3_exe, dep, new_dep):
                        print(f"    ✅ {dep}")
                        print(f"       → {new_dep}")
    else:
        print(f"\n⚠️  No se encontraron ejecutables python en {bin_dir}")
        return False

    # 3. Crear python3 en la raíz: un wrapper shell + binario parcheado
    # El wrapper configura PYTHONHOME para que Python encuentre lib-dynload
    python3_wrapper = framework_dir / "python3"
    python3_bin = framework_dir / "python3.bin"

    if python_executables:
        import shutil

        # Eliminar cualquier python3 existente (symlink o copia)
        if python3_wrapper.exists() or python3_wrapper.is_symlink():
            python3_wrapper.unlink()
        if python3_bin.exists() or python3_bin.is_symlink():
            python3_bin.unlink()

        # Copiar el ejecutable python a python3.bin y parchearlo
        print(f"\n🐍 Creando python3.bin en raíz con rutas parcheadas...")
        shutil.copy2(python_executables[0], python3_bin)

        # Parchear con rutas correctas para la ubicación raíz
        add_rpath(python3_bin, "@executable_path/Python.framework/Versions/3.12")
        add_rpath(python3_bin, "@executable_path/Python.framework/Versions/3.12/lib")

        deps = get_dependencies(python3_bin)
        for dep in deps:
            if "/Library/Frameworks/Python.framework/Versions/3.12/Python" in dep or \
               "@executable_path/../Python" in dep or \
               "Python.framework" in dep:
                new_dep = "@executable_path/Python.framework/Versions/3.12/Python"
                if dep != new_dep:
                    if patch_binary_dependency(python3_bin, dep, new_dep):
                        print(f"  ✅ {dep}")
                        print(f"     → {new_dep}")

        # Re-firmar después de modificar
        adhoc_sign(python3_bin)
        print(f"  ✅ python3.bin parcheado y firmado")

        # Crear wrapper shell que configure PYTHONHOME
        print(f"\n📜 Creando wrapper shell python3...")
        wrapper_content = '''#!/bin/bash
# Wrapper para python3 que configura PYTHONHOME

# Obtener directorio donde está este script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Configurar PYTHONHOME
export PYTHONHOME="$SCRIPT_DIR/Python.framework/Versions/3.12"

# Ejecutar python3.bin real con todos los argumentos
exec "$SCRIPT_DIR/python3.bin" "$@"
'''
        python3_wrapper.write_text(wrapper_content)
        python3_wrapper.chmod(0o755)
        print(f"  ✅ python3 wrapper creado")

    # 4. Parchear Python.app (ejecutable que se invoca al abrir archivos .py)
    python_app_exe = versions_dir / "Resources" / "Python.app" / "Contents" / "MacOS" / "Python"
    if python_app_exe.exists():
        print(f"\n🍎 Parcheando Python.app ejecutable...")
        deps = get_dependencies(python_app_exe)
        for dep in deps:
            if "/Library/Frameworks/Python.framework" in dep:
                # Python.app/Contents/MacOS/Python está en Resources/.../MacOS/
                # Python está en ../../../../Python
                new_dep = dep.replace(
                    "/Library/Frameworks/Python.framework/Versions/3.12/Python",
                    "@executable_path/../../../../Python"
                )
                if patch_binary_dependency(python_app_exe, dep, new_dep):
                    print(f"  ✅ {dep}")
                    print(f"     → {new_dep}")

    # 5. Parchear todos los módulos .so en lib/python3.12/lib-dynload/
    dynload_dir = versions_dir / "lib" / "python3.12" / "lib-dynload"
    if dynload_dir.exists():
        so_files = list(dynload_dir.glob("*.so"))
        if so_files:
            print(f"\n📚 Parcheando {len(so_files)} módulos de extensión...")
            patched_count = 0
            for so_file in so_files:
                deps = get_dependencies(so_file)
                needs_patch = False

                for dep in deps:
                    if "/Library/Frameworks/Python.framework" in dep:
                        needs_patch = True
                        # .so está en lib/python3.12/lib-dynload/, Python está en ../../../Python
                        new_dep = dep.replace(
                            "/Library/Frameworks/Python.framework/Versions/3.12/Python",
                            "@loader_path/../../../Python"
                        )
                        # También parchear todas las bibliotecas .dylib
                        new_dep = new_dep.replace(
                            "/Library/Frameworks/Python.framework/Versions/3.12/lib/",
                            "@loader_path/../../../lib/"
                        )
                        patch_binary_dependency(so_file, dep, new_dep)

                if needs_patch:
                    patched_count += 1

            print(f"  ✅ Parcheados {patched_count} módulos")

    # 6. Parchear bibliotecas en lib/ (si existen)
    lib_dir = versions_dir / "lib"
    if lib_dir.exists():
        dylib_files = list(lib_dir.glob("*.dylib"))
        if dylib_files:
            print(f"\n📚 Parcheando {len(dylib_files)} bibliotecas dinámicas...")
            patched_count = 0
            for dylib in dylib_files:
                # Cambiar install_name ID
                new_id = f"@rpath/Python.framework/Versions/3.12/lib/{dylib.name}"
                patch_binary_id(dylib, new_id)

                # Parchear dependencias
                deps = get_dependencies(dylib)
                for dep in deps:
                    if "/Library/Frameworks/Python.framework" in dep:
                        # .dylib está en lib/, Python está en ../Python
                        new_dep = dep.replace(
                            "/Library/Frameworks/Python.framework/Versions/3.12/Python",
                            "@loader_path/../Python"
                        )
                        # Parchear referencias a otras bibliotecas en lib/
                        new_dep = new_dep.replace(
                            "/Library/Frameworks/Python.framework/Versions/3.12/lib/",
                            "@loader_path/"
                        )
                        patch_binary_dependency(dylib, dep, new_dep)
                        patched_count += 1

            if patched_count > 0:
                print(f"  ✅ Parcheadas {len(dylib_files)} bibliotecas")

    # 7. Parchear específicamente las referencias de OpenSSL entre librerías
    # libssl.3.dylib referencia a libcrypto.3.dylib
    libssl = lib_dir / "libssl.3.dylib"
    libcrypto = lib_dir / "libcrypto.3.dylib"
    if libssl.exists() and libcrypto.exists():
        print(f"\n🔐 Parcheando referencias OpenSSL...")
        deps = get_dependencies(libssl)
        for dep in deps:
            if "libcrypto" in dep and "/Library/Frameworks" in dep:
                patch_binary_dependency(libssl, dep, "@loader_path/libcrypto.3.dylib")
                print(f"  ✅ libssl.3.dylib → libcrypto.3.dylib parcheado")

    print(f"\n{'='*80}")
    print(f"✅ Framework parcheado exitosamente")
    print(f"{'='*80}\n")

    # Re-firmar binarios modificados (ad-hoc signing)
    print("🔏 Re-firmando binarios modificados...")
    binaries_to_sign = [python_lib]
    binaries_to_sign.extend(python_executables)  # Todos los ejecutables parcheados
    if python3_bin.exists():
        binaries_to_sign.append(python3_bin)
    if python_app_exe.exists():
        binaries_to_sign.append(python_app_exe)

    signed_count = 0
    for binary in binaries_to_sign:
        if binary.exists():
            if adhoc_sign(binary):
                signed_count += 1

    print(f"  ✅ {signed_count} binarios re-firmados\n")

    # Verificar que funciona
    print("🧪 Verificando que los ejecutables funcionan...")

    # Probar todos los ejecutables parcheados
    all_working = True
    for python_exe in python_executables:
        result = run_command([str(python_exe), "--version"], check=False)
        if result.returncode == 0:
            print(f"  ✅ {python_exe.name}: {result.stdout.strip()}")
        else:
            print(f"  ⚠️  {python_exe.name} no funciona:")
            print(f"     {result.stderr}")
            all_working = False

    # Probar el wrapper (que configura PYTHONHOME correctamente)
    if python3_wrapper.exists():
        result_wrapper = run_command([str(python3_wrapper), "--version"], check=False)
        if result_wrapper.returncode == 0:
            print(f"  ✅ Wrapper python3: {result_wrapper.stdout.strip()}")
        else:
            print(f"  ⚠️  Wrapper python3 no funciona:")
            print(f"     {result_wrapper.stderr}")
            all_working = False

    return all_working


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        target_dir = Path(sys.argv[1])
    else:
        # Default: src-tauri/binaries/python-embed
        repo_root = Path(__file__).parent.parent
        target_dir = repo_root / "src-tauri" / "binaries" / "python-embed"

    if not target_dir.exists():
        print(f"❌ Directorio no encontrado: {target_dir}")
        return 1

    success = patch_python_framework(target_dir)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
