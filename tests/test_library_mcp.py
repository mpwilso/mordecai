"""The MCP server, through the SDK's in-process client: no subprocess, no port, no model."""

import json

import pytest

pytest.importorskip("mcp")
pytest.importorskip("strictyaml")

from libkit import add_card, commit, greeting_library  # noqa: E402
from mcp import Client  # noqa: E402

from mordecai.library.server import build  # noqa: E402
from mordecai.provenance import hash_dir  # noqa: E402


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def setup(gitenv):
    repo = greeting_library(gitenv / "lib")
    add_card(repo, repo / "library/greeting/variants/brief", "1.0.0", "hurts")
    commit(repo, "card")
    proj = gitenv / "proj"
    proj.mkdir()
    cfg = gitenv / "mordecai-library.toml"
    cfg.write_text(
        f'[[source]]\nname = "org"\npath = "{repo}"\n\n[install]\ntargets = ["agents", "claude"]\n'
    )
    return repo, proj, build(cfg, proj)


async def call(server, tool, **args):
    async with Client(server, raise_exceptions=True) as c:
        r = await c.call_tool(tool, args)
    if r.is_error:
        return {"error": " ".join(getattr(b, "text", "") for b in r.content)}
    return r.structured_content or json.loads(r.content[0].text)


@pytest.mark.anyio
async def test_tools_and_their_annotations(setup):
    _, _, server = setup
    async with Client(server) as c:
        tools = {t.name: t for t in (await c.list_tools()).tools}
    assert set(tools) == {
        "list_skills",
        "search_skills",
        "get_skill",
        "skill_history",
        "check_updates",
        "install_skill",
        "uninstall_skill",
    }
    for name in ("install_skill", "uninstall_skill"):
        assert tools[name].annotations.read_only_hint is False
        assert tools[name].annotations.destructive_hint is True
        assert "CHANGES FILES" in tools[name].description
    for name in ("list_skills", "search_skills", "get_skill", "skill_history", "check_updates"):
        assert tools[name].annotations.read_only_hint is True


@pytest.mark.anyio
async def test_reading_tools(setup):
    _, _, server = setup
    listed = await call(server, "list_skills")
    copies = {c["id"]: c for c in listed["skills"][0]["copies"]}
    assert copies["greeting.brief"]["evidence"]["verdict"] == "hurts"
    assert copies["greeting.formal"]["behindBase"] == "1.1.0"
    found = await call(server, "search_skills", query="formal")
    assert [m["id"] for m in found["matches"]] == ["greeting.formal"]
    got = await call(server, "get_skill", skill="greeting", variant="formal")
    assert "Say good day" in got["text"] and got["files"] == ["SKILL.md"]
    old = await call(server, "get_skill", skill="greeting", version="1.0.0")
    assert "warmly" not in old["text"]
    hist = await call(server, "skill_history", skill="greeting")
    assert [v["version"] for v in hist["versions"]] == ["1.1.0", "1.0.0"]


@pytest.mark.anyio
async def test_install_check_updates_and_uninstall(setup):
    repo, proj, server = setup
    r = await call(server, "install_skill", skill="greeting", version="1.0.0")
    assert r["installed"] is True and r["paths"] == [".agents/skills/greeting"]
    installed = proj / ".agents/skills/greeting"
    assert installed.is_dir()
    updates = await call(server, "check_updates")
    assert updates["installs"][0]["available"] == "1.1.0"
    assert updates["installs"][0]["update"] is True
    # Replacing needs a second call, after the diff.
    r = await call(server, "install_skill", skill="greeting")
    assert r["installed"] is False and r["needsConfirmation"] is True
    assert "+Say hello warmly." in r["diff"]
    assert "warmly" not in (installed / "SKILL.md").read_text()
    r = await call(server, "install_skill", skill="greeting", confirm_replace=True)
    assert r["installed"] is True
    assert hash_dir(installed) == hash_dir(repo / "library/greeting/base/greeting")
    r = await call(server, "uninstall_skill", skill="greeting")
    assert r["removed"] == [".agents/skills/greeting"] and not installed.exists()


@pytest.mark.anyio
async def test_install_refuses_hurts_and_targets_outside_the_config(setup):
    _, proj, server = setup
    r = await call(server, "install_skill", skill="greeting", variant="brief")
    assert r["installed"] is False and "hurts" in r["refused"]
    assert not (proj / ".agents").exists()
    for target in ("github", "../../etc", "/tmp/x"):
        r = await call(server, "install_skill", skill="greeting", target=target)
        assert "isn't allowed" in r["error"]
    assert not (proj / ".github").exists()


@pytest.mark.anyio
async def test_errors_are_tool_errors_not_crashes(setup):
    _, _, server = setup
    r = await call(server, "get_skill", skill="../etc")
    assert "isn't valid" in r["error"]
    r = await call(server, "uninstall_skill", skill="greeting")
    assert "no install" in r["error"]


@pytest.mark.anyio
async def test_mordecai_mcp_runs_over_stdio(setup, gitenv):
    """The real entry point, as a client would start it: only protocol messages on stdout."""
    import os
    import sys

    from mcp import StdioServerParameters

    repo, proj, _ = setup
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "mordecai",
            "mcp",
            "--config",
            str(gitenv / "mordecai-library.toml"),
            "--project",
            str(proj),
        ],
        env=dict(os.environ),
    )
    async with Client(params) as c:
        tools = (await c.list_tools()).tools
        r = await c.call_tool("list_skills", {})
    assert len(tools) == 7
    assert not r.is_error, r.content
    data = r.structured_content or json.loads(r.content[0].text)
    assert data["skills"][0]["skill"] == "greeting"
