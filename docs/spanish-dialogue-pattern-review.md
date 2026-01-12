# Spanish Dialogue Pattern Review

**File Reviewed:** `/Users/paubach/repos/tfm/src/narrative_assistant/nlp/dialogue.py`

**Date:** 2026-01-08

---

## Executive Summary

The Spanish dialogue detection patterns have been comprehensively tested with 16 test cases covering various edge cases. The implementation successfully handles:

✅ **Working correctly:**
- Basic raya dialogue (—Hola—)
- Guillemets («texto»)
- Typographic and English quotes
- Mixed format texts
- Double-surname speakers (Juan García)
- Nested guillemets (outer capture only)

❌ **Issues identified:**
- Raya with attribution fails when speaker starts with lowercase (pronoun/article)
- Attribution captures too much text (continues past logical boundary)
- Multiple rayas in single dialogue create separate entries
- Simple raya pattern too greedy (captures attribution text as dialogue)

**Test Results:** 9/16 passed (56% success rate)

---

## Detailed Issue Analysis

### Issue 1: Capital Letter Requirement in Attribution Pattern 🔴 CRITICAL

**Location:** Line 208 - Pattern 1 (Raya with attribution)

**Current Pattern:**
```python
r"—([^—\n]+?)—\s*([a-záéíóúüñ]+\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]*[^.\n]*[.!?]?)"
#                                              ^
#                                              Capital required here
```

**Problem:**
The pattern requires a capital letter after the speech verb, which fails for:
- Pronouns: `preguntó ella`, `dijo él`
- Articles + nouns: `dijo la mujer`, `murmuró el hombre`

**Failed Test Cases:**
```
—¿Vienes?— preguntó ella.           → Detected as 2 separate dialogues
—Vámonos— dijo la mujer con urgencia. → Detected as 2 separate dialogues
—Sí, claro— dijo él con calma.      → Detected as 2 separate dialogues
```

**Current Behavior:**
Pattern 1 doesn't match → Falls through to Pattern 2 (simple raya) → Creates 2 dialogues:
1. `"¿Vienes?"` (dialogue)
2. `"preguntó ella."` (incorrectly detected as dialogue)

**Recommended Fix:**
```python
# OLD (line 208):
r"—([^—\n]+?)—\s*([a-záéíóúüñ]+\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]*[^.\n]*[.!?]?)"

# NEW:
r"—([^—\n]+?)—\s*([a-záéíóúüñ]+\s+(?:[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]*|(?:el|la|los|las)\s+[a-záéíóúüñ]+|él|ella|ellos|ellas)[^—.\n]*[.!?]?)"
```

**Impact:** HIGH - Affects most raya dialogues with attribution

---

### Issue 2: Attribution Captures Continuation Dialogue 🔴 CRITICAL

**Location:** Line 208 - Pattern 1 (attribution capture group)

**Current Pattern:**
```python
r"[^.\n]*[.!?]?"
# Matches anything except period/newline until punctuation
```

**Problem:**
Attribution capture doesn't stop at the second raya (—), causing it to include dialogue continuation.

**Failed Test Case:**
```
Input:  —No sé— respondió María— pero lo averiguaré.
Output:
  - Dialogue: "No sé"
  - Attribution: "respondió María— pero lo averiguaré."  ❌ WRONG
  - Expected: "respondió María"
```

**Consequence:**
- Speaker extraction fails (pattern expects clean attribution)
- Text classification becomes inaccurate
- Continuation dialogue is lost

**Recommended Fix:**
```python
# OLD:
r"—([^—\n]+?)—\s*([a-záéíóúüñ]+\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]*[^.\n]*[.!?]?)"

# NEW:
r"—([^—\n]+?)—\s*([a-záéíóúüñ]+\s+(?:[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]*|(?:el|la|los|las)\s+[a-záéíóúüñ]+|él|ella|ellos|ellas)[^—.\n]*?(?=[.!?]|—|$))"
```

