# -*- coding: utf-8 -*-
"""
Modulo de evaluacion de precision para capacidades NLP.

Este modulo proporciona:
- Gold standards anotados manualmente
- Evaluadores por capacidad (NER, gramatica, relaciones, etc.)
- Script unificado de evaluacion
- Golden Corpus Harness con deteccion de regresiones

Uso:
    python tests/evaluation/run_evaluation.py --help
    python tests/evaluation/golden_corpus_harness.py --help
    pytest tests/evaluation/test_golden_corpus.py -v
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
from .golden_corpus_harness import GoldenCorpusHarness, HarnessReport
