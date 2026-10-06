"""Names, versions and release tags.

Skill and variant names follow the Agent Skills spec: 1 to 64 characters of a-z, 0-9 and
single hyphens, not starting or ending with one. The reference validator also accepts other
lowercase Unicode letters; the library doesn't, since names become folder and tag names.

A release is an annotated tag: skill/<skill>@X.Y.Z for a base, skill/<skill>.<variant>@X.Y.Z
for a variant. Names can't contain "." or "@", so a tag always splits one way.
"""

import re
from dataclasses import dataclass

from mordecai.library import LibraryError

NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
MAX_NAME = 64
RESERVED_VARIANTS = {"base"}
TAG_PREFIX = "skill/"
VERSION = re.compile(r"(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})")
TAG = re.compile(
    re.escape(TAG_PREFIX)
    + r"(?P<skill>[a-z0-9-]+)(?:\.(?P<variant>[a-z0-9-]+))?@(?P<version>[0-9.]+)"
)
BUMPS = ("patch", "minor", "major")


def valid_name(name) -> bool:
    return isinstance(name, str) and len(name) <= MAX_NAME and NAME.fullmatch(name) is not None


def check_name(name, what: str = "skill") -> str:
    """name, if it is a valid skill or variant name; otherwise a LibraryError."""
    if not valid_name(name):
        raise LibraryError(
            f"{what} name {name!r} isn't valid: use 1 to {MAX_NAME} characters of a-z, 0-9 and "
            "single hyphens, not starting or ending with a hyphen"
        )
    if what == "variant" and name in RESERVED_VARIANTS:
        raise LibraryError(f"{name!r} is reserved and can't be a variant name")
    return name


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def bump(self, part: str) -> "Version":
        if part == "major":
            return Version(self.major + 1, 0, 0)
        if part == "minor":
            return Version(self.major, self.minor + 1, 0)
        if part == "patch":
            return Version(self.major, self.minor, self.patch + 1)
        raise LibraryError(f"--bump should be one of {', '.join(BUMPS)}, not {part!r}")


ZERO = Version(0, 0, 0)


def parse_version(text) -> Version:
    """X.Y.Z with no leading zeros and no pre-release or build suffix."""
    m = VERSION.fullmatch(text) if isinstance(text, str) else None
    if not m:
        raise LibraryError(f"{text!r} isn't a version of the form X.Y.Z")
    return Version(*(int(g) for g in m.groups()))


def copy_id(skill: str, variant: str | None) -> str:
    """How a copy is named in tags and listings: the skill, or skill.variant."""
    return f"{skill}.{variant}" if variant else skill


def tag_name(skill: str, variant: str | None, version: Version) -> str:
    return f"{TAG_PREFIX}{copy_id(skill, variant)}@{version}"


def parse_tag(tag: str) -> tuple[str, str | None, Version] | None:
    """(skill, variant, version) for a library tag, or None for any other ref."""
    m = TAG.fullmatch(tag)
    if not m or not valid_name(m["skill"]):
        return None
    variant = m["variant"]
    if variant is not None and (not valid_name(variant) or variant in RESERVED_VARIANTS):
        return None
    try:
        return m["skill"], variant, parse_version(m["version"])
    except LibraryError:
        return None
