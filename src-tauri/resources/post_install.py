#!/usr/bin/env python3
"""
Post-installation script for Narrative Assistant.

This script is executed after the application is installed to download
required models. It can be run:
1. By the installer (NSIS/PKG) during installation
2. Manually by the user if models are missing
3. Automatically by the app on first launch

Usage:
    python post_install.py              # Interactive mode with GUI progress
    python post_install.py --silent     # Silent mode for installers
    python post_install.py --check      # Check if models are installed
    python post_install.py --ollama     # Also install Ollama and LLM models

Exit codes:
    0 - Success
    1 - Error during installation
    2 - User cancelled
"""

import argparse
import os
import platform
import subprocess
import sys
import urllib.request
import shutil
from pathlib import Path
from typing import Optional, Callable

# Determine paths
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    SCRIPT_DIR = Path(sys.executable).parent
    PROJECT_ROOT = SCRIPT_DIR.parent
else:
    # Running as script
    SCRIPT_DIR = Path(__file__).parent
    PROJECT_ROOT = SCRIPT_DIR.parent

# Add src to path for imports
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Model information
MODELS = {
    "spacy": {
        "name": "spaCy Spanish Model",
        "size_mb": 500,
        "required": True,
    },
    "embeddings": {
        "name": "Sentence Embeddings Model",
        "size_mb": 500,
        "required": True,
    },
    "ollama": {
        "name": "Ollama LLM Runtime",
        "size_mb": 800,
        "required": False,
    },
    "llm": {
        "name": "LLM Model (llama3.2)",
        "size_mb": 2000,
        "required": False,
    },
}


class ProgressReporter:
    """Base class for progress reporting."""

    def __init__(self):
        self.cancelled = False

    def report(self, message: str, percent: float):
        """Report progress. percent is 0.0 to 1.0"""
        pass

    def log(self, message: str):
        """Log a message."""
        pass

    def error(self, message: str):
        """Report an error."""
        pass

    def cancel(self):
        """Cancel the operation."""
        self.cancelled = True


class ConsoleProgress(ProgressReporter):
    """Console-based progress reporter."""

    def __init__(self, silent: bool = False):
        super().__init__()
        self.silent = silent
        self.last_percent = -1

    def report(self, message: str, percent: float):
        if self.silent:
            return

        percent_int = int(percent * 100)
        if percent_int != self.last_percent:
            bar_width = 40
            filled = int(bar_width * percent)
            bar = "=" * filled + "-" * (bar_width - filled)
            print(f"\r[{bar}] {percent_int:3d}% {message[:40]:<40}", end="", flush=True)
            self.last_percent = percent_int

            if percent >= 1.0:
                print()  # New line at end

    def log(self, message: str):
        if not self.silent:
            print(message)

    def error(self, message: str):
        print(f"ERROR: {message}", file=sys.stderr)


class GUIProgress(ProgressReporter):
    """GUI-based progress reporter using tkinter."""

    def __init__(self):
        super().__init__()
        self.root = None
        self.progress_var = None
        self.status_var = None
        self.progress_bar = None

        try:
            import tkinter as tk
            from tkinter import ttk

            self.root = tk.Tk()
            self.root.title("Narrative Assistant - Instalando modelos")
            self.root.geometry("500x200")
            self.root.resizable(False, False)

            # Center window
            self.root.update_idletasks()
            x = (self.root.winfo_screenwidth() - 500) // 2
            y = (self.root.winfo_screenheight() - 200) // 2
            self.root.geometry(f"+{x}+{y}")

            # Main frame
            frame = ttk.Frame(self.root, padding=20)
            frame.pack(fill=tk.BOTH, expand=True)

            # Title
            title = ttk.Label(frame, text="Descargando modelos necesarios...", font=("", 12, "bold"))
            title.pack(pady=(0, 10))

            # Status label
            self.status_var = tk.StringVar(value="Iniciando...")
            status = ttk.Label(frame, textvariable=self.status_var)
            status.pack(pady=5)

            # Progress bar
            self.progress_var = tk.DoubleVar(value=0)
            self.progress_bar = ttk.Progressbar(
                frame,
                variable=self.progress_var,
                maximum=100,
                length=400
            )
            self.progress_bar.pack(pady=10)

            # Cancel button
            cancel_btn = ttk.Button(frame, text="Cancelar", command=self.cancel)
            cancel_btn.pack(pady=10)

            # Handle window close
            self.root.protocol("WM_DELETE_WINDOW", self.cancel)

        except ImportError:
            # Fall back to console
            self.root = None

    def report(self, message: str, percent: float):
        if self.root:
            self.progress_var.set(percent * 100)
            self.status_var.set(message)
            self.root.update()

    def log(self, message: str):
        if self.root:
            self.status_var.set(message)
            self.root.update()

    def error(self, message: str):
        if self.root:
            try:
                from tkinter import messagebox
                messagebox.showerror("Error", message)
            except:
                pass
        print(f"ERROR: {message}", file=sys.stderr)

    def cancel(self):
        super().cancel()
        if self.root:
            self.root.destroy()

    def close(self):
        if self.root:
            self.root.destroy()


