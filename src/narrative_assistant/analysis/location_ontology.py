"""
Ontología de ubicaciones para detección de inconsistencias espaciales.

Proporciona:
- Jerarquía de ubicaciones (habitación < edificio < ciudad < región < país)
- Resolución de alias (Ciudad Condal → Barcelona)
- Compatibilidad jerárquica (cocina ⊂ casa → compatibles)
- Distancias geográficas (haversine) y alcanzabilidad temporal
- Gazetteer español (~50 ciudades con coordenadas)
"""

import logging
import math
import unicodedata
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class LocationType(Enum):
    """Tipo jerárquico de ubicación."""

    ROOM = "room"  # habitación, cocina, despacho
    BUILDING = "building"  # casa, castillo, hospital
    DISTRICT = "district"  # barrio, urbanización
    CITY = "city"  # Madrid, Barcelona
    REGION = "region"  # Cataluña, Andalucía
    COUNTRY = "country"  # España, Francia
    FICTIONAL = "fictional"  # Mordor, Macondo
    UNKNOWN = "unknown"


# Orden jerárquico: un tipo menor puede estar contenido en uno mayor
_TYPE_HIERARCHY = {
    LocationType.ROOM: 0,
    LocationType.BUILDING: 1,
    LocationType.DISTRICT: 2,
    LocationType.CITY: 3,
    LocationType.REGION: 4,
    LocationType.COUNTRY: 5,
    LocationType.FICTIONAL: -1,
    LocationType.UNKNOWN: -1,
}


class HistoricalPeriod(Enum):
    """Periodo histórico para cálculo de velocidad de viaje."""

    MEDIEVAL = "medieval"  # ~40 km/día a caballo
    EARLY_MODERN = "early_modern"  # ~60 km/día (carruaje)
    INDUSTRIAL = "industrial"  # ~300 km/día (tren vapor)
    MODERN = "modern"  # ~1000 km/día (coche/avión)


TRAVEL_SPEED_KM_DAY: dict[HistoricalPeriod, float] = {
    HistoricalPeriod.MEDIEVAL: 40.0,
    HistoricalPeriod.EARLY_MODERN: 60.0,
    HistoricalPeriod.INDUSTRIAL: 300.0,
    HistoricalPeriod.MODERN: 1000.0,
}


@dataclass
class LocationNode:
    """Nodo en la ontología de ubicaciones."""

    name: str
    normalized_name: str
    location_type: LocationType
    parent_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    aliases: list[str] = field(default_factory=list)


