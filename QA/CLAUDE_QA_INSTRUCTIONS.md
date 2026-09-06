# QA Playbook for a New Agent

You've been asked to test this app, verify a fix, or run a regression pass, and you've never seen
this repo's QA setup before. Read this file first — it sequences everything else in `QA/`.

## 1. Orient yourself (5-10 minutes)

Read, in order:
1. `QA/README.md` — how this directory works, how to record what you find.
2. `QA/APPLICATION_MAP.md` — what the product is.
3. `QA/UI_MAP.md` — what's actually on screen.
4. `QA/KNOWN_ISSUES.md` — don't waste time rediscovering KI-1/KI-2/KI-3.
5. `QA/TEST_HISTORY.md` — most recent entry, so you know the last established baseline.

Repo-root `CLAUDE.md` and the `read-block-framework`/`nfs-resource-formats` skills cover the
*code* — read those only if your task requires understanding *why* something behaves a certain
way, not just *whether* it does.

## 2. Understand what you're actually being asked to do

- **"Test the app" / "run regression" with no other context** → follow `QA/REGRESSION.md`
  end to end, using the current git state vs. the last `TEST_HISTORY.md` entry as your diff.
- **"Verify bug X is fixed"** → find X in `QA/KNOWN_ISSUES.md`, reproduce its exact repro steps
  first (confirm it's *actually* still broken/now fixed before touching anything else), then run
  the P0/P1 smoke scenarios from `QA/TEST_PLAN.md` around it (fixes in this codebase regress
  adjacent things surprisingly often — see `APPLICATION_MAP.md` on shared primitives).
- **"Test this new feature"** → check `QA/UI_MAP.md`/`QA/TEST_PLAN.md` for whether it's already
  described; if not, this is new functionality — explore it, then *add* it to both files as part
  of your task, not just to your final report.
- **A raw exploratory pass with no specific target** → follow `QA/TEST_PLAN.md` top to bottom,
  prioritizing "Not run" rows, and prioritizing P0/P1 over P2/P3.

## 3. Get a drivable instance of the app

Read `QA/TEST_ENVIRONMENT.md` in full before attempting any live GUI interaction — the app's
default run modes are **not** drivable by browser automation (native web view on macOS/Windows,
no window at all in Linux `--dev`, a separate app window in Linux production). The Docker + Linux
`--dev` recipe there is the one confirmed-working path to a real, automatable browser tab. Don't
try to invent a different approach without first checking whether the constraints in that file
still apply (they're architectural, not incidental — re-verify against current code if a lot of
time has passed or the bridge/build tooling changed).

If your task is purely about the **parsing library** (a specific format, a shared primitive) and
doesn't need the GUI, skip the whole GUI setup and use the headless corpus snippet in
`TEST_ENVIRONMENT.md` instead — it's much faster.

## 4. While testing

- Tag every claim you record as Confirmed (live), Confirmed (code), Inferred, or Unknown — see
  `QA/README.md`. Don't upgrade a claim's confidence without actually having done the thing.
- If you hit something that looks wrong: check `QA/KNOWN_ISSUES.md` first (is it already known?),
  then try to determine root cause before filing it (a one-line "X doesn't work" is much less
  useful than KI-1's level of detail — reproduce it, read the relevant code path, understand
  *why*, then write it up). Classify honestly: Confirmed bug / Suspected bug / Expected behavior /
  Unclear — never force something into "expected behavior" just because you don't have time to dig
  further; leave it Unclear instead.
- If you hit something ambiguous where you're not sure it's a bug: don't silently decide either
  way. Record it as Unclear/Unknown with your reasoning, so a human can make the call.
- Don't modify production code to make something testable unless the task explicitly calls for a
  fix — the QA docs and Docker/Xvfb tooling exist so you almost never need to.
- Never test destructive operations (Save, serialize, custom actions) against real user files —
  the app doesn't back up automatically. Use `test/golden_corpus/` or `test/samples/` copies, or a
  scratch copy of a `games/` file (never edit inside `games/` itself, and never assume its contents
  are disposable — it's the user's real, large, personal game installs).

## 5. Recording new fixtures from `games/`

`games/` is `.gitignore`d (real game installs, not part of the repo). If a test needs a specific
file from there and you want the test to be reproducible for anyone else who clones the repo,
**copy the file into a git-tracked location first** (`test/golden_corpus/` for small,
fully-supported files that should stay supported forever; elsewhere if it's meant to represent an
intentionally-unsupported/negative case — say which, in the commit or in `TEST_HISTORY.md`). Never
write a test that reads a path under `games/` directly.

## 6. When you're done

- Update `QA/TEST_HISTORY.md` with a new entry (don't overwrite the previous one).
- Update `QA/TEST_PLAN.md` statuses for whatever you ran (in place — this file is meant to always
  reflect the latest known status per scenario, not just the first run).
- Update `QA/KNOWN_ISSUES.md` for anything new, or the status of anything you just fixed/verified.
- Update `QA/UI_MAP.md`/`QA/APPLICATION_MAP.md` if you found undocumented screens/behavior, or
  found something documented incorrectly.
- If you built new reusable QA tooling (a script, a Docker recipe variant, a technique for driving
  something previously un-drivable), add it to `QA/TEST_ENVIRONMENT.md` — that file's whole
  purpose is to save the next agent from re-deriving things like the Tk-dialog xdotool trick.

## What not to assume

- Don't assume the existing `test/api/**` suite represents full product coverage — it covers a
  handful of edge cases around trailing-optional fields and the changes/save workflow, not the
  breadth of the UI (see `TEST_STRATEGY.md` item 11).
- Don't assume undocumented behavior is a bug, and don't assume it's fine — it's undocumented;
  find out, or record it as Unknown.
- Don't assume a passing golden-corpus round-trip means the GUI works — it only proves the parsing
  library handles that file; the GUI has its own, separately-tracked coverage in `TEST_PLAN.md`.
- Don't assume this file or any other in `QA/` is complete or currently accurate. It's a living
  snapshot from whenever it was last touched — verify anything load-bearing to your task against
  the current code/app rather than trusting it blindly, and fix it if it's stale.
