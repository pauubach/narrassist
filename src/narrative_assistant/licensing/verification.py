"""
Sistema de verificacion de licencias.

Proporciona:
- Verificacion online contra el backend
- Modo offline con periodo de gracia de 14 dias
- Gestion de dispositivos vinculados
- Control de cuota de manuscritos
"""

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from ..core.config import get_config
from ..core.result import Result
from ..core.errors import NarrativeError, ErrorSeverity
from .models import (
    License,
    LicenseStatus,
    LicenseTier,
    LicenseBundle,
    LicenseModule,
    Device,
    DeviceStatus,
    Subscription,
    UsageRecord,
    TierLimits,
    OFFLINE_GRACE_PERIOD_DAYS,
    DEVICE_DEACTIVATION_COOLDOWN_HOURS,
    initialize_licensing_schema,
)
from .fingerprint import get_hardware_fingerprint, get_hardware_info

logger = logging.getLogger(__name__)

# Lock para thread-safety
_license_lock = threading.Lock()
_cached_license: Optional[License] = None


# =============================================================================
# Errores de Licencia
# =============================================================================


@dataclass
class LicenseError(NarrativeError):
    """Error base para problemas de licencia."""
    pass


@dataclass
class LicenseNotFoundError(LicenseError):
    """No se encontro licencia valida."""

    message: str = "No license found"
    severity: ErrorSeverity = ErrorSeverity.FATAL
    user_message: Optional[str] = None

    def __post_init__(self):
        if self.user_message is None:
            self.user_message = (
                "No se encontro una licencia valida. "
                "Por favor, introduce tu clave de licencia en Configuracion."
            )
        super().__post_init__()


@dataclass
class LicenseExpiredError(LicenseError):
    """Licencia expirada."""

    expired_at: Optional[datetime] = None
    message: str = "License expired"
    severity: ErrorSeverity = ErrorSeverity.FATAL
    user_message: Optional[str] = None

    def __post_init__(self):
        if self.user_message is None:
            self.user_message = (
                "Tu licencia ha expirado. "
                "Por favor, renueva tu suscripcion para continuar."
            )
        super().__post_init__()


@dataclass
class LicenseOfflineError(LicenseError):
    """No se puede verificar licencia (sin conexion)."""

    grace_remaining: Optional[timedelta] = None
    message: str = "Cannot verify license offline"
    severity: ErrorSeverity = ErrorSeverity.DEGRADED
    user_message: Optional[str] = None

    def __post_init__(self):
        if self.grace_remaining:
            days = self.grace_remaining.days
            self.user_message = (
                f"Sin conexion. Modo offline activo ({days} dias restantes). "
                "Conectate a internet para verificar tu licencia."
            )
        else:
            self.user_message = (
                "No se puede verificar la licencia sin conexion a internet."
            )
        super().__post_init__()


@dataclass
class DeviceLimitError(LicenseError):
    """Limite de dispositivos alcanzado."""

    current_devices: int = 0
    max_devices: int = 0
    message: str = "Device limit reached"
    severity: ErrorSeverity = ErrorSeverity.FATAL
    user_message: Optional[str] = None

    def __post_init__(self):
        if self.user_message is None:
            self.user_message = (
                f"Has alcanzado el limite de {self.max_devices} dispositivo(s). "
                "Desactiva un dispositivo existente o actualiza tu plan."
            )
        super().__post_init__()


@dataclass
class DeviceCooldownError(LicenseError):
    """Dispositivo en periodo de cooldown."""

    cooldown_ends: Optional[datetime] = None
    message: str = "Device in cooldown period"
    severity: ErrorSeverity = ErrorSeverity.FATAL
    user_message: Optional[str] = None

    def __post_init__(self):
        if self.cooldown_ends:
            hours_remaining = int(
                (self.cooldown_ends - datetime.utcnow()).total_seconds() / 3600
            )
            self.user_message = (
                f"Este dispositivo fue desactivado recientemente. "
                f"Podras reactivarlo en {hours_remaining} horas."
            )
        else:
            self.user_message = (
                "Este dispositivo esta en periodo de espera tras desactivacion."
            )
        super().__post_init__()


