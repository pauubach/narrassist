"""
Modelos de datos para el sistema de licencias.

Define las estructuras para:
- Licencias y suscripciones
- Dispositivos vinculados
- Registro de uso (cuota en paginas)
- Tiers y features de funcionalidad
"""

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

# =============================================================================
# Constantes
# =============================================================================

# Estandar editorial: 1 pagina = 250 palabras
WORDS_PER_PAGE = 250

# Periodo de gracia offline en dias
OFFLINE_GRACE_PERIOD_DAYS = 14

# Cooldown al desactivar dispositivo en horas (7 dias)
DEVICE_DEACTIVATION_COOLDOWN_HOURS = 168

# Swaps de dispositivo permitidos por mes (sin cooldown)
DEVICE_SWAPS_PER_MONTH = 2

# Limite de palabras por manuscrito para tier Corrector
MAX_WORDS_PER_MANUSCRIPT_CORRECTOR = 60_000

# Editorial: puestos base y precio extra
EDITORIAL_BASE_SEATS = 3
EDITORIAL_EXTRA_SEAT_PRICE_EUR = 49

# Founding member program — descuentos fijos en €/mes
FOUNDING_DISCOUNT_EUR: dict[str, float] = {
    "corrector": 5.0,    # €24 - €5 = €19
    "profesional": 15.0,  # €49 - €15 = €34
    "editorial": 40.0,    # €159 - €40 = €119
}
FOUNDING_SPOTS: dict[str, int] = {
    "corrector": 10,
    "profesional": 15,
    "editorial": 5,
}
# Grace period en dias para recuperar descuento founding tras downgrade
FOUNDING_DOWNGRADE_GRACE_DAYS = 90


# =============================================================================
# Funciones auxiliares
# =============================================================================


def words_to_pages(word_count: int) -> int:
    """Convierte conteo de palabras a paginas (redondeo arriba).

    Args:
        word_count: Numero de palabras del documento.

    Returns:
        Numero de paginas (250 palabras = 1 pagina), minimo 0.
    """
    if word_count <= 0:
        return 0
    return math.ceil(word_count / WORDS_PER_PAGE)


# =============================================================================
# Enums
# =============================================================================


class LicenseTier(Enum):
    """Niveles de suscripcion disponibles."""

    CORRECTOR = "corrector"
    PROFESIONAL = "profesional"
    EDITORIAL = "editorial"

    @property
    def display_name(self) -> str:
        """Nombre para mostrar al usuario."""
        names = {
            LicenseTier.CORRECTOR: "Corrector",
            LicenseTier.PROFESIONAL: "Profesional",
            LicenseTier.EDITORIAL: "Editorial",
        }
        return names[self]

    @property
    def rank(self) -> int:
        """Orden numerico para comparar tiers (mayor = tier superior)."""
        return {
            LicenseTier.CORRECTOR: 0,
            LicenseTier.PROFESIONAL: 1,
            LicenseTier.EDITORIAL: 2,
        }[self]


class LicenseFeature(Enum):
    """Funcionalidades disponibles por tier."""

    ATTRIBUTE_CONSISTENCY = "attribute_consistency"
    GRAMMAR_SPELLING = "grammar_spelling"
    NER_COREFERENCE = "ner_coreference"
    NAME_VARIANTS = "name_variants"
    CHARACTER_PROFILING = "character_profiling"
    NETWORK_ANALYSIS = "network_analysis"
    ANACHRONISM_DETECTION = "anachronism_detection"
    OOC_DETECTION = "ooc_detection"
    CLASSICAL_SPANISH = "classical_spanish"
    MULTI_MODEL = "multi_model"
    FULL_REPORTS = "full_reports"
    EXPORT_IMPORT = "export_import"

    @property
    def display_name(self) -> str:
        """Nombre para mostrar al usuario."""
        names = {
            LicenseFeature.ATTRIBUTE_CONSISTENCY: "Consistencia de atributos",
            LicenseFeature.GRAMMAR_SPELLING: "Gramatica y ortografia",
            LicenseFeature.NER_COREFERENCE: "NER + correferencias",
            LicenseFeature.NAME_VARIANTS: "Deteccion de variantes de nombre",
            LicenseFeature.CHARACTER_PROFILING: "Character profiling",
            LicenseFeature.NETWORK_ANALYSIS: "Analisis de red de personajes",
            LicenseFeature.ANACHRONISM_DETECTION: "Deteccion de anacronismos",
            LicenseFeature.OOC_DETECTION: "Deteccion out-of-character",
            LicenseFeature.CLASSICAL_SPANISH: "Espanol clasico (Siglo de Oro)",
            LicenseFeature.MULTI_MODEL: "Analisis multi-modelo",
            LicenseFeature.FULL_REPORTS: "Informes completos",
            LicenseFeature.EXPORT_IMPORT: "Export/Import trabajo editorial",
        }
        return names[self]


