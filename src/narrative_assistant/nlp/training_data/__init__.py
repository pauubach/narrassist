"""
Módulo de datos de entrenamiento para votación ponderada.

Contiene:
- TrainingExample: estructura para ejemplos de entrenamiento
- generate_synthetic_dataset: genera datos sintéticos
- TrainableWeightedVoting: sistema de pesos aprendibles
"""

from .training_examples import (
    TrainingExample,
    generate_synthetic_dataset,
    load_training_data,
    save_training_data,
)
from .weight_learner import TrainableWeightedVoting

__all__ = [
    "TrainingExample",
    "generate_synthetic_dataset",
    "load_training_data",
    "save_training_data",
    "TrainableWeightedVoting",
]
