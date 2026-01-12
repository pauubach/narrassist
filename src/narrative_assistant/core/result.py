"""
Result Pattern para operaciones que pueden tener éxitos parciales.

Ejemplo de uso:
    result = run_ner_pipeline(document)
    if result.is_success:
        print(f"Entidades: {len(result.value.entities)}")
    if result.is_partial:
        for error in result.errors:
            print(f"Advertencia: {error.user_message}")
"""

from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar, Optional

from .errors import NarrativeError, ErrorSeverity

T = TypeVar("T")
U = TypeVar("U")


@dataclass
class Result(Generic[T]):
    """
    Resultado de una operación que puede tener éxitos parciales.

    Attributes:
        value: Resultado de la operación (si hay éxito)
        errors: Lista de errores encontrados
        warnings: Advertencias que no son errores
    """

    value: Optional[T] = None
    errors: list[NarrativeError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        """True si no hay errores fatales."""
        return not any(e.severity == ErrorSeverity.FATAL for e in self.errors)

    @property
    def is_partial(self) -> bool:
        """True si hay errores recuperables (éxito parcial)."""
        return any(e.severity == ErrorSeverity.RECOVERABLE for e in self.errors)

    @property
    def is_degraded(self) -> bool:
        """True si funciona pero con capacidad reducida."""
        return any(e.severity == ErrorSeverity.DEGRADED for e in self.errors)

    @property
    def is_failure(self) -> bool:
        """True si hay al menos un error fatal."""
        return any(e.severity == ErrorSeverity.FATAL for e in self.errors)

    @property
    def fatal_errors(self) -> list[NarrativeError]:
        """Retorna solo los errores fatales."""
        return [e for e in self.errors if e.severity == ErrorSeverity.FATAL]

    @property
    def recoverable_errors(self) -> list[NarrativeError]:
        """Retorna solo los errores recuperables."""
        return [e for e in self.errors if e.severity == ErrorSeverity.RECOVERABLE]

    @property
    def error(self) -> Optional[NarrativeError]:
        """Retorna el primer error (fatal o cualquiera) si existe."""
        if self.fatal_errors:
            return self.fatal_errors[0]
        return self.errors[0] if self.errors else None

    def add_error(self, error: NarrativeError) -> None:
        """Añade un error al resultado."""
        self.errors.append(error)

    def add_warning(self, message: str) -> None:
        """Añade una advertencia al resultado."""
        self.warnings.append(message)

    def merge(self, other: "Result") -> "Result[T]":
        """
        Combina este resultado con otro.

        Útil para agregar resultados de operaciones paralelas.
        """
        merged = Result(value=self.value if self.value is not None else other.value)
        merged.errors = self.errors + other.errors
        merged.warnings = self.warnings + other.warnings
        return merged

    @classmethod
    def success(cls, value: T) -> "Result[T]":
        """Crea un resultado exitoso."""
        return cls(value=value)

    @classmethod
    def failure(cls, error: NarrativeError) -> "Result[T]":
        """Crea un resultado fallido."""
        return cls(errors=[error])

    @classmethod
    def partial(cls, value: T, errors: list[NarrativeError]) -> "Result[T]":
        """Crea un resultado parcialmente exitoso."""
        return cls(value=value, errors=errors)

    def unwrap(self) -> T:
        """
        Retorna el valor o lanza el primer error fatal.

        Raises:
            NarrativeError: Si hay errores fatales
        """
        if self.is_failure:
            raise self.fatal_errors[0]
        if self.value is None:
            raise ValueError("Result has no value")
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Retorna el valor o un valor por defecto si hay error."""
        if self.is_failure or self.value is None:
            return default
        return self.value

    def map(self, func: Callable[[T], U]) -> "Result[U]":
        """
        Aplica una función al valor si existe.

        Útil para transformar resultados sin perder errores/warnings.

        Args:
            func: Función que transforma T en U

        Returns:
            Nuevo Result con el valor transformado
        """
        if self.value is not None and self.is_success:
            try:
                new_value = func(self.value)
                return Result(
                    value=new_value,
                    errors=self.errors.copy(),
                    warnings=self.warnings.copy(),
                )
            except Exception as e:
                new_result: Result[U] = Result(errors=self.errors.copy(), warnings=self.warnings.copy())
                new_result.add_error(
                    NarrativeError(
                        message=str(e),
                        severity=ErrorSeverity.FATAL,
                    )
                )
                return new_result
        return Result(value=None, errors=self.errors.copy(), warnings=self.warnings.copy())

    def __repr__(self) -> str:
        status = "success" if self.is_success else "failure"
        if self.is_partial:
            status = "partial"
        elif self.is_degraded:
            status = "degraded"
        return f"Result({status}, value={self.value}, errors={len(self.errors)}, warnings={len(self.warnings)})"