# Features basicas (Corrector)
_BASIC_FEATURES: frozenset[LicenseFeature] = frozenset(
    {
        LicenseFeature.ATTRIBUTE_CONSISTENCY,
        LicenseFeature.GRAMMAR_SPELLING,
        LicenseFeature.NER_COREFERENCE,
        LicenseFeature.NAME_VARIANTS,
    }
)

# Features Profesional (todas excepto export/import)
_PROFESIONAL_FEATURES: frozenset[LicenseFeature] = frozenset(
    f for f in LicenseFeature if f != LicenseFeature.EXPORT_IMPORT
)

# Todas las features (Editorial)
_ALL_FEATURES: frozenset[LicenseFeature] = frozenset(LicenseFeature)

# Mapping tier -> features disponibles
TIER_FEATURES: dict[LicenseTier, frozenset[LicenseFeature]] = {
    LicenseTier.CORRECTOR: _BASIC_FEATURES,
    LicenseTier.PROFESIONAL: _PROFESIONAL_FEATURES,
    LicenseTier.EDITORIAL: _ALL_FEATURES,
}


class CompLicenseType(Enum):
    """Tipos de licencias comp/regalo."""

    BETA = "beta"          # Beta testers (6-12 meses, 100%)
    PRESS = "press"        # Prensa/influencers (12 meses, 100%)
    FRIEND = "friend"      # Friends & family (indefinido, 50-100%)
    CONTEST = "contest"    # Ganadores de concursos (6-12 meses, 100%)
    PARTNER = "partner"    # Editoriales, universidades (negociado, 30-50%)
    GOODWILL = "goodwill"  # Compensacion por bugs/caidas (1-6 meses, 100%)


class LicenseStatus(Enum):
    """Estado de la licencia."""

    ACTIVE = "active"  # Licencia activa y verificada
    GRACE_PERIOD = "grace_period"  # Sin conexion, en periodo de gracia
    EXPIRED = "expired"  # Periodo de gracia agotado
    SUSPENDED = "suspended"  # Suspendida por el backend
    CANCELLED = "cancelled"  # Cancelada por el usuario


class DeviceStatus(Enum):
    """Estado de un dispositivo."""

    ACTIVE = "active"  # Dispositivo activo
    INACTIVE = "inactive"  # Dispositivo desactivado (cooldown)
    PENDING = "pending"  # Esperando confirmacion


# =============================================================================
# Limites por Tier
# =============================================================================


@dataclass(frozen=True)
class TierLimits:
    """Limites asociados a un tier de licencia."""

    max_pages_per_month: int  # -1 = ilimitado
    max_devices: int
    max_words_per_manuscript: int = -1  # -1 = ilimitado
    pages_rollover_months: int = 1  # Meses de rollover (0 = sin rollover)

    @classmethod
    def for_tier(cls, tier: LicenseTier) -> "TierLimits":
        """Obtiene los limites para un tier especifico."""
        limits = {
            LicenseTier.CORRECTOR: cls(
                max_pages_per_month=1500,
                max_devices=1,
                max_words_per_manuscript=MAX_WORDS_PER_MANUSCRIPT_CORRECTOR,
                pages_rollover_months=1,
            ),
            LicenseTier.PROFESIONAL: cls(
                max_pages_per_month=3000,
                max_devices=1,
                pages_rollover_months=1,
            ),
            LicenseTier.EDITORIAL: cls(
                max_pages_per_month=-1,  # Ilimitado
                max_devices=EDITORIAL_BASE_SEATS,
                pages_rollover_months=0,  # No aplica
            ),
        }
        return limits[tier]

    @property
    def is_unlimited(self) -> bool:
        """Verifica si la cuota es ilimitada."""
        return self.max_pages_per_month == -1


# =============================================================================
# Modelos de Datos
# =============================================================================


