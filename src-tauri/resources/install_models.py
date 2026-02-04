#!/usr/bin/env python3
"""
Standalone model installer for Narrative Assistant.

This script downloads NLP models WITHOUT requiring narrative_assistant package.
It can be bundled with the installer and run during installation.

Downloads:
- spaCy es_core_news_lg model (~500 MB)
- Sentence-transformers multilingual model (~500 MB)

Usage:
    python install_models.py              # Interactive mode
    python install_models.py --silent     # Silent mode for installers
    python install_models.py --check      # Check if models are installed
"""

import argparse
import os
import platform
import subprocess
import sys
import shutil
import hashlib
from pathlib import Path
from urllib.request import urlretrieve
from urllib.error import URLError

# Default models directory
def get_models_dir() -> Path:
    """Get the models directory path."""
    custom_dir = os.environ.get("NA_MODELS_DIR")
    if custom_dir:
        return Path(custom_dir)

    home = Path.home()
    return home / ".narrative_assistant" / "models"

MODELS_DIR = get_models_dir()

# Model information
SPACY_MODEL = "es_core_news_lg"
SPACY_VERSION = "3.8.0"
SPACY_URL = f"https://github.com/explosion/spacy-models/releases/download/{SPACY_MODEL}-{SPACY_VERSION}/{SPACY_MODEL}-{SPACY_VERSION}-py3-none-any.whl"

EMBEDDINGS_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDINGS_REPO = f"sentence-transformers/{EMBEDDINGS_MODEL}"


class ProgressReporter:
    """Progress reporter for downloads."""

    def __init__(self, silent: bool = False):
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
                print()

    def log(self, message: str):
        if not self.silent:
            print(message)

    def error(self, message: str):
        print(f"ERROR: {message}", file=sys.stderr)


def download_with_progress(url: str, dest: Path, progress: ProgressReporter, desc: str) -> bool:
    """Download a file with progress reporting."""
    try:
        def reporthook(block_num, block_size, total_size):
            if total_size > 0:
                downloaded = block_num * block_size
                percent = min(downloaded / total_size, 1.0)
                progress.report(f"{desc}: {downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB", percent)

        dest.parent.mkdir(parents=True, exist_ok=True)
        urlretrieve(url, dest, reporthook=reporthook)
        return True
    except URLError as e:
        progress.error(f"Error downloading {url}: {e}")
        return False
    except Exception as e:
        progress.error(f"Error: {e}")
        return False


def check_spacy_installed() -> bool:
    """Check if spaCy model is installed."""
    spacy_dir = MODELS_DIR / "spacy" / SPACY_MODEL
    return spacy_dir.exists() and (spacy_dir / "meta.json").exists()


def check_embeddings_installed() -> bool:
    """Check if embeddings model is installed."""
    emb_dir = MODELS_DIR / "embeddings" / EMBEDDINGS_MODEL
    return emb_dir.exists() and (emb_dir / "config.json").exists()


def install_spacy_model(progress: ProgressReporter, force: bool = False) -> bool:
    """Install spaCy model."""
    spacy_dir = MODELS_DIR / "spacy"
    model_dir = spacy_dir / SPACY_MODEL

    if model_dir.exists() and not force:
        progress.log(f"spaCy model already installed at {model_dir}")
        return True

    progress.log(f"Downloading spaCy model ({SPACY_MODEL})...")

    # Create temp directory for download
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        whl_path = tmpdir / f"{SPACY_MODEL}.whl"

        # Download the wheel file
        if not download_with_progress(SPACY_URL, whl_path, progress, "spaCy"):
            return False

        progress.log("Extracting spaCy model...")

        # Extract wheel (it's a zip file)
        import zipfile
        with zipfile.ZipFile(whl_path, 'r') as zip_ref:
            # Find the model directory in the wheel
            for name in zip_ref.namelist():
                if name.startswith(f"{SPACY_MODEL}/"):
                    zip_ref.extract(name, tmpdir)

        # Move to final location
        src = tmpdir / SPACY_MODEL
        if src.exists():
            if model_dir.exists():
                shutil.rmtree(model_dir)
            model_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(model_dir))
            progress.log(f"spaCy model installed at {model_dir}")
            return True
        else:
            progress.error("Failed to extract spaCy model")
            return False