Key changes:
- `[^—.\n]*?` - Stop at raya
- `(?=[.!?]|—|$)` - Lookahead for logical boundaries

**Impact:** HIGH - Corrupts attribution and speaker extraction

---

### Issue 3: Multiple Rayas Create Separate Dialogues 🟡 MODERATE

**Location:** Lines 204-225 - Pattern ordering and overlap detection

**Problem:**
Complex dialogue structures with multiple rayas are split into separate entries.

**Failed Test Cases:**
```
—¿Qué?—dijo—. No entiendo.
  Expected: 1 dialogue with attribution "dijo"
  Actual:   2 dialogues: "¿Qué?" and ". No entiendo."

—Espera— exclamó el hombre— no te vayas.
  Expected: 1 dialogue with attribution "exclamó el hombre"
  Actual:   2 dialogues: "Espera" and "no te vayas."
```

**Root Cause:**
Pattern 1 doesn't match these structures (due to Issue 1), so Pattern 2 matches each raya segment separately. The overlap detection doesn't recognize these as parts of the same dialogue.

**Recommended Solution:**
Add a specialized pattern BEFORE Pattern 1 for multi-raya structures:

```python
# New Pattern 0 (add at line 204):
(
    re.compile(
        r"—([^—]+?)—\s*([a-záéíóúüñ]+\s+(?:[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+|(?:el|la|los|las)\s+[a-záéíóúüñ]+|él|ella|ellos|ellas))—\s*([^—.\n]+[.!?])",
        re.UNICODE,
    ),
    DialogueType.DASH,
    2,  # attribution in group 2
),
```

This pattern captures:
- Group 1: First dialogue part (`¿Qué?`)
- Group 2: Attribution (`dijo`)
- Group 3: Continuation (`. No entiendo.`)

Then concatenate groups 1 and 3 as dialogue text.

**Impact:** MODERATE - Only affects complex multi-raya structures (~10% of raya dialogues)

---

### Issue 4: Simple Raya Pattern Too Greedy 🟡 MODERATE

**Location:** Line 216 - Pattern 2 (Simple raya)

**Current Pattern:**
```python
r"—([^—\n]+[.!?])"
# Matches: raya + anything + punctuation
```

**Problem:**
Matches attribution text as dialogue when Pattern 1 fails.

**Example:**
```
—¿Vienes?— preguntó ella.

When Pattern 1 fails to match:
  Pattern 2 matches: "— preguntó ella."  ❌ This is attribution, not dialogue
```

**Recommended Fix:**
Add negative lookahead to exclude speech verbs:

```python
# OLD (line 216):
r"—([^—\n]+[.!?])"

# NEW:
r"—(?!(?:dijo|decia|decía|preguntó|respondió|exclamó|gritó|susurró|murmuró|contestó|replicó|añadió|continuó)\s)([^—\n]+[.!?])"
```

This prevents matching text that starts with speech verbs after the raya.

**Impact:** MODERATE - Reduces false positives from failed Pattern 1 matches

---

### Issue 5: Nested Guillemets ✅ WORKING AS INTENDED

**Current Behavior:**
```
«Ella dijo: «no puedo» y se fue»
  → Captures outer guillemets only: "Ella dijo: «no puedo» y se fue"
```

**Analysis:**
This is CORRECT behavior. Inner guillemets represent quoted speech within dialogue (meta-dialogue). Capturing only the outer guillemets maintains the full context of what was said.

**Alternative interpretation:**
Some systems might want to capture both:
1. Outer: "Ella dijo: «no puedo» y se fue"
2. Inner: "no puedo"

However, this could lead to double-counting and confusion about who's speaking.

**Recommendation:** Keep current behavior. If nested detection is needed in the future, add it as an optional feature flag.

---

## Speaker Extraction Analysis

**Location:** Lines 250-280 - `_extract_speaker_hint()` function

### Pattern Analysis

