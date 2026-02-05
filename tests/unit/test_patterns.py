"""
Tests unitarios para el módulo de patrones de diseño.

Verifica que el decorator @singleton y utilidades relacionadas
funcionen correctamente en escenarios thread-safe.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest


class TestSingletonDecorator:
    """Tests para el decorator @singleton."""

    def test_singleton_returns_same_instance(self):
        """Instancias múltiples son la misma."""
        from narrative_assistant.core.patterns import singleton

        @singleton
        class TestClass:
            def __init__(self):
                self.value = 42

        instance1 = TestClass()
        instance2 = TestClass()

        assert instance1 is instance2
        assert instance1.value == 42

        # Cleanup
        TestClass.reset_instance()

    def test_singleton_get_instance(self):
        """get_instance retorna la misma instancia."""
        from narrative_assistant.core.patterns import singleton

        @singleton
        class TestService:
            pass

        instance1 = TestService.get_instance()
        instance2 = TestService.get_instance()

        assert instance1 is instance2

        TestService.reset_instance()

    def test_singleton_reset_instance(self):
        """reset_instance crea nueva instancia."""
        from narrative_assistant.core.patterns import singleton

        @singleton
        class Counter:
            def __init__(self):
                self.count = 0

        instance1 = Counter()
        instance1.count = 10

        Counter.reset_instance()

        instance2 = Counter()
        assert instance2.count == 0
        assert instance1 is not instance2

        Counter.reset_instance()

    def test_singleton_has_instance(self):
        """has_instance refleja estado correctamente."""
        from narrative_assistant.core.patterns import singleton

        @singleton
        class Service:
            pass

        assert not Service.has_instance()

        _ = Service()
        assert Service.has_instance()

        Service.reset_instance()
        assert not Service.has_instance()

    def test_singleton_thread_safe(self):
        """Singleton es thread-safe."""
        from narrative_assistant.core.patterns import singleton

        @singleton
        class SlowInit:
            def __init__(self):
                time.sleep(0.01)  # Simular inicialización lenta
                self.initialized_at = time.time()

        instances = []
        errors = []

        def get_instance():
            try:
                instances.append(SlowInit())
            except Exception as e:
                errors.append(e)

        # Crear muchos threads que intentan obtener instancia simultáneamente
        threads = [threading.Thread(target=get_instance) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors: {errors}"
        assert len(instances) == 20

        # Todas las instancias deben ser la misma
        first = instances[0]
        for inst in instances:
            assert inst is first

        SlowInit.reset_instance()

    def test_singleton_init_called_once(self):
        """__init__ solo se ejecuta una vez."""
        from narrative_assistant.core.patterns import singleton

        call_count = 0

        @singleton
        class Tracked:
            def __init__(self):
                nonlocal call_count
                call_count += 1

        Tracked()
        Tracked()
        Tracked()

        assert call_count == 1

        Tracked.reset_instance()

    def test_singleton_with_arguments(self):
        """Argumentos solo se usan en primera creación."""
        from narrative_assistant.core.patterns import singleton

        @singleton
        class Configurable:
            def __init__(self, value=None):
                self.value = value

        instance1 = Configurable(value="first")
        instance2 = Configurable(value="second")  # Ignorado

        assert instance1.value == "first"
        assert instance2.value == "first"
        assert instance1 is instance2

        Configurable.reset_instance()


class TestLazySingleton:
    """Tests para el decorator @lazy_singleton."""

    def test_lazy_singleton_basic(self):
        """lazy_singleton crea instancia bajo demanda."""
        from narrative_assistant.core.patterns import lazy_singleton

        created = False

        @lazy_singleton
        def get_resource():
            nonlocal created
            created = True
            return {"data": 42}

        assert not created
        assert not get_resource.has_instance()

        result = get_resource()
        assert created
        assert get_resource.has_instance()
        assert result["data"] == 42

        get_resource.reset()

    def test_lazy_singleton_same_instance(self):
        """lazy_singleton retorna misma instancia."""
        from narrative_assistant.core.patterns import lazy_singleton

        @lazy_singleton
        def get_service():
            return object()

        instance1 = get_service()
        instance2 = get_service()

        assert instance1 is instance2

        get_service.reset()

    def test_lazy_singleton_reset(self):
        """lazy_singleton reset crea nueva instancia."""
        from narrative_assistant.core.patterns import lazy_singleton

        counter = [0]

        @lazy_singleton
        def get_counter():
            counter[0] += 1
            return counter[0]

        first = get_counter()
        assert first == 1

        get_counter.reset()

        second = get_counter()
        assert second == 2

        get_counter.reset()

    def test_lazy_singleton_thread_safe(self):
        """lazy_singleton es thread-safe."""
        from narrative_assistant.core.patterns import lazy_singleton

        init_count = [0]

        @lazy_singleton
        def get_heavy():
            init_count[0] += 1
            time.sleep(0.01)
            return {"id": init_count[0]}

        results = []

        def fetch():
            results.append(get_heavy())

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch) for _ in range(20)]
            for f in futures:
                f.result()

        # Solo debe haberse inicializado una vez
        assert init_count[0] == 1
        assert all(r["id"] == 1 for r in results)

        get_heavy.reset()


class TestSingletonMeta:
    """Tests para SingletonMeta metaclass."""

    def test_meta_basic(self):
        """SingletonMeta crea singleton."""
        from narrative_assistant.core.patterns import SingletonMeta

        class MyClass(metaclass=SingletonMeta):
            def __init__(self, value=None):
                self.value = value

        instance1 = MyClass(value=1)
        instance2 = MyClass(value=2)

        assert instance1 is instance2
        assert instance1.value == 1  # Segundo valor ignorado

        MyClass.reset_instance()

    def test_meta_get_instance(self):
        """SingletonMeta.get_instance funciona."""
        from narrative_assistant.core.patterns import SingletonMeta

        class Service(metaclass=SingletonMeta):
            pass

        instance = Service.get_instance()
        assert instance is Service()

        Service.reset_instance()

    def test_meta_has_instance(self):
        """SingletonMeta.has_instance funciona."""
        from narrative_assistant.core.patterns import SingletonMeta

        class Checker(metaclass=SingletonMeta):
            pass

        assert not Checker.has_instance()
        _ = Checker()
        assert Checker.has_instance()
        Checker.reset_instance()
        assert not Checker.has_instance()

    def test_meta_thread_safe(self):
        """SingletonMeta es thread-safe."""
        from narrative_assistant.core.patterns import SingletonMeta

        class SlowService(metaclass=SingletonMeta):
            def __init__(self):
                time.sleep(0.01)

        instances = []

        def get():
            instances.append(SlowService())

        threads = [threading.Thread(target=get) for _ in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        first = instances[0]
        assert all(i is first for i in instances)

        SlowService.reset_instance()

    def test_meta_multiple_classes(self):
        """SingletonMeta funciona con múltiples clases."""
        from narrative_assistant.core.patterns import SingletonMeta

        class ClassA(metaclass=SingletonMeta):
            name = "A"

        class ClassB(metaclass=SingletonMeta):
            name = "B"

        a1 = ClassA()
        a2 = ClassA()
        b1 = ClassB()
        b2 = ClassB()

        assert a1 is a2
        assert b1 is b2
        assert a1 is not b1
        assert a1.name == "A"
        assert b1.name == "B"

        ClassA.reset_instance()
        ClassB.reset_instance()
