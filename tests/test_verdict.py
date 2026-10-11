"""Each verdict, in the order the rules apply, and the warnings."""

import json
from dataclasses import replace

from conftest import FIXTURES, fired_in, make_result, same

from mordecai.result import parse
from mordecai.verdict import Rules, read


def verdict_of(cases, **kw):
    return read(parse(make_result(cases, **kw)), ["demo-skill"])


def test_helps():
    r = verdict_of(same(6, [1, 1, 1], [0, 0, 0], fired=[True] * 3))
    assert r.verdict == "helps"
    assert r.change == 1.0
    assert (r.improved, r.flat, r.worse) == (6, 0, 0)
    assert r.fired == (18, 18)


def test_helps_with_an_interval_when_cases_differ():
    cases = same(4, [1, 1, 1], [0, 0, 0], fired=[True] * 3)
    cases += same(2, [1, 1, 1], [1, 0, 0], fired=[True] * 3)
    r = verdict_of(cases)
    assert r.verdict == "helps" and r.agreement is None
    lo, hi = r.interval
    assert 0 < lo < hi <= 1.0
    assert r.reason.startswith("The skill raised the score: 90% interval ")


def test_hurts():
    r = verdict_of(same(6, [0, 0, 0], [1, 1, 1], fired=[True] * 3))
    assert r.verdict == "hurts"
    assert r.reason == (
        "The skill lowered the score by 100 points in 6 of 6 cases. At 90% confidence, up to "
        "32% of cases like these could differ."
    )


def test_already_handled():
    r = verdict_of(same(10, [1, 1, 1], [1, 1, 1], fired=[True] * 3))
    assert r.verdict == "already-handled"
    assert r.without_score == 1.0


def test_no_effect_when_the_model_fails_either_way():
    r = verdict_of(same(10, [0, 0, 0], [0, 0, 0], fired=[True] * 3))
    assert r.verdict == "no-effect"


def test_when_every_case_agrees_the_card_counts_cases_instead_of_a_point_interval():
    """D22 (a): the bootstrap can only return one number, so the card reports N of N cases and
    an exact one-sided binomial bound on the share of cases that could differ."""
    r = verdict_of(same(9, [1, 1, 1], [0, 0, 0], fired=[True] * 3))
    assert r.verdict == "helps"
    assert r.interval is None
    assert r.agreement == (9, 0.2257)
    assert r.reason == (
        "The skill raised the score by 100 points in 9 of 9 cases. At 90% confidence, up to "
        "23% of cases like these could differ."
    )


def test_the_bound_is_clopper_pearson_at_the_rules_confidence():
    """With none of n cases differing, the exact one-sided upper bound p solves
    P(no case differs | p) = (1 - p)^n = 1 - confidence."""
    from mordecai.verdict import agreement_bound

    for n in range(1, 40):
        for conf in (0.8, 0.9, 0.95):
            p = agreement_bound(n, conf)
            assert abs((1 - p) ** n - (1 - conf)) < 1e-12, (n, conf)
    assert round(agreement_bound(5, 0.9), 4) == 0.3690
    assert round(agreement_bound(10, 0.9), 4) == 0.2057
    r = read(parse(make_result(same(9, [1, 1, 1], [0, 0, 0]))), rules=Rules(confidence=0.95))
    assert r.agreement == (9, round(agreement_bound(9, 0.95), 4))
    assert "At 95% confidence, up to 28% of cases" in r.reason


def test_cases_with_the_same_mean_change_but_noisy_runs_keep_their_interval():
    """D22 (a) applies only when the bootstrap has nothing to resample: runs that disagree
    inside a case still give it spread."""
    r = verdict_of(same(9, [1, 1, 0], [0, 0, 0], fired=[True] * 3))
    assert r.agreement is None
    lo, hi = r.interval
    assert lo < hi


def test_no_effect_and_already_handled_need_10_cases():
    """D22 (b): a null claims the effect is near zero, which takes more cases than a large
    effect does. Helps and Hurts keep the minimum of 5."""
    r = verdict_of(same(9, [1, 1, 1], [1, 1, 1], fired=[True] * 3))
    assert r.verdict == "inconclusive"
    assert r.agreement == (9, 0.2257)
    assert r.reason == (
        "The change was +0 points in 9 of 9 cases, but Already handled needs at least 10 "
        "compared cases. At 90% confidence, up to 23% of cases like these could differ."
    )
    r = verdict_of(same(9, [0, 0, 0], [0, 0, 0], fired=[True] * 3))
    assert r.verdict == "inconclusive"
    assert "but No effect needs at least 10 compared cases" in r.reason
    r = verdict_of(same(10, [0, 0, 0], [0, 0, 0], fired=[True] * 3))
    assert r.verdict == "no-effect"
    assert r.reason == (
        "The change was +0 points in 10 of 10 cases, inside plus or minus 10 points. At 90% "
        "confidence, up to 21% of cases like these could differ."
    )
    r = verdict_of(same(10, [1, 1, 1], [1, 1, 1], fired=[True] * 3))
    assert r.reason == (
        "The model scored 100% without the skill, and the change was +0 points in 10 of 10 "
        "cases. At 90% confidence, up to 21% of cases like these could differ."
    )
    assert verdict_of(same(5, [1, 1, 1], [0, 0, 0])).verdict == "helps"
    assert verdict_of(same(5, [0, 0, 0], [1, 1, 1])).verdict == "hurts"