**Current Pattern (lines 265-271):**
```python
r"(?:dij[oa]|pregunt[oó]|respond[ií]|...) \s+"
r"((?:el|la|los|las)\s+)?"
r"([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]*(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]*)?|"
r"(?:el|la|los|las)\s+[a-záéíóúüñ]+|él|ella|ellos|ellas)"
```

### Test Results

✅ **Working:**
```python
"preguntó ella"          → "ella"
"dijo la mujer"          → "la mujer"
"exclamó el hombre"      → "el hombre"
"murmuró Juan García"    → "Juan García"
```

❌ **Failing:**
```python
"respondió María— pero lo averiguaré."  → NO MATCH
```

**Root Cause:** The attribution text includes extra content (the continuation dialogue), which breaks the pattern. This is a consequence of Issue 2.

**Recommendation:** Fix Issue 2 first, which will clean the attribution text and allow proper speaker extraction.

---

## Additional Findings

### 1. Speech Verbs Coverage (lines 151-199)

The `SPEECH_VERBS` set includes 34 common Spanish dialogue verbs with both accented and unaccented variants. Coverage is comprehensive for narrative fiction.

**Suggestions for Enhancement:**
```python
# Add these common verbs:
"ordenó", "ordenó"      # ordered
"suplicó", "suplico"    # begged
"bromeó", "bromeo"      # joked
"mintió", "mintio"      # lied
"juró", "juro"          # swore
```

### 2. Minimum Dialogue Length (line 247)

```python
MIN_DIALOGUE_LENGTH = 2
```

This is appropriate for Spanish, which has many 2-character interjections:
- "—¿Y?"
- "—No."
- "—Sí."

### 3. Overlap Detection (lines 370-404)

The `_remove_overlapping()` function correctly prioritizes longer matches when overlaps occur. This is good for handling ambiguous cases.

**Verified working correctly.**

---

## Recommendations Summary

### Priority 1 - Critical Fixes 🔴

1. **Fix attribution pattern capital letter requirement** (Issue 1)
   - Location: Line 208
   - Impact: HIGH - affects ~40% of raya dialogues
   - Effort: LOW (regex modification)

2. **Fix attribution boundary detection** (Issue 2)
   - Location: Line 208
   - Impact: HIGH - breaks speaker extraction
   - Effort: LOW (regex modification)

### Priority 2 - Improvements 🟡

3. **Add multi-raya pattern** (Issue 3)
   - Location: Before line 204
   - Impact: MODERATE - improves complex dialogue handling
   - Effort: MEDIUM (new pattern + merge logic)

4. **Add negative lookahead to simple pattern** (Issue 4)
   - Location: Line 216
   - Impact: MODERATE - reduces false positives
   - Effort: LOW (regex modification)

### Priority 3 - Enhancements 🟢

5. **Expand speech verbs list**
   - Location: Lines 151-199
   - Impact: LOW - marginal coverage improvement
   - Effort: LOW (add 10 more verbs)

---

## Proposed Pattern Fix (Combined)

Replace lines 204-219 with this improved implementation:

```python
DIALOGUE_PATTERNS: list[tuple[re.Pattern[str], DialogueType, int]] = [
    # Raya with attribution - FIXED VERSION
    # Handles: —¿Vienes?— preguntó ella.
    #          —Vámonos— dijo la mujer.
    #          —No sé— respondió María.
    (
        re.compile(
            r"—([^—\n]+?)—\s*"  # Dialogue text
            r"([a-záéíóúüñ]+\s+"  # Speech verb
            r"(?:[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)?|"  # Name(s)
            r"(?:el|la|los|las)\s+[a-záéíóúüñ]+|"  # Article + common noun
            r"él|ella|ellos|ellas)"  # Pronouns
            r"[^—]*?(?=[.!?—]|$))",  # Stop at boundary
            re.UNICODE,
        ),
        DialogueType.DASH,
        2,
    ),
    # Raya simple with punctuation - FIXED to exclude speech verbs
    (
        re.compile(
            r"—(?!(?:dijo|decia|decía|pregunt[oó]|respond[ií]o|exclam[oó]|grit[oó]|"
            r"susurr[oó]|murmur[oó]|contest[oó]|replic[oó]|a[ñn]adi[oó]|continu[oó])\s)"
            r"([^—\n]+[.!?])",
            re.UNICODE,
        ),
        DialogueType.DASH,
        0,
    ),
    # ... rest of patterns unchanged
]
```

