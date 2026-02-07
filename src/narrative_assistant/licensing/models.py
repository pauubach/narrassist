"""
Modelos de datos para el sistema de licencias.

Define las estructuras para:
- Licencias y suscripciones
- Dispositivos vinculados
- Registro de uso
- Tiers y bundles de funcionalidad
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

# =============================================================================
# Enums y Constantes
# =============================================================================


class LicenseTier(Enum):
    """Niveles de suscripcion disponibles."""

    FREELANCE = "freelance"
    AGENCIA = "agencia"
    EDITORIAL = "editorial"

    @property
    def display_name(self) -> str:
        """Nombre para mostrar al usuario."""
        names = {
            LicenseTier.FREELANCE: "Freelance",
            LicenseTier.AGENCIA: "Agencia",
            LicenseTier.EDITORIAL: "Editorial",
        }
        return names[self]


class LicenseModule(Enum):
    """Modulos de funcionalidad disponibles."""

    CORE = "core"  # Base obligatoria
    NARRATIVA = "narrativa"  # Analisis narrativo
    VOZ_ESTILO = "voz_estilo"  # Voz y estilo
    AVANZADO = "avanzado"  # Funciones avanzadas

    @property
    def display_name(self) -> str:
        """Nombre para mostrar al usuario."""
        names = {
            LicenseModule.CORE: "Core",
            LicenseModule.NARRATIVA: "Narrativa",
            LicenseModule.VOZ_ESTILO: "Voz y Estilo",
            LicenseModule.AVANZADO: "Avanzado",
        }
        return names[self]


class LicenseBundle(Enum):
    """Bundles de modulos predefinidos."""

    SOLO_CORE = "solo_core"
    PROFESIONAL = "profesional"  # Core + Narrativa + Voz
    COMPLETO = "completo"  # Todo

    @property
    def modules(self) -> list[LicenseModule]:
        """Modulos incluidos en el bundle."""
        bundles = {
            LicenseBundle.SOLO_CORE: [LicenseModule.CORE],
            LicenseBundle.PROFESIONAL: [
                LicenseModule.CORE,
                LicenseModule.NARRATIVA,
                LicenseModule.VOZ_ESTILO,
            ],
            LicenseBundle.COMPLETO: [
                LicenseModule.CORE,
                LicenseModule.NARRATIVA,
                LicenseModule.VOZ_ESTILO,
                LicenseModule.AVANZADO,
            ],
        }
        return bundles[self]

    @property
    def display_name(self) -> str:
        """Nombre para mostrar al usuario."""
        names = {
            LicenseBundle.SOLO_CORE: "Solo Core",
            LicenseBundle.PROFESIONAL: "Profesional",
            LicenseBundle.COMPLETO: "Completo",
        }
        return names[self]


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

    max_manuscripts_per_month: int  # 0 = ilimitado
    max_devices: int
    min_devices: int = 1  # Minimo de dispositivos incluidos

    @classmethod
    def for_tier(cls, tier: LicenseTier) -> "TierLimits":
        """Obtiene los limites para un tier especifico."""
        limits = {
            LicenseTier.FREELANCE: cls(
                max_manuscripts_per_month=5,
                max_devices=1,
                min_devices=1,
            ),
            LicenseTier.AGENCIA: cls(
                max_manuscripts_per_month=15,
                max_devices=2,
                min_devices=1,
            ),
            LicenseTier.EDITORIAL: cls(
                max_manuscripts_per_month=0,  # Ilimitado
                max_devices=100,  # Maximo practico
                min_devices=5,
            ),
        }
        return limits[tier]


# Periodo de gracia offline en dias
OFFLINE_GRACE_PERIOD_DAYS = 14

# Cooldown al desactivar dispositivo en horas
DEVICE_DEACTIVATION_COOLDOWN_HOURS = 48


# =============================================================================
# Modelos de Datos
# =============================================================================


@dataclass
class Device:
    """
    Dispositivo vinculado a una licencia.

    Attributes:
        id: Identificador único en BD local
        license_id: ID de la licencia asociada
        hardware_fingerprint: Hash único del hardware
        device_name: Nombre amigable del dispositivo
        os_info: Información del sistema operativo
        status: Estado del dispositivo
        activated_at: Fecha de activación
        deactivated_at: Fecha de desactivación (si aplica)
        cooldown_ends_at: Fin del periodo de cooldown
        last_seen_at: Última vez que el dispositivo verificó la licencia
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
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "deactivated_at": self.deactivated_at.isoformat() if self.deactivated_at else None,
            "cooldown_ends_at": self.cooldown_ends_at.isoformat()
            if self.cooldown_ends_at
            else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
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
            activated_at=datetime.fromisoformat(data["activated_at"])
            if data.get("activated_at")
            else None,
            deactivated_at=datetime.fromisoformat(data["deactivated_at"])
            if data.get("deactivated_at")
            else None,
            cooldown_ends_at=datetime.fromisoformat(data["cooldown_ends_at"])
            if data.get("cooldown_ends_at")
            else None,
            last_seen_at=datetime.fromisoformat(data["last_seen_at"])
            if data.get("last_seen_at")
            else None,
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
            activated_at=datetime.fromisoformat(row["activated_at"])
            if row["activated_at"]
            else None,
            deactivated_at=datetime.fromisoformat(row["deactivated_at"])
            if row["deactivated_at"]
            else None,
            cooldown_ends_at=datetime.fromisoformat(row["cooldown_ends_at"])
            if row["cooldown_ends_at"]
            else None,
            last_seen_at=datetime.fromisoformat(row["last_seen_at"])
            if row["last_seen_at"]
            else None,
            is_current_device=bool(row["is_current_device"]),
        )


