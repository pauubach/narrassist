# Auditoría de Dependencias Locales, Arranque y Fallbacks

Fecha: 2026-03-08

## 1. Objetivo

Revisar de forma específica el ciclo de vida de dependencias locales críticas de la app desktop:

- backend Python embebido
- dependencias Python/NLP
- modelos NLP locales
- Ollama
- modelos LLM de Ollama
- LanguageTool
- Java requerido por LanguageTool

La revisión cubre:

- instalación mediante `exe` / `dmg`
- primera ejecución
- ejecuciones sucesivas
- arranque del backend y sidecar
- revalidación antes de analizar
- degradación controlada y fallbacks
- comportamiento ante fallos, desinstalaciones o reinicios parciales

## 2. Veredicto ejecutivo

Estado actual tras el hardening:

- el producto **no empaqueta** dentro del instalador final todos los motores pesados externos (`Ollama`, `LanguageTool`, `Java`) como artefactos ya listos para usar
- pero sí tiene ahora un flujo consistente para que queden listos **en la primera ejecución** o en aperturas posteriores si faltan
- en cada arranque de la app Tauri, el flujo inicial:
  - espera a que el backend local responda
  - comprueba modelos NLP
  - prepara servicios avanzados
  - instala o inicia `LanguageTool` si hace falta
  - instala o inicia `Ollama` si hace falta
  - descarga modelos LLM si el motor ya está operativo
- en runtime, antes de aplicar métodos NLP dependientes de servicios externos:
  - se intenta **autoarrancar** `Ollama`
  - se intenta **autoarrancar** `LanguageTool`
  - si siguen indisponibles, se filtran esos métodos y el análisis continúa con capacidad reducida

Conclusión:

- el sistema queda razonablemente robusto para una app local
- el objetivo de “no fallar silenciosamente” queda mucho mejor cubierto
- el hueco que queda no es de crash fácil, sino de política:
  - no se fuerza una instalación pesada nueva en mitad de un análisis ya lanzado
  - en ese punto se prioriza fallback y warning, no reparación invasiva en caliente

## 3. Inventario de dependencias y política aplicada

### 3.1 Backend Python y dependencias Python

- Base: el instalador desktop ya despliega el backend embebido
- Si faltan dependencias Python o el backend aún no está cargado:
  - el diálogo de configuración inicial dispara instalación de dependencias
  - el usuario recibe progreso y mensajes no técnicos
- Si algo falla:
  - el diálogo entra en error visible
  - no queda fallo silencioso

Cobertura actual:

- primera ejecución: sí
- ejecuciones sucesivas: sí, mediante recheck de estado
- reanálisis: sí, porque el backend ya debe estar operativo antes de aceptar la corrida

### 3.2 Modelos NLP locales

- Se descargan desde el flujo inicial si no están disponibles
- La UI muestra progreso real de descarga
- El flujo se revalida cada vez que la app se abre y el estado no está completo

Cobertura actual:

- primera ejecución: sí
- siguientes ejecuciones: sí
- falta o corrupción parcial: reintenta descarga / muestra error

### 3.3 LanguageTool + Java

- `LanguageTool` no se considera preinstalado de forma garantizada por el instalador
- El sistema lo prepara en app startup si falta:
  - instala `LanguageTool`
  - instala `Java` si no existe
  - inicia el servidor si está instalado pero parado
- En runtime del pipeline:
  - se vuelve a intentar autoarranque antes de descartar métodos `languagetool`

Cobertura actual:

- primera ejecución: sí
- aperturas posteriores: sí
- servicio parado: sí, auto-start
- Java ausente: sí, durante instalación de LT
- caída posterior del servicio: sí, se intenta reactivar; si no, fallback

### 3.4 Ollama

- `Ollama` tampoco se da por empaquetado como binario funcional garantizado dentro del instalador
- El flujo inicial ahora:
  - instala `Ollama` si no está
  - lo inicia si está instalado pero parado
- En runtime del pipeline:
  - se intenta autoarranque antes de descartar métodos dependientes de LLM
- Si el motor está listo pero faltan modelos:
  - se descargan modelos LLM desde el mismo flujo inicial

Cobertura actual:

- primera ejecución: sí
- aperturas posteriores: sí
- servicio parado: sí, auto-start
- modelos ausentes: sí, descarga posterior
- caída posterior del servicio: sí, reintento de arranque y fallback

## 4. Cobertura por fase del ciclo de vida

### 4.1 Instalación del `exe` / `dmg`