class LocationOntology:
    """
    Ontología jerárquica de ubicaciones.

    Gestiona relaciones padre-hijo entre ubicaciones,
    resolución de alias y cálculos de distancia/alcanzabilidad.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, LocationNode] = {}  # normalized_name → node
        self._children: dict[str, set[str]] = {}  # parent_norm → {child_norm}
        self._alias_map: dict[str, str] = {}  # alias_norm → canonical_norm

    def add_location(self, node: LocationNode) -> None:
        """Añade una ubicación a la ontología."""
        norm = node.normalized_name
        self._nodes[norm] = node

        # Registrar hijos del padre
        if node.parent_name:
            parent_norm = self._normalize(node.parent_name)
            if parent_norm not in self._children:
                self._children[parent_norm] = set()
            self._children[parent_norm].add(norm)

        # Registrar aliases
        for alias in node.aliases:
            alias_norm = self._normalize(alias)
            self._alias_map[alias_norm] = norm

    def add_from_text(
        self,
        name: str,
        location_type: LocationType = LocationType.UNKNOWN,
        parent: str | None = None,
    ) -> LocationNode:
        """Crea y añade una ubicación desde texto plano."""
        node = LocationNode(
            name=name,
            normalized_name=self._normalize(name),
            location_type=location_type,
            parent_name=parent,
        )
        self.add_location(node)
        return node

    def resolve(self, name: str) -> LocationNode | None:
        """Resuelve un nombre (o alias) a su LocationNode."""
        norm = self._normalize(name)

        # Búsqueda directa
        if norm in self._nodes:
            return self._nodes[norm]

        # Búsqueda por alias
        canonical = self._alias_map.get(norm)
        if canonical and canonical in self._nodes:
            return self._nodes[canonical]

        return None

    def get_ancestors(self, name: str) -> list[str]:
        """Devuelve la cadena de ancestros [padre, abuelo, ...]."""
        node = self.resolve(name)
        if not node:
            return []

        ancestors = []
        current = node
        visited: set[str] = {current.normalized_name}

        while current.parent_name:
            parent_norm = self._normalize(current.parent_name)
            if parent_norm in visited:
                break  # Evitar ciclos
            visited.add(parent_norm)
            ancestors.append(current.parent_name)
            parent_node = self.resolve(current.parent_name)
            if not parent_node:
                break
            current = parent_node

        return ancestors

    def get_descendants(self, name: str) -> set[str]:
        """Devuelve todos los descendientes de una ubicación."""
        node = self.resolve(name)
        if not node:
            return set()

        result: set[str] = set()
        queue = [node.normalized_name]

        while queue:
            current = queue.pop()
            children = self._children.get(current, set())
            for child in children:
                if child not in result:
                    result.add(child)
                    queue.append(child)

        return result

    def are_compatible(self, loc1: str, loc2: str) -> bool:
        """
        Determina si dos ubicaciones son compatibles (un personaje podría
        estar en ambas simultáneamente).

        Reglas:
        - UNKNOWN → siempre compatible (fail-safe, evita falsos positivos)
        - Misma ubicación → compatible
        - Una es ancestro de la otra → compatible (cocina ⊂ casa)
        - Comparten ancestro → depende del nivel jerárquico
        - Ciudades diferentes sin relación → incompatible
        """
        norm1 = self._normalize(loc1)
        norm2 = self._normalize(loc2)

        # Misma ubicación
        if norm1 == norm2:
            return True

        # Resolver aliases
        norm1 = self._alias_map.get(norm1, norm1)
        norm2 = self._alias_map.get(norm2, norm2)

        if norm1 == norm2:
            return True

        node1 = self._nodes.get(norm1)
        node2 = self._nodes.get(norm2)

        # UNKNOWN o no encontrado → fail-safe
        if not node1 or not node2:
            return True
        if (
            node1.location_type == LocationType.UNKNOWN
            or node2.location_type == LocationType.UNKNOWN
        ):
            return True
        if (
            node1.location_type == LocationType.FICTIONAL
            or node2.location_type == LocationType.FICTIONAL
        ):
            return True

        # Una es ancestro de la otra → compatible
        ancestors1 = {self._normalize(a) for a in self.get_ancestors(loc1)}
        ancestors1.add(norm1)
        ancestors2 = {self._normalize(a) for a in self.get_ancestors(loc2)}
        ancestors2.add(norm2)

        if norm1 in ancestors2 or norm2 in ancestors1:
            return True

        # ROOM/BUILDING bajo el mismo padre → compatible (cocina y salón en la misma casa)
        if (
            node1.location_type in (LocationType.ROOM, LocationType.BUILDING)
            and node2.location_type in (LocationType.ROOM, LocationType.BUILDING)
            and node1.parent_name
            and node2.parent_name
            and self._normalize(node1.parent_name) == self._normalize(node2.parent_name)
        ):
            return True

        # Ciudades (o niveles >= CITY) diferentes sin relación jerárquica → incompatible
        level1 = _TYPE_HIERARCHY.get(node1.location_type, -1)
        level2 = _TYPE_HIERARCHY.get(node2.location_type, -1)
        city_level = _TYPE_HIERARCHY[LocationType.CITY]

        if level1 >= city_level and level2 >= city_level:
            # Ambas son city+ sin relación → incompatible
            return False

        # Comparten ancestro a nivel ciudad+ → compatible (barrios de la misma ciudad)
        common = ancestors1 & ancestors2
        if common:
            return True

        # Ubicaciones pequeñas sin padre conocido → fail-safe
        if (
            level1 <= _TYPE_HIERARCHY[LocationType.BUILDING]
            or level2 <= _TYPE_HIERARCHY[LocationType.BUILDING]
        ):
            return True

        return False

    def is_reachable(
        self,
        loc1: str,
        loc2: str,
        hours: float,
        period: HistoricalPeriod = HistoricalPeriod.MODERN,
    ) -> bool:
        """
        Determina si es posible viajar de loc1 a loc2 en el tiempo dado.

        Si no hay coordenadas disponibles, retorna True (fail-safe).
        """
        dist = self.distance_km(loc1, loc2)
        if dist is None:
            return True  # Sin datos → no generar falso positivo

        speed_km_day = TRAVEL_SPEED_KM_DAY[period]
        speed_km_hour = speed_km_day / 24.0
        max_distance = speed_km_hour * hours

        return dist <= max_distance

    def distance_km(self, loc1: str, loc2: str) -> float | None:
        """Calcula distancia en km entre dos ubicaciones (haversine)."""
        node1 = self.resolve(loc1)
        node2 = self.resolve(loc2)

        if not node1 or not node2:
            return None

        # Intentar con coordenadas propias
        lat1, lon1 = node1.latitude, node1.longitude
        lat2, lon2 = node2.latitude, node2.longitude

        # Si no tiene coordenadas, buscar en ancestros
        if lat1 is None or lon1 is None:
            lat1, lon1 = self._find_ancestor_coords(node1)
        if lat2 is None or lon2 is None:
            lat2, lon2 = self._find_ancestor_coords(node2)

        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            return None

        return self._haversine(lat1, lon1, lat2, lon2)

    def _find_ancestor_coords(
        self, node: LocationNode
    ) -> tuple[float | None, float | None]:
        """Busca coordenadas en ancestros."""
        current = node
        visited: set[str] = {current.normalized_name}

        while current.parent_name:
            parent = self.resolve(current.parent_name)
            if not parent:
                break
            if parent.normalized_name in visited:
                break
            visited.add(parent.normalized_name)
            if parent.latitude is not None and parent.longitude is not None:
                return parent.latitude, parent.longitude
            current = parent

        return None, None

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula distancia en km usando fórmula de Haversine."""
        R = 6371.0  # Radio de la Tierra en km

        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    @staticmethod
    def _normalize(name: str) -> str:
        """Normaliza nombre: minúsculas + quita acentos."""
        lower = name.lower().strip()
        # Descomponer caracteres Unicode y quitar diacríticos
        nfkd = unicodedata.normalize("NFKD", lower)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    def load_spanish_gazetteer(self) -> None:
        """Carga el gazetteer español predefinido."""
        for entry in SPANISH_GAZETTEER:
            node = LocationNode(
                name=entry["name"],
                normalized_name=self._normalize(entry["name"]),
                location_type=LocationType(entry["type"]),
                parent_name=entry.get("parent"),
                latitude=entry.get("lat"),
                longitude=entry.get("lon"),
                aliases=entry.get("aliases", []),
            )
            self.add_location(node)

        # Cargar tipos de habitación como ROOM
        for room in ROOM_TYPES:
            if self._normalize(room) not in self._nodes:
                self.add_from_text(room, LocationType.ROOM)

        # Cargar tipos de edificio como BUILDING
        for building in BUILDING_TYPES:
            if self._normalize(building) not in self._nodes:
                self.add_from_text(building, LocationType.BUILDING)

        # Cargar tipos de exterior como DISTRICT (nivel intermedio)
        for ext in EXTERIOR_TYPES:
            if self._normalize(ext) not in self._nodes:
                self.add_from_text(ext, LocationType.DISTRICT)