def install_embeddings_model(progress: ProgressReporter, force: bool = False) -> bool:
    """Install sentence-transformers embeddings model."""
    emb_dir = MODELS_DIR / "embeddings"
    model_dir = emb_dir / EMBEDDINGS_MODEL

    if model_dir.exists() and not force:
        progress.log(f"Embeddings model already installed at {model_dir}")
        return True

    progress.log(f"Downloading embeddings model ({EMBEDDINGS_MODEL})...")

    # Use huggingface_hub if available, otherwise direct download
    try:
        from huggingface_hub import snapshot_download

        progress.log("Using huggingface_hub for download...")

        if model_dir.exists():
            shutil.rmtree(model_dir)

        model_dir.parent.mkdir(parents=True, exist_ok=True)

        snapshot_download(
            repo_id=EMBEDDINGS_REPO,
            local_dir=str(model_dir),
            local_dir_use_symlinks=False,
        )

        progress.log(f"Embeddings model installed at {model_dir}")
        return True

    except ImportError:
        progress.log("huggingface_hub not available, using pip...")

    # Fallback: use pip to download sentence-transformers which will cache models
    try:
        progress.log("Installing via sentence-transformers...")

        # Install sentence-transformers if not present
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "sentence-transformers"],
            check=True,
            capture_output=True
        )

        # Import and download model
        from sentence_transformers import SentenceTransformer

        progress.log("Downloading model (this may take a few minutes)...")
        model = SentenceTransformer(EMBEDDINGS_MODEL)

        # Get the cache location
        cache_dir = Path(model._model_card_vars.get("__cache_dir__", ""))

        if cache_dir.exists():
            if model_dir.exists():
                shutil.rmtree(model_dir)
            model_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(str(cache_dir), str(model_dir))
            progress.log(f"Embeddings model installed at {model_dir}")
            return True

        # Alternative: save directly
        model.save(str(model_dir))
        progress.log(f"Embeddings model installed at {model_dir}")
        return True

    except Exception as e:
        progress.error(f"Failed to install embeddings model: {e}")
        return False


def check_all_models() -> dict:
    """Check status of all models."""
    return {
        "spacy": check_spacy_installed(),
        "embeddings": check_embeddings_installed(),
        "models_dir": str(MODELS_DIR),
    }


def run_installation(silent: bool = False, force: bool = False) -> int:
    """Run the full installation process."""
    progress = ProgressReporter(silent=silent)

    progress.log("=" * 60)
    progress.log("Narrative Assistant - Model Installation")
    progress.log("=" * 60)
    progress.log(f"Models directory: {MODELS_DIR}")
    progress.log("")

    # Check current status
    status = check_all_models()

    need_spacy = not status["spacy"] or force
    need_embeddings = not status["embeddings"] or force

    if not need_spacy and not need_embeddings:
        progress.log("All models are already installed!")
        return 0

    success = True

    # Install spaCy
    if need_spacy:
        progress.log("")
        progress.log("[1/2] Installing spaCy model...")
        if not install_spacy_model(progress, force):
            success = False
    else:
        progress.log("[1/2] spaCy model: OK")

    # Install embeddings
    if need_embeddings:
        progress.log("")
        progress.log("[2/2] Installing embeddings model...")
        if not install_embeddings_model(progress, force):
            success = False
    else:
        progress.log("[2/2] Embeddings model: OK")

    progress.log("")
    progress.log("=" * 60)

    if success:
        progress.log("Installation completed successfully!")
        progress.log(f"Models installed at: {MODELS_DIR}")
        return 0
    else:
        progress.error("Some models failed to install.")
        progress.error("You may need to run this script again or install manually.")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Install NLP models for Narrative Assistant"
    )

    parser.add_argument(
        "--silent", "-s",
        action="store_true",
        help="Run in silent mode (minimal output)"
    )

    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Check if models are installed and exit"
    )

    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force re-download of models"
    )

    args = parser.parse_args()

    if args.check:
        status = check_all_models()
        print(f"Models directory: {status['models_dir']}")
        print(f"spaCy ({SPACY_MODEL}): {'OK' if status['spacy'] else 'NOT INSTALLED'}")
        print(f"Embeddings ({EMBEDDINGS_MODEL}): {'OK' if status['embeddings'] else 'NOT INSTALLED'}")

        all_ok = status["spacy"] and status["embeddings"]
        return 0 if all_ok else 1

    return run_installation(silent=args.silent, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
