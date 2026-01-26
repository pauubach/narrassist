"""
Módulo de diccionarios offline para consulta de definiciones y sinónimos.

Este módulo gestiona múltiples fuentes de diccionarios:
- Wiktionary español (definiciones libres)
- Diccionario de sinónimos/antónimos
- Diccionarios personalizados del usuario

Todas las consultas son 100% offline después de la descarga inicial.
Los manuscritos NUNCA se envían a internet.

Uso:
    from narrative_assistant.dictionaries import get_dictionary_manager

    manager = get_dictionary_manager()

    # Buscar definición
    result = manager.lookup("efímero")
    if result.is_success:
        entry = result.value
        print(entry.definitions)
        print(entry.synonyms)
"""

from .manager import (
    DictionaryManager,
    get_dictionary_manager,
    reset_dictionary_manager,
)
from .models import (
    DictionaryEntry,
    DictionarySource,
    SynonymEntry,
    WordRelation,
)
from .sources import (
    BaseDictionarySource,
    WiktionarySource,
    SynonymSource,
    CustomDictionarySource,
)

__all__ = [
    # Manager
    "DictionaryManager",
    "get_dictionary_manager",
    "reset_dictionary_manager",
    # Models
    "DictionaryEntry",
    "DictionarySource",
    "SynonymEntry",
    "WordRelation",
    # Sources
    "BaseDictionarySource",
    "WiktionarySource",
    "SynonymSource",
    "CustomDictionarySource",
]