# ~50 ciudades españolas + principales europeas/latinoamericanas
SPANISH_GAZETTEER: list[dict] = [
    # España - Comunidades Autónomas (como regiones)
    {
        "name": "Cataluña",
        "type": "region",
        "parent": "España",
        "lat": 41.59,
        "lon": 1.52,
    },
    {
        "name": "Andalucía",
        "type": "region",
        "parent": "España",
        "lat": 37.54,
        "lon": -4.73,
    },
    {
        "name": "Comunidad de Madrid",
        "type": "region",
        "parent": "España",
        "lat": 40.42,
        "lon": -3.70,
    },
    {
        "name": "País Vasco",
        "type": "region",
        "parent": "España",
        "lat": 42.99,
        "lon": -2.62,
    },
    {
        "name": "Castilla y León",
        "type": "region",
        "parent": "España",
        "lat": 41.65,
        "lon": -4.73,
    },
    {
        "name": "Castilla-La Mancha",
        "type": "region",
        "parent": "España",
        "lat": 39.28,
        "lon": -3.10,
    },
    {
        "name": "Galicia",
        "type": "region",
        "parent": "España",
        "lat": 42.57,
        "lon": -8.13,
    },
    {
        "name": "Aragón",
        "type": "region",
        "parent": "España",
        "lat": 41.60,
        "lon": -0.88,
    },
    {
        "name": "Comunidad Valenciana",
        "type": "region",
        "parent": "España",
        "lat": 39.48,
        "lon": -0.35,
    },
    # España - Ciudades principales
    {
        "name": "Madrid",
        "type": "city",
        "parent": "Comunidad de Madrid",
        "lat": 40.4168,
        "lon": -3.7038,
        "aliases": ["Villa y Corte", "capital de España"],
    },
    {
        "name": "Barcelona",
        "type": "city",
        "parent": "Cataluña",
        "lat": 41.3851,
        "lon": 2.1734,
        "aliases": ["Ciudad Condal", "Barna"],
    },
    {
        "name": "Sevilla",
        "type": "city",
        "parent": "Andalucía",
        "lat": 37.3891,
        "lon": -5.9845,
        "aliases": ["Hispalis"],
    },
    {
        "name": "Valencia",
        "type": "city",
        "parent": "Comunidad Valenciana",
        "lat": 39.4699,
        "lon": -0.3763,
    },
    {
        "name": "Bilbao",
        "type": "city",
        "parent": "País Vasco",
        "lat": 43.2630,
        "lon": -2.9350,
    },
    {
        "name": "Zaragoza",
        "type": "city",
        "parent": "Aragón",
        "lat": 41.6488,
        "lon": -0.8891,
        "aliases": ["Caesaraugusta"],
    },
    {
        "name": "Málaga",
        "type": "city",
        "parent": "Andalucía",
        "lat": 36.7213,
        "lon": -4.4214,
    },
    {
        "name": "Murcia",
        "type": "city",
        "parent": "España",
        "lat": 37.9922,
        "lon": -1.1307,
    },
    {
        "name": "Palma",
        "type": "city",
        "parent": "España",
        "lat": 39.5696,
        "lon": 2.6502,
        "aliases": ["Palma de Mallorca"],
    },
    {
        "name": "Las Palmas",
        "type": "city",
        "parent": "España",
        "lat": 28.1235,
        "lon": -15.4363,
        "aliases": ["Las Palmas de Gran Canaria"],
    },
    {
        "name": "Alicante",
        "type": "city",
        "parent": "Comunidad Valenciana",
        "lat": 38.3452,
        "lon": -0.4810,
    },
    {
        "name": "Córdoba",
        "type": "city",
        "parent": "Andalucía",
        "lat": 37.8882,
        "lon": -4.7794,
        "aliases": ["Corduba"],
    },
    {
        "name": "Valladolid",
        "type": "city",
        "parent": "Castilla y León",
        "lat": 41.6523,
        "lon": -4.7245,
    },
    {
        "name": "Vigo",
        "type": "city",
        "parent": "Galicia",
        "lat": 42.2406,
        "lon": -8.7207,
    },
    {
        "name": "Gijón",
        "type": "city",
        "parent": "España",
        "lat": 43.5453,
        "lon": -5.6616,
    },
    {
        "name": "Granada",
        "type": "city",
        "parent": "Andalucía",
        "lat": 37.1773,
        "lon": -3.5986,
    },
    {
        "name": "Toledo",
        "type": "city",
        "parent": "Castilla-La Mancha",
        "lat": 39.8628,
        "lon": -4.0273,
        "aliases": ["Ciudad Imperial"],
    },
    {
        "name": "Salamanca",
        "type": "city",
        "parent": "Castilla y León",
        "lat": 40.9701,
        "lon": -5.6635,
    },
    {
        "name": "Burgos",
        "type": "city",
        "parent": "Castilla y León",
        "lat": 42.3440,
        "lon": -3.6969,
    },
    {
        "name": "Cádiz",
        "type": "city",
        "parent": "Andalucía",
        "lat": 36.5271,
        "lon": -6.2886,
        "aliases": ["Gadir", "Gades"],
    },
    {
        "name": "Santander",
        "type": "city",
        "parent": "España",
        "lat": 43.4623,
        "lon": -3.8100,
    },
    {
        "name": "San Sebastián",
        "type": "city",
        "parent": "País Vasco",
        "lat": 43.3183,
        "lon": -1.9812,
        "aliases": ["Donostia"],
    },
    {
        "name": "Santiago de Compostela",
        "type": "city",
        "parent": "Galicia",
        "lat": 42.8782,
        "lon": -8.5448,
    },
    {
        "name": "Pamplona",
        "type": "city",
        "parent": "España",
        "lat": 42.8125,
        "lon": -1.6458,
        "aliases": ["Iruña"],
    },
    {
        "name": "Segovia",
        "type": "city",
        "parent": "Castilla y León",
        "lat": 40.9429,
        "lon": -4.1088,
    },
    {
        "name": "Ávila",
        "type": "city",
        "parent": "Castilla y León",
        "lat": 40.6565,
        "lon": -4.6812,
    },
    # Países
    {"name": "España", "type": "country", "lat": 40.46, "lon": -3.75},
    {"name": "Francia", "type": "country", "lat": 46.23, "lon": 2.21},
    {"name": "Portugal", "type": "country", "lat": 39.40, "lon": -8.22},
    {"name": "Italia", "type": "country", "lat": 41.87, "lon": 12.57},
    {"name": "Alemania", "type": "country", "lat": 51.17, "lon": 10.45},
    {"name": "Reino Unido", "type": "country", "lat": 55.38, "lon": -3.44},
    {"name": "México", "type": "country", "lat": 23.63, "lon": -102.55},
    {"name": "Argentina", "type": "country", "lat": -38.42, "lon": -63.62},
    {"name": "Colombia", "type": "country", "lat": 4.57, "lon": -74.30},
    # Ciudades europeas/latam importantes en literatura española
    {
        "name": "París",
        "type": "city",
        "parent": "Francia",
        "lat": 48.8566,
        "lon": 2.3522,
        "aliases": ["Paris"],
    },
    {
        "name": "Londres",
        "type": "city",
        "parent": "Reino Unido",
        "lat": 51.5074,
        "lon": -0.1278,
        "aliases": ["London"],
    },
    {
        "name": "Roma",
        "type": "city",
        "parent": "Italia",
        "lat": 41.9028,
        "lon": 12.4964,
    },
    {
        "name": "Berlín",
        "type": "city",
        "parent": "Alemania",
        "lat": 52.5200,
        "lon": 13.4050,
        "aliases": ["Berlin"],
    },
    {
        "name": "Lisboa",
        "type": "city",
        "parent": "Portugal",
        "lat": 38.7223,
        "lon": -9.1393,
    },
    {
        "name": "Buenos Aires",
        "type": "city",
        "parent": "Argentina",
        "lat": -34.6037,
        "lon": -58.3816,
    },
    {
        "name": "Ciudad de México",
        "type": "city",
        "parent": "México",
        "lat": 19.4326,
        "lon": -99.1332,
        "aliases": ["México D.F.", "CDMX"],
    },
    {
        "name": "Bogotá",
        "type": "city",
        "parent": "Colombia",
        "lat": 4.7110,
        "lon": -74.0721,
    },
]


