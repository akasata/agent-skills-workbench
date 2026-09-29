#!/usr/bin/env python3
"""Inventory a repository's skills and distribution manifests (read-only).

Usage: python inspect_repo.py [repo-root]

Reports:
  - every SKILL.md with its frontmatter name and location category
  - known platform manifests / marketplace files that exist
  - duplicate skills (same name in several places, or identical content)
  - symlinks inside skill-related directories
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}


def iter_skill_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if "SKILL.md" in filenames:
            yield Path(dirpath) / "SKILL.md"


def frontmatter_name(text: str) -> str:
    """Best-effort `name` lookup for the inventory (full validation lives in skill-validator)."""
    m = re.match(r"^﻿?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", text, re.S)
    if not m:
        return "? (no frontmatter)"
    nm = re.search(r"^name:[ \t]*(.+?)[ \t]*$", m.group(1), re.M)
    return nm.group(1).strip("\"'") if nm else "?"

KNOWN_FILES = [
    (".claude-plugin/plugin.json", "Claude Code plugin manifest"),
    (".claude-plugin/marketplace.json", "Claude Code marketplace"),
    ("plugin.json", "root plugin.json (Codex/Agent Plugins format if $schema says so)"),
    (".codex-plugin/plugin.json", "Codex plugin manifest (compat format)"),
    (".agents/plugins/marketplace.json", "Codex marketplace"),
    (".cursor-plugin/plugin.json", "Cursor plugin manifest"),
    (".mcp.json", "Claude Code MCP config"),
    ("mcp.json", "Agent Plugins MCP config"),
    ("README.md", "README"),
]


def category(rel: Path) -> str:
    parts = rel.parts
    s = "/".join(parts)
    if s.startswith(".claude/skills/"):
        return "Claude Code project skill (.claude/skills)"
    if s.startswith(".agents/skills/"):
        return "Codex/agents repo skill (.agents/skills)"
    if s.startswith(".codex/skills/"):
        return "Codex legacy (.codex/skills)"
    if "skills" in parts:
        idx = parts.index("skills")
        prefix = "/".join(parts[:idx]) or "."
        return f"skills dir under {prefix}"
    if len(parts) == 1:
        return "repo root skill"
    return "other"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    print(f"Repository: {root}\n")

    print("== Manifests / distribution files")
    found_any = False
    for rel, desc in KNOWN_FILES:
        p = root / rel
        if p.exists():
            found_any = True
            extra = ""
            if p.suffix == ".json":
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        keys = ", ".join(list(data.keys())[:12])
                        extra = f"  keys: {keys}"
                        if "plugins" in data and isinstance(data["plugins"], list):
                            names = [str(e.get("name")) for e in data["plugins"] if isinstance(e, dict)]
                            extra += f"\n      plugins: {names}"
                except Exception as e:  # noqa: BLE001
                    extra = f"  (JSON parse error: {e})"
            print(f"  [x] {rel} — {desc}{extra}")
    # nested plugin manifests (e.g. plugins/<p>/.claude-plugin/plugin.json)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = Path(dirpath).relative_to(root)
        if rel_dir == Path("."):
            continue
        for mdir in (".claude-plugin", ".codex-plugin"):
            if Path(dirpath).name == mdir and "plugin.json" in filenames and rel_dir.parent != Path("."):
                found_any = True
                print(f"  [x] {rel_dir.as_posix()}/plugin.json — nested plugin manifest")
    if not found_any:
        print("  (none)")

    print("\n== Skills")
    by_name: dict[str, list[str]] = defaultdict(list)
    by_hash: dict[str, list[str]] = defaultdict(list)
    skills = sorted(iter_skill_files(root))
    if not skills:
        print("  (none)")
    for f in skills:
        rel = f.relative_to(root)
        raw = f.read_bytes()
        by_hash[hashlib.sha256(raw).hexdigest()].append(rel.as_posix())
        name = frontmatter_name(raw.decode("utf-8", errors="replace"))
        by_name[name].append(rel.as_posix())
        subdirs = sorted(p.name for p in f.parent.iterdir() if p.is_dir())
        print(f"  - {rel.parent.as_posix()}  name={name}  [{category(rel)}]"
              + (f"  subdirs={subdirs}" if subdirs else ""))

    print("\n== Possible duplication")
    dup = False
    for name, paths in by_name.items():
        if len(paths) > 1:
            dup = True
            print(f"  same name '{name}': {paths}")
    for paths in by_hash.values():
        if len(paths) > 1:
            dup = True
            print(f"  identical content: {paths}")
    if not dup:
        print("  (none)")

    print("\n== Symlinks")
    links = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames_keep = []
        for d in dirnames:
            full = Path(dirpath) / d
            if full.is_symlink():
                links.append(full)
            elif d not in SKIP_DIRS:
                dirnames_keep.append(d)
        dirnames[:] = dirnames_keep
        links += [Path(dirpath) / fn for fn in filenames if (Path(dirpath) / fn).is_symlink()]
    for link in links:
        try:
            target = os.readlink(link)
        except OSError:
            target = "?"
        print(f"  {link.relative_to(root).as_posix()} -> {target}")
    if not links:
        print("  (none)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
