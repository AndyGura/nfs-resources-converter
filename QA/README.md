# QA Knowledge Base

This directory is the project's persistent QA memory. It exists because the app is a **desktop
GUI** with almost no automated UI test coverage (`test/` covers the parsing library and a handful
of API endpoints; there is no automated test that drives the Angular UI). Everything here was
built by actually running the app and exercising it, not by reading the source alone — see
`TEST_HISTORY.md` for what was verified live vs. inferred from code.

## Files in this directory

| File | Authoritative for |
|---|---|
| `APPLICATION_MAP.md` | What the product *is*: functional areas, workflows, data flow. |
| `UI_MAP.md` | Every screen/dialog/menu, its controls, and how to reach it. |
| `TEST_STRATEGY.md` | What kinds of testing matter here and when to run them. |
| `TEST_PLAN.md` | Concrete, numbered test scenarios derived from the map above. |
| `REGRESSION.md` | Step-by-step procedure to follow when testing a new revision/release. |
| `KNOWN_ISSUES.md` | Bugs and open questions found so far, with reproduction steps. |
| `TEST_ENVIRONMENT.md` | How to actually get a *drivable* instance of this desktop app (this is the non-obvious part — read it before attempting any live GUI test). |
| `TEST_HISTORY.md` | Append-only log of every test pass that has been run. |
| `CLAUDE_QA_INSTRUCTIONS.md` | Step-by-step playbook for a future agent that has never seen this repo before. |

## How a future agent should use this

1. Start at `CLAUDE_QA_INSTRUCTIONS.md`, not here — it sequences the other files for you.
2. Treat `UI_MAP.md` and `APPLICATION_MAP.md` as living documents: when you discover a screen,
   control, or workflow that isn't described (or is described wrong), fix the file as part of your
   task. Don't let drift accumulate for the next agent.
3. Treat `KNOWN_ISSUES.md` and `TEST_HISTORY.md` as append-mostly logs: add new entries, correct
   an entry's status in place, but don't delete history of what was found before.
4. `CLAUDE.md` (repo root) and the `read-block-framework` / `nfs-resource-formats` skills describe
   how the code is built; nothing here duplicates that. This directory only covers *how the running
   app behaves and how to test it*.

## Confirmed vs. inferred vs. unknown

Every non-trivial claim in these files is tagged, inline, with how it was established:

- **Confirmed (live)** — observed by actually running the app (GUI or CLI) and watching it happen.
- **Confirmed (code)** — read directly off the source; not exercised at runtime.
- **Inferred** — a reasonable deduction from code/behavior that was not directly verified.
- **Unknown** — genuinely unclear; do not silently resolve this to "not a bug" or "not important".

When you add new information, tag it the same way. Never upgrade an "Inferred" claim to
"Confirmed" without actually having exercised it.

## Recording a new bug

Add it to `KNOWN_ISSUES.md` with reproduction steps, expected vs. actual behavior, and severity.
Classify it as **confirmed bug**, **suspected bug**, **expected behavior** (if you learn the
"bug" is intentional), or **unclear / needs product decision** — never invent an "expected
behavior" you have no evidence for. If it's a genuine, reproducible defect, it's also a candidate
regression scenario — add a line for it in `TEST_PLAN.md` / `REGRESSION.md`'s regression set once
it's fixed (or as a documented-broken case before it is).

## Recording newly discovered behavior/functionality

Update `APPLICATION_MAP.md` or `UI_MAP.md` directly (whichever is the closer fit), then check
whether `TEST_PLAN.md` needs a new scenario for it. Cross-link with `[[…]]`-style relative
references between files only if this project's tooling renders them; otherwise use plain
relative Markdown links (`[UI_MAP](./UI_MAP.md)`), which is what these files do.
