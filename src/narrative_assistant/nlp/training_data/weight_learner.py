"""
Sistema de pesos entrenables para votación ponderada.

Implementa Non-Negative Least Squares (NNLS) para aprender pesos óptimos
desde datos de entrenamiento.

Métodos disponibles:
1. NNLS: Optimización convexa con restricción de no-negatividad
2. Grid Search: Búsqueda exhaustiva en espacio de pesos
3. Cross-Validation: Validación cruzada para evitar overfitting
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .training_examples import TrainingExample

logger = logging.getLogger(__name__)


@dataclass
class TrainingResult:
    """Resultado del entrenamiento de pesos."""

    weights: dict  # {método: peso}
    mse: float  # Error cuadrático medio
    accuracy: float  # Precisión en clasificación
    cv_scores: list  # Scores de validación cruzada
    cv_mean: float
    cv_std: float
    n_examples: int
    n_iterations: int = 0


class TrainableWeightedVoting:
    """
    Sistema de votación con pesos aprendibles.

    Aprende los pesos óptimos para combinar múltiples métodos de extracción
    usando datos de entrenamiento etiquetados.

    Example:
        >>> learner = TrainableWeightedVoting(["llm", "embeddings", "dependency", "patterns"])
        >>> examples = generate_synthetic_dataset()
        >>> result = learner.train(examples)
        >>> print(result.weights)
        {'llm': 0.42, 'embeddings': 0.28, 'dependency': 0.18, 'patterns': 0.12}
    """

    DEFAULT_WEIGHTS = {
        "llm": 0.40,
        "embeddings": 0.25,
        "dependency": 0.20,
        "patterns": 0.15,
    }

    def __init__(
        self,
        methods: list[str] | None = None,
        min_weight: float = 0.05,
        normalize: bool = True,
    ):
        """
        Inicializa el sistema de pesos.

        Args:
            methods: Lista de métodos a ponderar
            min_weight: Peso mínimo por método
            normalize: Si normalizar pesos para que sumen 1.0
        """
        self.methods = methods or list(self.DEFAULT_WEIGHTS.keys())
        self.min_weight = min_weight
        self.normalize = normalize

        # Pesos actuales (empezar con defaults)
        self.weights = {m: self.DEFAULT_WEIGHTS.get(m, 0.25) for m in self.methods}
        self.is_trained = False
        self.training_result: TrainingResult | None = None

    def train(
        self,
        examples: list[TrainingExample],
        method: str = "nnls",
        cv_folds: int = 5,
        verbose: bool = True,
    ) -> TrainingResult:
        """
        Entrena los pesos con datos de entrenamiento.

        Args:
            examples: Ejemplos de entrenamiento
            method: Método de optimización ('nnls', 'grid_search')
            cv_folds: Número de folds para validación cruzada
            verbose: Mostrar progreso

        Returns:
            TrainingResult con pesos y métricas
        """
        if len(examples) < 10:
            raise ValueError("Se necesitan al menos 10 ejemplos de entrenamiento")

        if verbose:
            logger.info(f"Entrenando pesos con {len(examples)} ejemplos...")

        if method == "nnls":
            result = self._train_nnls(examples, cv_folds, verbose)
        elif method == "grid_search":
            result = self._train_grid_search(examples, cv_folds, verbose)
        else:
            raise ValueError(f"Método desconocido: {method}")

        self.weights = result.weights
        self.is_trained = True
        self.training_result = result

        if verbose:
            logger.info(f"Pesos aprendidos: {result.weights}")
            logger.info(f"MSE: {result.mse:.4f}, Accuracy: {result.accuracy:.2%}")
            logger.info(f"CV: {result.cv_mean:.4f} ± {result.cv_std:.4f}")

        return result

    def _train_nnls(
        self,
        examples: list[TrainingExample],
        cv_folds: int,
        verbose: bool,
    ) -> TrainingResult:
        """
        Entrena usando Non-Negative Least Squares.

        Minimiza: ||Xw - y||² sujeto a w >= 0
        """
        from scipy.optimize import nnls

        # Preparar datos
        X, y = self._prepare_data(examples)

        # Resolver NNLS
        weights_raw, residual = nnls(X, y)

        # Aplicar peso mínimo
        weights_raw = np.maximum(weights_raw, self.min_weight)

        # Normalizar si es necesario
        if self.normalize:
            weights_raw = weights_raw / weights_raw.sum()

        weights = {m: float(w) for m, w in zip(self.methods, weights_raw, strict=False)}

        # Calcular métricas
        predictions = X @ weights_raw
        mse = float(np.mean((predictions - y) ** 2))
        accuracy = self._calculate_accuracy(predictions, y)

        # Validación cruzada
        cv_scores = self._cross_validate(X, y, cv_folds)

        return TrainingResult(
            weights=weights,
            mse=mse,
            accuracy=accuracy,
            cv_scores=cv_scores,
            cv_mean=float(np.mean(cv_scores)),
            cv_std=float(np.std(cv_scores)),
            n_examples=len(examples),
        )

    def _train_grid_search(
        self,
        examples: list[TrainingExample],
        cv_folds: int,
        verbose: bool,
        resolution: int = 10,
    ) -> TrainingResult:
        """
        Entrena usando Grid Search sobre el espacio de pesos.

        Busca la mejor combinación de pesos que minimiza el error.
        """
        X, y = self._prepare_data(examples)

        best_weights: np.ndarray | None = None
        best_score = float("inf")
        n_iterations = 0

        # Generar grid de pesos (que sumen ~1.0)
        step = 1.0 / resolution

        def generate_weight_combinations(n_methods, current_sum=0.0, depth=0):
            """Genera combinaciones de pesos que suman 1.0"""
            if depth == n_methods - 1:
                remaining = 1.0 - current_sum
                if remaining >= self.min_weight:
                    yield [remaining]
                return

            for w in np.arange(
                self.min_weight, 1.0 - current_sum - self.min_weight * (n_methods - depth - 1), step
            ):
                for rest in generate_weight_combinations(n_methods, current_sum + w, depth + 1):
                    yield [w] + rest

        for weights_list in generate_weight_combinations(len(self.methods)):
            n_iterations += 1
            weights_arr = np.array(weights_list)

            # Evaluar
            predictions = X @ weights_arr
            score = np.mean((predictions - y) ** 2)

            if score < best_score:
                best_score = score
                best_weights = weights_arr

        if verbose:
            logger.info(f"Grid search: {n_iterations} combinaciones evaluadas")

        if best_weights is None:
            # Fallback defensivo: pesos uniformes si no se evaluó ninguna combinación válida.
            method_count = max(1, len(self.methods))
            best_weights = np.array([1.0 / method_count] * len(self.methods))

        # Resultados
        weights = {m: float(w) for m, w in zip(self.methods, best_weights, strict=True)}
        predictions = X @ best_weights
        accuracy = self._calculate_accuracy(predictions, y)
        cv_scores = self._cross_validate(X, y, cv_folds)

        return TrainingResult(
            weights=weights,
            mse=float(best_score),
            accuracy=accuracy,
            cv_scores=cv_scores,
            cv_mean=float(np.mean(cv_scores)),
            cv_std=float(np.std(cv_scores)),
            n_examples=len(examples),
            n_iterations=n_iterations,
        )

    def _prepare_data(
        self,
        examples: list[TrainingExample],
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Prepara matrices X (scores) e y (labels) para entrenamiento.

        Returns:
            (X, y) donde:
            - X: shape (n_samples, n_methods)
            - y: shape (n_samples,)
        """
        X = []
        y = []

        for example in examples:
            # Extraer scores para cada método (usar 0.5 si no existe)
            row = [example.scores.get(m, 0.5) for m in self.methods]
            X.append(row)

            # Label: 1.0 si es correcto, 0.0 si no
            y.append(1.0 if example.is_correct else 0.0)

        return np.array(X, dtype=np.float64), np.array(y, dtype=np.float64)

    def _cross_validate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_folds: int,
    ) -> list[float]:
        """
        Validación cruzada K-fold.

        Returns:
            Lista de scores (MSE) para cada fold
        """
        from scipy.optimize import nnls

        n_samples = len(X)
        fold_size = n_samples // n_folds
        indices = np.random.permutation(n_samples)

        cv_scores = []

        for fold in range(n_folds):
            # Dividir datos
            test_start = fold * fold_size
            test_end = test_start + fold_size

            test_idx = indices[test_start:test_end]
            train_idx = np.concatenate([indices[:test_start], indices[test_end:]])

            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            # Entrenar en fold
            weights_fold, _ = nnls(X_train, y_train)
            weights_fold = np.maximum(weights_fold, self.min_weight)
            if self.normalize:
                weights_fold = weights_fold / weights_fold.sum()

            # Evaluar
            predictions = X_test @ weights_fold
            mse = float(np.mean((predictions - y_test) ** 2))
            cv_scores.append(mse)

        return cv_scores

    def _calculate_accuracy(
        self,
        predictions: np.ndarray,
        y_true: np.ndarray,
        threshold: float = 0.5,
    ) -> float:
        """Calcula accuracy de clasificación."""
        pred_binary = (predictions >= threshold).astype(int)
        true_binary = (y_true >= threshold).astype(int)
        return float(np.mean(pred_binary == true_binary))

    def vote(
        self,
        scores: dict[str, float],
    ) -> tuple[float, dict[str, float]]:
        """
        Calcula voto ponderado con los pesos actuales.

        Args:
            scores: {método: score}

        Returns:
            (score_final, pesos_usados)
        """
        total = 0.0
        total_weight = 0.0

        for method in self.methods:
            if method in scores:
                weight = self.weights.get(method, 0.25)
                total += scores[method] * weight
                total_weight += weight

        if total_weight > 0:
            final_score = total / total_weight
        else:
            final_score = 0.5

        return final_score, dict(self.weights)

    def save(self, path: Path) -> None:
        """Guarda los pesos entrenados a archivo."""
        data = {
            "methods": self.methods,
            "weights": self.weights,
            "is_trained": self.is_trained,
            "training_result": None,
        }

        if self.training_result:
            data["training_result"] = {
                "weights": self.training_result.weights,
                "mse": self.training_result.mse,
                "accuracy": self.training_result.accuracy,
                "cv_mean": self.training_result.cv_mean,
                "cv_std": self.training_result.cv_std,
                "n_examples": self.training_result.n_examples,
            }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Pesos guardados en {path}")

    def load(self, path: Path) -> None:
        """Carga pesos desde archivo."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        self.methods = data["methods"]
        self.weights = data["weights"]
        self.is_trained = data["is_trained"]

        if data.get("training_result"):
            tr = data["training_result"]
            self.training_result = TrainingResult(
                weights=tr["weights"],
                mse=tr["mse"],
                accuracy=tr["accuracy"],
                cv_scores=[],
                cv_mean=tr["cv_mean"],
                cv_std=tr["cv_std"],
                n_examples=tr["n_examples"],
            )

        logger.info(f"Pesos cargados desde {path}: {self.weights}")


# =============================================================================
# Funciones de utilidad
# =============================================================================


def train_weights_from_examples(
    examples: list[TrainingExample],
    output_path: Path | None = None,
    method: str = "nnls",
) -> dict[str, float]:
    """
    Función de conveniencia para entrenar pesos.

    Args:
        examples: Ejemplos de entrenamiento
        output_path: Ruta para guardar pesos (opcional)
        method: Método de optimización

    Returns:
        Diccionario de pesos {método: peso}
    """
    learner = TrainableWeightedVoting()
    result = learner.train(examples, method=method)

    if output_path:
        learner.save(output_path)

    return result.weights


def compare_weights(
    default_weights: dict[str, float],
    learned_weights: dict[str, float],
    examples: list[TrainingExample],
) -> dict:
    """
    Compara rendimiento de pesos default vs aprendidos.

    Returns:
        Diccionario con métricas comparativas
    """
    default_learner = TrainableWeightedVoting()
    default_learner.weights = default_weights

    learned_learner = TrainableWeightedVoting()
    learned_learner.weights = learned_weights

    X, y = default_learner._prepare_data(examples)

    # Evaluar default
    default_preds = X @ np.array([default_weights[m] for m in default_learner.methods])
    default_mse = float(np.mean((default_preds - y) ** 2))
    default_acc = default_learner._calculate_accuracy(default_preds, y)

    # Evaluar learned
    learned_preds = X @ np.array([learned_weights[m] for m in learned_learner.methods])
    learned_mse = float(np.mean((learned_preds - y) ** 2))
    learned_acc = learned_learner._calculate_accuracy(learned_preds, y)

    return {
        "default": {
            "weights": default_weights,
            "mse": default_mse,
            "accuracy": default_acc,
        },
        "learned": {
            "weights": learned_weights,
            "mse": learned_mse,
            "accuracy": learned_acc,
        },
        "improvement": {
            "mse_reduction": (default_mse - learned_mse) / default_mse * 100,
            "accuracy_gain": (learned_acc - default_acc) * 100,
        },
    }