def check_models_installed() -> dict:
    """Check which models are installed."""
    try:
        from narrative_assistant.core.model_manager import get_model_manager, ModelType

        manager = get_model_manager()
        status = manager.get_all_models_status()

        result = {
            "spacy": status.get("spacy", {}).get("installed", False),
            "embeddings": status.get("embeddings", {}).get("installed", False),
        }

        # Check Ollama
        result["ollama"] = shutil.which("ollama") is not None

        # Check LLM model
        if result["ollama"]:
            try:
                output = subprocess.check_output(
                    ["ollama", "list"],
                    stderr=subprocess.DEVNULL,
                    text=True
                )
                result["llm"] = "llama3.2" in output or "llama3" in output
            except:
                result["llm"] = False
        else:
            result["llm"] = False

        return result

    except ImportError:
        return {"spacy": False, "embeddings": False, "ollama": False, "llm": False}


def download_nlp_models(progress: ProgressReporter, force: bool = False) -> bool:
    """Download NLP models (spaCy and embeddings)."""
    try:
        from narrative_assistant.core.model_manager import get_model_manager, ModelType

        manager = get_model_manager()

        # Download spaCy
        progress.log("Descargando modelo spaCy (es_core_news_lg)...")

        def spacy_callback(msg: str, pct: float):
            progress.report(f"spaCy: {msg}", pct * 0.5)  # First 50%
            if progress.cancelled:
                raise InterruptedError("Cancelled by user")

        result = manager.ensure_model(
            ModelType.SPACY,
            force_download=force,
            progress_callback=spacy_callback
        )

        if result.is_failure:
            progress.error(f"Error descargando spaCy: {result.error}")
            return False

        if progress.cancelled:
            return False

        # Download embeddings
        progress.log("Descargando modelo de embeddings...")

        def emb_callback(msg: str, pct: float):
            progress.report(f"Embeddings: {msg}", 0.5 + pct * 0.5)  # Last 50%
            if progress.cancelled:
                raise InterruptedError("Cancelled by user")

        result = manager.ensure_model(
            ModelType.EMBEDDINGS,
            force_download=force,
            progress_callback=emb_callback
        )

        if result.is_failure:
            progress.error(f"Error descargando embeddings: {result.error}")
            return False

        progress.report("Modelos NLP instalados correctamente", 1.0)
        return True

    except InterruptedError:
        progress.log("Instalación cancelada por el usuario")
        return False
    except Exception as e:
        progress.error(f"Error inesperado: {e}")
        return False


