"""Tests para el módulo de ontología de ubicaciones."""

import pytest

from narrative_assistant.analysis.location_ontology import (
    BUILDING_TYPES,
    EXTERIOR_TYPES,
    ROOM_TYPES,
    SPANISH_GAZETTEER,
    HistoricalPeriod,
    LocationNode,
    LocationOntology,
    LocationType,
    get_default_ontology,
)


class TestLocationOntologyBasic:
    """Tests básicos de la ontología de ubicaciones."""

    @pytest.fixture
    def ontology(self):
        """Ontología con datos de prueba."""
        o = LocationOntology()
        # España > Comunidad de Madrid > Madrid > casa > cocina
        o.add_from_text("España", LocationType.COUNTRY)
        o.add_from_text("Comunidad de Madrid", LocationType.REGION, parent="España")
        o.add_from_text("Madrid", LocationType.CITY, parent="Comunidad de Madrid")
        o.add_from_text("casa", LocationType.BUILDING, parent="Madrid")
        o.add_from_text("cocina", LocationType.ROOM, parent="casa")
        o.add_from_text("salón", LocationType.ROOM, parent="casa")
        # España > Cataluña > Barcelona
        o.add_from_text("Cataluña", LocationType.REGION, parent="España")
        o.add_from_text("Barcelona", LocationType.CITY, parent="Cataluña")
        return o

    def test_room_in_building_compatible(self, ontology):
        """cocina ⊂ casa → compatibles."""
        assert ontology.are_compatible("cocina", "casa") is True

    def test_multi_level_hierarchy(self, ontology):
        """cocina ⊂ casa ⊂ Madrid → todos compatibles entre sí."""
        assert ontology.are_compatible("cocina", "Madrid") is True
        assert ontology.are_compatible("casa", "Madrid") is True
        assert ontology.are_compatible("cocina", "casa") is True

    def test_different_cities_incompatible(self, ontology):
        """Madrid vs Barcelona → incompatibles."""
        assert ontology.are_compatible("Madrid", "Barcelona") is False

    def test_unknown_location_failsafe(self):
        """Ubicación desconocida → siempre compatible (evita falsos positivos)."""
        o = LocationOntology()
        o.add_from_text("Madrid", LocationType.CITY)
        # "taberna misteriosa" no está en la ontología
        assert o.are_compatible("Madrid", "taberna misteriosa") is True

    def test_rooms_same_parent_compatible(self, ontology):
        """Cocina y salón en la misma casa → compatibles."""
        assert ontology.are_compatible("cocina", "salón") is True

    def test_ancestors_chain(self, ontology):
        """Cadena de ancestros correcta."""
        ancestors = ontology.get_ancestors("cocina")
        # casa, Madrid, Comunidad de Madrid, España
        assert len(ancestors) >= 2
        assert "casa" in ancestors
        assert (
            "Madrid" in [ontology._normalize(a) for a in ancestors]
            or "Madrid" in ancestors
        )

    def test_descendants(self, ontology):
        """Descendientes de casa: cocina, salón."""
        descendants = ontology.get_descendants("casa")
        assert "cocina" in descendants
        assert "salon" in descendants  # normalized (sin acento)


class TestLocationOntologyReachability:
    """Tests de alcanzabilidad geográfica."""

    @pytest.fixture
    def ontology(self):
        """Ontología con coordenadas."""
        o = LocationOntology()
        o.add_location(
            LocationNode(
                name="Madrid",
                normalized_name="madrid",
                location_type=LocationType.CITY,
                latitude=40.4168,
                longitude=-3.7038,
            )
        )
        o.add_location(
            LocationNode(
                name="Barcelona",
                normalized_name="barcelona",
                location_type=LocationType.CITY,
                latitude=41.3851,
                longitude=2.1734,
            )
        )
        return o

    def test_reachability_modern(self, ontology):
        """Madrid→Barcelona en 24h moderno (coche) → alcanzable."""
        assert (
            ontology.is_reachable(
                "Madrid", "Barcelona", hours=24, period=HistoricalPeriod.MODERN
            )
            is True
        )

    def test_reachability_medieval_impossible(self, ontology):
        """Madrid→Barcelona en 2h medieval → inalcanzable."""
        assert (
            ontology.is_reachable(
                "Madrid", "Barcelona", hours=2, period=HistoricalPeriod.MEDIEVAL
            )
            is False
        )

    def test_haversine_distance(self, ontology):
        """Distancia Madrid-Barcelona ~500-625 km."""
        dist = ontology.distance_km("Madrid", "Barcelona")
        assert dist is not None
        assert 500 <= dist <= 625


class TestAliasResolution:
    """Tests de resolución de alias."""

    def test_alias_resolution(self):
        """'Ciudad Condal' → Barcelona."""
        o = LocationOntology()
        o.add_location(
            LocationNode(
                name="Barcelona",
                normalized_name="barcelona",
                location_type=LocationType.CITY,
                aliases=["Ciudad Condal", "Barna"],
            )
        )
        node = o.resolve("Ciudad Condal")
        assert node is not None
        assert node.name == "Barcelona"

    def test_alias_with_accents(self):
        """Resolución con/sin acentos."""
        o = LocationOntology()
        o.add_location(
            LocationNode(
                name="Córdoba",
                normalized_name="cordoba",
                location_type=LocationType.CITY,
                aliases=["Corduba"],
            )
        )
        node = o.resolve("córdoba")
        assert node is not None
        assert node.name == "Córdoba"

        node2 = o.resolve("Corduba")
        assert node2 is not None
        assert node2.name == "Córdoba"


class TestDefaultOntology:
    """Tests para la ontología por defecto."""

    def test_default_has_gazetteer(self):
        """La ontología por defecto tiene las ciudades del gazetteer."""
        o = get_default_ontology()
        assert o.resolve("Madrid") is not None
        assert o.resolve("Barcelona") is not None
        assert o.resolve("París") is not None

    def test_default_has_room_types(self):
        """La ontología por defecto tiene tipos de habitación."""
        o = get_default_ontology()
        assert o.resolve("cocina") is not None
        assert o.resolve("habitación") is not None

    def test_default_has_building_types(self):
        """La ontología por defecto tiene tipos de edificio."""
        o = get_default_ontology()
        assert o.resolve("casa") is not None
        assert o.resolve("castillo") is not None

    def test_gazetteer_completeness(self):
        """El gazetteer tiene al menos 50 entradas."""
        assert len(SPANISH_GAZETTEER) >= 50

    def test_room_building_exterior_sets(self):
        """Los conjuntos de tipos están poblados."""
        assert len(ROOM_TYPES) >= 10
        assert len(BUILDING_TYPES) >= 10
        assert len(EXTERIOR_TYPES) >= 10

    def test_cocina_casa_not_false_positive(self):
        """Regresión: cocina y casa NO deben ser incompatibles."""
        o = get_default_ontology()
        # Sin padre explícito, ambos son ROOM/BUILDING sin relación
        # → fail-safe (compatible)
        assert o.are_compatible("cocina", "casa") is True

    def test_cities_are_incompatible(self):
        """Madrid y Barcelona son incompatibles en la ontología default."""
        o = get_default_ontology()
        assert o.are_compatible("Madrid", "Barcelona") is False