def test_a_null_interval_under_10_cases_is_inconclusive_too():
    noisy = same(9, [0.52, 0.5, 0.48], [0.5, 0.5, 0.5], fired=[True] * 3)
    r = verdict_of(noisy)
    assert r.agreement is None and r.interval is not None
    assert r.verdict == "inconclusive"
    assert r.reason.startswith("The 90% interval (")
    assert r.reason.endswith(
        "stays inside plus or minus 10 points, but No effect needs at least 10 compared cases; "
        "9 were compared."
    )
    more = noisy + [{**noisy[0], "name": "case-9"}]
    assert verdict_of(more).verdict == "no-effect"


def test_the_null_threshold_is_not_a_rule_field():
    """D20: a card's rules must equal the engine's, so a new Rules field would break every
    recorded library card. The threshold is a constant, like D21's."""
    from dataclasses import fields

    from mordecai.verdict import NULL_MIN_CASES

    assert NULL_MIN_CASES == 10
    names = {f.name for f in fields(Rules)}
    assert names == {"min_cases", "min_effect", "ceiling", "confidence", "resamples", "seed"}


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
    r = verdict_of(same(10, [0.55, 0.55, 0.55], [0.5, 0.5, 0.5], fired=[True] * 3))
    assert r.verdict == "no-effect"


def test_never_fired_beats_a_good_score():
    r = verdict_of(same(6, [1, 1, 1], [0, 0, 0], fired=[False] * 3))
    assert r.verdict == "never-fired"
    assert r.reason == "The skill didn't fire in any of the 18 runs where it should have."


def test_a_skill_that_fired_in_1_of_27_runs_is_rarely_fired():
    """D21: the model barely opened the skill, so the interval says little about it. Every case
    agrees, so without the rule this would be Already handled."""
    r = verdict_of(fired_in(1, 9, [1, 1, 1], [1, 1, 1]))
    assert r.fired == (1, 27)
    assert r.verdict == "rarely-fired"
    assert r.reason == (
        "The skill fired in only 1 of the 27 runs where it should have, under 10%, so the "
        "change says little about it."
    )
    assert r.interval is None


def test_rarely_fired_beats_no_effect_and_too_few_cases():
    assert verdict_of(fired_in(1, 9, [0, 0, 0], [0, 0, 0])).verdict == "rarely-fired"
    assert verdict_of(fired_in(1, 4, [1, 1, 1], [0, 0, 0])).verdict == "rarely-fired"


def test_rarely_fired_is_under_10_percent_exactly():
    assert verdict_of(fired_in(2, 10, [1, 1, 1], [1, 1, 1])).verdict == "rarely-fired"  # 7%
    assert verdict_of(fired_in(4, 12, [1, 1, 1], [1, 1, 1])).verdict == "already-handled"  # 11%
    r = verdict_of(fired_in(2, 10, [1, 1], [1, 1]))  # exactly 10%
    assert r.fired == (2, 20) and r.verdict == "already-handled"


def test_firing_in_under_half_the_runs_is_a_warning_not_a_verdict():
    r = verdict_of(fired_in(10, 10, [1, 1, 1], [1, 1, 1]))
    assert r.fired == (10, 30)
    assert r.verdict == "already-handled"
    warning = (
        "The skill fired in only 10 of the 30 runs where it should have, so the change mostly "
        "reflects runs where it wasn't used."
    )
    assert warning in r.warnings
    # A Rarely fired card already says so in its reason, so it doesn't repeat it as a warning.
    rare = verdict_of(fired_in(2, 9, [1, 1, 1], [1, 1, 1]))
    assert rare.verdict == "rarely-fired"
    assert not any("runs where it wasn't used" in w for w in rare.warnings)
    edge = verdict_of(fired_in(3, 10, [1, 1, 1], [1, 1, 1]))  # 10%: a verdict, so the warning
    assert warning.replace("10 of", "3 of") in edge.warnings


def test_no_fire_warning_at_half_or_more_or_never():
    for fired in (14, 27, 0):
        r = verdict_of(fired_in(fired, 9, [1, 1, 1], [1, 1, 1]))
        assert not any("runs where it wasn't used" in w for w in r.warnings), fired
    assert verdict_of(fired_in(0, 9, [1, 1, 1], [1, 1, 1])).verdict == "never-fired"


def test_invalid_beats_rarely_fired():
    cases = fired_in(1, 9, [1, 1, 1], [1, 1, 1])
    r = verdict_of(cases, partial=True, partial_reason="cost_ceiling")
    assert r.verdict == "invalid"


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
    cases = same(10, [1, 1, 1], [1, 1, 1], fired=[True] * 3)
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
    assert r.cases_compared == 10
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


def test_runs_the_setup_blocked_make_the_card_invalid():
    """D19: a refusal inside the run's own folder means the setup, not the skill, decided it."""
    cases = same(6, [1, 1, 1], [0, 0, 0], fired=[True] * 3)
    suite = parse(make_result(cases))
    r = read(replace(suite, blocked_runs=2), ["demo-skill"])
    assert r.verdict == "invalid" and r.blocked_runs == 2
    assert "2 of 36 runs had a tool call refused inside their own folder" in r.reason
    assert read(suite, ["demo-skill"]).verdict == "helps"