@dataclass
class Subscription:
    """
    Suscripcion asociada a una licencia (datos de Stripe).

    Attributes:
        id: Identificador unico en BD local
        license_id: ID de la licencia asociada
        stripe_subscription_id: ID de la suscripcion en Stripe
        stripe_customer_id: ID del cliente en Stripe
        tier: Nivel de suscripcion
        bundle: Bundle de modulos
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
    tier: LicenseTier = LicenseTier.FREELANCE
    bundle: LicenseBundle = LicenseBundle.SOLO_CORE
    status: str = "active"  # Stripe status: active, past_due, canceled, etc.
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
            "bundle": self.bundle.value,
            "status": self.status,
            "current_period_start": self.current_period_start.isoformat()
            if self.current_period_start
            else None,
            "current_period_end": self.current_period_end.isoformat()
            if self.current_period_end
            else None,
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
            tier=LicenseTier(data.get("tier", "freelance")),
            bundle=LicenseBundle(data.get("bundle", "solo_core")),
            status=data.get("status", "active"),
            current_period_start=datetime.fromisoformat(data["current_period_start"])
            if data.get("current_period_start")
            else None,
            current_period_end=datetime.fromisoformat(data["current_period_end"])
            if data.get("current_period_end")
            else None,
            cancel_at_period_end=data.get("cancel_at_period_end", False),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            updated_at=datetime.fromisoformat(data["updated_at"])
            if data.get("updated_at")
            else None,
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
            bundle=LicenseBundle(row["bundle"]),
            status=row["status"],
            current_period_start=datetime.fromisoformat(row["current_period_start"])
            if row["current_period_start"]
            else None,
            current_period_end=datetime.fromisoformat(row["current_period_end"])
            if row["current_period_end"]
            else None,
            cancel_at_period_end=bool(row["cancel_at_period_end"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )


@dataclass
class UsageRecord:
    """
    Registro de uso de manuscritos.

    Attributes:
        id: Identificador unico en BD local
        license_id: ID de la licencia asociada
        project_id: ID del proyecto analizado
        document_fingerprint: Fingerprint del documento
        document_name: Nombre del documento
        word_count: Conteo de palabras
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
    analysis_started_at: datetime | None = None
    analysis_completed_at: datetime | None = None
    billing_period: str = ""  # YYYY-MM
    counted_for_quota: bool = True

    @classmethod
    def current_billing_period(cls) -> str:
        """Retorna el periodo de facturacion actual."""
        now = datetime.utcnow()
        return f"{now.year}-{now.month:02d}"

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            "id": self.id,
            "license_id": self.license_id,
            "project_id": self.project_id,
            "document_fingerprint": self.document_fingerprint,
            "document_name": self.document_name,
            "word_count": self.word_count,
            "analysis_started_at": self.analysis_started_at.isoformat()
            if self.analysis_started_at
            else None,
            "analysis_completed_at": self.analysis_completed_at.isoformat()
            if self.analysis_completed_at
            else None,
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
            analysis_started_at=datetime.fromisoformat(data["analysis_started_at"])
            if data.get("analysis_started_at")
            else None,
            analysis_completed_at=datetime.fromisoformat(data["analysis_completed_at"])
            if data.get("analysis_completed_at")
            else None,
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
            analysis_started_at=datetime.fromisoformat(row["analysis_started_at"])
            if row["analysis_started_at"]
            else None,
            analysis_completed_at=datetime.fromisoformat(row["analysis_completed_at"])
            if row["analysis_completed_at"]
            else None,
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
        bundle: Bundle de modulos
        modules: Lista de modulos habilitados (calculado desde bundle)
        status: Estado actual de la licencia
        created_at: Fecha de creacion
        activated_at: Fecha de primera activacion
        expires_at: Fecha de expiracion
        last_verified_at: Ultima verificacion online
        grace_period_ends_at: Fin del periodo de gracia offline
        subscription: Datos de suscripcion Stripe
        devices: Lista de dispositivos vinculados
        extra_data: Datos adicionales (JSON)
    """

    id: int | None = None
    license_key: str = ""
    user_email: str = ""
    user_name: str = ""
    tier: LicenseTier = LicenseTier.FREELANCE
    bundle: LicenseBundle = LicenseBundle.SOLO_CORE
    status: LicenseStatus = LicenseStatus.ACTIVE
    created_at: datetime | None = None
    activated_at: datetime | None = None
    expires_at: datetime | None = None
    last_verified_at: datetime | None = None
    grace_period_ends_at: datetime | None = None
    subscription: Subscription | None = None
    devices: list[Device] = field(default_factory=list)
    extra_data: dict = field(default_factory=dict)

    @property
    def modules(self) -> list[LicenseModule]:
        """Modulos habilitados segun el bundle."""
        return self.bundle.modules

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

    def has_module(self, module: LicenseModule) -> bool:
        """Verifica si un modulo esta habilitado."""
        return module in self.modules

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
            "bundle": self.bundle.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_verified_at": self.last_verified_at.isoformat()
            if self.last_verified_at
            else None,
            "grace_period_ends_at": self.grace_period_ends_at.isoformat()
            if self.grace_period_ends_at
            else None,
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
            tier=LicenseTier(data.get("tier", "freelance")),
            bundle=LicenseBundle(data.get("bundle", "solo_core")),
            status=LicenseStatus(data.get("status", "active")),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            activated_at=datetime.fromisoformat(data["activated_at"])
            if data.get("activated_at")
            else None,
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
            last_verified_at=datetime.fromisoformat(data["last_verified_at"])
            if data.get("last_verified_at")
            else None,
            grace_period_ends_at=datetime.fromisoformat(data["grace_period_ends_at"])
            if data.get("grace_period_ends_at")
            else None,
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
            bundle=LicenseBundle(row["bundle"]),
            status=LicenseStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            activated_at=datetime.fromisoformat(row["activated_at"])
            if row["activated_at"]
            else None,
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            last_verified_at=datetime.fromisoformat(row["last_verified_at"])
            if row["last_verified_at"]
            else None,
            grace_period_ends_at=datetime.fromisoformat(row["grace_period_ends_at"])
            if row["grace_period_ends_at"]
            else None,
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
    tier TEXT NOT NULL DEFAULT 'freelance',
    bundle TEXT NOT NULL DEFAULT 'solo_core',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    activated_at TEXT,
    expires_at TEXT,
    last_verified_at TEXT,
    grace_period_ends_at TEXT,
    extra_data TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_licenses_key ON licenses(license_key);
CREATE INDEX IF NOT EXISTS idx_licenses_email ON licenses(user_email);
CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status);

-- Suscripciones (datos de Stripe)
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id INTEGER NOT NULL UNIQUE,
    stripe_subscription_id TEXT NOT NULL,
    stripe_customer_id TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'freelance',
    bundle TEXT NOT NULL DEFAULT 'solo_core',
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

-- Registros de uso de manuscritos
CREATE TABLE IF NOT EXISTS usage_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id INTEGER NOT NULL,
    project_id INTEGER,
    document_fingerprint TEXT NOT NULL,
    document_name TEXT,
    word_count INTEGER DEFAULT 0,
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
"""


def initialize_licensing_schema(db) -> None:
    """
    Inicializa el schema de licencias en la base de datos.

    Args:
        db: Instancia de Database
    """
    with db.connection() as conn:
        conn.executescript(LICENSING_SCHEMA_SQL)
