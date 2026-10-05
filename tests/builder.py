"""Builds claude plugin eval results for tests, the simulation and the brand's demo card."""


def make_result(
    cases,
    *,
    model="claude-opus-5-5",
    partial=False,
    partial_reason=None,
    ablation="with-without",
    plugin_path="/nowhere/plugin",
):
    """A claude plugin eval result in the shape of tests/fixtures/probe-result.json.

    Each case is a dict: name, with (run scores), without (run scores), and optionally
    fired (one bool per with-run), quiet (True for a "must not fire" case, with misfired as
    one bool per with-run), prompt, errors (with-run index to error text) and skipped (True
    to mark every run as having skipped its paid graders).
    """
    out = []
    for c in cases:
        graders = [{"name": "result", "type": "regex", "weight": 1, "config": {}}]
        if c.get("fired") is not None:
            graders.append(
                {"name": "fired", "type": "tool_used", "weight": 1, "config": {"tool": "Skill"}}
            )
        if c.get("quiet"):
            graders.append(
                {
                    "name": "quiet",
                    "type": "tool_used",
                    "weight": 1,
                    "config": {"tool": "Skill", "min": 0, "max": 0},
                }
            )

        def run(score, i, arm, c=c):
            gs = [{"name": "result", "passed": score >= 1, "scored": True}]
            if arm == "with" and c.get("fired") is not None:
                gs.append({"name": "fired", "passed": c["fired"][i], "scored": False})
            if c.get("quiet"):
                mis = c.get("misfired", [False] * 99)[i] if arm == "with" else False
                gs.append({"name": "quiet", "passed": not mis, "scored": True})
            return {
                "score": score,
                "passed": score >= 1,
                "turns": 2,
                "costUsd": 0.02 if arm == "with" else 0.015,
                "judgeCostUsd": 0,
                "error": (c.get("errors") or {}).get(i) if arm == "with" else None,
                "skippedPaidGraders": bool(c.get("skipped")),
                "graders": gs,
            }

        out.append(
            {
                "name": c["name"],
                "dir": f"evals/{c['name']}",
                "promptMarkdown": c.get("prompt", f"Do task {c['name']}."),
                "runsPerCase": len(c["with"]),
                "graders": graders,
                "arms": {
                    "with": [run(s, i, "with") for i, s in enumerate(c["with"])],
                    "without": [run(s, i, "without") for i, s in enumerate(c["without"])],
                },
            }
        )
    return {
        "schemaVersion": 1,
        "claudeVersion": "2.1.289",
        "startedAt": "2026-10-05T12:00:00.000Z",
        "costUsd": 1.0,
        "partial": partial,
        "partialReason": partial_reason,
        "suite": {
            "root": plugin_path,
            "ablation": ablation,
            "modelOverride": model,
            "judgeModel": "claude-haiku-4-5-20251001",
            "plugins": [{"name": "demo", "version": "1.0.0", "path": plugin_path}],
        },
        "cases": out,
    }


def same(n, with_, without, **extra):
    """n cases that all ran the same way."""
    return [{"name": f"case-{i}", "with": with_, "without": without, **extra} for i in range(n)]
