# Regression Procedure

Follow this whenever a new revision/release needs to be checked before shipping, or after any
change lands that isn't trivially scoped to a single format file.

## Guiding principle

> **Test changed functionality deeply, related functionality broadly, and critical core workflows
> regardless of whether they appear in the diff.**

This codebase makes "regardless of the diff" unusually important: most formats are implemented by
composing a small set of shared primitives (`library/read_blocks/`), so a change that *looks*
scoped to one format's Python file can still be a change to a primitive it happens to use, with
consequences for every other format that shares it. Never reason "the diff only touches
`resources/eac/maps/tnfs.py`, so only TNFS maps need testing" without first checking *what* changed
in that file.

## Step by step

### 1. Establish the baseline
- Know the last-known-good commit/tag and its `TEST_HISTORY.md` entry (if one exists). That
  entry's pass/fail state is your baseline — a regression is something that was passing there and
  isn't now, or a new gap in something that used to be covered.
- If no prior `TEST_HISTORY.md` entry exists for anything comparable, the current pass *is* the
  baseline going forward — say so explicitly in the new entry rather than implying continuity that
  doesn't exist.

### 2. Inspect what actually changed
```bash
git log --oneline <baseline>..HEAD
git diff --stat <baseline>..HEAD
```
Group the changed files mentally into:
- `library/read_blocks/**` or other framework-level code → **treat as high blast radius**, see
  step 4 regardless of how small the diff looks.
- `resources/**` (a specific format's definition) → scope to that format **plus** anything else
  that imports/subclasses the same base blocks it touches (`grep` for the class name).
- `frontend/src/app/components/editor/library/**` (generic block-ui components) → same high
  blast radius as framework changes, GUI side.
- `frontend/src/app/components/editor/eac/**` or `.../common/**` (bespoke viewers) → scoped to
  that viewer.
- `api/**` → check both the Python endpoint's own tests (`test/api/**`) and every Angular call
  site (`grep` the TS method name in `frontend/src`).
- Build/tooling/dependency changes (`angular.json`, `requirements.txt`, `package.json`, CI config)
  → re-verify `TEST_ENVIRONMENT.md`'s setup still works *before* trusting anything else — the test
  harness itself is a dependency of every other result in this pass.

### 3. Identify functionality potentially affected
For each changed area from step 2, use `TEST_PLAN.md`'s tables to find matching scenarios by
"Area" column. If a change doesn't map cleanly onto any existing scenario, that's a signal the
plan has a gap — add a scenario rather than skipping testing for that area.

### 4. Select targeted regression scenarios
Pull every scenario marked ✅ (Regression-candidate) in `TEST_PLAN.md` for the affected area(s).
For framework/generic-component changes, pull **all** ✅ scenarios in the "Editor — generic
components" and "Smoke" sections regardless of which specific format triggered the change.

### 5. Run the broader regression suite
Minimum bar, every time:
```bash
./.venv/bin/python -m unittest                 # backend + API tests
cd frontend && npm run test -- --watch=false --no-progress --browsers=ChromeHeadless
```
Plus the golden-corpus round-trip snippet (`TEST_ENVIRONMENT.md`) — not part of the committed
suite, but cheap enough to run every time regardless of scope.

If `library/read_blocks/**` or a widely-shared `resources/` module changed, additionally un-skip
and run `test/resources/test_games_directory.py::test_all_game_files_should_remain_the_same`
locally (it's `@unittest.skip`'d for CI cost reasons, not because it's unreliable) against
whatever `games/` directory is available — this is the only check with real-world format-variety
coverage at scale. Re-apply the skip afterward; don't commit it un-skipped.

### 6. Run the broader exploratory pass around changed areas
Bring up the environment from `TEST_ENVIRONMENT.md` and manually/agent-drive the affected screens
per `UI_MAP.md`, going a bit wider than the exact scenario list — e.g. if a map-viewer change is
being tested, open more than one map file, try switching the "Current preview FAM" dropdown, try
Undo after editing a field in it, not just the one exact repro.

### 7. Verify existing behavior wasn't broken
For every scenario re-run, compare against its last recorded expected result in `TEST_PLAN.md`
— not against a fresh guess at what "should" happen. If the expected result itself looks wrong on
reflection, fix the plan and say so in `TEST_HISTORY.md`, don't just silently change what's being
asserted.

### 8. Test newly added functionality
New format definitions: does it get a rich viewer or fall back to generic components? Confirm the
fallback message (`UI not implemented for …`) doesn't appear for something that's supposed to be
supported. New GUI features: add scenarios to `TEST_PLAN.md` before or immediately after testing
them, so the next regression pass inherits coverage of them automatically.

### 9. Document failures
Every failure goes in `KNOWN_ISSUES.md` with reproduction steps, following the classification
rules in `QA/README.md`. Don't leave a failure undocumented because "it'll obviously get fixed
before release" — the next agent has no way to know that unless it's written down.

### 10. Screenshot/UI-state comparison
Where a visual regression is plausible (layout/CSS changes, a new Angular Material version,
theme changes), take screenshots of the same scenario before/after and diff by eye — there is no
automated visual-diff tooling in this repo currently. Remember the WebGL screenshot-hang caveat
(`KNOWN_ISSUES.md` KI-3) when planning which screens to screenshot.

### 11. Update regression knowledge after a fix
Once a `KNOWN_ISSUES.md` entry is fixed: verify the fix against its exact repro, update its status
in place (don't delete the entry — mark it fixed, with the commit/PR that fixed it if known), and
promote its repro into a permanent `TEST_PLAN.md` scenario (✅ regression candidate) if it isn't
one already, so the same bug can't silently come back unnoticed.

### 12. Use the previous release as a behavioral baseline, not a spec
When something behaves differently from the last release, that's a lead to investigate, not
automatically a bug (it could be an intentional change) and not automatically fine (it could be an
unnoticed regression). Check the changelog/commit messages between the two before concluding
either way, and record the conclusion (with reasoning) in `TEST_HISTORY.md`.
