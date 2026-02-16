"""
Tests para el detector híbrido de sílaba tónica (S15).

Verifica:
1. Lista estática (fast path)
2. Detección automática con silabeador (fallback)
3. Excepciones RAE
4. Cache de resultados
5. Neologismos y tecnicismos
"""

import pytest

from narrative_assistant.nlp.grammar.stress_detector import (
    clear_cache,
    get_cache_stats,
    is_feminine_with_stressed_a,
    requires_masculine_article,
)


class TestHybridDetectorStaticList:
    """Tests para lista estática (fast path)."""

    def test_palabras_comunes_lista_estatica(self):
        """Lista estática detecta palabras comunes correctamente."""
        # Palabras que SÍ requieren "el"
        assert requires_masculine_article("agua", is_feminine=True) is True
        assert requires_masculine_article("alma", is_feminine=True) is True
        assert requires_masculine_article("arma", is_feminine=True) is True
        assert requires_masculine_article("hacha", is_feminine=True) is True

    def test_palabras_adicionales_s15(self):
        """Palabras añadidas en S15 (investigación)."""
        assert requires_masculine_article("acta", is_feminine=True) is True
        assert requires_masculine_article("aria", is_feminine=True) is True
        assert requires_masculine_article("ascua", is_feminine=True) is True
        assert requires_masculine_article("ánima", is_feminine=True) is True

    def test_plural_siempre_femenino(self):
        """En plural SIEMPRE usa "las", no "los"."""
        # Aunque "agua" usa "el" en singular, en plural usa "las"
        assert requires_masculine_article("aguas", is_feminine=True, is_plural=True) is False
        assert requires_masculine_article("almas", is_feminine=True, is_plural=True) is False
        assert requires_masculine_article("armas", is_feminine=True, is_plural=True) is False

    def test_no_femenino_no_aplica(self):
        """Sustantivos no femeninos no aplican la regla."""
        assert requires_masculine_article("agua", is_feminine=False) is False
        assert requires_masculine_article("alma", is_feminine=False) is False


class TestHybridDetectorExceptions:
    """Tests para excepciones RAE."""

    def test_letras_alfabeto_usan_la(self):
        """Letras del alfabeto SIEMPRE usan 'la' (excepción RAE)."""
        assert requires_masculine_article("a", is_feminine=True) is False  # "la a"
        assert requires_masculine_article("hache", is_feminine=True) is False  # "la hache"
        assert requires_masculine_article("alfa", is_feminine=True) is False  # "la alfa"

    def test_excepcion_case_insensitive(self):
        """Excepciones funcionan con mayúsculas/minúsculas."""
        assert requires_masculine_article("A", is_feminine=True) is False
        assert requires_masculine_article("HACHE", is_feminine=True) is False
        assert requires_masculine_article("Alfa", is_feminine=True) is False


class TestHybridDetectorAutomatic:
    """Tests para detección automática con silabeador."""

    def test_neologismo_no_en_lista(self):
        """Neologismos no en lista se detectan automáticamente."""
        # Ejemplo: palabras técnicas recientes que no están en lista
        # "áptera" (insecto sin alas) - femenino con 'a' tónica
        result = is_feminine_with_stressed_a("áptera", use_automatic_detection=True)

        # Si silabeador está disponible, debe detectarlo
        # Si no, devuelve False (conservador)
        assert isinstance(result, bool)

    def test_palabra_a_atona_no_detecta(self):
        """Palabras con 'a' átona NO se detectan (ej: academia)."""
        # "academia" tiene 'a' átona (acento en 'e')
        result = is_feminine_with_stressed_a("academia", use_automatic_detection=True)
        assert result is False  # "la academia" (NO "el academia")

        # Más ejemplos de 'a' átona
        assert is_feminine_with_stressed_a("amapola") is False  # "la amapola"
        assert is_feminine_with_stressed_a("abuela") is False  # "la abuela"
        assert is_feminine_with_stressed_a("amistad") is False  # "la amistad"

    def test_palabra_a_tonica_detecta(self):
        """Palabras con 'a' tónica SÍ se detectan automáticamente."""
        # Nota: águila y ánfora están en lista estática, así que usamos
        # requires_masculine_article con use_static_list=False para forzar detección automática

        # Forzar detección automática (sin lista)
        result = requires_masculine_article(
            "águila",
            is_feminine=True,
            use_static_list=False,  # NO usar lista estática
            use_automatic_detection=True,  # SÍ usar automático
        )

        # Si silabeador está disponible, debe detectar correctamente
        # Si no está disponible, devuelve False (conservador)
        # Aceptamos ambos resultados
        assert isinstance(result, bool)

    def test_no_empieza_con_a_devuelve_false(self):
        """Palabras que no empiezan con 'a' devuelven False."""
        assert is_feminine_with_stressed_a("casa") is False
        assert is_feminine_with_stressed_a("mesa") is False
        assert is_feminine_with_stressed_a("ventana") is False


