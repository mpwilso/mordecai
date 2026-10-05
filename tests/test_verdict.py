"""Each verdict, in the order the rules apply, and the warnings."""

import json

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
