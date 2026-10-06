"""Each verdict, in the order the rules apply, and the warnings."""

import json
from dataclasses import replace

from conftest import FIXTURES, make_result, same

from mordecai.result import parse
from mordecai.verdict import Rules, read


def verdict_of(cases, **kw):
    return read(parse(make_result(cases, **kw)), ["demo-skill"])


def test_helps():
    r = verdict_of(same(6, [1, 1, 1], [0, 0, 0], fired=[True] * 3))
    assert r.verdict == "helps"
    assert r.change == 1.0 and r.interval == (1.0, 1.0)
    assert (r.improved, r.flat, r.worse) == (6, 0, 0)
    assert r.fired == (18, 18)


def test_hurts():
    r = verdict_of(same(6, [0, 0, 0], [1, 1, 1], fired=[True] * 3))
    assert r.verdict == "hurts"
    assert r.reason == "The skill lowered the score: 90% interval -100 to -100 points."


def test_already_handled():
    r = verdict_of(same(6, [1, 1, 1], [1, 1, 1], fired=[True] * 3))
    assert r.verdict == "already-handled"
    assert r.without_score == 1.0


def test_no_effect_when_the_model_fails_either_way():
    r = verdict_of(same(6, [0, 0, 0], [0, 0, 0], fired=[True] * 3))
    assert r.verdict == "no-effect"


def test_inconclusive_when_cases_disagree():
    cases = same(3, [1, 1, 1], [0, 0, 0], fired=[True] * 3)
    cases += [
        {"name": f"down-{i}", "with": [0, 0, 0], "without": [1, 1, 1], "fired": [True] * 3}
        for i in range(3)
    ]
    r = verdict_of(cases)
    assert r.verdict == "inconclusive"
    assert "too wide to call" in r.reason
    assert (r.improved, r.worse) == (3, 3)


def test_too_few_cases_is_inconclusive_whatever_the_change():
    r = verdict_of(same(4, [1, 1, 1], [0, 0, 0], fired=[True] * 3))
    assert r.verdict == "inconclusive"
    assert r.reason == "Only 4 case(s) were compared; the rules need at least 5."
    assert r.interval is None


def test_small_gain_under_the_minimum_effect_is_not_helps():
    # Every case gains 5 points: real, but under the 10-point minimum.
    r = verdict_of(same(6, [0.55, 0.55, 0.55], [0.5, 0.5, 0.5], fired=[True] * 3))
    assert r.verdict == "no-effect"


def test_never_fired_beats_a_good_score():
    r = verdict_of(same(6, [1, 1, 1], [0, 0, 0], fired=[False] * 3))
    assert r.verdict == "never-fired"
    assert r.reason == "The skill didn't fire in any of the 18 runs where it should have."


def test_partial_is_invalid():
    r = verdict_of(same(6, [1, 1, 1], [0, 0, 0]), partial=True, partial_reason="cost_ceiling")
    assert r.verdict == "invalid"
    assert r.reason == "The eval stopped early (cost_ceiling)."


def test_a_rate_limit_is_invalid_not_a_regression():
    cases = same(6, [1, 1, 1], [1, 1, 1])
    cases[0] = {**cases[0], "with": [0, 1, 1], "errors": {0: "API Error: 429 rate_limit_error"}}
    r = verdict_of(cases)
    assert r.verdict == "invalid"
    assert "1 of 36 runs hit a usage or rate limit." in r.reason


def test_other_errors_are_data_with_a_warning():
    cases = same(6, [1, 1, 1], [0, 0, 0], fired=[True] * 3)
    cases[0] = {**cases[0], "errors": {0: "timed out after 300s"}}
    r = verdict_of(cases)
    assert r.verdict == "helps"
    assert any("1 of 36 runs ended with an error" in w for w in r.warnings)


def with_denials(cases, with_denied, without_denied, **kw):
    """The reading of cases where the first with_denied with-runs and the first without_denied
    without-runs, counted across cases, had a tool call refused."""
    suite = parse(make_result(cases, **kw))
    left = {"with": with_denied, "without": without_denied}

    def mark(runs, arm):
        out = []
        for r in runs:
            out.append(replace(r, denied=left[arm] > 0))
            left[arm] -= 1
        return tuple(out)

    cases = tuple(
        replace(
            c, with_runs=mark(c.with_runs, "with"), without_runs=mark(c.without_runs, "without")
        )
        for c in suite.cases
    )
    return read(replace(suite, cases=cases), ["demo-skill"])


def test_refused_tool_calls_are_a_warning_not_a_verdict():
    cases = same(6, [1, 1, 1], [0, 0, 0], fired=[True] * 3)
    r = with_denials(cases, 1, 2)
    assert r.verdict == "helps"
    assert (
        "3 of 36 runs had a tool call refused by permissions (1 with the skill, 2 without). "
        "They were graded on what they produced, so a refusal, not the skill, may have moved "
        "their scores." in r.warnings
    )