Estado actual:

- se instala la app desktop y el backend local
- no se garantiza que `Ollama`, `LanguageTool` y `Java` queden ya operativos dentro del instalador
- la política real es:
  - instalador ligero y seguro
  - preparación de dependencias pesadas en primera ejecución

Evaluación:

- esto cumple el requisito funcional si la primera ejecución es robusta y no silenciosa
- no equivale a “todo prebundled”, pero sí a “todo listo antes de usar”

### 4.2 Primera ejecución

Cobertura actual:

- espera activa del backend
- comprobación de modelos NLP
- instalación de dependencias Python si falta algo
- preparación de servicios avanzados
- instalación/arranque de `LanguageTool`
- instalación/arranque de `Ollama`
- descarga de modelos LLM si procede
- notificación final:
  - completa
  - parcial con warnings

### 4.3 Aperturas posteriores

Cobertura actual:

- `ModelSetupDialog` se monta en Tauri en cada apertura
- si el núcleo NLP ya está listo:
  - no se cierra directamente
  - antes prepara otra vez servicios avanzados
- esto permite reparar escenarios como:
  - servicio detenido entre sesiones
  - desinstalación externa entre una ejecución y otra
  - actualización parcial o corrupción de herramientas

### 4.4 Justo antes del análisis

Cobertura actual:

- el pipeline backend vuelve a comprobar servicios runtime
- para métodos dependientes de `Ollama` o `LanguageTool`:
  - intenta autoarrancar
  - solo después decide si el método es viable
- si sigue sin estar disponible:
  - el método se filtra
  - se registran warnings de capacidad reducida

### 4.5 Durante el análisis ya lanzado

Política actual:

- se permite autoarranque de servicio parado
- no se fuerza instalación pesada nueva a mitad del análisis
- si el servicio no puede reactivarse:
  - se desactivan métodos afectados
  - el análisis continúa con fallback

Esta decisión es deliberada:

- instalar `Ollama` o `LanguageTool` en caliente durante una corrida larga es demasiado invasivo
- aumenta riesgo de bloqueo, latencia extrema y estados ambiguos
- para una app local, es más seguro degradar con warning que congelar la corrida

## 5. Hardening aplicado en esta iteración

### 5.1 Frontend de arranque

`frontend/src/stores/system.ts`

- nueva preparación explícita de servicios avanzados:
  - `prepareAdvancedServicesOnStartup()`
- intenta:
  - instalar `LanguageTool` si falta
  - iniciar `LanguageTool` si está parado
  - instalar `Ollama` si falta
  - iniciar `Ollama` si está parado
- devuelve estado resumido:
  - `warnings`
  - `ollamaReady`
  - `languagetoolReady`

`frontend/src/components/ModelSetupDialog.vue`

- el diálogo ya no cierra al detectar solo modelos NLP listos
- ahora encadena:
  - `ensureAutoConfigReady()`
  - `prepareAdvancedServicesOnStartup()`
  - `LLM readiness`
  - descarga de modelos LLM si faltan
- nueva fase visible:
  - `preparing-services`
- notificación final diferenciada:
  - instalación completa
  - instalación parcial con fallback
- deduplicación de `continueWithAdvancedSetup()` para evitar doble ejecución concurrente

### 5.2 Backend runtime

`api-server/routers/_analysis_runtime.py`

- antes:
  - `Ollama` se evaluaba con `is_ollama_available()`
  - `LanguageTool` se evaluaba con `_check_languagetool_available()` sin autoarranque
- ahora:
  - `Ollama` se valida con `ensure_ollama_ready(start_if_stopped=True, install_if_missing=False)`
  - `LanguageTool` se valida con `_check_languagetool_available(auto_start=True)`

Impacto:

- se evita filtrar prematuramente métodos válidos solo porque el servicio estaba parado
- el sistema intenta recuperar servicio antes de degradar

## 6. Tests añadidos o actualizados

Frontend:

- `frontend/src/stores/__tests__/system.spec.ts`
  - cobertura de `prepareAdvancedServicesOnStartup()`
  - casos:
    - LT faltante con warning
    - LT parado con auto-start
    - Ollama faltante + arranque posterior
    - Ollama parado con warning si no arranca
- `frontend/src/components/__tests__/ModelSetupDialog.spec.ts`
  - preparación avanzada al montar con `modelsReady`
  - preparación avanzada tras `retryStartup`
  - preparación avanzada tras `recheckPython`
  - notificación de instalación parcial

