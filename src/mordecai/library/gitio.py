"""Git, read through its objects: a ref resolves to a commit, and files come from that commit with
`git cat-file`, never from a checkout. So no filter, hook or fsmonitor command from a source
repository runs, and an install is always pinned to a SHA.

GitHub sources are fetched over HTTPS into a bare repository in the cache. A token for private
repositories comes only from MORDECAI_GITHUB_TOKEN or GITHUB_TOKEN. It is passed to Git in the
environment as an HTTP header for github.com, never on a command line, and is scrubbed from any
message Git prints.
"""

import base64
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from mordecai.library import LibraryError
from mordecai.library.paths import no_links, open_new
from mordecai.library.skillmd import BAD_PART

GITHUB = "https://github.com"
REPO = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}")
SHA = re.compile(r"[0-9a-f]{40}")
TOKEN_VARS = ("MORDECAI_GITHUB_TOKEN", "GITHUB_TOKEN")
SAFE = ["-c", "core.fsmonitor=false", "-c", "protocol.ext.allow=never"]
# The most bytes a source's materialized files may take, across one command.
MAX_TREE_BYTES = 200 * 1024 * 1024


def token() -> str | None:
    for var in TOKEN_VARS:
        value = os.environ.get(var)
        if value:
            return value
    return None


def _scrub(text: str) -> str:
    secret = token()
    if secret:
        text = text.replace(secret, "***")
        text = text.replace(base64.b64encode(f"x-access-token:{secret}".encode()).decode(), "***")
    return text


def _env(auth: bool) -> dict[str, str]:
    """The environment for git: no prompts, plain messages, and with auth the token header added
    after any GIT_CONFIG_* entries the user already set."""
    env = dict(os.environ)
    env.update(GIT_TERMINAL_PROMPT="0", LC_ALL="C", GIT_OPTIONAL_LOCKS="0")
    secret = token() if auth else None
    if secret:
        try:
            n = int(env.get("GIT_CONFIG_COUNT", "0"))
        except ValueError:
            n = 0
        basic = base64.b64encode(f"x-access-token:{secret}".encode()).decode()
        env[f"GIT_CONFIG_KEY_{n}"] = f"http.{GITHUB}/.extraheader"
        env[f"GIT_CONFIG_VALUE_{n}"] = f"AUTHORIZATION: basic {basic}"
        env["GIT_CONFIG_COUNT"] = str(n + 1)
    return env


def git(repo: Path | None, *args: str, auth: bool = False, check: bool = True, config=()) -> str:
    """git's standard output. A failure is a LibraryError with git's message, token removed.
    config is extra -c settings, as a flat list."""
    cmd = ["git", *SAFE, *config] + (["-C", str(repo)] if repo is not None else []) + list(args)
    try:
        done = subprocess.run(cmd, capture_output=True, env=_env(auth), timeout=300, check=False)
    except FileNotFoundError as e:
        raise LibraryError("git isn't installed or isn't on PATH") from e
    except subprocess.TimeoutExpired as e:
        raise LibraryError(f"git {args[0]} took more than five minutes") from e
    if check and done.returncode != 0:
        msg = _scrub(done.stderr.decode("utf-8", "replace").strip()).splitlines()
        raise LibraryError(f"git {args[0]} failed: {msg[-1] if msg else done.returncode}")
    return done.stdout.decode("utf-8", "replace")


def is_repo(path: Path) -> bool:
    done = subprocess.run(
        ["git", *SAFE, "-C", str(path), "rev-parse", "--git-dir"],
        capture_output=True,
        env=_env(False),
        check=False,
    )
    return done.returncode == 0


def toplevel(path: Path) -> Path:
    return Path(git(path, "rev-parse", "--show-toplevel").strip())


def resolve(repo: Path, ref: str) -> str:
    """The commit SHA ref names."""
    if ref.startswith("-") or BAD_PART.search(ref) or not ref:
        raise LibraryError(f"{ref!r} isn't a ref Mordecai will use")
    out = git(
        repo,
        "rev-parse",
        "--verify",
        "--quiet",
        "--end-of-options",
        f"{ref}^{{commit}}",
        check=False,
    ).strip()
    if not SHA.fullmatch(out):
        raise LibraryError(f"{ref!r} isn't a branch, tag or commit in {repo}")
    return out


@dataclass(frozen=True)
class Tag:
    name: str
    commit: str
    date: str  # YYYY-MM-DD, from the tag (or the commit, for a lightweight tag)


def library_tags(repo: Path, within: str | None = None) -> list[Tag]:
    """Every skill/* tag, or only those whose commit is in within's history."""
    args = [
        "for-each-ref",
        "--format=%(refname:strip=2)%00%(objectname)%00%(*objectname)%00%(creatordate:short)",
        "refs/tags/skill/",
    ]
    if within:
        args.insert(1, f"--merged={within}")
    tags = []
    for line in git(repo, *args).splitlines():
        name, obj, peeled, date = (line.split("\0") + ["", "", "", ""])[:4]
        commit = peeled or obj
        if SHA.fullmatch(commit):
            tags.append(Tag(name, commit, date))
    return tags


