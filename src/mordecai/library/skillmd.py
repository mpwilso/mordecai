"""Reads and checks one stored skill folder against the Agent Skills spec.

Frontmatter is parsed with strictyaml, the parser the reference validator (skills-ref) uses, so
what this accepts matches it: no flow style, anchors, tags or duplicate keys, and every scalar
is a string. A folder may hold only regular files and folders, so that an install can copy it
byte for byte and a card's hash still verifies; a link or anything else is an error.

Everything here may come from someone else. Limits on size and file count come first, and no
file is opened through a link.
"""

import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path

import strictyaml

from mordecai.library import LibraryError
from mordecai.library.versions import check_name, valid_name

MAX_FRONTMATTER = 64 * 1024
MAX_SKILL_MD = 1 << 20
MAX_FILES = 1000
MAX_BYTES = 20 * 1024 * 1024
MAX_LINES = 500
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
STAMPS = ("mordecai-version", "mordecai-variant", "mordecai-based-on")
# A path component from a source may not carry control characters or a backslash.
BAD_PART = re.compile(r"[\x00-\x1f\x7f\\]")


@dataclass
class Report:
    """What checking one folder found. errors make it unusable; warnings don't."""

    fields: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    executable: bool = False

    @property
    def stamps(self) -> dict[str, str]:
        meta = self.fields.get("metadata")
        return {k: meta[k] for k in STAMPS if isinstance(meta, dict) and k in meta}


def split(text: str) -> tuple[str, str]:
    """(frontmatter, body) of a SKILL.md. It must open with a --- line and close with one."""
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise LibraryError("SKILL.md should start with a '---' line opening the frontmatter")
    end = re.search(r"^---[ \t]*$", text[4:], re.M)
    if end is None:
        raise LibraryError("SKILL.md's frontmatter has no closing '---' line")
    head = text[4 : 4 + end.start()]
    if len(head.encode()) > MAX_FRONTMATTER:
        raise LibraryError(f"SKILL.md's frontmatter is over {MAX_FRONTMATTER // 1024} KB")
    return head, text[4 + end.end() :].lstrip("\n")


def _load_yaml(head: str) -> dict:
    try:
        data = strictyaml.load(head).data
    except strictyaml.YAMLError as e:
        first = str(e).strip().splitlines()
        raise LibraryError(
            "SKILL.md's frontmatter isn't YAML the spec's validator accepts: "
            + (first[0] if first else type(e).__name__)
        ) from e
    if not isinstance(data, dict):
        raise LibraryError("SKILL.md's frontmatter should be a list of key: value fields")
    return data


def frontmatter(text: str) -> tuple[dict, str]:
    head, body = split(text)
    return _load_yaml(head), body


def _string(fields: dict, key: str, high: int, errors: list[str], required: bool) -> None:
    """A text field of 1 to high characters."""
    low = 1
    value = fields.get(key)
    if value is None:
        if required:
            errors.append(f"SKILL.md has no {key}")
        return
    if not isinstance(value, str):
        errors.append(f"SKILL.md's {key} should be text")
    elif len(value.strip()) < low or len(value) > high:
        errors.append(f"SKILL.md's {key} should be {low} to {high} characters, not {len(value)}")


def check_fields(fields: dict, folder_name: str, report: Report) -> None:
    e = report.errors
    name = fields.get("name")
    if not isinstance(name, str):
        e.append("SKILL.md has no name")
    elif not valid_name(name):
        e.append(
            f"SKILL.md's name {name!r} isn't valid: 1 to 64 characters of a-z, 0-9 and single "
            "hyphens, not starting or ending with a hyphen"
        )
    elif name != folder_name:
        e.append(f"SKILL.md's name {name!r} doesn't match its folder {folder_name!r}")
    _string(fields, "description", 1024, e, required=True)
    _string(fields, "compatibility", 500, e, required=False)
    for key in ("license", "allowed-tools"):
        if key in fields and not isinstance(fields[key], str):
            e.append(f"SKILL.md's {key} should be text")
    meta = fields.get("metadata")
    if meta is not None and not (
        isinstance(meta, dict) and all(isinstance(v, str) for v in meta.values())
    ):
        e.append("SKILL.md's metadata should map names to text values, with nothing nested")
    extra = sorted(set(fields) - SPEC_FIELDS)
    if extra:
        report.warnings.append(
            f"SKILL.md has fields outside the spec ({', '.join(extra)}). Some tools accept them, "
            "but skills-ref validate and claude.ai uploads refuse them."
        )