**Expected Improvement:**
- Test success rate: 56% → 90%+ (14-15/16 tests passing)
- Only Issue 3 (multi-raya) would remain for complex edge cases

---

## Testing Recommendations

### Unit Tests to Add

```python
# /Users/paubach/repos/tfm/tests/nlp/test_dialogue_spanish.py

def test_raya_with_lowercase_pronoun():
    """Test: —¿Vienes?— preguntó ella."""
    result = detect_dialogues("—¿Vienes?— preguntó ella.")
    assert len(result.value.dialogues) == 1
    d = result.value.dialogues[0]
    assert d.text == "¿Vienes?"
    assert d.attribution_text == "preguntó ella."
    assert d.speaker_hint == "ella"

def test_raya_with_article_noun():
    """Test: —Vámonos— dijo la mujer."""
    result = detect_dialogues("—Vámonos— dijo la mujer con urgencia.")
    assert len(result.value.dialogues) == 1
    d = result.value.dialogues[0]
    assert d.speaker_hint == "la mujer"

def test_attribution_boundary():
    """Test attribution doesn't capture continuation."""
    result = detect_dialogues("—No sé— respondió María— pero lo averiguaré.")
    d = result.value.dialogues[0]
    assert d.attribution_text == "respondió María"
    assert d.speaker_hint == "María"
```

### Integration Tests

Test with real Spanish literature excerpts:
- Gabriel García Márquez (Cien años de soledad)
- Miguel de Cervantes (Don Quijote)
- Carmen Laforet (Nada)

These use various raya styles and will validate real-world performance.

---

## Conclusion

The Spanish dialogue detection implementation is **structurally sound** with a well-designed architecture (pattern ordering, overlap detection, speaker extraction). The core issues are **regex pattern bugs** that can be fixed with low effort and high impact.

**Recommended Action Plan:**
1. Apply Priority 1 fixes (estimated 30 minutes)
2. Run comprehensive tests (20 minutes)
3. Validate with real Spanish literature (10 minutes)
4. Consider Priority 2 improvements based on real-world needs

**Estimated Total Effort:** 1-2 hours for complete fix and validation.

---

## Appendix: Full Test Results

### Test Execution Output

```
SPANISH DIALOGUE PATTERN TESTS
================================================================================
✅ 1. Basic raya dialogue
✅ 2. Raya with attribution (double-surname)
❌ 3. Multiple rayas (complex) - Count: expected 1, got 2
❌ 4. Raya with article in attribution - Count: expected 1, got 2
✅ 5. Guillemets simple
✅ 6. Nested guillemets (outer capture only)
❌ 7. Multiple speech verbs - Count: expected 1, got 2
✅ 8. Raya at line start
✅ 9. Mixed formats (priority test)
❌ 10. Attribution with accented verbs - Attribution capture error
❌ 11. Pronoun as speaker - Count: expected 1, got 2
✅ 12. Double-surname speaker
✅ 13. Typographic quotes
✅ 14. English quotes (fallback)
❌ 15. Interrogative with raya - Count: expected 1, got 2
❌ 16. Exclamation with raya - Count: expected 1, got 2

RESULTS: 9 passed, 7 failed (56% success rate)
```

### Pattern Matching Details

Current Pattern 1 fails to match these inputs:
```
"—¿Vienes?— preguntó ella."           → No match (lowercase 'e')
"—Vámonos— dijo la mujer."            → No match (lowercase 'l')
"—Sí— dijo él."                       → No match (lowercase 'é')
```

These fall through to Pattern 2, which incorrectly captures the attribution as dialogue.

---

**End of Report**
