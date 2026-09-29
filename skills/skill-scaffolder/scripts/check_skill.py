#!/usr/bin/env python3
"""Check SKILL.md files against Agent Skills spec constraints, and sanity-check
distribution manifests. Read-only.

Usage:
  python check_skill.py [repo-root | skill-dir ...]

Exit code 1 if any ERROR is found. WARNINGs do not fail the run.

This mirrors the constraints documented at https://agentskills.io/specification
(as summarised in ../references/agent-skills.md). It is not the official
validator; run `skills-ref validate` too when it is installed.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _frontmatter import iter_skill_files, parse_yaml, split_frontmatter  # noqa: E402

SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
# Documented Claude Code extensions (see ../references/claude-code.md).
CLAUDE_CODE_FIELDS = {
    "when_to_use", "argument-hint", "arguments", "disable-model-invocation", "user-invocable",
    "disallowed-tools", "model", "effort", "context", "agent", "background", "hooks", "paths", "shell",
}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_BODY_LINES = 500

errors = 0
warnings = 0


def err(where: str, msg: str) -> None:
    global errors
    errors += 1
    print(f"  ERROR   {where}: {msg}")


def warn(where: str, msg: str) -> None:
    global warnings
    warnings += 1
    print(f"  WARNING {where}: {msg}")


def check_skill(skill_md: Path, base: Path) -> None:
    where = skill_md.parent.relative_to(base).as_posix() if skill_md.parent != base else "."
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fm, body = split_frontmatter(text)
    if fm is None:
        err(where, "SKILL.md has no YAML frontmatter delimited by ---")
        return
    try:
        data = parse_yaml(fm)
    except Exception as e:  # noqa: BLE001
        err(where, f"frontmatter parse error: {e}")
        return

    extra = set(data) - SPEC_FIELDS
    cc = extra & CLAUDE_CODE_FIELDS
    unknown = extra - CLAUDE_CODE_FIELDS
    if cc:
        warn(where, f"Claude Code-specific fields {sorted(cc)} are outside the Agent Skills spec "
                    "(skills-ref validate will reject them)")
    if unknown:
        err(where, f"unexpected frontmatter fields {sorted(unknown)} (not in Agent Skills spec)")

    name = data.get("name")
    if not isinstance(name, str) or not name:
        err(where, "missing required 'name'")
    else:
        name_n = unicodedata.normalize("NFKC", name)
        if len(name_n) > 64:
            err(where, f"name longer than 64 chars ({len(name_n)})")
        if not NAME_RE.match(name_n):
            err(where, f"name '{name}' must be lowercase alphanumerics and single hyphens, "
                       "no leading/trailing hyphen")
        dirname = unicodedata.normalize("NFKC", skill_md.parent.name)
        if name_n != dirname:
            err(where, f"name '{name}' does not match directory name '{skill_md.parent.name}'")

    desc = data.get("description")
    if not isinstance(desc, str) or not desc.strip():
        err(where, "missing or empty required 'description'")
    elif len(desc) > 1024:
        err(where, f"description longer than 1024 chars ({len(desc)})")

    comp = data.get("compatibility")
    if comp is not None and (not isinstance(comp, str) or not (1 <= len(comp) <= 500)):
        err(where, "compatibility must be a string of 1-500 chars")

    meta = data.get("metadata")
    if meta is not None:
        if not isinstance(meta, dict):
            err(where, "metadata must be a map")
        else:
            bad = [k for k, v in meta.items() if not isinstance(k, str) or not isinstance(v, str)]
            if bad:
                warn(where, f"metadata values should be strings (keys: {bad})")

    at = data.get("allowed-tools")
    if at is not None and not isinstance(at, str):
        warn(where, "allowed-tools should be a space-separated string per the Agent Skills spec")

    lic = data.get("license")
    if lic is not None and not isinstance(lic, str):
        err(where, "license must be a string")

    n_lines = body.count("\n") + 1
    if n_lines > MAX_BODY_LINES:
        warn(where, f"SKILL.md body is {n_lines} lines; spec recommends < {MAX_BODY_LINES}")

    # Referenced relative files should exist.
    for ref in sorted(set(re.findall(r"`((?:references|scripts|assets)/[^`\s]+)`", body))):
        if not (skill_md.parent / ref).exists():
            err(where, f"referenced file '{ref}' does not exist")

    for sub in ("references", "scripts", "assets"):
        d = skill_md.parent / sub
        if d.is_dir() and not any(d.iterdir()):
            warn(where, f"empty directory '{sub}/' (create supporting dirs only when needed)")


def check_json_files(root: Path) -> None:
    candidates = [
        ".claude-plugin/plugin.json", ".claude-plugin/marketplace.json", "plugin.json",
        ".codex-plugin/plugin.json", ".agents/plugins/marketplace.json",
    ]
    candidates += [p.relative_to(root).as_posix() for p in root.glob("*/**/.claude-plugin/plugin.json")]
    candidates += [p.relative_to(root).as_posix() for p in root.glob("*/**/.codex-plugin/plugin.json")]
    for rel in dict.fromkeys(candidates):
        p = root / rel
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            err(rel, f"invalid JSON: {e}")
            continue
        print(f"  ok      {rel}: valid JSON")
        if not isinstance(data, dict):
            err(rel, "top level must be an object")
            continue
        if rel.endswith("plugin.json") and "name" not in data:
            if rel == "plugin.json" or rel.endswith(".claude-plugin/plugin.json"):
                err(rel, "missing 'name'")
            else:
                warn(rel, "missing 'name' (falls back to folder name in Codex)")
        if rel.endswith("marketplace.json"):
            check_marketplace(rel, data, root)


def check_marketplace(rel: str, data: dict, root: Path) -> None:
    required = ["name", "plugins"] + (["owner"] if rel.startswith(".claude-plugin") else [])
    for k in required:
        if k not in data:
            err(rel, f"missing required '{k}'")
    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        return
    plugin_root = (data.get("metadata") or {}).get("pluginRoot") if isinstance(data.get("metadata"), dict) else None
    seen = set()
    for i, entry in enumerate(plugins):
        tag = f"{rel} plugins[{i}]"
        if not isinstance(entry, dict):
            err(tag, "entry must be an object")
            continue
        name = entry.get("name")
        if not name:
            err(tag, "missing 'name'")
        elif name in seen:
            err(tag, f"duplicate plugin name '{name}'")
        seen.add(name)
        src = entry.get("source")
        path = None
        if isinstance(src, str):
            path = src
        elif isinstance(src, dict) and src.get("source") == "local":
            path = src.get("path")
        elif src is None:
            err(tag, "missing 'source'")
        if path is not None:
            if ".." in Path(path).parts:
                err(tag, f"source path '{path}' must not contain '..'")
            if not path.startswith(".") and plugin_root:
                target = root / plugin_root / path
            else:
                target = root / path
            if not target.is_dir():
                err(tag, f"source path '{path}' does not exist (resolved from marketplace root)")
        if rel.startswith(".agents/plugins"):
            pol = entry.get("policy") or {}
            for k in ("installation", "authentication"):
                if k not in pol:
                    warn(tag, f"Codex docs say to always include policy.{k}")
            if "category" not in entry:
                warn(tag, "Codex docs say to always include 'category'")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [Path(a).resolve() for a in sys.argv[1:]] or [Path(".").resolve()]
    for target in args:
        print(f"== {target}")
        if (target / "SKILL.md").is_file():
            check_skill(target / "SKILL.md", target.parent)
            continue
        skills = sorted(iter_skill_files(target))
        print(f"  {len(skills)} SKILL.md file(s) found")
        for s in skills:
            check_skill(s, target)
        check_json_files(target)
    print(f"\nResult: {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
