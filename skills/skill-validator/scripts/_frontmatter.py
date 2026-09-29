"""Shared helpers: locate SKILL.md files and parse their YAML frontmatter.

Uses PyYAML when available; otherwise falls back to a minimal parser that
handles top-level scalars, block scalars (| and >), and one level of nested
string maps (enough for the Agent Skills frontmatter fields).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}


def iter_skill_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if "SKILL.md" in filenames:
            yield Path(dirpath) / "SKILL.md"


def split_frontmatter(text: str):
    """Return (frontmatter_text, body) or (None, text) if absent."""
    text = text.lstrip("﻿")
    m = re.match(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", text, re.S)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def parse_yaml(fm: str) -> dict:
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(fm)
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise ValueError("frontmatter is not a mapping")
        return data
    except ImportError:
        return _minimal_parse(fm)


def _minimal_parse(fm: str) -> dict:
    lines = fm.splitlines()
    out: dict = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            raise ValueError(f"cannot parse line: {line!r}")
        key, val = m.group(1), m.group(2).strip()
        i += 1
        if val in ("|", ">", "|-", ">-", "|+", ">+") or val == "":
            block = []
            while i < len(lines) and (not lines[i].strip() or lines[i].startswith((" ", "\t"))):
                block.append(lines[i])
                i += 1
            if val == "":
                nested = {}
                for b in block:
                    if not b.strip():
                        continue
                    nm = re.match(r"^\s+([A-Za-z0-9_.-]+):\s*(.*)$", b)
                    if not nm:
                        raise ValueError(f"cannot parse nested line: {b!r}")
                    nested[nm.group(1)] = _unquote(nm.group(2).strip())
                out[key] = nested if nested else None
            else:
                stripped = [b.strip() for b in block]
                out[key] = ("\n" if val.startswith("|") else " ").join(s for s in stripped if s)
        else:
            out[key] = _unquote(val)
    return out


def _unquote(v: str):
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v in ("true", "false"):
        return v == "true"
    return v
