# Immediate Action Checklist
## Post-Audit Quick Wins (2 hours total)

**Date**: 2026-02-13
**Priority**: Complete before v1.0 release
**Total effort**: ~2 hours

---

## Task 1: Fix sync_version.py (30 min) ⚠️ CRITICAL

**Problem**: Script doesn't sync docs, causing version drift
- VERSION: 0.9.3 ✓
- PROJECT_STATUS.md: 0.7.17 ✗ (2 minor versions behind)
- CHANGELOG.md: 0.3.22 ✗ (6 minor versions behind!)

**Action**:
1. Edit `scripts/sync_version.py`
2. Add to `TARGETS` dict:
   ```python
   "docs/PROJECT_STATUS.md": {
       "pattern": r'^> \*\*Version\*\*: ".*"',
       "replacement": '> **Version**: "{version}"',
   },
   "docs/CHANGELOG.md": {
       "pattern": r'^## \[Unreleased\]',
       "replacement": '## [Unreleased]\n\n## [{version}] - ' + datetime.now().strftime('%Y-%m-%d'),
       "inject_new_version": True,  # Special case: adds new version header
   },
   ```
3. Run `python scripts/sync_version.py 0.9.3` to sync all files

**Verification**:
```bash
python scripts/sync_version.py --check
# Should show all files in sync
```

---

## Task 2: Update PROJECT_STATUS.md (5 min) ⚠️ CRITICAL

**Action**: Manual fix until sync_version.py is updated
```bash
# Line 4 in docs/PROJECT_STATUS.md
OLD: > **Version**: 0.7.17
NEW: > **Version**: 0.9.3
```

**File**: `D:\repos\tfm\docs\PROJECT_STATUS.md`

---

## Task 3: Update CHANGELOG.md (10 min) ⚠️ CRITICAL

**Problem**: CHANGELOG shows 0.3.22 as latest, missing 0.4.x - 0.9.x releases

**Action**: Add missing version entries
```markdown
## [Unreleased]

## [0.9.3] - 2026-02-10
### Added
- Editorial work export/import (.narrassist format)
- Work preservation across re-analysis
- Version tracking in export format

### Fixed
- Undo-merge preserved across re-analysis

## [0.9.2] - 2026-02-09
(add details from git log)

## [0.9.1] - 2026-02-08
(add details from git log)

... (fill in missing versions)
```

**Helper command**:
```bash
# Get git history for missing versions
git log --oneline --decorate --since="2026-01-29"
```

---

## Task 4: Add CI comments (10 min) 🔧 GOOD HYGIENE

**Problem**: `|| true` in CI looks like hiding failures, needs explanation

**Action**: Edit `.github/workflows/ci.yml`

**Line 80** (after `Install dependencies`):
```yaml
      - name: Run MyPy
        run: |
          # Informational only: Type hints are advisory in Python, not blocking.
          # Many false positives due to dynamic imports and third-party stubs.
          mypy src/narrative_assistant --ignore-missing-imports || true
```

**Line 109** (in `integration-tests` job):
```yaml
      - name: Run integration tests
        run: |
          # Informational: Integration tests require NLP models (~2GB) not available in CI.
          # Models download on first run (network required). Local dev runs these fully.
          pytest tests/integration -v --tb=short -x --junitxml=junit-integration.xml || true
```

**Line 142** (in `performance-tests` job):
```yaml
      - name: Run performance tests
        run: |
          # Informational: Performance tests are manual trigger only (workflow_dispatch).
          # These are slow (~60min) and track regressions over time, not blocking CI.
          pytest tests/performance -v --tb=short -m slow --junitxml=junit-perf.xml || true
```

---

## Task 5: Verify xfails (1 hour) 🧪 TEST HYGIENE

**Problem**: Some xfail markers may be obsolete (tests now pass)

**Action**:
```bash
# Run xfails to see if they pass
pytest --runxfail tests/adversarial/ -v

# If some pass consistently, remove @pytest.mark.xfail from those tests
```

**Files to check**:
```bash
grep -r "@pytest.mark.xfail" tests/ --include="*.py"
# Found in 5 files:
# - tests/adversarial/test_attribute_adversarial.py (likely most xfails)
# - tests/regression/test_ojos_verdes_bug.py
# - tests/unit/test_coreference.py
# - (2 others)
```

**Decision criteria**:
- If test passes 3+ times consecutively → Remove xfail marker
- If test fails due to known NLP limitation (pro-drop, voseo, irony) → Keep xfail + add reason comment
- If test fails inconsistently → Investigate root cause

**Example**:
```python
# BEFORE
@pytest.mark.xfail
def test_possessive_pronoun_resolution():
    ...

# AFTER (if now passing)
def test_possessive_pronoun_resolution():
    """Possessive pronoun resolution - now working after coreference improvements."""
    ...

# AFTER (if still failing, known limitation)
@pytest.mark.xfail(reason="Pro-drop subject elision not supported - requires syntactic parser")
def test_elided_subject_attribution():
    ...
```

---

## Post-Completion Checklist

After completing all tasks:

```bash
# 1. Verify version sync
python scripts/sync_version.py --check

# 2. Run tests to ensure nothing broke
pytest -v -x -m "not heavy"

# 3. Git commit
git add scripts/sync_version.py docs/PROJECT_STATUS.md docs/CHANGELOG.md .github/workflows/ci.yml
git commit -m "fix: sync version docs to 0.9.3, clarify CI intent (audit findings)"

# 4. Verify CI on GitHub
git push origin master
# Check GitHub Actions to ensure all steps still pass
```

---

## Effort Breakdown

| Task | Time | Impact |
|------|------|--------|
| Fix sync_version.py | 30 min | Prevents future version drift |
| Update PROJECT_STATUS.md | 5 min | Users see correct version |
| Update CHANGELOG.md | 10 min | Release history is accurate |
| Add CI comments | 10 min | Future contributors understand intent |
| Verify xfails | 1 hour | Test suite hygiene |
| **TOTAL** | **~2 hours** | **High ROI** |

---

## Optional: Git Pre-Commit Hook (15 min)

**Prevents future version drift**:

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Check if VERSION is in sync with all files

python scripts/sync_version.py --check
if [ $? -ne 0 ]; then
    echo "ERROR: Version files out of sync!"
    echo "Run: python scripts/sync_version.py"
    exit 1
fi
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## Notes

- These are **quick wins** with high impact
- No breaking changes, no new features
- Improves documentation hygiene and CI transparency
- Total time: ~2 hours (well-invested before v1.0)

---

**Priority**: Complete this checklist before tagging v1.0
**Owner**: Pau
**Status**: Ready to implement