def walk(folder: Path) -> tuple[list[str], list[str], bool]:
    """(files, errors, has an executable file) for a folder, links never followed. Stops at
    the file count or size limit."""
    files, errors, executable, total = [], [], False, 0

    def visit(d: Path, prefix: str) -> None:
        nonlocal executable, total
        with os.scandir(d) as it:
            entries = sorted(it, key=lambda x: x.name)
        for entry in entries:
            rel = prefix + entry.name
            if BAD_PART.search(entry.name):
                errors.append(f"{rel!r} has a control character or backslash in its name")
                continue
            mode = entry.stat(follow_symlinks=False).st_mode
            if stat.S_ISDIR(mode):
                visit(Path(entry.path), rel + "/")
            elif stat.S_ISREG(mode):
                files.append(rel)
                total += entry.stat(follow_symlinks=False).st_size
                executable = executable or bool(mode & 0o111)
            elif stat.S_ISLNK(mode):
                errors.append(f"{rel} is a symbolic link; a stored skill may hold only files")
            else:
                errors.append(f"{rel} isn't a regular file or folder")
            if len(files) > MAX_FILES or total > MAX_BYTES:
                raise LibraryError(
                    f"{folder.name} has more than {MAX_FILES} files or "
                    f"{MAX_BYTES // 2**20} MB; a skill folder must be smaller"
                )

    visit(folder, "")
    return files, errors, executable


def check_folder(folder: Path, skill: str) -> Report:
    """Everything wrong with folder as a stored copy of skill. Never raises for bad content;
    a LibraryError only for a folder over the size limits."""
    report = Report()
    check_name(skill)
    if folder.is_symlink() or not folder.is_dir():
        report.errors.append(f"{folder.name} should be a folder, not a link or a file")
        return report
    if folder.name != skill:
        report.errors.append(f"the skill folder {folder.name!r} should be named {skill!r}")
    report.files, errors, report.executable = walk(folder)
    report.errors += errors
    skill_md = folder / "SKILL.md"
    if "SKILL.md" not in report.files:
        report.errors.append(f"{skill}/SKILL.md is missing")
        return report
    if skill_md.stat().st_size > MAX_SKILL_MD:
        report.errors.append("SKILL.md is over 1 MB")
        return report
    try:
        text = skill_md.read_bytes().decode("utf-8")
        report.fields, body = frontmatter(text)
    except UnicodeDecodeError:
        report.errors.append("SKILL.md isn't UTF-8 text")
        return report
    except LibraryError as e:
        report.errors.append(str(e))
        return report
    check_fields(report.fields, folder.name, report)
    lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    if lines > MAX_LINES:
        report.warnings.append(f"SKILL.md has {lines} lines; the spec suggests under {MAX_LINES}")
    if not body.strip():
        report.warnings.append("SKILL.md has no instructions after the frontmatter")
    if any(f.startswith("scripts/") for f in report.files):
        report.executable = True
    return report


def set_stamps(text: str, values: dict[str, str]) -> str:
    """SKILL.md text with the given mordecai-* metadata values set. Each key that is already
    there is rewritten in place; a missing one is added after the last stamp, or at the end
    of the metadata block. Only the frontmatter changes."""
    head, _ = split(text)
    body_start = 4 + len(head)
    lines = head.split("\n")
    meta = next((i for i, line in enumerate(lines) if re.fullmatch(r"metadata:\s*", line)), None)
    if meta is None:
        raise LibraryError("SKILL.md has no metadata block to write version stamps into")
    end = meta + 1
    while end < len(lines) and (lines[end].startswith((" ", "\t")) or not lines[end].strip()):
        end += 1
    while end > meta + 1 and not lines[end - 1].strip():
        end -= 1
    indent = "  "
    for i in range(meta + 1, end):
        if lines[i].strip():
            indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
            break
    for key, value in values.items():
        line = f'{indent}{key}: "{value}"'
        at = next(
            (i for i in range(meta + 1, end) if re.match(rf"\s+{re.escape(key)}:", lines[i])), None
        )
        if at is not None:
            lines[at] = line
            continue
        stamps = [i for i in range(meta + 1, end) if lines[i].strip().startswith("mordecai-")]
        at = (stamps[-1] if stamps else end - 1) + 1
        lines.insert(at, line)
        end += 1
    new_text = "---\n" + "\n".join(lines) + text.replace("\r\n", "\n")[body_start:]
    fields, _ = frontmatter(new_text)
    got = fields.get("metadata") or {}
    if any(got.get(k) != v for k, v in values.items()):
        raise LibraryError("couldn't write the version stamps into SKILL.md's metadata")
    return new_text