@dataclass
class Device:
    """
    Dispositivo vinculado a una licencia.

    Attributes:
        id: Identificador unico en BD local
        license_id: ID de la licencia asociada
        hardware_fingerprint: Hash unico del hardware
        device_name: Nombre amigable del dispositivo
        os_info: Informacion del sistema operativo
        status: Estado del dispositivo
        activated_at: Fecha de activacion
        deactivated_at: Fecha de desactivacion (si aplica)
        cooldown_ends_at: Fin del periodo de cooldown
        last_seen_at: Ultima vez que el dispositivo verifico la licencia
        is_current_device: True si es el dispositivo actual
    """

    id: int | None = None
    license_id: int = 0
    hardware_fingerprint: str = ""
    device_name: str = ""
    os_info: str = ""
    status: DeviceStatus = DeviceStatus.PENDING
    activated_at: datetime | None = None
    deactivated_at: datetime | None = None
    cooldown_ends_at: datetime | None = None
    last_seen_at: datetime | None = None
    is_current_device: bool = False

    @property
    def is_in_cooldown(self) -> bool:
        """Verifica si el dispositivo esta en periodo de cooldown."""
        if self.cooldown_ends_at is None:
            return False
        return datetime.utcnow() < self.cooldown_ends_at

    @property
    def cooldown_remaining(self) -> timedelta | None:
        """Tiempo restante de cooldown."""
        if not self.is_in_cooldown or self.cooldown_ends_at is None:
            return None
        return self.cooldown_ends_at - datetime.utcnow()

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            "id": self.id,
            "license_id": self.license_id,
            "hardware_fingerprint": self.hardware_fingerprint,
            "device_name": self.device_name,
            "os_info": self.os_info,
            "status": self.status.value,
            "activated_at": (
                self.activated_at.isoformat() if self.activated_at else None
            ),
            "deactivated_at": (
                self.deactivated_at.isoformat() if self.deactivated_at else None
            ),
            "cooldown_ends_at": (
                self.cooldown_ends_at.isoformat() if self.cooldown_ends_at else None
            ),
            "last_seen_at": (
                self.last_seen_at.isoformat() if self.last_seen_at else None
            ),
            "is_current_device": self.is_current_device,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Device":
        """Deserializa desde diccionario."""
        return cls(
            id=data.get("id"),
            license_id=data.get("license_id", 0),
            hardware_fingerprint=data.get("hardware_fingerprint", ""),
            device_name=data.get("device_name", ""),
            os_info=data.get("os_info", ""),
            status=DeviceStatus(data.get("status", "pending")),
            activated_at=(
                datetime.fromisoformat(data["activated_at"])
                if data.get("activated_at")
                else None
            ),
            deactivated_at=(
                datetime.fromisoformat(data["deactivated_at"])
                if data.get("deactivated_at")
                else None
            ),
            cooldown_ends_at=(
                datetime.fromisoformat(data["cooldown_ends_at"])
                if data.get("cooldown_ends_at")
                else None
            ),
            last_seen_at=(
                datetime.fromisoformat(data["last_seen_at"])
                if data.get("last_seen_at")
                else None
            ),
            is_current_device=data.get("is_current_device", False),
        )

    @classmethod
    def from_db_row(cls, row) -> "Device":
        """Crea Device desde una fila de SQLite."""
        return cls(
            id=row["id"],
            license_id=row["license_id"],
            hardware_fingerprint=row["hardware_fingerprint"],
            device_name=row["device_name"],
            os_info=row["os_info"],
            status=DeviceStatus(row["status"]),
            activated_at=(
                datetime.fromisoformat(row["activated_at"])
                if row["activated_at"]
                else None
            ),
            deactivated_at=(
                datetime.fromisoformat(row["deactivated_at"])
                if row["deactivated_at"]
                else None
            ),
            cooldown_ends_at=(
                datetime.fromisoformat(row["cooldown_ends_at"])
                if row["cooldown_ends_at"]
                else None
            ),
            last_seen_at=(
                datetime.fromisoformat(row["last_seen_at"])
                if row["last_seen_at"]
                else None
            ),
            is_current_device=bool(row["is_current_device"]),
        )