@dataclass
class QuotaExceededError(LicenseError):
    """Cuota de manuscritos excedida."""

    current_usage: int = 0
    max_usage: int = 0
    billing_period: str = ""
    message: str = "Manuscript quota exceeded"
    severity: ErrorSeverity = ErrorSeverity.FATAL
    user_message: Optional[str] = None

    def __post_init__(self):
        if self.user_message is None:
            self.user_message = (
                f"Has alcanzado el limite de {self.max_usage} manuscritos este mes "
                f"({self.current_usage}/{self.max_usage}). "
                "Espera al proximo periodo o actualiza tu plan."
            )
        super().__post_init__()


@dataclass
class ModuleNotLicensedError(LicenseError):
    """Modulo no incluido en la licencia."""

    module: Optional[LicenseModule] = None
    message: str = "Module not licensed"
    severity: ErrorSeverity = ErrorSeverity.FATAL
    user_message: Optional[str] = None

    def __post_init__(self):
        if self.user_message is None:
            module_name = self.module.display_name if self.module else "este modulo"
            self.user_message = (
                f"Tu licencia no incluye {module_name}. "
                "Actualiza tu plan para acceder a esta funcionalidad."
            )
        super().__post_init__()


# =============================================================================
# Resultados de Verificacion
# =============================================================================


@dataclass
class VerificationResult:
    """Resultado de verificacion de licencia."""

    is_valid: bool
    license: Optional[License]
    status: LicenseStatus
    message: str
    is_offline: bool = False
    grace_remaining: Optional[timedelta] = None
    quota_remaining: Optional[int] = None
    devices_remaining: int = 0

    @property
    def can_analyze(self) -> bool:
        """Verifica si se puede analizar un manuscrito."""
        if not self.is_valid:
            return False
        if self.quota_remaining is not None and self.quota_remaining <= 0:
            return False
        return True


# =============================================================================
# Clase Principal de Verificacion
# =============================================================================


