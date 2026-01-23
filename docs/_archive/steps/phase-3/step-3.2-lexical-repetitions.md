# STEP 3.2: Detector de Repeticiones Léxicas

[← Volver a STEPs](../README.md) | [← Índice principal](../../../README.md)

---

## Metadata

| Campo | Valor |
|-------|-------|
| **Complejidad** | M (4-6 horas) |
| **Prioridad** | P1 (Alto valor) |
| **Prerequisitos** | STEP 1.1 |

---

## Descripción

Detectar repeticiones de palabras exactas en ventanas de texto cercanas. Esto ayuda a identificar:
- Repeticiones accidentales que afectan la fluidez
- Muletillas del autor
- Palabras infrecuentes repetidas innecesariamente

---

## Inputs

- Texto procesado por párrafos
- Configuración de ventana (palabras)
- Lista de stopwords a ignorar

---

## Outputs

- `src/narrative_assistant/analysis/lexical_repetitions.py`
- Repeticiones detectadas con posiciones
- Frecuencia por palabra repetida
- Excluir diálogos (configuración opcional)

---

## Algoritmo

1. Tokenizar texto en palabras
2. Ignorar stopwords y palabras cortas
3. Detectar misma palabra en ventana de N palabras
4. Calcular "gravedad" basada en frecuencia esperada
5. Generar alertas ordenadas por gravedad

---

## Implementación