@dataclass
class Subscription:
    """
    Suscripcion asociada a una licencia (datos del proveedor de pagos).

    Attributes:
        id: Identificador unico en BD local
        license_id: ID de la licencia asociada
        stripe_subscription_id: ID de la suscripcion en el proveedor
        stripe_customer_id: ID del cliente en el proveedor
        tier: Nivel de suscripcion
        status: Estado de la suscripcion
        current_period_start: Inicio del periodo actual
        current_period_end: Fin del periodo actual
        cancel_at_period_end: Si se cancela al final del periodo
        created_at: Fecha de creacion
        updated_at: Ultima actualizacion
    """

    id: int | None = None
    license_id: int = 0
    stripe_subscription_id: str = ""
    stripe_customer_id: str = ""
    tier: LicenseTier = LicenseTier.CORRECTOR
    status: str = (
        "active"  # Payment provider status: active, past_due, canceled, trialing
    )
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        """Verifica si la suscripcion esta activa."""
        return self.status in ("active", "trialing")

    @property
    def days_until_renewal(self) -> int | None:
        """Dias hasta la proxima renovacion."""
        if self.current_period_end is None:
            return None
        delta = self.current_period_end - datetime.utcnow()
        return max(0, delta.days)

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            "id": self.id,
            "license_id": self.license_id,
            "stripe_subscription_id": self.stripe_subscription_id,
            "stripe_customer_id": self.stripe_customer_id,
            "tier": self.tier.value,
            "status": self.status,
            "current_period_start": (
                self.current_period_start.isoformat()
                if self.current_period_start
                else None
            ),
            "current_period_end": (
                self.current_period_end.isoformat() if self.current_period_end else None
            ),
            "cancel_at_period_end": self.cancel_at_period_end,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Subscription":
        """Deserializa desde diccionario."""
        return cls(
            id=data.get("id"),
            license_id=data.get("license_id", 0),
            stripe_subscription_id=data.get("stripe_subscription_id", ""),
            stripe_customer_id=data.get("stripe_customer_id", ""),
            tier=LicenseTier(data.get("tier", "corrector")),
            status=data.get("status", "active"),
            current_period_start=(
                datetime.fromisoformat(data["current_period_start"])
                if data.get("current_period_start")
                else None
            ),
            current_period_end=(
                datetime.fromisoformat(data["current_period_end"])
                if data.get("current_period_end")
                else None
            ),
            cancel_at_period_end=data.get("cancel_at_period_end", False),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else None
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if data.get("updated_at")
                else None
            ),
        )

    @classmethod
    def from_db_row(cls, row) -> "Subscription":
        """Crea Subscription desde una fila de SQLite."""
        return cls(
            id=row["id"],
            license_id=row["license_id"],
            stripe_subscription_id=row["stripe_subscription_id"],
            stripe_customer_id=row["stripe_customer_id"],
            tier=LicenseTier(row["tier"]),
            status=row["status"],
            current_period_start=(
                datetime.fromisoformat(row["current_period_start"])
                if row["current_period_start"]
                else None
            ),
            current_period_end=(
                datetime.fromisoformat(row["current_period_end"])
                if row["current_period_end"]
                else None
            ),
            cancel_at_period_end=bool(row["cancel_at_period_end"]),
            created_at=(
                datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
            ),
            updated_at=(
                datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
            ),
        )


@dataclass
class UsageRecord:
    """
    Registro de uso de manuscritos (cuota en paginas).

    Attributes:
        id: Identificador unico en BD local
        license_id: ID de la licencia asociada
        project_id: ID del proyecto analizado
        document_fingerprint: Fingerprint del documento
        document_name: Nombre del documento
        word_count: Conteo de palabras
        page_count: Conteo de paginas (ceil(word_count / 250))
        analysis_started_at: Inicio del analisis
        analysis_completed_at: Fin del analisis (si aplica)
        billing_period: Periodo de facturacion (YYYY-MM)
        counted_for_quota: Si cuenta para la cuota mensual
    """

    id: int | None = None
    license_id: int = 0
    project_id: int | None = None
    document_fingerprint: str = ""
    document_name: str = ""
    word_count: int = 0
    page_count: int = 0
    analysis_started_at: datetime | None = None
    analysis_completed_at: datetime | None = None
    billing_period: str = ""  # YYYY-MM
    counted_for_quota: bool = True

    def __post_init__(self):
        """Calcula page_count si no se proporciono."""
        if self.page_count == 0 and self.word_count > 0:
            self.page_count = words_to_pages(self.word_count)

    @classmethod
    def current_billing_period(cls) -> str:
        """Retorna el periodo de facturacion actual."""
        now = datetime.utcnow()
        return f"{now.year}-{now.month:02d}"

    @classmethod
    def previous_billing_period(cls) -> str:
        """Retorna el periodo de facturacion anterior."""
        now = datetime.utcnow()
        if now.month == 1:
            return f"{now.year - 1}-12"
        return f"{now.year}-{now.month - 1:02d}"

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            "id": self.id,
            "license_id": self.license_id,
            "project_id": self.project_id,
            "document_fingerprint": self.document_fingerprint,
            "document_name": self.document_name,
            "word_count": self.word_count,
            "page_count": self.page_count,
            "analysis_started_at": (
                self.analysis_started_at.isoformat()
                if self.analysis_started_at
                else None
            ),
            "analysis_completed_at": (
                self.analysis_completed_at.isoformat()
                if self.analysis_completed_at
                else None
            ),
            "billing_period": self.billing_period,
            "counted_for_quota": self.counted_for_quota,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UsageRecord":
        """Deserializa desde diccionario."""
        return cls(
            id=data.get("id"),
            license_id=data.get("license_id", 0),
            project_id=data.get("project_id"),
            document_fingerprint=data.get("document_fingerprint", ""),
            document_name=data.get("document_name", ""),
            word_count=data.get("word_count", 0),
            page_count=data.get("page_count", 0),
            analysis_started_at=(
                datetime.fromisoformat(data["analysis_started_at"])
                if data.get("analysis_started_at")
                else None
            ),
            analysis_completed_at=(
                datetime.fromisoformat(data["analysis_completed_at"])
                if data.get("analysis_completed_at")
                else None
            ),
            billing_period=data.get("billing_period", ""),
            counted_for_quota=data.get("counted_for_quota", True),
        )

    @classmethod
    def from_db_row(cls, row) -> "UsageRecord":
        """Crea UsageRecord desde una fila de SQLite."""
        return cls(
            id=row["id"],
            license_id=row["license_id"],
            project_id=row["project_id"],
            document_fingerprint=row["document_fingerprint"],
            document_name=row["document_name"],
            word_count=row["word_count"],
            page_count=row.get("page_count", 0),
            analysis_started_at=(
                datetime.fromisoformat(row["analysis_started_at"])
                if row["analysis_started_at"]
                else None
            ),
            analysis_completed_at=(
                datetime.fromisoformat(row["analysis_completed_at"])
                if row["analysis_completed_at"]
                else None
            ),
            billing_period=row["billing_period"],
            counted_for_quota=bool(row["counted_for_quota"]),
        )


