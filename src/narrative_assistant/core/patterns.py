"""
Patrones de diseño reutilizables.

Este módulo proporciona decorators y utilidades para patrones comunes
como Singleton, evitando duplicación de código boilerplate.
"""

import threading
from functools import wraps
from typing import Callable, TypeVar

T = TypeVar("T")


class SingletonMeta(type):
    """
    Metaclase para singleton thread-safe.

    Uso:
        class MyClass(metaclass=SingletonMeta):
            def __init__(self, config=None):
                self.config = config

        # Obtener instancia
        instance = MyClass.get_instance()

        # Con argumentos (solo la primera vez)
        instance = MyClass.get_instance(config=my_config)

        # Reset (para testing)
        MyClass.reset_instance()
    """

    _instances: dict[type, object] = {}
    _locks: dict[type, threading.Lock] = {}
    _init_locks_lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        """
        Crear/obtener instancia singleton.

        Advertencia: Los argumentos solo se usan en la primera creación.
        Llamadas subsecuentes ignoran los argumentos.
        """
        if cls not in cls._locks:
            with cls._init_locks_lock:
                if cls not in cls._locks:
                    cls._locks[cls] = threading.Lock()

        if cls not in cls._instances:
            with cls._locks[cls]:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance

        return cls._instances[cls]

    def get_instance(cls, *args, **kwargs) -> T:
        """Alias explícito para obtener la instancia singleton."""
        return cls(*args, **kwargs)

    def reset_instance(cls) -> None:
        """Reset la instancia singleton (para testing)."""
        if cls in cls._locks:
            with cls._locks[cls]:
                cls._instances.pop(cls, None)
        else:
            cls._instances.pop(cls, None)

    def has_instance(cls) -> bool:
        """Verificar si ya existe una instancia."""
        return cls in cls._instances


def singleton(cls: type[T]) -> type[T]:
    """
    Decorator para convertir una clase en singleton thread-safe.

    Uso simple:
        @singleton
        class MyService:
            def __init__(self):
                pass

        # Obtener instancia
        service = MyService()

        # Reset (para testing)
        MyService.reset_instance()

    El decorator añade:
        - get_instance(): Alias para obtener instancia
        - reset_instance(): Reset para testing
        - has_instance(): Verificar si existe instancia
    """
    _instance = None
    _lock = threading.Lock()
    original_init = cls.__init__

    @wraps(original_init)
    def new_init(self, *args, **kwargs):
        # Solo inicializar si es nueva instancia
        if not getattr(self, "_initialized", False):
            original_init(self, *args, **kwargs)
            self._initialized = True

    def new_call(cls_inner, *args, **kwargs):
        nonlocal _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = object.__new__(cls_inner)
                    _instance._initialized = False
        # Llamar init (que verificará _initialized)
        _instance.__init__(*args, **kwargs)
        return _instance

    def get_instance(*args, **kwargs) -> T:
        """Obtener instancia singleton."""
        return new_call(cls, *args, **kwargs)

    def reset_instance() -> None:
        """Reset la instancia singleton (para testing)."""
        nonlocal _instance
        with _lock:
            _instance = None

    def has_instance() -> bool:
        """Verificar si ya existe una instancia."""
        return _instance is not None

    cls.__init__ = new_init
    cls.__new__ = lambda c, *a, **kw: new_call(c, *a, **kw)
    cls.get_instance = staticmethod(get_instance)
    cls.reset_instance = staticmethod(reset_instance)
    cls.has_instance = staticmethod(has_instance)

    return cls


def lazy_singleton(factory: Callable[[], T]) -> Callable[[], T]:
    """
    Decorator para funciones factory que crean singletons.

    Uso:
        @lazy_singleton
        def get_heavy_resource() -> HeavyResource:
            return HeavyResource()

        # Lazy - solo se crea cuando se necesita
        resource = get_heavy_resource()

        # Reset
        get_heavy_resource.reset()

    Útil cuando:
        - La creación es costosa
        - Se necesita lazy initialization
        - No quieres modificar la clase original
    """
    _instance: T | None = None
    _lock = threading.Lock()

    @wraps(factory)
    def wrapper() -> T:
        nonlocal _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = factory()
        return _instance

    def reset() -> None:
        """Reset la instancia singleton."""
        nonlocal _instance
        with _lock:
            _instance = None

    def has_instance() -> bool:
        """Verificar si ya existe una instancia."""
        return _instance is not None

    wrapper.reset = reset
    wrapper.has_instance = has_instance

    return wrapper