```python
import re
from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional
from collections import defaultdict

@dataclass
class LexicalRepetition:
    word: str
    positions: List[int]  # Posiciones de carácter
    paragraph_ids: List[int]
    distance_words: int  # Distancia en palabras entre ocurrencias
    severity: str  # 'high', 'medium', 'low'
    context: str  # Texto circundante

# Stopwords españolas (palabras funcionales comunes)
SPANISH_STOPWORDS = {
    'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
    'de', 'del', 'al', 'a', 'en', 'con', 'por', 'para',
    'y', 'e', 'o', 'u', 'ni', 'que', 'se', 'su', 'sus',
    'lo', 'le', 'les', 'me', 'te', 'nos', 'os',
    'mi', 'tu', 'él', 'ella', 'ellos', 'ellas', 'nosotros',
    'este', 'esta', 'estos', 'estas', 'ese', 'esa',
    'no', 'sí', 'ya', 'muy', 'más', 'menos', 'tan',
    'pero', 'sin', 'sobre', 'entre', 'hasta', 'desde',
    'como', 'cuando', 'donde', 'quien', 'cual',
    'ser', 'estar', 'haber', 'tener', 'hacer', 'ir',
    'es', 'era', 'fue', 'son', 'eran', 'fueron',
    'ha', 'había', 'han', 'habían', 'he', 'has',
    'tiene', 'tenía', 'tienen', 'tenían',
    'está', 'estaba', 'están', 'estaban',
}

@dataclass
class RepetitionConfig:
    window_size: int = 100  # Palabras
    min_word_length: int = 4
    ignore_dialogue: bool = False
    custom_stopwords: Set[str] = field(default_factory=set)
    severity_thresholds: Dict[str, int] = field(default_factory=lambda: {
        'high': 20,    # Repetición a menos de 20 palabras
        'medium': 50,  # Repetición entre 20-50 palabras
        'low': 100     # Repetición entre 50-100 palabras
    })

class LexicalRepetitionDetector:
    def __init__(self, config: Optional[RepetitionConfig] = None):
        self.config = config or RepetitionConfig()
        self.stopwords = SPANISH_STOPWORDS | self.config.custom_stopwords

    def detect(
        self,
        text: str,
        dialogue_spans: Optional[List[tuple]] = None
    ) -> List[LexicalRepetition]:
        """Detecta repeticiones léxicas en el texto."""
        repetitions = []

        # Tokenizar
        tokens = self._tokenize(text)

        # Filtrar diálogos si está configurado
        if self.config.ignore_dialogue and dialogue_spans:
            tokens = self._filter_dialogue(tokens, dialogue_spans)

        # Agrupar posiciones por palabra
        word_positions: Dict[str, List[dict]] = defaultdict(list)
        for token in tokens:
            if self._should_check(token['word']):
                word_positions[token['word'].lower()].append(token)

        # Buscar repeticiones cercanas
        for word, positions in word_positions.items():
            if len(positions) < 2:
                continue

            for i, pos1 in enumerate(positions):
                for pos2 in positions[i+1:]:
                    distance = pos2['word_index'] - pos1['word_index']

                    if distance <= self.config.window_size:
                        severity = self._calculate_severity(distance)
                        context = self._get_context(
                            text, pos1['char_pos'], pos2['char_pos']
                        )

                        repetitions.append(LexicalRepetition(
                            word=word,
                            positions=[pos1['char_pos'], pos2['char_pos']],
                            paragraph_ids=[pos1.get('para_id', 0), pos2.get('para_id', 0)],
                            distance_words=distance,
                            severity=severity,
                            context=context
                        ))

        # Ordenar por severidad
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        return sorted(repetitions, key=lambda r: (
            severity_order[r.severity],
            r.distance_words
        ))

    def _tokenize(self, text: str) -> List[dict]:
        """Tokeniza texto preservando posiciones."""
        tokens = []
        word_index = 0

        for match in re.finditer(r'\b\w+\b', text):
            tokens.append({
                'word': match.group(),
                'char_pos': match.start(),
                'word_index': word_index
            })
            word_index += 1

        return tokens

    def _should_check(self, word: str) -> bool:
        """Determina si una palabra debe ser verificada."""
        word_lower = word.lower()
        return (
            len(word) >= self.config.min_word_length and
            word_lower not in self.stopwords and
            not word.isdigit()
        )

    def _calculate_severity(self, distance: int) -> str:
        """Calcula severidad basada en distancia."""
        thresholds = self.config.severity_thresholds
        if distance <= thresholds['high']:
            return 'high'
        elif distance <= thresholds['medium']:
            return 'medium'
        else:
            return 'low'

    def _get_context(
        self,
        text: str,
        pos1: int,
        pos2: int,
        context_chars: int = 50
    ) -> str:
        """Extrae contexto alrededor de las repeticiones."""
        start = max(0, pos1 - context_chars)
        end = min(len(text), pos2 + context_chars)
        return text[start:end]

    def _filter_dialogue(
        self,
        tokens: List[dict],
        dialogue_spans: List[tuple]
    ) -> List[dict]:
        """Filtra tokens que están dentro de diálogos."""
        return [
            t for t in tokens
            if not any(start <= t['char_pos'] <= end
                      for start, end in dialogue_spans)
        ]

    def get_frequency_report(
        self,
        repetitions: List[LexicalRepetition]
    ) -> Dict[str, int]:
        """Genera reporte de frecuencia de palabras repetidas."""
        freq = defaultdict(int)
        for rep in repetitions:
            freq[rep.word] += 1
        return dict(sorted(freq.items(), key=lambda x: -x[1]))
```

---

## Criterio de DONE

```python
from narrative_assistant.analysis import LexicalRepetitionDetector, RepetitionConfig

detector = LexicalRepetitionDetector(RepetitionConfig(window_size=50))

text = """
El protagonista caminaba por el sendero oscuro. El sendero
serpenteaba entre los árboles. Los árboles proyectaban sombras
alargadas sobre el sendero polvoriento.
"""

repetitions = detector.detect(text)

# Debe detectar "sendero" repetido 3 veces cerca
sendero_reps = [r for r in repetitions if r.word == "sendero"]
assert len(sendero_reps) >= 2  # Al menos 2 pares de repeticiones

# Verificar reporte de frecuencia
freq_report = detector.get_frequency_report(repetitions)
assert freq_report.get("sendero", 0) >= 2

print(f"✅ Detectadas {len(repetitions)} repeticiones")
for rep in repetitions[:5]:
    print(f"  - '{rep.word}' ({rep.severity}): {rep.distance_words} palabras de distancia")
```

---

## Siguiente

[STEP 3.3: Repeticiones Semánticas](./step-3.3-semantic-repetitions.md)