@dataclass
class License:
    """
    Licencia de usuario.

    Attributes:
        id: Identificador unico en BD local
        license_key: Clave de licencia unica
        user_email: Email del usuario
        user_name: Nombre del usuario
        tier: Nivel de suscripcion
        status: Estado actual de la licencia
        created_at: Fecha de creacion
        activated_at: Fecha de primera activacion
        expires_at: Fecha de expiracion
        last_verified_at: Ultima verificacion online
        grace_period_ends_at: Fin del periodo de gracia offline
        is_founding_member: True si es founding member
        founding_tier: Tier original al unirse como founder
        founding_discount_eur: Descuento fijo en EUR/mes (€5, €15, €40)
        downgrade_grace_until: Si no es None, puede recuperar descuento founding hasta esta fecha
        is_comp: True si es licencia regalo/comp
        comp_type: Tipo de comp (beta, press, friend, contest, partner, goodwill)
        comp_discount_pct: Porcentaje de descuento comp (0-100)
        comp_expires_at: Fecha de expiracion de la comp
        comp_notes: Notas internas del admin
        subscription: Datos de suscripcion
        devices: Lista de dispositivos vinculados
        extra_data: Datos adicionales (JSON)
    """

    id: int | None = None
    license_key: str = ""
    user_email: str = ""
    user_name: str = ""
    tier: LicenseTier = LicenseTier.CORRECTOR
    status: LicenseStatus = LicenseStatus.ACTIVE
    created_at: datetime | None = None
    activated_at: datetime | None = None
    expires_at: datetime | None = None
    last_verified_at: datetime | None = None
    grace_period_ends_at: datetime | None = None
    # Founding member
    is_founding_member: bool = False
    founding_tier: LicenseTier | None = None
    founding_discount_eur: float = 0.0
    downgrade_grace_until: datetime | None = None
    # Comp/regalo
    is_comp: bool = False
    comp_type: CompLicenseType | None = None
    comp_discount_pct: float = 0.0
    comp_expires_at: datetime | None = None
    comp_notes: str = ""
    # Relaciones
    subscription: Subscription | None = None
    devices: list[Device] = field(default_factory=list)
    extra_data: dict = field(default_factory=dict)

    @property
    def features(self) -> frozenset[LicenseFeature]:
        """Features disponibles segun el tier."""
        return TIER_FEATURES.get(self.tier, _BASIC_FEATURES)

    @property
    def limits(self) -> TierLimits:
        """Limites segun el tier."""
        return TierLimits.for_tier(self.tier)

    @property
    def is_valid(self) -> bool:
        """Verifica si la licencia es valida para uso."""
        return self.status in (LicenseStatus.ACTIVE, LicenseStatus.GRACE_PERIOD)

    @property
    def is_in_grace_period(self) -> bool:
        """Verifica si esta en periodo de gracia offline."""
        return self.status == LicenseStatus.GRACE_PERIOD

    @property
    def grace_period_remaining(self) -> timedelta | None:
        """Tiempo restante de periodo de gracia."""
        if self.grace_period_ends_at is None:
            return None
        remaining = self.grace_period_ends_at - datetime.utcnow()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    @property
    def active_devices(self) -> list[Device]:
        """Dispositivos activos."""
        return [d for d in self.devices if d.status == DeviceStatus.ACTIVE]

    @property
    def active_device_count(self) -> int:
        """Numero de dispositivos activos."""
        return len(self.active_devices)

    @property
    def founding_discount_active(self) -> bool:
        """True si el descuento founding esta activo (no suspendido por downgrade)."""
        if not self.is_founding_member or self.founding_discount_eur <= 0:
            return False
        if self.founding_tier is None:
            return False
        # Descuento activo si tier actual >= tier original del founding
        if self.tier.rank < self.founding_tier.rank:
            return False
        # Suspendido si estamos en grace period de downgrade
        if self.downgrade_grace_until is not None:
            return False
        return True

    @property
    def comp_active(self) -> bool:
        """True si la licencia comp esta activa (no expirada)."""
        if not self.is_comp:
            return False
        if self.comp_expires_at is None:
            return True  # Sin expiracion = indefinida
        return datetime.utcnow() < self.comp_expires_at

    def calculate_effective_discount(self, base_price: float) -> float:
        """Calcula el descuento efectivo total en EUR/mes.

        Args:
            base_price: Precio base del tier actual en EUR/mes.

        Returns:
            Descuento total en EUR (nunca mayor que base_price).
        """
        discount = 0.0
        # Founding discount (fijo en EUR)
        if self.founding_discount_active:
            discount += self.founding_discount_eur
        # Comp discount (porcentaje sobre precio base)
        if self.comp_active and self.comp_discount_pct > 0:
            discount += base_price * (self.comp_discount_pct / 100.0)
        return min(discount, base_price)  # Floor: no puede ser > precio base

    def has_feature(self, feature: LicenseFeature) -> bool:
        """Verifica si una feature esta disponible en el tier actual."""
        return feature in self.features

    def can_add_device(self) -> bool:
        """Verifica si se puede agregar otro dispositivo."""
        return self.active_device_count < self.limits.max_devices

    def start_grace_period(self) -> None:
        """Inicia el periodo de gracia offline."""
        if self.status == LicenseStatus.ACTIVE:
            self.status = LicenseStatus.GRACE_PERIOD
            self.grace_period_ends_at = datetime.utcnow() + timedelta(
                days=OFFLINE_GRACE_PERIOD_DAYS
            )

    def end_grace_period(self) -> None:
        """Finaliza el periodo de gracia (verificacion exitosa)."""
        if self.status == LicenseStatus.GRACE_PERIOD:
            self.status = LicenseStatus.ACTIVE
            self.grace_period_ends_at = None
            self.last_verified_at = datetime.utcnow()

    def expire_grace_period(self) -> None:
        """Expira el periodo de gracia."""
        if self.status == LicenseStatus.GRACE_PERIOD:
            self.status = LicenseStatus.EXPIRED

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            "id": self.id,
            "license_key": self.license_key,
            "user_email": self.user_email,
            "user_name": self.user_name,
            "tier": self.tier.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "activated_at": (
                self.activated_at.isoformat() if self.activated_at else None
            ),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_verified_at": (
                self.last_verified_at.isoformat() if self.last_verified_at else None
            ),
            "grace_period_ends_at": (
                self.grace_period_ends_at.isoformat()
                if self.grace_period_ends_at
                else None
            ),
            "is_founding_member": self.is_founding_member,
            "founding_tier": self.founding_tier.value if self.founding_tier else None,
            "founding_discount_eur": self.founding_discount_eur,
            "downgrade_grace_until": (
                self.downgrade_grace_until.isoformat()
                if self.downgrade_grace_until
                else None
            ),
            "is_comp": self.is_comp,
            "comp_type": self.comp_type.value if self.comp_type else None,
            "comp_discount_pct": self.comp_discount_pct,
            "comp_expires_at": (
                self.comp_expires_at.isoformat() if self.comp_expires_at else None
            ),
            "comp_notes": self.comp_notes,
            "subscription": self.subscription.to_dict() if self.subscription else None,
            "devices": [d.to_dict() for d in self.devices],
            "extra_data": self.extra_data,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "License":
        """Deserializa desde diccionario."""
        license_obj = cls(
            id=data.get("id"),
            license_key=data.get("license_key", ""),
            user_email=data.get("user_email", ""),
            user_name=data.get("user_name", ""),
            tier=LicenseTier(data.get("tier", "corrector")),
            status=LicenseStatus(data.get("status", "active")),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else None
            ),
            activated_at=(
                datetime.fromisoformat(data["activated_at"])
                if data.get("activated_at")
                else None
            ),
            expires_at=(
                datetime.fromisoformat(data["expires_at"])
                if data.get("expires_at")
                else None
            ),
            last_verified_at=(
                datetime.fromisoformat(data["last_verified_at"])
                if data.get("last_verified_at")
                else None
            ),
            grace_period_ends_at=(
                datetime.fromisoformat(data["grace_period_ends_at"])
                if data.get("grace_period_ends_at")
                else None
            ),
            is_founding_member=data.get("is_founding_member", False),
            founding_tier=(
                LicenseTier(data["founding_tier"])
                if data.get("founding_tier")
                else None
            ),
            founding_discount_eur=data.get("founding_discount_eur", 0.0),
            downgrade_grace_until=(
                datetime.fromisoformat(data["downgrade_grace_until"])
                if data.get("downgrade_grace_until")
                else None
            ),
            is_comp=data.get("is_comp", False),
            comp_type=(
                CompLicenseType(data["comp_type"])
                if data.get("comp_type")
                else None
            ),
            comp_discount_pct=data.get("comp_discount_pct", 0.0),
            comp_expires_at=(
                datetime.fromisoformat(data["comp_expires_at"])
                if data.get("comp_expires_at")
                else None
            ),
            comp_notes=data.get("comp_notes", ""),
            extra_data=data.get("extra_data", {}),
        )

        if data.get("subscription"):
            license_obj.subscription = Subscription.from_dict(data["subscription"])

        if data.get("devices"):
            license_obj.devices = [Device.from_dict(d) for d in data["devices"]]

        return license_obj

    @classmethod
    def from_db_row(cls, row) -> "License":
        """Crea License desde una fila de SQLite (sin relaciones)."""
        return cls(
            id=row["id"],
            license_key=row["license_key"],
            user_email=row["user_email"],
            user_name=row["user_name"],
            tier=LicenseTier(row["tier"]),
            status=LicenseStatus(row["status"]),
            created_at=(
                datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
            ),
            activated_at=(
                datetime.fromisoformat(row["activated_at"])
                if row["activated_at"]
                else None
            ),
            expires_at=(
                datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
            ),
            last_verified_at=(
                datetime.fromisoformat(row["last_verified_at"])
                if row["last_verified_at"]
                else None
            ),
            grace_period_ends_at=(
                datetime.fromisoformat(row["grace_period_ends_at"])
                if row["grace_period_ends_at"]
                else None
            ),
            is_founding_member=bool(row["is_founding_member"]) if "is_founding_member" in row else False,
            founding_tier=(
                LicenseTier(row["founding_tier"])
                if "founding_tier" in row and row["founding_tier"]
                else None
            ),
            founding_discount_eur=float(row["founding_discount_eur"]) if "founding_discount_eur" in row else 0.0,
            downgrade_grace_until=(
                datetime.fromisoformat(row["downgrade_grace_until"])
                if "downgrade_grace_until" in row and row["downgrade_grace_until"]
                else None
            ),
            is_comp=bool(row["is_comp"]) if "is_comp" in row else False,
            comp_type=(
                CompLicenseType(row["comp_type"])
                if "comp_type" in row and row["comp_type"]
                else None
            ),
            comp_discount_pct=float(row["comp_discount_pct"]) if "comp_discount_pct" in row else 0.0,
            comp_expires_at=(
                datetime.fromisoformat(row["comp_expires_at"])
                if "comp_expires_at" in row and row["comp_expires_at"]
                else None
            ),
            comp_notes=row.get("comp_notes", ""),
            extra_data=json.loads(row["extra_data"]) if row["extra_data"] else {},
        )


