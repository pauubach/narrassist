"""
ChangeDetector - Detección estadística de cambios en métricas de habla.
"""

import logging
import math
from typing import Optional

from .types import MetricChangeResult

logger = logging.getLogger(__name__)

# Thresholds de cambio por métrica (cambio relativo mínimo)
METRIC_THRESHOLDS = {
    "filler_rate": 0.15,  # Cambio > 15%
    "formality_score": 0.25,  # Cambio > 0.25 (escala 0-1)
    "avg_sentence_length": 0.30,  # Cambio > 30%
    "lexical_diversity": 0.20,  # Cambio > 20%
    "exclamation_rate": 0.50,  # Cambio > 50%
    "question_rate": 0.50,  # Cambio > 50%
}

# Métricas discretas (usan chi-cuadrado) vs continuas (usan z-test)
DISCRETE_METRICS = {"filler_rate", "exclamation_rate", "question_rate"}


class ChangeDetector:
    """
    Detecta cambios estadísticamente significativos en métricas de habla.

    Usa dos tipos de pruebas estadísticas:
    - Chi-cuadrado: Para métricas discretas (conteos)
    - Z-test: Para métricas continuas (promedios)

    Un cambio es significativo si:
    1. p-value < 0.05 (significancia estadística)
    2. relative_change > threshold (magnitud mínima)
    """

    @staticmethod
    def detect_metric_change(
        metric_name: str,
        value1: float,
        value2: float,
        n1: int,  # Tamaño de muestra ventana 1 (palabras)
        n2: int,  # Tamaño de muestra ventana 2 (palabras)
    ) -> MetricChangeResult:
        """
        Detecta si cambio en métrica es estadísticamente significativo.

        Args:
            metric_name: Nombre de la métrica
            value1: Valor en ventana 1
            value2: Valor en ventana 2
            n1: Tamaño de muestra ventana 1 (palabras)
            n2: Tamaño de muestra ventana 2 (palabras)

        Returns:
            MetricChangeResult con análisis del cambio
        """
        # Calcular cambio relativo
        if value1 == 0:
            relative_change = float("inf") if value2 > 0 else 0
        else:
            relative_change = abs(value2 - value1) / abs(value1)

        # Obtener threshold específico de la métrica
        threshold = METRIC_THRESHOLDS.get(metric_name, 0.20)

        # Prueba de significancia estadística
        if metric_name in DISCRETE_METRICS:
            # Chi-cuadrado para métricas discretas
            p_value = ChangeDetector._chi_squared_test(
                metric_name, value1, value2, n1, n2
            )
        else:
            # Z-test para métricas continuas
            p_value = ChangeDetector._z_test(metric_name, value1, value2, n1, n2)

        # Determinar si es significativo
        is_significant = (p_value < 0.05) and (relative_change > threshold)

        return MetricChangeResult(
            metric_name=metric_name,
            value1=value1,
            value2=value2,
            relative_change=relative_change,
            p_value=p_value,
            is_significant=is_significant,
        )

    @staticmethod
    def _chi_squared_test(
        metric_name: str, value1: float, value2: float, n1: int, n2: int
    ) -> float:
        """
        Prueba de chi-cuadrado para métricas discretas.

        Convierte tasas (%) a conteos absolutos y aplica chi2.

        Args:
            metric_name: Nombre de la métrica
            value1: Tasa en ventana 1 (ej: 8.5 muletillas/100 palabras)
            value2: Tasa en ventana 2
            n1: Total palabras en ventana 1
            n2: Total palabras en ventana 2

        Returns:
            p-value (0.0 - 1.0)
        """
        try:
            from scipy.stats import chi2_contingency

            # Convertir tasas a conteos absolutos
            # Ej: 8.5/100 palabras * 500 palabras = 42.5 → 43 muletillas
            count1 = int((value1 / 100) * n1)
            count2 = int((value2 / 100) * n2)

            # Crear tabla de contingencia
            # [[count, no_count], [count, no_count]]
            table = [[count1, n1 - count1], [count2, n2 - count2]]

            # Aplicar chi-cuadrado
            chi2, p_value, dof, expected = chi2_contingency(table)

            logger.debug(
                f"Chi2 test for {metric_name}: chi2={chi2:.3f}, p={p_value:.4f}"
            )

            return p_value

        except ImportError:
            logger.warning("scipy not available, using fallback p-value")
            # Fallback: Heurística simple basada en cambio relativo
            relative_change = abs(value2 - value1) / (abs(value1) + 0.0001)
            return max(0.01, 1.0 - relative_change)  # Rough approximation

        except Exception as e:
            logger.warning(f"Chi-squared test failed: {e}")
            return 1.0  # No significativo si falla

    @staticmethod
    def _z_test(
        metric_name: str, value1: float, value2: float, n1: int, n2: int
    ) -> float:
        """
        Z-test para métricas continuas.

        Asume distribución normal y calcula z-score basado en
        desviación estándar estimada.

        Args:
            metric_name: Nombre de la métrica
            value1: Valor en ventana 1
            value2: Valor en ventana 2
            n1: Tamaño de muestra ventana 1
            n2: Tamaño de muestra ventana 2

        Returns:
            p-value (0.0 - 1.0)
        """
        try:
            from scipy.stats import norm

            # Estimar pooled standard deviation
            pooled_std = ChangeDetector._estimate_pooled_std(
                metric_name, value1, value2
            )

            if pooled_std == 0:
                # Si no hay variación, no hay cambio significativo
                return 1.0

            # Calcular z-score
            # z = (mean1 - mean2) / (pooled_std * sqrt(1/n1 + 1/n2))
            std_error = pooled_std * math.sqrt(1 / n1 + 1 / n2)
            z_score = (value2 - value1) / std_error

            # Calcular p-value (two-tailed test)
            p_value = 2 * (1 - norm.cdf(abs(z_score)))

            logger.debug(
                f"Z-test for {metric_name}: z={z_score:.3f}, p={p_value:.4f}"
            )

            return p_value

        except ImportError:
            logger.warning("scipy not available, using fallback p-value")
            # Fallback: Heurística simple
            relative_change = abs(value2 - value1) / (abs(value1) + 0.0001)
            return max(0.01, 1.0 - relative_change)

        except Exception as e:
            logger.warning(f"Z-test failed: {e}")
            return 1.0

    @staticmethod
    def _estimate_pooled_std(metric_name: str, value1: float, value2: float) -> float:
        """
        Estima desviación estándar combinada (pooled std).

        Usa valores esperados basados en corpus literario español.

        Args:
            metric_name: Nombre de la métrica
            value1: Valor en ventana 1
            value2: Valor en ventana 2

        Returns:
            Desviación estándar estimada
        """
        # Desviaciones estándar típicas por métrica (basadas en corpus)
        typical_stds = {
            "formality_score": 0.15,  # Formalidad varía ~0.15
            "avg_sentence_length": 3.5,  # ASL varía ~3.5 palabras
            "lexical_diversity": 0.08,  # TTR varía ~0.08
        }

        # Obtener std típica para la métrica
        base_std = typical_stds.get(metric_name, 0.10)

        # Ajustar según magnitud de los valores
        avg_value = (value1 + value2) / 2
        scaling_factor = max(0.1, avg_value / 10)  # Escalar con magnitud

        pooled_std = base_std * scaling_factor

        return pooled_std

    @staticmethod
    def calculate_change_confidence(
        changes: dict[str, MetricChangeResult],
        window1_words: int,
        window2_words: int,
        window1_dialogues: int,
        window2_dialogues: int,
    ) -> float:
        """
        Calcula confianza agregada del cambio detectado.

        Combina múltiples factores:
        - Significancia estadística (p-values)
        - Tamaño de muestra (más palabras = más confianza)
        - Magnitud del cambio (cambios grandes = más confianza)
        - Número de diálogos (más líneas = más confianza)
        - Consenso entre métricas (más métricas cambian = más confianza)

        Args:
            changes: Dict de métricas que cambiaron
            window1_words: Total palabras en ventana 1
            window2_words: Total palabras en ventana 2
            window1_dialogues: Total diálogos en ventana 1
            window2_dialogues: Total diálogos en ventana 2

        Returns:
            Confianza agregada (0.0 - 1.0)
        """
        if not changes:
            return 0.0

        # 1. Significancia estadística promedio
        avg_p_value = sum(c.p_value for c in changes.values()) / len(changes)
        significance_component = 1 - avg_p_value

        # 2. Tamaño de muestra (cap a 500 palabras)
        avg_sample_size = (window1_words + window2_words) / 2
        sample_component = min(1.0, avg_sample_size / 500)

        # 3. Magnitud del cambio promedio
        avg_change_magnitude = sum(c.relative_change for c in changes.values()) / len(
            changes
        )
        magnitude_component = min(1.0, avg_change_magnitude)

        # 4. Número de diálogos (cap a 50 líneas)
        avg_dialogue_lines = (window1_dialogues + window2_dialogues) / 2
        dialogue_component = min(1.0, avg_dialogue_lines / 50)

        # 5. Consenso entre métricas (cuántas métricas cambiaron)
        from .metrics import TRACKED_METRICS

        metric_consensus = len(changes) / len(TRACKED_METRICS)

        # Combinar componentes con pesos
        confidence = (
            0.30 * significance_component
            + 0.25 * sample_component
            + 0.25 * magnitude_component
            + 0.10 * dialogue_component
            + 0.10 * metric_consensus
        )

        # Asegurar rango [0, 1]
        confidence = max(0.0, min(1.0, confidence))

        logger.debug(
            f"Confidence calculation: sig={significance_component:.2f}, "
            f"sample={sample_component:.2f}, mag={magnitude_component:.2f}, "
            f"dialogue={dialogue_component:.2f}, consensus={metric_consensus:.2f} "
            f"→ total={confidence:.2f}"
        )

        return round(confidence, 2)

    @staticmethod
    def determine_severity(
        changes: dict[str, MetricChangeResult],
        confidence: float,
        narrative_context: Optional = None,
    ) -> str:
        """
        Determina severidad de la alerta.

        Args:
            changes: Dict de métricas que cambiaron
            confidence: Confianza agregada (0.0-1.0)
            narrative_context: Contexto narrativo (opcional)

        Returns:
            Severidad: "low", "medium", "high"
        """
        # Severidad base según confianza y número de métricas
        if confidence > 0.85 and len(changes) >= 4:
            base_severity = "high"
        elif confidence > 0.7 and len(changes) >= 3:
            base_severity = "medium"
        else:
            base_severity = "low"

        # Ajustar según contexto narrativo
        if narrative_context and narrative_context.has_dramatic_event:
            # Reducir severidad si hay evento justificante
            severity_map = {"high": "medium", "medium": "low", "low": "low"}
            return severity_map[base_severity]

        return base_severity