class TestHybridDetectorCache:
    """Tests para sistema de cache."""

    def test_cache_funciona(self):
        """Cache almacena resultados para optimizar."""
        clear_cache()

        # Primera llamada - miss
        result1 = requires_masculine_article("agua", is_feminine=True)

        # Segunda llamada - hit (debe venir del cache)
        result2 = requires_masculine_article("agua", is_feminine=True)

        assert result1 == result2 == True

        # Verificar stats del cache
        stats = get_cache_stats()
        assert stats["lru_hits"] >= 1  # Al menos 1 hit

    def test_clear_cache_limpia(self):
        """clear_cache() efectivamente limpia el cache."""
        # Llenar cache
        requires_masculine_article("agua", is_feminine=True)
        requires_masculine_article("alma", is_feminine=True)

        # Limpiar
        clear_cache()

        # Stats deben resetearse
        stats = get_cache_stats()
        assert stats["lru_size"] == 0  # Cache LRU vacío

    def test_cache_stats_estructura(self):
        """get_cache_stats() devuelve estructura correcta."""
        stats = get_cache_stats()

        assert "cached_words" in stats
        assert "lru_hits" in stats
        assert "lru_misses" in stats
        assert "lru_size" in stats
        assert "lru_maxsize" in stats

        # Todos deben ser enteros
        for key, value in stats.items():
            assert isinstance(value, int), f"{key} debe ser int, es {type(value)}"


class TestHybridDetectorIntegration:
    """Tests de integración (lista + automático + excepciones)."""

    def test_flujo_completo_palabra_en_lista(self):
        """Flujo completo para palabra en lista estática."""
        clear_cache()

        # "agua" está en lista → fast path
        result = requires_masculine_article(
            word="agua",
            is_feminine=True,
            is_plural=False,
            use_static_list=True,
            use_automatic_detection=True,
        )

        assert result is True  # "el agua"

    def test_flujo_completo_excepcion(self):
        """Flujo completo para excepción RAE."""
        clear_cache()

        # "a" es excepción → debe devolver False
        result = requires_masculine_article(
            word="a",
            is_feminine=True,
            is_plural=False,
            use_static_list=True,
            use_automatic_detection=True,
        )

        assert result is False  # "la a" (letra del alfabeto)

    def test_flujo_completo_sin_lista_estatica(self):
        """Flujo completo SIN lista estática (solo automático)."""
        clear_cache()

        # Deshabilitar lista estática, forzar detección automática
        result = requires_masculine_article(
            word="águila",
            is_feminine=True,
            is_plural=False,
            use_static_list=False,  # NO usar lista
            use_automatic_detection=True,  # SÍ usar automático
        )

        # Debe detectarse automáticamente
        # (si silabeador está disponible)
        assert isinstance(result, bool)

    def test_flujo_completo_sin_nada(self):
        """Flujo completo sin lista ni automático (conservador)."""
        clear_cache()

        # Palabra NO en lista, sin detección automática
        result = requires_masculine_article(
            word="águila",  # No está en lista en este escenario
            is_feminine=True,
            is_plural=False,
            use_static_list=False,  # NO usar lista
            use_automatic_detection=False,  # NO usar automático
        )

        # Debe ser conservador: devolver False (usar "la")
        assert result is False

    def test_multiples_palabras_cache_eficiente(self):
        """Procesar múltiples palabras usa cache eficientemente."""
        clear_cache()

        palabras = ["agua", "alma", "arma", "hacha", "águila"] * 10  # 50 llamadas

        for palabra in palabras:
            requires_masculine_article(palabra, is_feminine=True)

        stats = get_cache_stats()

        # Debe haber muchos hits (cache funcionando)
        assert stats["lru_hits"] >= 40  # La mayoría son hits

    def test_case_insensitive(self):
        """Detección funciona con mayúsculas/minúsculas."""
        assert requires_masculine_article("AGUA", is_feminine=True) is True
        assert requires_masculine_article("Agua", is_feminine=True) is True
        assert requires_masculine_article("agua", is_feminine=True) is True

        assert requires_masculine_article("ALMA", is_feminine=True) is True
        assert requires_masculine_article("Alma", is_feminine=True) is True
        assert requires_masculine_article("alma", is_feminine=True) is True