# =============================================================================
# Schema SQL para SQLite
# =============================================================================


LICENSING_SCHEMA_SQL = """
-- Licencias de usuario
CREATE TABLE IF NOT EXISTS licenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_key TEXT NOT NULL UNIQUE,
    user_email TEXT NOT NULL,
    user_name TEXT,
    tier TEXT NOT NULL DEFAULT 'corrector',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    activated_at TEXT,
    expires_at TEXT,
    last_verified_at TEXT,
    grace_period_ends_at TEXT,
    -- Founding member
    is_founding_member INTEGER DEFAULT 0,
    founding_tier TEXT,
    founding_discount_eur REAL DEFAULT 0.0,
    downgrade_grace_until TEXT,
    -- Comp/regalo
    is_comp INTEGER DEFAULT 0,
    comp_type TEXT,
    comp_discount_pct REAL DEFAULT 0.0,
    comp_expires_at TEXT,
    comp_notes TEXT DEFAULT '',
    -- Extra
    extra_data TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_licenses_key ON licenses(license_key);
CREATE INDEX IF NOT EXISTS idx_licenses_email ON licenses(user_email);
CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status);

-- Suscripciones (datos del proveedor de pagos)
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id INTEGER NOT NULL UNIQUE,
    stripe_subscription_id TEXT NOT NULL,
    stripe_customer_id TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'corrector',
    status TEXT NOT NULL DEFAULT 'active',
    current_period_start TEXT,
    current_period_end TEXT,
    cancel_at_period_end INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_license ON subscriptions(license_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe ON subscriptions(stripe_subscription_id);

-- Dispositivos vinculados
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id INTEGER NOT NULL,
    hardware_fingerprint TEXT NOT NULL,
    device_name TEXT,
    os_info TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    activated_at TEXT,
    deactivated_at TEXT,
    cooldown_ends_at TEXT,
    last_seen_at TEXT,
    is_current_device INTEGER DEFAULT 0,
    FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE CASCADE,
    UNIQUE (license_id, hardware_fingerprint)
);

CREATE INDEX IF NOT EXISTS idx_devices_license ON devices(license_id);
CREATE INDEX IF NOT EXISTS idx_devices_fingerprint ON devices(hardware_fingerprint);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);

-- Registros de uso (cuota en paginas)
CREATE TABLE IF NOT EXISTS usage_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id INTEGER NOT NULL,
    project_id INTEGER,
    document_fingerprint TEXT NOT NULL,
    document_name TEXT,
    word_count INTEGER DEFAULT 0,
    page_count INTEGER DEFAULT 0,
    analysis_started_at TEXT NOT NULL DEFAULT (datetime('now')),
    analysis_completed_at TEXT,
    billing_period TEXT NOT NULL,
    counted_for_quota INTEGER DEFAULT 1,
    FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_usage_license ON usage_records(license_id);
CREATE INDEX IF NOT EXISTS idx_usage_period ON usage_records(billing_period);
CREATE INDEX IF NOT EXISTS idx_usage_fingerprint ON usage_records(document_fingerprint);

-- Cache de verificacion de licencia (para modo offline)
CREATE TABLE IF NOT EXISTS license_verification_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id INTEGER NOT NULL UNIQUE,
    cached_response TEXT NOT NULL,
    cached_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL,
    FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_verification_cache_license ON license_verification_cache(license_id);

-- Registro de swaps de dispositivo (para conteo mensual)
CREATE TABLE IF NOT EXISTS device_swaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    swapped_at TEXT NOT NULL DEFAULT (datetime('now')),
    billing_period TEXT NOT NULL,
    FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_device_swaps_license_period ON device_swaps(license_id, billing_period);

-- Auditoria de cambios de descuento (founding/comp)
CREATE TABLE IF NOT EXISTS discount_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    old_tier TEXT,
    new_tier TEXT,
    discount_before REAL DEFAULT 0.0,
    discount_after REAL DEFAULT 0.0,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_discount_events_license ON discount_events(license_id);
"""