def install_ollama(progress: ProgressReporter) -> bool:
    """Install Ollama LLM runtime."""
    system = platform.system().lower()

    progress.log("Instalando Ollama...")

    try:
        if system == "windows":
            # Download Ollama installer
            url = "https://ollama.com/download/OllamaSetup.exe"
            installer_path = Path(os.environ.get("TEMP", "/tmp")) / "OllamaSetup.exe"

            progress.report("Descargando Ollama...", 0.2)
            urllib.request.urlretrieve(url, installer_path)

            progress.report("Instalando Ollama...", 0.5)
            # Run installer silently
            subprocess.run(
                [str(installer_path), "/S"],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

        elif system == "darwin":
            # Use brew if available, otherwise download
            if shutil.which("brew"):
                progress.report("Instalando via Homebrew...", 0.3)
                subprocess.run(["brew", "install", "ollama"], check=True)
            else:
                # Download PKG
                url = "https://ollama.com/download/Ollama-darwin.zip"
                # ... download and install
                progress.error("Instala Homebrew o descarga Ollama manualmente desde ollama.com")
                return False

        elif system == "linux":
            progress.report("Instalando via script oficial...", 0.3)
            subprocess.run(
                "curl -fsSL https://ollama.com/install.sh | sh",
                shell=True,
                check=True
            )

        progress.report("Ollama instalado", 0.8)

        # Start Ollama service
        progress.log("Iniciando servicio Ollama...")
        if system == "windows":
            subprocess.Popen(["ollama", "serve"],
                           creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.Popen(["ollama", "serve"],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)

        import time
        time.sleep(2)  # Wait for service to start

        progress.report("Ollama listo", 1.0)
        return True

    except Exception as e:
        progress.error(f"Error instalando Ollama: {e}")
        return False


def download_llm_model(progress: ProgressReporter, model: str = "llama3.2") -> bool:
    """Download LLM model via Ollama."""
    progress.log(f"Descargando modelo LLM ({model})...")

    try:
        # Run ollama pull
        process = subprocess.Popen(
            ["ollama", "pull", model],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            # Parse progress from ollama output
            if "pulling" in line.lower():
                # Extract percentage if available
                if "%" in line:
                    try:
                        pct = float(line.split("%")[0].split()[-1]) / 100
                        progress.report(f"Descargando {model}...", pct)
                    except:
                        pass

            if progress.cancelled:
                process.terminate()
                return False

        process.wait()

        if process.returncode == 0:
            progress.report(f"Modelo {model} instalado", 1.0)
            return True
        else:
            progress.error(f"Error descargando modelo {model}")
            return False

    except Exception as e:
        progress.error(f"Error: {e}")
        return False


def run_installation(
    silent: bool = False,
    include_ollama: bool = False,
    force: bool = False
) -> int:
    """Run the full installation process."""

    # Create progress reporter
    if silent:
        progress = ConsoleProgress(silent=True)
    else:
        # Try GUI, fall back to console
        progress = GUIProgress()
        if progress.root is None:
            progress = ConsoleProgress(silent=False)

    try:
        # Check what's already installed
        status = check_models_installed()

        total_steps = 0
        current_step = 0

        # Count steps
        if not status["spacy"] or force:
            total_steps += 1
        if not status["embeddings"] or force:
            total_steps += 1
        if include_ollama:
            if not status["ollama"]:
                total_steps += 1
            if not status["llm"]:
                total_steps += 1

        if total_steps == 0:
            progress.log("Todos los modelos ya están instalados.")
            if isinstance(progress, GUIProgress):
                progress.close()
            return 0

        progress.log(f"Instalando {total_steps} componente(s)...")

        # Download NLP models
        if not status["spacy"] or not status["embeddings"] or force:
            if not download_nlp_models(progress, force):
                if progress.cancelled:
                    return 2
                return 1

        # Install Ollama if requested
        if include_ollama:
            if not status["ollama"]:
                if not install_ollama(progress):
                    if progress.cancelled:
                        return 2
                    # Non-fatal, continue
                    progress.log("Ollama no instalado, continuando...")

            if not status["llm"] and shutil.which("ollama"):
                if not download_llm_model(progress):
                    if progress.cancelled:
                        return 2
                    # Non-fatal
                    progress.log("Modelo LLM no instalado, continuando...")

        progress.log("Instalación completada correctamente.")

        if isinstance(progress, GUIProgress):
            try:
                from tkinter import messagebox
                messagebox.showinfo(
                    "Instalación completada",
                    "Los modelos se han instalado correctamente.\n\n"
                    "Narrative Assistant está listo para usar."
                )
            except:
                pass
            progress.close()

        return 0

    except Exception as e:
        progress.error(f"Error durante la instalación: {e}")
        if isinstance(progress, GUIProgress):
            progress.close()
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Post-installation script for Narrative Assistant"
    )

    parser.add_argument(
        "--silent", "-s",
        action="store_true",
        help="Run in silent mode (no GUI, minimal output)"
    )

    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Check if models are installed and exit"
    )

    parser.add_argument(
        "--ollama",
        action="store_true",
        help="Also install Ollama and LLM models"
    )

    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force re-download of models"
    )

    args = parser.parse_args()

    if args.check:
        status = check_models_installed()
        all_required = status["spacy"] and status["embeddings"]

        print("Model Status:")
        for model, installed in status.items():
            icon = "[OK]" if installed else "[  ]"
            required = "(required)" if MODELS.get(model, {}).get("required") else "(optional)"
            print(f"  {icon} {model} {required}")

        return 0 if all_required else 1

    return run_installation(
        silent=args.silent,
        include_ollama=args.ollama,
        force=args.force
    )


if __name__ == "__main__":
    sys.exit(main())