class LicenseVerifier:
    """
    Verificador de licencias.

    Maneja:
    - Verificacion online/offline
    - Cache de verificacion
    - Gestion de dispositivos
    - Control de cuotas
    """

    # URL del backend de licencias
    DEFAULT_LICENSE_SERVER = "https://api.narrativeassistant.com/v1/licenses"

    def __init__(
        self,
        db=None,
        license_server_url: Optional[str] = None,
    ):
        """
        Args:
            db: Instancia de Database (opcional)
            license_server_url: URL del servidor de licencias
        """
        self._db = db
        self._license_server = license_server_url or self.DEFAULT_LICENSE_SERVER
        self._current_fingerprint: Optional[str] = None

    def _get_db(self):
        """Obtiene instancia de base de datos."""
        if self._db is None:
            from ..persistence.database import get_database
            self._db = get_database()
            # Asegurar que el schema de licencias existe
            initialize_licensing_schema(self._db)
        return self._db

    def _get_current_fingerprint(self) -> str:
        """Obtiene el fingerprint del dispositivo actual."""
        if self._current_fingerprint is None:
            result = get_hardware_fingerprint()
            if result.is_failure:
                raise result.error
            self._current_fingerprint = result.value
        return self._current_fingerprint

    # =========================================================================
    # Verificacion Principal
    # =========================================================================

    def verify(self, force_online: bool = False) -> Result[VerificationResult]:
        """
        Verifica el estado de la licencia.

        Args:
            force_online: Forzar verificacion online

        Returns:
            Result con VerificationResult
        """
        try:
            # 1. Cargar licencia local
            license_result = self._load_local_license()
            if license_result.is_failure:
                return Result.failure(LicenseNotFoundError())

            license_obj = license_result.value

            # 2. Verificar dispositivo actual
            device_result = self._verify_current_device(license_obj)
            if device_result.is_failure:
                return Result.failure(device_result.error)

            # 3. Intentar verificacion online
            if force_online or self._should_verify_online(license_obj):
                online_result = self._verify_online(license_obj)
                if online_result.is_success:
                    license_obj = online_result.value
                    self._save_local_license(license_obj)
                else:
                    # Manejar fallo de conexion
                    license_obj = self._handle_offline_mode(license_obj)

            # 4. Verificar estado final
            if license_obj.status == LicenseStatus.EXPIRED:
                return Result.failure(
                    LicenseExpiredError(expired_at=license_obj.expires_at)
                )

            # 5. Calcular cuota restante
            quota_remaining = self._calculate_quota_remaining(license_obj)

            # 6. Construir resultado
            verification = VerificationResult(
                is_valid=license_obj.is_valid,
                license=license_obj,
                status=license_obj.status,
                message=self._get_status_message(license_obj),
                is_offline=license_obj.is_in_grace_period,
                grace_remaining=license_obj.grace_period_remaining,
                quota_remaining=quota_remaining,
                devices_remaining=license_obj.limits.max_devices - license_obj.active_device_count,
            )

            # Cache global
            global _cached_license
            with _license_lock:
                _cached_license = license_obj

            return Result.success(verification)

        except Exception as e:
            logger.exception("Error verificando licencia")
            return Result.failure(
                NarrativeError(
                    message=f"License verification failed: {e}",
                    severity=ErrorSeverity.FATAL,
                    user_message="Error al verificar la licencia. Por favor, reinicia la aplicacion.",
                )
            )

    def _should_verify_online(self, license_obj: License) -> bool:
        """Determina si se debe verificar online."""
        if license_obj.last_verified_at is None:
            return True

        # Verificar cada 24 horas
        time_since_verification = datetime.utcnow() - license_obj.last_verified_at
        return time_since_verification > timedelta(hours=24)

    def _verify_online(self, license_obj: License) -> Result[License]:
        """
        Verifica licencia contra el servidor.

        NOTA: Esta funcion hace una excepcion a la regla de no usar internet,
        ya que la verificacion de licencias es el unico caso permitido.
        """
        try:
            import urllib.request
            import urllib.error

            fingerprint = self._get_current_fingerprint()

            # Preparar request
            url = urljoin(self._license_server, f"/verify/{license_obj.license_key}")
            data = json.dumps({
                "device_fingerprint": fingerprint,
                "app_version": "1.0.0",  # TODO: obtener version real
            }).encode("utf-8")

            request = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )

            # Timeout de 10 segundos
            with urllib.request.urlopen(request, timeout=10) as response:
                response_data = json.loads(response.read().decode("utf-8"))

            # Actualizar licencia con datos del servidor
            if response_data.get("valid"):
                license_obj.status = LicenseStatus.ACTIVE
                license_obj.last_verified_at = datetime.utcnow()
                license_obj.grace_period_ends_at = None

                # Actualizar datos de suscripcion si vienen
                if sub_data := response_data.get("subscription"):
                    license_obj.subscription = Subscription.from_dict(sub_data)

                # Actualizar tier/bundle si cambiaron
                if tier := response_data.get("tier"):
                    license_obj.tier = LicenseTier(tier)
                if bundle := response_data.get("bundle"):
                    license_obj.bundle = LicenseBundle(bundle)

                logger.info("Licencia verificada online exitosamente")
                return Result.success(license_obj)
            else:
                # Licencia invalidada por el servidor
                reason = response_data.get("reason", "unknown")
                logger.warning(f"Licencia rechazada por servidor: {reason}")

                if reason == "expired":
                    license_obj.status = LicenseStatus.EXPIRED
                elif reason == "suspended":
                    license_obj.status = LicenseStatus.SUSPENDED
                elif reason == "cancelled":
                    license_obj.status = LicenseStatus.CANCELLED

                return Result.failure(
                    LicenseExpiredError(
                        message=f"License invalid: {reason}",
                        user_message=response_data.get("message"),
                    )
                )

        except urllib.error.URLError as e:
            logger.warning(f"No se pudo conectar al servidor de licencias: {e}")
            return Result.failure(
                LicenseOfflineError(
                    message=f"Cannot connect to license server: {e}",
                    grace_remaining=license_obj.grace_period_remaining,
                )
            )
        except Exception as e:
            logger.exception("Error en verificacion online")
            return Result.failure(
                NarrativeError(
                    message=f"Online verification failed: {e}",
                    severity=ErrorSeverity.RECOVERABLE,
                )
            )

    def _handle_offline_mode(self, license_obj: License) -> License:
        """Maneja el modo offline con periodo de gracia."""
        if license_obj.status == LicenseStatus.ACTIVE:
            # Iniciar periodo de gracia
            license_obj.start_grace_period()
            logger.info(
                f"Modo offline activado. Periodo de gracia hasta: "
                f"{license_obj.grace_period_ends_at}"
            )
        elif license_obj.status == LicenseStatus.GRACE_PERIOD:
            # Verificar si expiro el periodo de gracia
            if license_obj.grace_period_ends_at:
                if datetime.utcnow() > license_obj.grace_period_ends_at:
                    license_obj.expire_grace_period()
                    logger.warning("Periodo de gracia expirado")

        self._save_local_license(license_obj)
        return license_obj

    def _get_status_message(self, license_obj: License) -> str:
        """Genera mensaje de estado legible."""
        messages = {
            LicenseStatus.ACTIVE: "Licencia activa",
            LicenseStatus.GRACE_PERIOD: (
                f"Modo offline ({license_obj.grace_period_remaining.days if license_obj.grace_period_remaining else 0} dias restantes)"
            ),
            LicenseStatus.EXPIRED: "Licencia expirada",
            LicenseStatus.SUSPENDED: "Licencia suspendida",
            LicenseStatus.CANCELLED: "Licencia cancelada",
        }
        return messages.get(license_obj.status, "Estado desconocido")

    # =========================================================================
    # Gestion de Dispositivos
    # =========================================================================

    def _verify_current_device(self, license_obj: License) -> Result[Device]:
        """Verifica que el dispositivo actual este autorizado."""
        fingerprint = self._get_current_fingerprint()

        # Buscar dispositivo en la lista
        current_device = None
        for device in license_obj.devices:
            if device.hardware_fingerprint == fingerprint:
                current_device = device
                break

        if current_device is None:
            # Dispositivo no registrado - intentar registrar
            return self._register_device(license_obj, fingerprint)

        # Verificar estado del dispositivo
        if current_device.status == DeviceStatus.INACTIVE:
            if current_device.is_in_cooldown:
                return Result.failure(
                    DeviceCooldownError(cooldown_ends=current_device.cooldown_ends_at)
                )
            # Cooldown terminado, se puede reactivar
            return self._reactivate_device(license_obj, current_device)

        if current_device.status == DeviceStatus.PENDING:
            # Activar dispositivo pendiente
            return self._activate_device(license_obj, current_device)

        # Actualizar last_seen
        current_device.last_seen_at = datetime.utcnow()
        current_device.is_current_device = True
        self._update_device(current_device)

        return Result.success(current_device)

    def _register_device(
        self,
        license_obj: License,
        fingerprint: str,
    ) -> Result[Device]:
        """Registra un nuevo dispositivo."""
        if not license_obj.can_add_device():
            return Result.failure(
                DeviceLimitError(
                    current_devices=license_obj.active_device_count,
                    max_devices=license_obj.limits.max_devices,
                )
            )

        # Obtener info del hardware
        hw_info_result = get_hardware_info()
        hw_info = hw_info_result.value if hw_info_result.is_success else None

        device = Device(
            license_id=license_obj.id,
            hardware_fingerprint=fingerprint,
            device_name=hw_info.device_name if hw_info else "Unknown Device",
            os_info=hw_info.os_info if hw_info else "Unknown OS",
            status=DeviceStatus.ACTIVE,
            activated_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
            is_current_device=True,
        )

        # Guardar en BD
        db = self._get_db()
        with db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO devices (
                    license_id, hardware_fingerprint, device_name, os_info,
                    status, activated_at, last_seen_at, is_current_device
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    device.license_id,
                    device.hardware_fingerprint,
                    device.device_name,
                    device.os_info,
                    device.status.value,
                    device.activated_at.isoformat(),
                    device.last_seen_at.isoformat(),
                    1,
                ),
            )
            device.id = cursor.lastrowid

        license_obj.devices.append(device)
        logger.info(f"Nuevo dispositivo registrado: {device.device_name}")

        return Result.success(device)

    def _activate_device(
        self,
        license_obj: License,
        device: Device,
    ) -> Result[Device]:
        """Activa un dispositivo pendiente."""
        device.status = DeviceStatus.ACTIVE
        device.activated_at = datetime.utcnow()
        device.last_seen_at = datetime.utcnow()
        device.is_current_device = True

        self._update_device(device)
        logger.info(f"Dispositivo activado: {device.device_name}")

        return Result.success(device)

    def _reactivate_device(
        self,
        license_obj: License,
        device: Device,
    ) -> Result[Device]:
        """Reactiva un dispositivo tras cooldown."""
        if not license_obj.can_add_device():
            return Result.failure(
                DeviceLimitError(
                    current_devices=license_obj.active_device_count,
                    max_devices=license_obj.limits.max_devices,
                )
            )

        device.status = DeviceStatus.ACTIVE
        device.deactivated_at = None
        device.cooldown_ends_at = None
        device.last_seen_at = datetime.utcnow()
        device.is_current_device = True

        self._update_device(device)
        logger.info(f"Dispositivo reactivado: {device.device_name}")

        return Result.success(device)

    def _update_device(self, device: Device) -> None:
        """Actualiza un dispositivo en BD."""
        db = self._get_db()
        with db.transaction() as conn:
            conn.execute(
                """
                UPDATE devices SET
                    status = ?,
                    activated_at = ?,
                    deactivated_at = ?,
                    cooldown_ends_at = ?,
                    last_seen_at = ?,
                    is_current_device = ?
                WHERE id = ?
                """,
                (
                    device.status.value,
                    device.activated_at.isoformat() if device.activated_at else None,
                    device.deactivated_at.isoformat() if device.deactivated_at else None,
                    device.cooldown_ends_at.isoformat() if device.cooldown_ends_at else None,
                    device.last_seen_at.isoformat() if device.last_seen_at else None,
                    1 if device.is_current_device else 0,
                    device.id,
                ),
            )

    def deactivate_device(self, device_id: int) -> Result[Device]:
        """
        Desactiva un dispositivo (inicia cooldown).

        Args:
            device_id: ID del dispositivo a desactivar

        Returns:
            Result con el dispositivo actualizado
        """
        db = self._get_db()
        row = db.fetchone("SELECT * FROM devices WHERE id = ?", (device_id,))
        if not row:
            return Result.failure(
                NarrativeError(
                    message=f"Device {device_id} not found",
                    severity=ErrorSeverity.FATAL,
                    user_message="Dispositivo no encontrado.",
                )
            )

        device = Device.from_db_row(row)
        device.status = DeviceStatus.INACTIVE
        device.deactivated_at = datetime.utcnow()
        device.cooldown_ends_at = datetime.utcnow() + timedelta(
            hours=DEVICE_DEACTIVATION_COOLDOWN_HOURS
        )
        device.is_current_device = False

        self._update_device(device)
        logger.info(
            f"Dispositivo desactivado: {device.device_name}. "
            f"Cooldown hasta: {device.cooldown_ends_at}"
        )

        return Result.success(device)

    # =========================================================================
    # Gestion de Cuotas
    # =========================================================================

    def _calculate_quota_remaining(self, license_obj: License) -> Optional[int]:
        """Calcula manuscritos restantes en el periodo actual."""
        limits = license_obj.limits
        if limits.max_manuscripts_per_month == 0:
            return None  # Ilimitado

        billing_period = UsageRecord.current_billing_period()
        db = self._get_db()

        row = db.fetchone(
            """
            SELECT COUNT(*) as count FROM usage_records
            WHERE license_id = ? AND billing_period = ? AND counted_for_quota = 1
            """,
            (license_obj.id, billing_period),
        )

        used = row["count"] if row else 0
        remaining = limits.max_manuscripts_per_month - used

        return max(0, remaining)

    def check_quota(self, license_obj: Optional[License] = None) -> Result[int]:
        """
        Verifica si hay cuota disponible.

        Args:
            license_obj: Licencia a verificar (usa cache si None)

        Returns:
            Result con manuscritos restantes
        """
        if license_obj is None:
            license_obj = get_cached_license()
            if license_obj is None:
                return Result.failure(LicenseNotFoundError())

        remaining = self._calculate_quota_remaining(license_obj)
        if remaining is None:
            return Result.success(-1)  # Ilimitado

        if remaining <= 0:
            return Result.failure(
                QuotaExceededError(
                    current_usage=license_obj.limits.max_manuscripts_per_month,
                    max_usage=license_obj.limits.max_manuscripts_per_month,
                    billing_period=UsageRecord.current_billing_period(),
                )
            )

        return Result.success(remaining)

    def record_usage(
        self,
        project_id: int,
        document_fingerprint: str,
        document_name: str,
        word_count: int,
    ) -> Result[UsageRecord]:
        """
        Registra uso de un manuscrito.

        Args:
            project_id: ID del proyecto
            document_fingerprint: Fingerprint del documento
            document_name: Nombre del documento
            word_count: Conteo de palabras

        Returns:
            Result con el registro de uso
        """
        license_obj = get_cached_license()
        if license_obj is None:
            return Result.failure(LicenseNotFoundError())

        # Verificar si ya existe registro para este documento en este periodo
        billing_period = UsageRecord.current_billing_period()
        db = self._get_db()

        existing = db.fetchone(
            """
            SELECT id FROM usage_records
            WHERE license_id = ? AND document_fingerprint = ? AND billing_period = ?
            """,
            (license_obj.id, document_fingerprint, billing_period),
        )

        if existing:
            # Ya registrado, actualizar
            db.execute(
                """
                UPDATE usage_records SET
                    analysis_completed_at = ?,
                    word_count = ?
                WHERE id = ?
                """,
                (datetime.utcnow().isoformat(), word_count, existing["id"]),
            )
            return Result.success(
                UsageRecord(
                    id=existing["id"],
                    license_id=license_obj.id,
                    project_id=project_id,
                    document_fingerprint=document_fingerprint,
                    document_name=document_name,
                    word_count=word_count,
                    billing_period=billing_period,
                )
            )

        # Nuevo registro
        record = UsageRecord(
            license_id=license_obj.id,
            project_id=project_id,
            document_fingerprint=document_fingerprint,
            document_name=document_name,
            word_count=word_count,
            analysis_started_at=datetime.utcnow(),
            billing_period=billing_period,
            counted_for_quota=True,
        )

        with db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO usage_records (
                    license_id, project_id, document_fingerprint, document_name,
                    word_count, analysis_started_at, billing_period, counted_for_quota
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.license_id,
                    record.project_id,
                    record.document_fingerprint,
                    record.document_name,
                    record.word_count,
                    record.analysis_started_at.isoformat(),
                    record.billing_period,
                    1,
                ),
            )
            record.id = cursor.lastrowid

        logger.info(f"Uso registrado: {document_name} ({word_count} palabras)")
        return Result.success(record)

    # =========================================================================
    # Verificacion de Modulos
    # =========================================================================

    def check_module(
        self,
        module: LicenseModule,
        license_obj: Optional[License] = None,
    ) -> Result[bool]:
        """
        Verifica si un modulo esta disponible.

        Args:
            module: Modulo a verificar
            license_obj: Licencia (usa cache si None)

        Returns:
            Result con True si disponible
        """
        if license_obj is None:
            license_obj = get_cached_license()
            if license_obj is None:
                return Result.failure(LicenseNotFoundError())

        if not license_obj.has_module(module):
            return Result.failure(ModuleNotLicensedError(module=module))

        return Result.success(True)

    # =========================================================================
    # Persistencia Local
    # =========================================================================

    def _load_local_license(self) -> Result[License]:
        """Carga licencia desde BD local."""
        db = self._get_db()

        row = db.fetchone(
            """
            SELECT * FROM licenses
            WHERE status != 'cancelled'
            ORDER BY created_at DESC
            LIMIT 1
            """
        )

        if not row:
            return Result.failure(LicenseNotFoundError())

        license_obj = License.from_db_row(row)

        # Cargar suscripcion
        sub_row = db.fetchone(
            "SELECT * FROM subscriptions WHERE license_id = ?",
            (license_obj.id,),
        )
        if sub_row:
            license_obj.subscription = Subscription.from_db_row(sub_row)

        # Cargar dispositivos
        device_rows = db.fetchall(
            "SELECT * FROM devices WHERE license_id = ?",
            (license_obj.id,),
        )
        license_obj.devices = [Device.from_db_row(r) for r in device_rows]

        return Result.success(license_obj)

    def _save_local_license(self, license_obj: License) -> None:
        """Guarda licencia en BD local."""
        db = self._get_db()

        with db.transaction() as conn:
            if license_obj.id:
                conn.execute(
                    """
                    UPDATE licenses SET
                        tier = ?,
                        bundle = ?,
                        status = ?,
                        last_verified_at = ?,
                        grace_period_ends_at = ?,
                        extra_data = ?
                    WHERE id = ?
                    """,
                    (
                        license_obj.tier.value,
                        license_obj.bundle.value,
                        license_obj.status.value,
                        license_obj.last_verified_at.isoformat() if license_obj.last_verified_at else None,
                        license_obj.grace_period_ends_at.isoformat() if license_obj.grace_period_ends_at else None,
                        json.dumps(license_obj.extra_data),
                        license_obj.id,
                    ),
                )
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO licenses (
                        license_key, user_email, user_name, tier, bundle,
                        status, created_at, activated_at, last_verified_at,
                        grace_period_ends_at, extra_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        license_obj.license_key,
                        license_obj.user_email,
                        license_obj.user_name,
                        license_obj.tier.value,
                        license_obj.bundle.value,
                        license_obj.status.value,
                        license_obj.created_at.isoformat() if license_obj.created_at else datetime.utcnow().isoformat(),
                        license_obj.activated_at.isoformat() if license_obj.activated_at else None,
                        license_obj.last_verified_at.isoformat() if license_obj.last_verified_at else None,
                        license_obj.grace_period_ends_at.isoformat() if license_obj.grace_period_ends_at else None,
                        json.dumps(license_obj.extra_data),
                    ),
                )
                license_obj.id = cursor.lastrowid

    def activate_license(self, license_key: str) -> Result[License]:
        """
        Activa una nueva licencia.

        Args:
            license_key: Clave de licencia

        Returns:
            Result con la licencia activada
        """
        try:
            import urllib.request
            import urllib.error

            fingerprint = self._get_current_fingerprint()
            hw_info_result = get_hardware_info()
            hw_info = hw_info_result.value if hw_info_result.is_success else None

            # Request al servidor
            url = urljoin(self._license_server, "/activate")
            data = json.dumps({
                "license_key": license_key,
                "device_fingerprint": fingerprint,
                "device_name": hw_info.device_name if hw_info else "Unknown",
                "os_info": hw_info.os_info if hw_info else "Unknown",
            }).encode("utf-8")

            request = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )

            with urllib.request.urlopen(request, timeout=15) as response:
                response_data = json.loads(response.read().decode("utf-8"))

            if not response_data.get("success"):
                return Result.failure(
                    NarrativeError(
                        message=response_data.get("error", "Activation failed"),
                        severity=ErrorSeverity.FATAL,
                        user_message=response_data.get(
                            "message",
                            "No se pudo activar la licencia. Verifica la clave."
                        ),
                    )
                )

            # Crear licencia local
            license_data = response_data.get("license", {})
            license_obj = License(
                license_key=license_key,
                user_email=license_data.get("email", ""),
                user_name=license_data.get("name", ""),
                tier=LicenseTier(license_data.get("tier", "freelance")),
                bundle=LicenseBundle(license_data.get("bundle", "solo_core")),
                status=LicenseStatus.ACTIVE,
                created_at=datetime.utcnow(),
                activated_at=datetime.utcnow(),
                last_verified_at=datetime.utcnow(),
            )

            # Guardar
            self._save_local_license(license_obj)

            # Registrar dispositivo
            self._register_device(license_obj, fingerprint)

            logger.info(f"Licencia activada: {license_obj.tier.display_name}")
            return Result.success(license_obj)

        except urllib.error.URLError as e:
            return Result.failure(
                NarrativeError(
                    message=f"Cannot connect to license server: {e}",
                    severity=ErrorSeverity.FATAL,
                    user_message=(
                        "No se pudo conectar al servidor de licencias. "
                        "Verifica tu conexion a internet."
                    ),
                )
            )
        except Exception as e:
            logger.exception("Error activando licencia")
            return Result.failure(
                NarrativeError(
                    message=f"License activation failed: {e}",
                    severity=ErrorSeverity.FATAL,
                    user_message="Error al activar la licencia.",
                )
            )


