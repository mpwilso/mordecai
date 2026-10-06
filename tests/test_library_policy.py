"""The default refusals (Hurts, Invalid, broken) can't be dropped by any file: not a config, not
a project's own mordecai-library.toml, not a lockfile. Only --allow, typed at the command line
for one install or update, overrides them."""

import io
import json

import pytest

pytest.importorskip("strictyaml")

from libkit import add_card, commit, greeting_library  # noqa: E402

from mordecai.cli import main  # noqa: E402
from mordecai.library import install as inst  # noqa: E402
from mordecai.library.lock import Lock  # noqa: E402
from mordecai.library.sources import Library, load_config  # noqa: E402

LOOSE = "refuse = []"


def run(argv):
    out = io.StringIO()
    code = main(argv, out=out)
    return code, out.getvalue()


@pytest.fixture
def cloned(gitenv, monkeypatch):
    """A library with a Hurts variant, and a project someone else wrote whose own config lists
    that library and tries to switch the gate off."""
    repo = greeting_library(gitenv / "lib")
    add_card(repo, repo / "library/greeting/variants/brief", "1.0.0", "hurts")
    commit(repo, "card")
    proj = gitenv / "cloned-project"
    proj.mkdir()
    (proj / "mordecai-library.toml").write_text(
        f'[[source]]\nname = "theirs"\npath = "{repo}"\n\n'
        f'[variants]\ngreeting = "brief"\n\n[policy]\n{LOOSE}\n'
    )
    monkeypatch.chdir(proj)
    return repo, proj


def test_a_cloned_projects_config_cant_switch_the_gate_off(cloned):
    _, proj = cloned
    assert load_config(None, proj).refuse == ("hurts", "invalid", "broken")
    code, text = run(["library", "install", "greeting"])
    assert code == 1 and "Refused" in text and "hurts" in text
    assert not (proj / ".agents").exists()


def test_every_config_location_gets_the_defaults(cloned, gitenv, monkeypatch):
    repo, proj = cloned
    loose = gitenv / "elsewhere.toml"
    loose.write_text(f'[[source]]\nname = "s"\npath = "{repo}"\n[policy]\n{LOOSE}\n')
    user = gitenv / "xdg-config" / "mordecai"
    user.mkdir(parents=True)
    (user / "library.toml").write_text(loose.read_text())
    assert load_config(loose).refuse[:3] == ("hurts", "invalid", "broken")
    monkeypatch.setenv("MORDECAI_LIBRARY_CONFIG", str(loose))
    assert load_config(None, gitenv).refuse[:3] == ("hurts", "invalid", "broken")
    monkeypatch.delenv("MORDECAI_LIBRARY_CONFIG")
    assert load_config(None, gitenv / "nowhere").refuse[:3] == ("hurts", "invalid", "broken")


def test_only_allow_at_the_command_line_overrides(cloned):
    _, proj = cloned
    code, _ = run(["library", "install", "greeting", "--allow", "hurts"])
    assert code == 0
    lock = json.loads((proj / "mordecai-lock.json").read_text())
    assert lock["installed"][".agents/skills/greeting"]["allowed"] == ["hurts"]


def test_a_lockfiles_recorded_override_is_never_reused(cloned):
    """A lockfile may have been edited; an entry saying hurts was allowed doesn't let update or
    check_updates take a Hurts version without a person typing --allow."""
    repo, proj = cloned
    assert run(["library", "install", "greeting", "--variant", "formal"])[0] == 0
    lock_path = proj / "mordecai-lock.json"
    doc = json.loads(lock_path.read_text())
    entry = doc["installed"][".agents/skills/greeting"]
    entry.update(variant="brief", allowed=["hurts"])
    lock_path.write_text(json.dumps(doc))
    with Library(load_config(None, proj)) as lib:
        [u] = inst.plan_updates(lib, inst.project(proj), Lock(lock_path), force=True)
    assert u.plan.refused and "hurts" in u.plan.refused
    code, text = run(["library", "update", "--yes", "--force"])
    assert code == 1 and "refused" in text
    code, text = run(["library", "update", "--yes", "--force", "--allow", "hurts"])
    assert code == 0, text


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_the_mcp_server_uses_the_defaults_too(cloned):
    pytest.importorskip("mcp")
    from mcp import Client

    from mordecai.library.server import build

    _, proj = cloned
    async with Client(build(None, proj)) as c:
        r = await c.call_tool("install_skill", {"skill": "greeting"})
    assert not r.is_error, r.content
    data = r.structured_content or json.loads(r.content[0].text)
    assert data["installed"] is False and "hurts" in data["refused"]
    assert not (proj / ".agents").exists()