def test_refusals_are_counted_only_in_runs_whose_traces_were_read():
    cases = same(6, [1, 1, 1], [0, 0, 0], fired=[True] * 3)
    assert not any("refused" in w for w in with_denials(cases, 0, 0).warnings)
    assert not any("refused" in w for w in verdict_of(cases).warnings)
    suite = parse(make_result(cases))
    first = suite.cases[0]
    first = replace(first, with_runs=(replace(first.with_runs[0], denied=True),))
    r = read(replace(suite, cases=(first,) + suite.cases[1:]), ["demo-skill"])
    assert "1 of the 1 runs whose traces were read (of 34) had a tool call refused" in " ".join(
        r.warnings
    )


def test_skipped_judges_are_invalid():
    r = verdict_of(same(6, [1, 1, 1], [0, 0, 0], skipped=True))
    assert r.verdict == "invalid"
    assert "skipped their judge graders" in r.reason


def test_no_baseline_is_invalid():
    r = verdict_of(same(6, [1, 1, 1], []), ablation="none")
    assert r.verdict == "invalid"
    assert "nothing to compare" in r.reason


def test_quiet_cases_are_left_out_of_the_change_and_count_misfires():
    cases = same(6, [1, 1, 1], [1, 1, 1], fired=[True] * 3)
    cases.append(
        {
            "name": "unrelated",
            "with": [0, 1, 1],
            "without": [1, 1, 1],
            "quiet": True,
            "misfired": [True, False, False],
        }
    )
    r = verdict_of(cases)
    assert r.cases_compared == 6
    assert r.verdict == "already-handled"
    assert r.misfired == (1, 3)


def test_warnings():
    cases = same(6, [1], [0], fired=[True], prompt="Use the demo-skill to do this.")
    r = verdict_of(cases, model="sonnet")
    text = " ".join(r.warnings)
    assert "The model was sonnet, not a pinned model ID" in text
    assert "Some cases ran 1 time(s) per side" in text
    assert "No case checks that the skill stays quiet" in text
    assert "6 case prompt(s) name the skill" in text


def test_a_prompt_names_the_skill_only_as_a_whole_word():
    from mordecai.verdict import case_warnings

    def named(prompt, skill):
        cases = parse(make_result(same(1, [1], [0], fired=[True], prompt=prompt))).cases
        return any("name the skill" in w for w in case_warnings(cases, cases, [3], [skill]))

    assert named("Use commit to save this.", "commit")
    assert named("Write a PR description.", "pr-description")
    assert named("Run the pr-description skill.", "pr-description")
    assert not named("Stage the uncommitted files.", "commit")
    assert not named("Demonstrate the change.", "demo")
    assert not named("Improve the project.", "pr")


def test_a_pinned_model_and_a_full_suite_has_no_warnings():
    cases = same(6, [1, 1, 1], [0, 0, 0], fired=[True] * 3)
    cases.append({"name": "quiet", "with": [1, 1, 1], "without": [1, 1, 1], "quiet": True})
    assert verdict_of(cases).warnings == ()


def test_the_interval_is_repeatable():
    cases = same(3, [1, 0, 1], [0, 0, 1], fired=[True] * 3) + same(
        3, [0.5, 1, 0], [0, 0.5, 0], fired=[True] * 3
    )
    suite = parse(make_result(cases))
    assert read(suite).interval == read(suite).interval
    assert read(suite, rules=Rules(seed=1)).interval != read(suite).interval


def test_the_real_result():
    suite = parse(json.loads((FIXTURES / "probe-result.json").read_text()))
    r = read(suite, ["team-signoff"])
    assert r.verdict == "inconclusive"
    assert r.fired == (2, 2)
    assert (r.with_score, r.without_score) == (1.0, 0.0)
    assert round(r.cost_with, 4) == 0.0186 and round(r.cost_without, 4) == 0.0152


def test_already_handled_must_rule_out_a_loss_too():
    """0.2.0: a high baseline with an interval that reaches a 10-point loss is Inconclusive,
    not Already handled."""
    cases = same(6, [1, 1, 1], [1, 1, 1], fired=[True] * 3)
    cases[0] = {**cases[0], "with": [0, 0, 0]}
    cases[1] = {**cases[1], "with": [0, 0, 1]}
    r = verdict_of(cases)
    assert r.without_score == 1.0
    assert r.interval[0] <= -0.10 < r.interval[1]
    assert r.verdict == "inconclusive"
    assert "doesn't rule out a loss of 10 points" in r.reason


def test_suite_3_from_the_planted_check():
    """The real result that motivated the change: an outdated skill that gave the wrong answer
    in 5 of the 6 runs where it fired. The original rules called it Already handled."""
    suite = parse(json.loads((FIXTURES / "suite3-result.json").read_text()))
    r = read(suite, ["python-project-commands"])
    assert r.verdict == "inconclusive"
    assert r.interval == (-0.4074, 0.0741)
    assert (r.improved, r.flat, r.worse) == (1, 6, 2)
    assert r.reason == (
        "The model scored 93% without the skill, but the 90% interval (-41 to +7 points) "
        "doesn't rule out a loss of 10 points."
    )
