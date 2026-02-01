"""
Fingerprinting de documentos para detectar documentos similares.

Permite:
- Detectar si un documento ya fue analizado
- Detectar versiones modificadas del mismo documento
- Continuar análisis donde se dejó
"""

import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from ..core.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class DocumentFingerprint:
    """
    Fingerprint de un documento.

    Attributes:
        full_hash: Hash SHA-256 del contenido completo normalizado
        sample_hash: Hash de una muestra (primeros N caracteres)
        word_count: Conteo de palabras
        char_count: Conteo de caracteres
        first_words: Primeras 50 palabras (para display)
        unique_words_sample: Palabras únicas para Jaccard básico
        ngram_shingles: Set de n-gramas para MinHash/Jaccard más preciso
    """

    full_hash: str
    sample_hash: str
    word_count: int
    char_count: int
    first_words: str
    unique_words_sample: frozenset  # Para calcular similitud Jaccard básica
    ngram_shingles: frozenset = frozenset()  # N-gramas para similitud más precisa

    def __str__(self) -> str:
        return f"Fingerprint({self.full_hash[:12]}..., {self.word_count} words)"

    def to_dict(self) -> dict:
        """Serializa a diccionario para almacenamiento."""
        return {
            "full_hash": self.full_hash,
            "sample_hash": self.sample_hash,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "first_words": self.first_words,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DocumentFingerprint":
        """Deserializa desde diccionario."""
        return cls(
            full_hash=data["full_hash"],
            sample_hash=data["sample_hash"],
            word_count=data["word_count"],
            char_count=data["char_count"],
            first_words=data["first_words"],
            unique_words_sample=frozenset(),  # Se recalcula si es necesario
        )


class FingerprintGenerator:
    """Genera fingerprints de documentos."""

    # Tamaño de n-grama por defecto (caracteres)
    DEFAULT_NGRAM_SIZE = 5
    # Número máximo de shingles a almacenar
    MAX_SHINGLES = 2000

    def __init__(
        self,
        sample_size: Optional[int] = None,
        ngram_size: int = DEFAULT_NGRAM_SIZE,
    ):
        """
        Args:
            sample_size: Caracteres a usar para sample_hash. Default: config.
            ngram_size: Tamaño de los n-gramas para shingles.
        """
        config = get_config()
        self.sample_size = sample_size or config.persistence.fingerprint_sample_size
        self.ngram_size = ngram_size

    def normalize_text(self, text: str) -> str:
        """
        Normaliza texto para fingerprinting consistente.

        - Unicode NFC
        - Lowercase
        - Colapsar whitespace
        - Remover puntuación (solo para hash)
        """
        # Unicode normalization
        text = unicodedata.normalize("NFC", text)

        # Lowercase
        text = text.lower()

        # Colapsar whitespace
        text = re.sub(r"\s+", " ", text)

        # Remover puntuación para hash (mantener palabras)
        text = re.sub(r"[^\w\s]", "", text)

        return text.strip()

    def generate_ngram_shingles(self, text: str) -> frozenset:
        """
        Genera n-gramas (shingles) del texto para comparación Jaccard.

        Usar n-gramas de caracteres es más robusto que palabras porque:
        - Captura orden y contexto local
        - Menos sensible a errores tipográficos
        - Mejor para detectar reordenamientos menores

        Args:
            text: Texto normalizado

        Returns:
            frozenset de n-gramas hasheados
        """
        if len(text) < self.ngram_size:
            return frozenset([text])

        # Generar n-gramas
        ngrams = set()
        for i in range(len(text) - self.ngram_size + 1):
            ngram = text[i : i + self.ngram_size]
            # Hashear para reducir memoria
            ngram_hash = hash(ngram) & 0xFFFFFFFF  # 32-bit hash
            ngrams.add(ngram_hash)

            # Limitar cantidad de shingles
            if len(ngrams) >= self.MAX_SHINGLES:
                break

        return frozenset(ngrams)

    def generate(self, text: str) -> DocumentFingerprint:
        """
        Genera fingerprint de un documento.

        Args:
            text: Contenido completo del documento

        Returns:
            DocumentFingerprint con hashes y métricas
        """
        # Normalizar
        normalized = self.normalize_text(text)

        # Hash completo
        full_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

        # Hash de muestra (primeros N caracteres)
        sample = normalized[: self.sample_size]
        sample_hash = hashlib.sha256(sample.encode("utf-8")).hexdigest()

        # Métricas
        words = normalized.split()
        word_count = len(words)
        char_count = len(text)

        # Primeras palabras (del texto original, no normalizado)
        original_words = text.split()[:50]
        first_words = " ".join(original_words)
        if len(original_words) == 50:
            first_words += "..."

        # Palabras únicas para similitud Jaccard básica (muestra)
        sample_words = set(words[: self.sample_size // 5])  # ~2000 palabras

        # N-gramas para similitud más precisa
        ngram_shingles = self.generate_ngram_shingles(sample)

        return DocumentFingerprint(
            full_hash=full_hash,
            sample_hash=sample_hash,
            word_count=word_count,
            char_count=char_count,
            first_words=first_words,
            unique_words_sample=frozenset(sample_words),
            ngram_shingles=ngram_shingles,
        )


@dataclass
class FingerprintMatch:
    """Resultado de comparación de fingerprints."""

    is_exact_match: bool  # Mismo documento exacto
    is_similar: bool  # Versión modificada probable
    similarity_score: float  # 0.0 - 1.0
    existing_fingerprint: Optional[DocumentFingerprint]
    existing_project_id: Optional[int]
    existing_project_name: Optional[str]

    @property
    def match_type(self) -> str:
        """Tipo de match en texto."""
        if self.is_exact_match:
            return "exact"
        elif self.is_similar:
            return "similar"
        else:
            return "none"


class FingerprintMatcher:
    """Busca documentos similares en la base de datos."""

    def __init__(self, similarity_threshold: Optional[float] = None):
        """
        Args:
            similarity_threshold: Umbral para considerar documentos similares.
        """
        config = get_config()
        self.threshold = (
            similarity_threshold or config.persistence.similarity_threshold_same_doc
        )
        self.generator = FingerprintGenerator()

    def jaccard_similarity(self, set1: frozenset, set2: frozenset) -> float:
        """Calcula similitud Jaccard entre dos conjuntos."""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def combined_similarity(
        self,
        fp1: DocumentFingerprint,
        fp2: DocumentFingerprint,
    ) -> float:
        """
        Calcula similitud combinada usando múltiples señales.

        Combina:
        - Jaccard de palabras únicas
        - Jaccard de n-gramas (más preciso para orden)
        - Ratio de word_count

        Returns:
            Score combinado 0.0 - 1.0
        """
        # Jaccard de palabras
        word_jaccard = self.jaccard_similarity(
            fp1.unique_words_sample, fp2.unique_words_sample
        )

        # Jaccard de n-gramas (más peso porque considera orden)
        ngram_jaccard = self.jaccard_similarity(
            fp1.ngram_shingles, fp2.ngram_shingles
        )

        # Ratio de longitud
        word_ratio = min(fp1.word_count, fp2.word_count) / max(
            fp1.word_count, fp2.word_count, 1
        )

        # Ponderación: n-gramas tienen más peso
        combined = (word_jaccard * 0.3) + (ngram_jaccard * 0.5) + (word_ratio * 0.2)

        return combined

    def find_match(
        self, fingerprint: DocumentFingerprint, db
    ) -> FingerprintMatch:
        """
        Busca documentos similares en la base de datos.

        Args:
            fingerprint: Fingerprint del documento nuevo
            db: Instancia de Database

        Returns:
            FingerprintMatch con resultado de búsqueda
        """
        # 1. Buscar match exacto por full_hash
        exact = db.fetchone(
            """
            SELECT id, name, document_fingerprint
            FROM projects
            WHERE document_fingerprint = ?
            """,
            (fingerprint.full_hash,),
        )

        if exact:
            return FingerprintMatch(
                is_exact_match=True,
                is_similar=True,
                similarity_score=1.0,
                existing_fingerprint=fingerprint,
                existing_project_id=exact["id"],
                existing_project_name=exact["name"],
            )

        # 2. Buscar por sample_hash (podría ser versión anterior)
        # Nota: sample_hash se compara contra document_fingerprint (full_hash)
        # usando prefijo, lo que detecta documentos que comparten inicio idéntico.
        sample_match = db.fetchone(
            """
            SELECT id, name, document_fingerprint, word_count
            FROM projects
            WHERE document_fingerprint LIKE ?
            AND id != COALESCE(?, -1)
            """,
            (fingerprint.sample_hash[:16] + "%", None),
        )

        if sample_match:
            # El inicio del documento coincide — probable revisión
            word_ratio = (
                min(sample_match["word_count"], fingerprint.word_count)
                / max(sample_match["word_count"], fingerprint.word_count)
                if sample_match["word_count"] and fingerprint.word_count
                else 0.0
            )
            return FingerprintMatch(
                is_exact_match=False,
                is_similar=True,
                similarity_score=max(0.85, word_ratio),
                existing_fingerprint=None,
                existing_project_id=sample_match["id"],
                existing_project_name=sample_match["name"],
            )

        # 3. Buscar por word_count similar y calcular Jaccard
        similar_projects = db.fetchall(
            """
            SELECT id, name, document_fingerprint, word_count
            FROM projects
            WHERE word_count BETWEEN ? AND ?
            ORDER BY ABS(word_count - ?) ASC
            LIMIT 10
            """,
            (
                int(fingerprint.word_count * 0.8),
                int(fingerprint.word_count * 1.2),
                fingerprint.word_count,
            ),
        )

        best_match = None
        best_score = 0.0

        for project in similar_projects:
            # Necesitamos recalcular el fingerprint del proyecto existente
            # para comparar unique_words_sample
            # Por ahora, usamos heurística basada en word_count
            word_ratio = min(
                project["word_count"], fingerprint.word_count
            ) / max(project["word_count"], fingerprint.word_count)

            if word_ratio > best_score:
                best_score = word_ratio
                best_match = project

        if best_match and best_score >= self.threshold:
            return FingerprintMatch(
                is_exact_match=False,
                is_similar=True,
                similarity_score=best_score,
                existing_fingerprint=None,
                existing_project_id=best_match["id"],
                existing_project_name=best_match["name"],
            )

        # No match
        return FingerprintMatch(
            is_exact_match=False,
            is_similar=False,
            similarity_score=0.0,
            existing_fingerprint=None,
            existing_project_id=None,
            existing_project_name=None,
        )


def generate_fingerprint(text: str) -> DocumentFingerprint:
    """Atajo para generar fingerprint."""
    return FingerprintGenerator().generate(text)
