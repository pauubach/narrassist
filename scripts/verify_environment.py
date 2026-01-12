#!/usr/bin/env python3
"""
Script de verificación del entorno de desarrollo.
Verifica todas las dependencias y capacidades GPU.

Uso:
    python scripts/verify_environment.py
"""

import sys
import time
from typing import Optional


def print_header(text: str) -> None:
    """Imprime header con formato."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")


def print_result(name: str, success: bool, detail: str = "") -> None:
    """Imprime resultado de verificación."""
    icon = "✅" if success else "❌"
    detail_str = f" ({detail})" if detail else ""
    print(f"  {icon} {name}{detail_str}")


def check_python_version() -> tuple[bool, str]:
    """Verifica versión de Python."""
    version = sys.version_info
    ok = version >= (3, 11)
    detail = f"{version.major}.{version.minor}.{version.micro}"
    return ok, detail


def check_spacy() -> tuple[bool, str]:
    """Verifica spaCy y modelo."""
    try:
        import spacy

        try:
            nlp = spacy.load("es_core_news_lg")
            return True, f"v{spacy.__version__}, modelo lg cargado"
        except OSError:
            try:
                nlp = spacy.load("es_core_news_sm")
                return True, f"v{spacy.__version__}, modelo sm cargado (lg no disponible)"
            except OSError:
                return False, f"v{spacy.__version__}, modelo no descargado"
    except ImportError:
        return False, "spacy no instalado"


def check_coreferee() -> tuple[bool, str]:
    """Verifica coreferee."""
    try:
        import coreferee

        try:
            import spacy

            nlp = spacy.load("es_core_news_lg")
            nlp.add_pipe("coreferee")
            return True, f"v{coreferee.__version__}"
        except Exception as e:
            return False, f"v{coreferee.__version__}, error al cargar: {e}"
    except ImportError:
        return False, "coreferee no instalado"


def check_sentence_transformers() -> tuple[bool, str]:
    """Verifica sentence-transformers."""
    try:
        from sentence_transformers import SentenceTransformer

        # No cargar modelo completo para verificación rápida
        return True, "instalado"
    except ImportError:
        return False, "sentence-transformers no instalado"


def check_docx() -> tuple[bool, str]:
    """Verifica python-docx."""
    try:
        import docx

        return True, f"v{docx.__version__}"
    except ImportError:
        return False, "python-docx no instalado"


def check_cuda() -> tuple[bool, str]:
    """Verifica soporte CUDA."""
    try:
        import torch

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            return True, f"{name} ({mem:.1f} GB)"
        return False, "CUDA no disponible"
    except ImportError:
        return False, "PyTorch no instalado"


def check_cupy() -> tuple[bool, str]:
    """Verifica CuPy para spaCy GPU."""
    try:
        import cupy

        cupy.cuda.runtime.getDeviceCount()
        return True, f"v{cupy.__version__}"
    except ImportError:
        return False, "cupy no instalado"
    except Exception:
        return False, "CUDA runtime error"


def check_mps() -> tuple[bool, str]:
    """Verifica soporte MPS (Apple Silicon)."""
    try:
        import torch

        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return True, "Apple Silicon GPU"
        return False, "MPS no disponible"
    except ImportError:
        return False, "PyTorch no instalado"


def check_thinc_apple() -> tuple[bool, str]:
    """Verifica thinc-apple-ops."""
    try:
        import thinc_apple_ops

        return True, "instalado"
    except ImportError:
        return False, "no instalado"


def check_pdf_support() -> tuple[bool, str]:
    """Verifica soporte PDF."""
    try:
        import pdfplumber

        return True, f"pdfplumber v{pdfplumber.__version__}"
    except ImportError:
        return False, "pdfplumber no instalado (opcional)"


def check_epub_support() -> tuple[bool, str]:
    """Verifica soporte EPUB."""
    try:
        import ebooklib

        return True, "ebooklib instalado"
    except ImportError:
        return False, "ebooklib no instalado (opcional)"


def benchmark_ner(use_gpu: bool = False) -> Optional[float]:
    """Benchmark de NER."""
    try:
        import spacy

        if use_gpu:
            try:
                spacy.require_gpu()
            except Exception:
                return None
        else:
            spacy.require_cpu()

        try:
            nlp = spacy.load("es_core_news_lg")
        except OSError:
            nlp = spacy.load("es_core_news_sm")

        # Texto de prueba (~500 palabras)
        text = """
        Juan García llegó a Madrid en una fría mañana de diciembre.
        La ciudad estaba cubierta de niebla y las calles permanecían casi desiertas.
        María lo esperaba en la estación, nerviosa por el reencuentro después de tantos años.
        """ * 20

        start = time.time()
        for _ in range(5):
            doc = nlp(text)
            _ = [(ent.text, ent.label_) for ent in doc.ents]
        elapsed = time.time() - start

        return elapsed / 5
    except Exception:
        return None


def benchmark_embeddings(device: str) -> Optional[float]:
    """Benchmark de embeddings."""
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(
            "paraphrase-multilingual-MiniLM-L12-v2", device=device
        )

        sentences = [f"Esta es la oración número {i}" for i in range(50)]

        start = time.time()
        _ = model.encode(sentences, batch_size=16)
        elapsed = time.time() - start

        return elapsed
    except Exception:
        return None


def main():
    print_header("VERIFICACIÓN DE ENTORNO - Asistente Corrección Narrativa")

    # 1. Core
    print("\n📦 Dependencias Core:")
    ok, detail = check_python_version()
    print_result("Python 3.11+", ok, detail)

    ok, detail = check_spacy()
    print_result("spaCy + modelo español", ok, detail)

    ok, detail = check_coreferee()
    print_result("Coreferee", ok, detail)

    ok, detail = check_sentence_transformers()
    print_result("sentence-transformers", ok, detail)

    ok, detail = check_docx()
    print_result("python-docx", ok, detail)

    # 2. Opcionales
    print("\n📦 Dependencias Opcionales:")

    ok, detail = check_pdf_support()
    print_result("Soporte PDF", ok, detail)

    ok, detail = check_epub_support()
    print_result("Soporte EPUB", ok, detail)

    # 3. GPU
    print("\n🎮 Soporte GPU:")

    cuda_ok, cuda_detail = check_cuda()
    print_result("CUDA (PyTorch)", cuda_ok, cuda_detail)

    cupy_ok, cupy_detail = check_cupy()
    print_result("CuPy (spaCy GPU)", cupy_ok, cupy_detail)

    mps_ok, mps_detail = check_mps()
    print_result("MPS (Apple Silicon)", mps_ok, mps_detail)

    thinc_ok, thinc_detail = check_thinc_apple()
    print_result("thinc-apple-ops", thinc_ok, thinc_detail)

    # 4. Benchmarks (opcional, puede tardar)
    run_benchmarks = "--benchmark" in sys.argv

    if run_benchmarks:
        print("\n⚡ Benchmarks (esto puede tardar unos segundos):")

        print("  Ejecutando benchmark NER (CPU)...", end=" ", flush=True)
        cpu_time = benchmark_ner(use_gpu=False)
        if cpu_time:
            print(f"{cpu_time:.3f}s/doc")
        else:
            print("error")

        if cuda_ok and cupy_ok:
            print("  Ejecutando benchmark NER (GPU)...", end=" ", flush=True)
            gpu_time = benchmark_ner(use_gpu=True)
            if gpu_time and cpu_time:
                speedup = cpu_time / gpu_time
                print(f"{gpu_time:.3f}s/doc (speedup: {speedup:.1f}x)")
            else:
                print("error")

        print("  Ejecutando benchmark embeddings (CPU)...", end=" ", flush=True)
        cpu_emb_time = benchmark_embeddings("cpu")
        if cpu_emb_time:
            print(f"{cpu_emb_time:.3f}s/50 oraciones")
        else:
            print("error")

        if cuda_ok:
            print("  Ejecutando benchmark embeddings (CUDA)...", end=" ", flush=True)
            gpu_emb_time = benchmark_embeddings("cuda")
            if gpu_emb_time and cpu_emb_time:
                speedup = cpu_emb_time / gpu_emb_time
                print(f"{gpu_emb_time:.3f}s/50 oraciones (speedup: {speedup:.1f}x)")
            else:
                print("error")
        elif mps_ok:
            print("  Ejecutando benchmark embeddings (MPS)...", end=" ", flush=True)
            mps_emb_time = benchmark_embeddings("mps")
            if mps_emb_time and cpu_emb_time:
                speedup = cpu_emb_time / mps_emb_time
                print(f"{mps_emb_time:.3f}s/50 oraciones (speedup: {speedup:.1f}x)")
            else:
                print("error")

    # 5. Resumen
    print_header("RESUMEN")

    gpu_available = cuda_ok or mps_ok
    spacy_gpu = (cuda_ok and cupy_ok) or (mps_ok and thinc_ok)

    print(f"\n  🖥️  GPU disponible: {'Sí' if gpu_available else 'No'}")
    print(f"  📝 spaCy puede usar GPU: {'Sí' if spacy_gpu else 'No'}")
    print(f"  🔢 Embeddings pueden usar GPU: {'Sí' if gpu_available else 'No'}")

    if gpu_available:
        print("\n  💡 Recomendación: Entorno óptimo con aceleración GPU")
    else:
        print("\n  💡 Recomendación: Considere instalar soporte GPU para mejor rendimiento")
        print("     Ver: docs/gpu-setup.md")

    if not run_benchmarks:
        print("\n  ℹ️  Ejecuta con --benchmark para ver comparativas de rendimiento")

    print()


if __name__ == "__main__":
    main()
