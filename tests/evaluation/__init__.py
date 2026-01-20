# -*- coding: utf-8 -*-
"""
Modulo de evaluacion de precision para capacidades NLP.

Este modulo proporciona:
- Gold standards anotados manualmente
- Evaluadores por capacidad (NER, gramatica, relaciones, etc.)
- Script unificado de evaluacion

Uso:
    python tests/evaluation/run_evaluation.py --help
"""

from .gold_standards import (
    ALL_GOLD_STANDARDS,
    GoldStandard,
    GoldEntity,
    GoldAttribute,
    GoldRelation,
    GoldEvent,
    GoldChapter,
    GoldGrammarError,
    GoldCoreference,
    TextType,
)