# =============================================================================
# Funciones Publicas
# =============================================================================


def get_cached_license() -> Optional[License]:
    """Obtiene la licencia cacheada (thread-safe)."""
    with _license_lock:
        return _cached_license


def verify_license(force_online: bool = False) -> Result[VerificationResult]:
    """
    Verifica el estado de la licencia actual.

    Args:
        force_online: Forzar verificacion online

    Returns:
        Result con VerificationResult
    """
    verifier = LicenseVerifier()
    return verifier.verify(force_online=force_online)


def activate_license(license_key: str) -> Result[License]:
    """
    Activa una nueva licencia.

    Args:
        license_key: Clave de licencia

    Returns:
        Result con la licencia activada
    """
    verifier = LicenseVerifier()
    return verifier.activate_license(license_key)


def check_module_access(module: LicenseModule) -> Result[bool]:
    """
    Verifica si un modulo esta disponible.

    Args:
        module: Modulo a verificar

    Returns:
        Result con True si disponible
    """
    verifier = LicenseVerifier()
    return verifier.check_module(module)


def check_quota() -> Result[int]:
    """
    Verifica la cuota de manuscritos restante.

    Returns:
        Result con manuscritos restantes (-1 si ilimitado)
    """
    verifier = LicenseVerifier()
    return verifier.check_quota()


