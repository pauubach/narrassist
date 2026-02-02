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

    # 3. Manejar python3 en la raíz (puede ser symlink o copia)
    python3_root = framework_dir / "python3"
    if python3_root.exists():
        if python3_root.is_symlink():
            print(f"\n🔗 python3 es symlink (OK)")
        else:
            # Es una copia del binario, parchearlo también
            print(f"\n🐍 Parcheando python3 en raíz (copia)...")

            # Añadir RPATHs para que encuentre el framework
            add_rpath(python3_root, "@executable_path")

            deps = get_dependencies(python3_root)
            for dep in deps:
                if "/Library/Frameworks/Python.framework" in dep:
                    new_dep = dep.replace(
                        "/Library/Frameworks/Python.framework",
                        "@executable_path"
                    )
                    if patch_binary_dependency(python3_root, dep, new_dep):
                        print(f"  ✅ {dep}")
                        print(f"     → {new_dep}")
    elif python3_exe.exists():
        # Crear symlink relativo
        python3_root.symlink_to(python3_exe)
        print(f"\n🔗 Creado symlink: {python3_root} -> {python3_exe}")

    # 4. Parchear todos los módulos .so en lib/python3.12/lib-dynload/
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
                        patch_binary_dependency(so_file, dep, new_dep)

                if needs_patch:
                    patched_count += 1

            print(f"  ✅ Parcheados {patched_count} módulos")

    # 5. Parchear bibliotecas en lib/ (si existen)
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
                        patch_binary_dependency(dylib, dep, new_dep)
                        patched_count += 1

            if patched_count > 0:
                print(f"  ✅ Parcheadas {len(dylib_files)} bibliotecas")

    print(f"\n{'='*80}")
    print(f"✅ Framework parcheado exitosamente")
    print(f"{'='*80}\n")

    # Re-firmar binarios modificados (ad-hoc signing)
    print("🔏 Re-firmando binarios modificados...")
    binaries_to_sign = [python_lib]
    binaries_to_sign.extend(python_executables)  # Todos los ejecutables parcheados
    if python3_root.exists() and not python3_root.is_symlink():
        binaries_to_sign.append(python3_root)

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

    # Probar el ejecutable en la raíz (si existe y no es symlink)
    if python3_root.exists() and not python3_root.is_symlink():
        result_root = run_command([str(python3_root), "--version"], check=False)
        if result_root.returncode == 0:
            print(f"  ✅ Root python3: {result_root.stdout.strip()}")
        else:
            print(f"  ⚠️  Root python3 no funciona:")
            print(f"     {result_root.stderr}")
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
