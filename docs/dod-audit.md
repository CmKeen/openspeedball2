# Definition-of-Done audit (summary)

Source: `.superpowers/sdd/task-12-report.md` (gitignored, agent-local
working notes). This file is the durable, tracked summary of that audit's
substance, kept in sync at each significant Task 12 pass.

## Result at the initial Task 12 audit (2026-07-13/14)

51/51 headless tests passing. Sim core confirmed render-free (no pygame/
random/time imports; importing `sim.match` never loads pygame). Fixed
50Hz tick loop with seedable RNG confirmed deterministic via
`state_hash()` replay. README/LICENSE checked for required content
(tech-stack rationale, asset policy, GPLv3 text) — present.

DoD items requiring a human at a keyboard (window shows scrolling pitch;
human moves/contests/scores; CPU chases/passes/tackles/scores) were
substituted with a headless smoke test driving `Match.tick_with_ai()` +
the render calls for 2000 ticks under `SDL_VIDEODRIVER=dummy`, with
scripted "human" inputs. That smoke run showed **team 2 (CPU) scoring 50
goals in 2000 ticks against 0 for team 1**, with 58 possession changes —
flagged in that report only as a "scoring balance observation," not
investigated further.

DoD item 7 (data-driven configs, no magic gameplay numbers in `sim/`) was
graded with caveats: beyond the brief's pre-accepted formation-anchor
exception, roughly eight more small hardcoded gameplay-shaped constants
were found (AI thresholds, tackle-damage formula constants, bank-eject
physics) and documented as future cleanup rather than moved to
`data/*.json`, to keep that pass's diff scoped to verification/docs.

## What the follow-up final-review pass found (2026-07-14)

The "50 goals in 2000 ticks" result from the initial audit's smoke test
was not a balance quirk — it was **Critical bug #2**: `check_goal()`
ignored ball possession, so simply *carrying* the ball across the goal
line scored, and because Critical bug #1 (the thrower instantly
re-picking-up their own live throw) made genuine passes/shots into
no-ops, carrying was effectively the *only* way the ball ever crossed a
goal line. Both are fixed; see the "Final-review fix report" section
appended to `.superpowers/sdd/task-12-report.md` for the full
finding-by-finding writeup, test additions, and a fresh headless smoke
comparison (AI-only vs. AI+scripted-human).

## Known hardcoded exceptions (not yet in `data/*.json`)

Still open, unchanged by the final-review pass (out of its stated scope):
see `docs/spec/mechanics.md`'s "Known hardcoded exceptions" subsection
for the current list and file/line pointers.