def record_manuscript_usage(
    project_id: int,
    document_fingerprint: str,
    document_name: str,
    word_count: int,
) -> Result[UsageRecord]:
    """
    Registra el uso de un manuscrito.

    Args:
        project_id: ID del proyecto
        document_fingerprint: Fingerprint del documento
        document_name: Nombre del documento
        word_count: Conteo de palabras

    Returns:
        Result con el registro de uso
    """
    verifier = LicenseVerifier()
    return verifier.record_usage(
        project_id=project_id,
        document_fingerprint=document_fingerprint,
        document_name=document_name,
        word_count=word_count,
    )


def deactivate_device(device_id: int) -> Result[Device]:
    """
    Desactiva un dispositivo (inicia cooldown de 48h).

    Args:
        device_id: ID del dispositivo

    Returns:
        Result con el dispositivo actualizado
    """
    verifier = LicenseVerifier()
    return verifier.deactivate_device(device_id)


def get_license_info() -> Optional[dict]:
    """
    Obtiene informacion de la licencia para mostrar al usuario.

    Returns:
        Dict con informacion de licencia o None si no hay licencia
    """
    license_obj = get_cached_license()
    if license_obj is None:
        result = verify_license()
        if result.is_failure:
            return None
        license_obj = result.value.license

    if license_obj is None:
        return None

    verifier = LicenseVerifier()
    quota = verifier._calculate_quota_remaining(license_obj)

    return {
        "tier": license_obj.tier.display_name,
        "bundle": license_obj.bundle.display_name,
        "status": license_obj.status.value,
        "user_email": license_obj.user_email,
        "user_name": license_obj.user_name,
        "modules": [m.display_name for m in license_obj.modules],
        "devices": {
            "active": license_obj.active_device_count,
            "max": license_obj.limits.max_devices,
        },
        "quota": {
            "remaining": quota,
            "max": license_obj.limits.max_manuscripts_per_month,
            "unlimited": license_obj.limits.max_manuscripts_per_month == 0,
        },
        "offline": {
            "is_offline": license_obj.is_in_grace_period,
            "days_remaining": (
                license_obj.grace_period_remaining.days
                if license_obj.grace_period_remaining
                else None
            ),
        },
    }