def has_path(repo: Path, commit: str, path: str) -> bool:
    done = subprocess.run(
        ["git", *SAFE, "-C", str(repo), "cat-file", "-e", f"{commit}:{path}"],
        capture_output=True,
        env=_env(False),
        check=False,
    )
    return done.returncode == 0


@dataclass(frozen=True)
class Entry:
    mode: str
    kind: str
    sha: str
    path: str


def tree(repo: Path, commit: str, prefix: str = "") -> list[Entry]:
    """Every entry under prefix in commit's tree, recursively."""
    args = ["ls-tree", "-r", "-z", "--full-tree", commit]
    if prefix:
        args += ["--", prefix]
    out = []
    for item in git(repo, *args).split("\0"):
        if not item:
            continue
        meta, _, path = item.partition("\t")
        mode, kind, sha = meta.split(" ")
        out.append(Entry(mode, kind, sha, path))
    return out


def safe_path(path: str) -> PurePosixPath:
    p = PurePosixPath(path)
    if (
        p.is_absolute()
        or not p.parts
        or any(part in ("..", ".", ".git") or BAD_PART.search(part) for part in p.parts)
    ):
        raise LibraryError(f"the source has a path Mordecai won't write: {path!r}")
    return p


class Reader:
    """Reads blobs with one `git cat-file --batch` process."""

    def __init__(self, repo: Path):
        self.proc = subprocess.Popen(
            ["git", *SAFE, "-C", str(repo), "cat-file", "--batch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=_env(False),
        )

    def read(self, sha: str) -> bytes:
        assert self.proc.stdin and self.proc.stdout
        self.proc.stdin.write(sha.encode() + b"\n")
        self.proc.stdin.flush()
        header = self.proc.stdout.readline().decode().split()
        if len(header) != 3 or header[1] != "blob":
            raise LibraryError(f"git couldn't read object {sha}")
        size = int(header[2])
        data = self.proc.stdout.read(size)
        self.proc.stdout.read(1)
        return data

    def close(self) -> None:
        if self.proc.stdin:
            self.proc.stdin.close()
        self.proc.wait(timeout=30)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def materialize(repo: Path, commit: str, prefix: str, dest: Path, budget: list[int]) -> None:
    """Write the files under prefix in commit into dest, at the same relative paths. Links are
    written as links and never followed; submodules are left out. budget is a one-item list of
    bytes still allowed, shared across calls."""
    entries = tree(repo, commit, prefix)
    with Reader(repo) as reader:
        for e in entries:
            rel = safe_path(e.path)
            target = dest.joinpath(*rel.parts)
            if e.kind != "blob" or target.exists() or target.is_symlink():
                continue
            data = reader.read(e.sha)
            budget[0] -= len(data)
            if budget[0] < 0:
                raise LibraryError("the source is too large to read")
            # A link written earlier is never gone through: on a case-insensitive file system
            # a link "A" and a file "a/b" from one tree would otherwise meet.
            no_links(dest, target.parent)
            target.parent.mkdir(parents=True, exist_ok=True)
            no_links(dest, target)
            if e.mode == "120000":
                os.symlink(os.fsdecode(data), target)
            else:
                with os.fdopen(open_new(target, 0o755 if e.mode == "100755" else 0o644), "wb") as f:
                    f.write(data)


def cache_dir() -> Path:
    if os.environ.get("MORDECAI_CACHE"):
        return Path(os.environ["MORDECAI_CACHE"])
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "mordecai"


def fetch_github(repo: str, ref: str | None) -> tuple[Path, str]:
    """(bare repository, commit SHA) for owner/repo at ref, fetched into the cache. The default
    branch when ref is None. Library tags are fetched too."""
    if not REPO.fullmatch(repo) or ".." in repo:
        raise LibraryError(f"{repo!r} isn't a GitHub repository of the form owner/name")
    bare = cache_dir() / "git" / f"{repo}.git"
    if not (bare / "HEAD").exists():
        bare.parent.mkdir(parents=True, exist_ok=True)
        git(None, "init", "--quiet", "--bare", str(bare))
    url = f"{GITHUB}/{repo}.git"
    specs = ["+refs/tags/skill/*:refs/tags/skill/*"]
    want = "HEAD"
    if ref is None:
        specs.append("+HEAD:refs/mordecai/head")
        want = "refs/mordecai/head"
    elif SHA.fullmatch(ref):
        specs.append(ref)
        want = ref
    else:
        if ref.startswith("-") or BAD_PART.search(ref) or ":" in ref:
            raise LibraryError(f"{ref!r} isn't a ref Mordecai will use")
        specs.append(f"+{ref}:refs/mordecai/ref")
        want = "refs/mordecai/ref"
    # Only HTTPS to github.com (the tests point GITHUB at a local folder instead), no submodules,
    # and no hooks, even if the cache's Git config or a template added some.
    guard = ["-c", f"core.hooksPath={os.devnull}"]
    if url.startswith("https://"):
        guard += ["-c", "protocol.allow=never", "-c", "protocol.https.allow=always"]
    git(
        bare,
        "fetch",
        "--quiet",
        "--no-tags",
        "--no-recurse-submodules",
        "--",
        url,
        *specs,
        auth=url.startswith("https://github.com/"),
        config=guard,
    )
    return bare, resolve(bare, want)
