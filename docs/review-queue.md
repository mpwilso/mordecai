# Review queue: the planted skills check, stage 2

Written 2026-10-05. **Stopped on a listed stop condition:** the V2 placebo was called Hurts. Everything below is committed and nothing is pushed. Details: [planted-skills-results.md](planted-skills-results.md). Predictions for V1 and V2: [validation-skills.md](validation-skills.md).

## Where things stand

| Step | Status |
|---|---|
| 1. Relative paths in cards | Done (4943c2f). Only `paths` changed in the seven cards. No absolute local path, token or key in any tracked file. |
| 2. Rule change, 0.2.0 | Done (03d2619). Only suite 3 moves, from Already handled to Inconclusive, shown in a post-hoc section. |
| 3. Simulation recalibration | Done (d7dafe8). Real runs matched the 94% agreement setting. The +20 point finding survives. |
| 4. Validation suites | V1 and V2 written, predicted (f848767) and run. **Stopped after V2.** The sealed holdouts did not run. |
| 5. Suite 2 on Sonnet | Not run. |
| 6. `check --model` | Not started. |
| 7. README rewrite | Not started. |

## Scorecard for the new suites (Haiku 4.5, 0.2.0 rules)

| Suite | Predicted | Actual | | Better / same / worse | With / without | Fired |
|---|---|---|---|---|---|---|
| V1 outdated rule that fires | Hurts | Inconclusive (-11, interval -26 to +0) | Miss | 0 / 7 / 2 | 85% / 96% | 1 of 27 |
| V2 noisy placebo | Not Helps or Hurts | **Hurts** (-37, interval -59 to -15) | **Miss, stop** | 0 / 3 / 6 | 0% / 37% | 27 of 27 |

**V1 didn't test what it was built to test.** The skill fired in only 1 of 27 runs, even though its description names every dependency task. Haiku answered from pyproject.toml and uv.lock without opening the skill. The 2 worse cases came from runs where the skill never fired. The new rule did its job: under 0.1.0 this card would have said Already handled, and under 0.2.0 it says Inconclusive.

**V2 was not a placebo, and that's my design error.** Its body says "Say what changed in plain words". The grader looks for a Conventional Commits prefix. With the skill, all 27 runs wrote plain messages such as "Upgrade pytest from 7.4 to 8.2". Without it, 10 of 27 used a prefix such as "chore: upgrade pytest from 7.4 to 8.2". That is a real, consistent effect, and Hurts reads it correctly.

## The false-positive picture

- **No placebo has yet produced a false call from noise.** 5a and 5b had no noise at all. V2 had noise on the baseline side (19 of 24 cells agreed), but its Hurts came from a real effect.
- **So the open question is the same as before:** does a truly inert skill on a noisy task stay out of Helps and Hurts? It still hasn't been tested on real runs.
- The simulation says it should, but only because real runs mostly agree: no false calls at 94% agreement, against up to 4% with independent coin flips.

## Spend

| | Cost |
|---|---|
| Stage 1 (seven runs) | $10.83 |
| Stage 2: V2 pilot | $0.25 |
| Stage 2: V1 | $1.54 |
| Stage 2: V2 | $1.23 |
| **Total** | **$13.85**, against the $22.83 ceiling ($3.02 of the stage's $12) |

**Haiku vs Sonnet:** only suite 1 has run on both, and its verdict didn't move (Helps, +100 on both). Suite 2 on Sonnet, the comparison that could show drift, has not run.

## Decisions for you

1. **How to treat V2. Recommendation: accept it as a placebo design error, not a rule failure, and run a truly inert placebo (V3).** V3 would use the same commit cases with a body that says nothing about style or format, for example a short note about the team's history. That would also show whether merely firing a skill shifts behavior. Predictions would be committed first. About $1.30 (cap $3).
2. **Holdouts. Recommendation: run both now, once each, under the frozen 0.2.0 rules.** Nothing in V1 or V2 touches them. Holdout 7's filler also says to "describe what changed in plain language", but its grader checks a made-up format (`ZK-318 | web | ...`) that no run passes without the real skill, so that advice can't move its score. About $2.80 (caps $6).
3. **V1's trigger problem. Recommendation: don't chase Hurts with another outdated-rule-in-a-repo skill.** It's a finding that Haiku rarely consults a skill when the repo already answers the question. If you want a Hurts check, plant a wrong rule on a task the model answers from memory, for example a unit-conversion skill with a wrong factor, so the skill is the only source it uses. About $1.30 (cap $3), with predictions committed first.
4. **Suite 2 on Sonnet** (the drift demo): still worth running. The prediction would be committed first. About $1.80 (cap $3).
5. **`check --model` and the README** (both free): do them after 1–4, so the README can report the final numbers.
6. **Old absolute paths in git history. Recommendation: leave them.**
   - They are 7 lines, the `casesRoot` field in the cards committed in ea8021a through 2c991f4, showing an absolute local path.
   - They reveal the local username and folder layout, nothing secret. Your name is already in LICENSE.
   - Rewriting before the first push is possible, since nothing is pushed. But it changes every commit hash from ea8021a on, and the docs cite those hashes (6c37ff9, 03d2619, f848767) as proof that predictions came before results.
   - The options:
     - **Leave them.** Free.
     - **Rewrite and update every cited hash.** About an hour, and the commit order becomes your word rather than the hashes'.
     - **Squash to one commit.** Loses the evidence entirely.

Doing 1 through 4 would cost about $7.20, leaving about $1.80 of the stage ceiling.

## Ready to push?

**No.**
- The README still says "v0.1: the verdict rules have not yet been checked against real eval runs", while the code is 0.2.0 and two rounds of real runs exist. Step 7 fixes that.
- The stop condition is still open, and needs your call on decision 1.
- Decision 6 needs your call before the first push. After a push, rewriting history is much more disruptive.