ROOM_TYPES: set[str] = {
    "habitación",
    "cocina",
    "dormitorio",
    "sala",
    "salón",
    "despacho",
    "baño",
    "cuarto",
    "estudio",
    "biblioteca",
    "sótano",
    "desván",
    "ático",
    "bodega",
    "comedor",
    "recibidor",
    "alcoba",
    "aposento",
}

BUILDING_TYPES: set[str] = {
    "casa",
    "castillo",
    "palacio",
    "hospital",
    "iglesia",
    "catedral",
    "convento",
    "monasterio",
    "posada",
    "taberna",
    "mesón",
    "edificio",
    "torre",
    "fortaleza",
    "mansión",
    "hacienda",
    "finca",
    "cortijo",
    "ayuntamiento",
    "escuela",
    "universidad",
    "teatro",
    "hotel",
    "tienda",
    "mercado",
}

EXTERIOR_TYPES: set[str] = {
    "jardín",
    "plaza",
    "calle",
    "campo",
    "bosque",
    "playa",
    "montaña",
    "río",
    "puerto",
    "parque",
    "cementerio",
    "camino",
    "pradera",
    "huerto",
    "patio",
}


def get_default_ontology() -> LocationOntology:
    """Crea una ontología con el gazetteer español cargado."""
    ontology = LocationOntology()
    ontology.load_spanish_gazetteer()
    return ontology