Backend:

- `tests/unit/test_analysis_runtime.py`
  - confirma autoarranque de `Ollama`
  - confirma autoarranque de `LanguageTool`

Además se ha revalidado:

- `tests/unit/test_cr03_runtime_settings.py`

## 7. Casos extremos revisados

### 7.1 Usuario abre la app y el backend tarda en estar listo

Cobertura:

- espera activa con timeout
- error visible si el backend no responde
- no queda spinner “muerto” sin información

### 7.2 Usuario abre la app y faltan dependencias Python/NLP

Cobertura:

- se instala o descarga desde el flujo inicial
- hay progreso y error visible

### 7.3 Usuario abre la app y falta `LanguageTool` / `Java`

Cobertura:

- se intenta instalar `LanguageTool`
- su propio instalador cubre `Java`
- si falla, el usuario recibe warning comprensible y la app sigue con revisión básica

### 7.4 Usuario abre la app y falta `Ollama`

Cobertura:

- se intenta instalar
- si falla, la app sigue con análisis básico y avisa

### 7.5 Servicio instalado pero detenido

Cobertura:

- app startup: sí
- runtime pipeline: sí

### 7.6 Usuario desinstala una dependencia entre sesiones

Cobertura:

- la siguiente apertura vuelve a detectarlo
- se intenta reinstalar o reactivar

### 7.7 Usuario desinstala o rompe una dependencia con la app abierta

Cobertura:

- el arranque actual ya no lo ve porque la sesión ya está iniciada
- en el siguiente análisis:
  - el backend intenta autoarranque
  - si no puede, filtra el método y degrada con warnings

Evaluación:

- no hay garantía razonable de “reinstalación transparente instantánea” a mitad de una sesión ya abierta
- sí hay garantía de no fallo silencioso y de degradación segura

### 7.8 Red caída / sin Internet durante primera ejecución

Cobertura:

- dependencias externas pesadas pueden no instalarse
- el flujo informa del fallo
- la app queda utilizable con capacidad reducida si lo demás está listo

### 7.9 Cierre de app durante instalación

Cobertura:

- en la siguiente apertura se reevalúa el estado real
- no depende de un flag ciego “ya instalado”

### 7.10 Servicio cae entre fases del análisis

Cobertura:

- solo parcial
- el runtime filtra antes de arrancar fases dependientes, no a mitad exacta de una fase ya ejecutándose

Evaluación:

- esto es aceptable para el producto actual
- endurecer recuperación dentro de subfase concreta sería un bloque distinto de resiliencia fina

## 8. Fallbacks efectivos hoy

Fallbacks confirmados:

- sin `Ollama`:
  - desactivar métodos LLM
  - seguir con heurísticas / reglas / métodos no LLM
- sin `LanguageTool`:
  - seguir con reglas locales / revisión básica
- sin modelos LLM descargados:
  - descargar si el motor está listo
  - si no se puede, degradación controlada
- sin red:
  - no se completa la preparación pesada
  - no se produce fallo silencioso

## 9. Riesgos residuales reales

No quedan riesgos P0 visibles en este bloque, pero sí estos límites estructurales:

1. `Ollama`, `LanguageTool` y `Java` no quedan completamente preinstalados desde el instalador final.
   - Política actual: preparación en primera ejecución y aperturas posteriores.

2. No se fuerza instalación pesada nueva en mitad de un análisis ya lanzado.
   - Política actual: auto-start si está instalado; si no, fallback.

3. La recuperación “ultrafina” si el usuario rompe dependencias exactamente durante una subfase interna no está garantizada.
   - El sistema protege mejor el arranque del análisis que la autocuración en caliente dentro de una fase ya en ejecución.

## 10. Recomendación de cierre

Este bloque puede considerarse **cerrado funcionalmente** con la siguiente formulación:

- dependencias críticas locales revisadas en:
  - instalación
  - primera ejecución
  - aperturas sucesivas
  - runtime previo al análisis
- auto-start implementado para servicios ya instalados
- auto-install implementado en arranque inicial/sucesivo para servicios avanzados faltantes
- fallbacks y warnings visibles en lugar de fallos silenciosos

El siguiente escalón, si se quiere seguir endureciendo, ya sería otro sprint:

- reparación de dependencias “en caliente” dentro de corridas ya iniciadas
- ejecución automática del smoke sobre artefactos empaquetados reales en todos los runners de release
- observabilidad unificada de warnings runtime de capacidad reducida a nivel UX final