# SQL para migrar BD existentes (añadir columnas nuevas)
LICENSING_MIGRATION_V2_SQL = """
-- Migración v2: Founding member fields + Comp license fields
ALTER TABLE licenses ADD COLUMN is_founding_member INTEGER DEFAULT 0;
ALTER TABLE licenses ADD COLUMN founding_tier TEXT;
ALTER TABLE licenses ADD COLUMN founding_discount_eur REAL DEFAULT 0.0;
ALTER TABLE licenses ADD COLUMN downgrade_grace_until TEXT;
ALTER TABLE licenses ADD COLUMN is_comp INTEGER DEFAULT 0;
ALTER TABLE licenses ADD COLUMN comp_type TEXT;
ALTER TABLE licenses ADD COLUMN comp_discount_pct REAL DEFAULT 0.0;
ALTER TABLE licenses ADD COLUMN comp_expires_at TEXT;
ALTER TABLE licenses ADD COLUMN comp_notes TEXT DEFAULT '';
"""


def initialize_licensing_schema(db) -> None:
    """
    Inicializa el schema de licencias en la base de datos.

    Ejecuta CREATE TABLE IF NOT EXISTS para todas las tablas.
    Si la BD ya existia, intenta añadir las columnas nuevas de v2.

    Args:
        db: Instancia de Database
    """
    with db.connection() as conn:
        conn.executescript(LICENSING_SCHEMA_SQL)
        # Migrar BD existentes: añadir columnas nuevas si no existen
        try:
            cursor = conn.execute("PRAGMA table_info(licenses)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            if "is_founding_member" not in existing_cols:
                for line in LICENSING_MIGRATION_V2_SQL.strip().split("\n"):
                    line = line.strip()
                    if line and not line.startswith("--"):
                        try:
                            conn.execute(line)
                        except Exception:
                            pass  # Column already exists
        except Exception:
            pass  # PRAGMA failed (shouldn't happen)
