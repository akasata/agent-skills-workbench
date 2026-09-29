#!/usr/bin/env python3
"""Validate Agent Skills and their distribution layout in a repository. Read-only.

Usage:
  python validate.py [--strict] [repo-root | skill-dir ...]

Checks (each finding is tagged with the spec it comes from; see
../references/checks.md for the rule catalogue and primary sources):
  [agent-skills]  SKILL.md frontmatter / structure (agentskills.io)
  [claude-code]   .claude-plugin/plugin.json, .claude-plugin/marketplace.json
  [codex]         plugin.json (Agent Plugins), .codex-plugin/plugin.json,
                  .agents/plugins/marketplace.json
  [skills.sh]     discoverability by `npx skills`
  [consistency]   cross-platform agreement and duplicated skills

Exit code 1 if any ERROR is found (or any WARNING with --strict).
This is not an official validator; also run the platform tools
(`claude plugin validate`, `skills-ref validate`) when they are available.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _frontmatter import iter_skill_files, parse_yaml, split_frontmatter  # noqa: E402

SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
CLAUDE_CODE_FIELDS = {
    "when_to_use", "argument-hint", "arguments", "disable-model-invocation", "user-invocable",
    "disallowed-tools", "model", "effort", "context", "agent", "background", "hooks", "paths", "shell",
}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_BODY_LINES = 500

# Documented reserved Claude Code marketplace names (partial list; see checks.md).
CLAUDE_RESERVED_MARKETPLACES = {
    "claude-code-marketplace", "claude-code-plugins", "claude-plugins-official",
    "anthropic-marketplace", "anthropic-plugins", "agent-skills", "anthropic-agent-skills",
    "life-sciences", "knowledge-work-plugins", "claude-for-legal", "claude-for-financial-services",
    "financial-services-plugins", "first-party-plugins", "claude-tag-plugins", "claude-community",
    "claude-plugins-community", "healthcare", "anthropic-plugin-directory", "claude-plugin-directory",
    "inline", "builtin", "skills-dir", "synced", "claude-plugin-test",
    "npm", "pip", "uv", "cargo", "github", "gh",
}
CLAUDE_PATH_FIELDS = ("skills", "commands", "agents", "hooks", "mcpServers", "lspServers",
                      "outputStyles", "workflows")
AGENT_PLUGIN_SCHEMA_PREFIX = "https://agent-plugins.org/schemas/"
CODEX_COMPAT_FIELDS = {"name", "version", "description", "keywords", "skills", "mcpServers",
                       "apps", "hooks", "interface", "extensions", "commands"}
CODEX_INSTALLATION = {"AVAILABLE", "INSTALLED_BY_DEFAULT", "NOT_AVAILABLE"}
SKILLS_SH_MAX_DEPTH = 3


class Report:
    def __init__(self) -> None:
        self.counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}

    def add(self, level: str, tag: str, where: str, msg: str) -> None:
        self.counts[level] += 1
        print(f"  {level:<7} [{tag}] {where}: {msg}")

    def error(self, tag, where, msg):
        self.add("ERROR", tag, where, msg)

    def warn(self, tag, where, msg):
        self.add("WARNING", tag, where, msg)

    def info(self, tag, where, msg):
        self.add("INFO", tag, where, msg)


R = Report()


def load_json(root: Path, rel: str):
    p = root / rel
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        R.error("json", rel, f"invalid JSON: {e}")
        return None
    if not isinstance(data, dict):
        R.error("json", rel, "top level must be an object")
        return None
    print(f"  ok      [json] {rel}: valid JSON")
    return data


def rel_path_problem(path: str, allow_root: bool) -> str | None:
    if not isinstance(path, str):
        return "path must be a string"
    if path in (".", "./"):
        return None if allow_root else "path must not be the plugin root itself"
    if not path.startswith("./"):
        return "path must start with './'"
    if ".." in Path(path).parts:
        return "path must not contain '..'"
    return None


# --------------------------------------------------------------------------- skills

def check_skill(skill_md: Path, base: Path) -> dict | None:
    where = skill_md.parent.relative_to(base).as_posix() if skill_md.parent != base else "."
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fm, body = split_frontmatter(text)
    if fm is None:
        R.error("agent-skills", where, "SKILL.md has no YAML frontmatter delimited by ---")
        return None
    try:
        data = parse_yaml(fm)
    except Exception as e:  # noqa: BLE001
        R.error("agent-skills", where, f"frontmatter parse error: {e}")
        return None

    extra = set(data) - SPEC_FIELDS
    cc = extra & CLAUDE_CODE_FIELDS
    unknown = extra - CLAUDE_CODE_FIELDS
    if cc:
        R.warn("agent-skills", where, f"Claude Code-specific fields {sorted(cc)} are outside the "
               "Agent Skills spec (skills-ref validate rejects them; other agents ignore them)")
    if unknown:
        R.error("agent-skills", where, f"unexpected frontmatter fields {sorted(unknown)}")

    name = data.get("name")
    if not isinstance(name, str) or not name:
        R.error("agent-skills", where, "missing required 'name'")
    else:
        name_n = unicodedata.normalize("NFKC", name)
        if len(name_n) > 64:
            R.error("agent-skills", where, f"name longer than 64 chars ({len(name_n)})")
        if not NAME_RE.match(name_n):
            R.error("agent-skills", where, f"name '{name}' must be lowercase alphanumerics and single "
                    "hyphens, no leading/trailing hyphen")
        if name_n != unicodedata.normalize("NFKC", skill_md.parent.name):
            R.error("agent-skills", where, f"name '{name}' does not match directory name "
                    f"'{skill_md.parent.name}'")

    desc = data.get("description")
    if not isinstance(desc, str) or not desc.strip():
        R.error("agent-skills", where, "missing or empty required 'description'")
    elif len(desc) > 1024:
        R.error("agent-skills", where, f"description longer than 1024 chars ({len(desc)})")

    comp = data.get("compatibility")
    if comp is not None and (not isinstance(comp, str) or not (1 <= len(comp) <= 500)):
        R.error("agent-skills", where, "compatibility must be a string of 1-500 chars")

    meta = data.get("metadata")
    if meta is not None:
        if not isinstance(meta, dict):
            R.error("agent-skills", where, "metadata must be a map")
        else:
            bad = [k for k, v in meta.items() if not isinstance(k, str) or not isinstance(v, str)]
            if bad:
                R.warn("agent-skills", where, f"metadata values should be strings (keys: {bad})")
            if meta.get("internal") in (True, "true"):
                R.info("skills.sh", where, "metadata.internal is true: hidden from `npx skills` "
                       "unless INSTALL_INTERNAL_SKILLS=1")

    at = data.get("allowed-tools")
    if at is not None and not isinstance(at, str):
        R.warn("agent-skills", where, "allowed-tools should be a space-separated string")

    lic = data.get("license")
    if lic is not None and not isinstance(lic, str):
        R.error("agent-skills", where, "license must be a string")

    n_lines = body.count("\n") + 1
    if n_lines > MAX_BODY_LINES:
        R.warn("agent-skills", where, f"SKILL.md body is {n_lines} lines; spec recommends < {MAX_BODY_LINES}")

    for ref in sorted(set(re.findall(r"`((?:references|scripts|assets)/[^`\s]+)`", body))):
        if not (skill_md.parent / ref).exists():
            R.error("agent-skills", where, f"referenced file '{ref}' does not exist")

    for sub in ("references", "scripts", "assets"):
        d = skill_md.parent / sub
        if d.is_dir() and not any(d.iterdir()):
            R.warn("agent-skills", where, f"empty directory '{sub}/'")

    return {"name": name if isinstance(name, str) else None, "path": where,
            "hash": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def check_skills_sh_depth(root: Path, skills: list[Path], declared: set[Path]) -> None:
    container = root / "skills"
    for s in skills:
        d = s.parent
        try:
            depth = len(d.relative_to(container).parts)
        except ValueError:
            continue
        if depth > SKILLS_SH_MAX_DEPTH and d.resolve() not in declared:
            R.warn("skills.sh", d.relative_to(root).as_posix(),
                   f"nested {depth} levels under skills/; `npx skills` walks {SKILLS_SH_MAX_DEPTH} levels "
                   "unless declared in a .claude-plugin manifest")


def check_duplicates(infos: list[dict]) -> None:
    by_name, by_hash = defaultdict(list), defaultdict(list)
    for i in infos:
        if i["name"]:
            by_name[i["name"]].append(i["path"])
        by_hash[i["hash"]].append(i["path"])
    for name, paths in by_name.items():
        if len(paths) > 1:
            R.warn("consistency", name, f"same skill name in several places {paths}; keep one canonical copy")
    for paths in by_hash.values():
        if len(paths) > 1:
            R.warn("consistency", paths[0], f"identical SKILL.md content duplicated at {paths}")


# --------------------------------------------------------------------------- claude code

def check_claude_plugin(root: Path, rel: str, data: dict) -> None:
    plugin_root = (root / rel).parent.parent
    name = data.get("name")
    if not isinstance(name, str) or not name:
        R.error("claude-code", rel, "missing required 'name'")
    elif re.search(r"[\s@:]", name) or not NAME_RE.match(name):
        R.warn("claude-code", rel, f"name '{name}' should be kebab-case without spaces, '@' or ':'")
    author = data.get("author")
    if author is not None and (not isinstance(author, dict) or "name" not in author):
        R.error("claude-code", rel, "author must be an object with 'name'")
    for field in CLAUDE_PATH_FIELDS:
        val = data.get(field)
        vals = val if isinstance(val, list) else [val] if isinstance(val, str) else []
        for v in vals:
            if v.startswith(("http://", "https://")):
                continue
            prob = rel_path_problem(v, allow_root=(field == "skills"))
            if prob:
                R.error("claude-code", rel, f"{field}: '{v}' {prob}")
            elif not (plugin_root / v).exists():
                R.error("claude-code", rel, f"{field}: '{v}' does not exist")
    if not (plugin_root / "skills").is_dir() and "skills" not in data:
        R.info("claude-code", rel, "no skills/ directory at plugin root")


def check_claude_marketplace(root: Path, rel: str, data: dict) -> dict[str, dict]:
    for k in ("name", "owner", "plugins"):
        if k not in data:
            R.error("claude-code", rel, f"missing required '{k}'")
    name = data.get("name")
    if isinstance(name, str):
        low = name.lower()
        if low in CLAUDE_RESERVED_MARKETPLACES or low.startswith("claudeai-"):
            R.error("claude-code", rel, f"marketplace name '{name}' is reserved")
        if re.search(r"[\s/\\]|\.\.", name):
            R.error("claude-code", rel, f"marketplace name '{name}' has forbidden characters")
    owner = data.get("owner")
    if owner is not None and (not isinstance(owner, dict) or "name" not in owner):
        R.error("claude-code", rel, "owner must be an object with 'name'")
    if "description" not in data and "description" not in (data.get("metadata") or {}):
        R.warn("claude-code", rel, "no description (claude plugin validate warns about this)")
    meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    return check_plugin_entries(root, rel, data, "claude-code", meta.get("pluginRoot"))


# --------------------------------------------------------------------------- codex

def check_codex_manifests(root: Path, root_pj: dict | None, compat: dict | None) -> None:
    if root_pj is not None:
        schema = str(root_pj.get("$schema", ""))
        if schema.startswith(AGENT_PLUGIN_SCHEMA_PREFIX):
            if not root_pj.get("name"):
                R.error("codex", "plugin.json", "missing 'name'")
            if compat is not None:
                R.warn("codex", "plugin.json", "both root plugin.json (Agent Plugins) and "
                       ".codex-plugin/plugin.json exist; Codex uses the root one")
        else:
            R.info("codex", "plugin.json", "root plugin.json has no Agent Plugins $schema; "
                   "Codex does not treat it as a plugin manifest")
    if compat is not None:
        rel = ".codex-plugin/plugin.json"
        ignored = sorted(set(compat) - CODEX_COMPAT_FIELDS - {"$schema"})
        if ignored:
            R.info("codex", rel, f"fields ignored by Codex (compat format): {ignored}")
        for field in ("skills", "mcpServers", "apps", "hooks"):
            val = compat.get(field)
            vals = val if isinstance(val, list) else [val] if isinstance(val, str) else []
            for v in vals:
                prob = rel_path_problem(v, allow_root=False)
                if prob:
                    R.warn("codex", rel, f"{field}: '{v}' {prob} (Codex ignores it)")
                elif not (root / v).exists():
                    R.error("codex", rel, f"{field}: '{v}' does not exist")
        iface = compat.get("interface")
        if isinstance(iface, dict):
            prompts = iface.get("defaultPrompt")
            if isinstance(prompts, str):
                prompts = [prompts]
            if isinstance(prompts, list):
                if len(prompts) > 3:
                    R.warn("codex", rel, "interface.defaultPrompt: at most 3 entries are used")
                for p in prompts:
                    if isinstance(p, str) and len(p) > 128:
                        R.warn("codex", rel, "interface.defaultPrompt entry longer than 128 chars")


def check_codex_marketplace(root: Path, rel: str, data: dict) -> dict[str, dict]:
    for k in ("name", "plugins"):
        if k not in data:
            R.error("codex", rel, f"missing required '{k}'")
    entries = check_plugin_entries(root, rel, data, "codex", None)
    for i, entry in enumerate(data.get("plugins") or []):
        if not isinstance(entry, dict):
            continue
        tag = f"{rel} plugins[{i}]"
        pol = entry.get("policy") if isinstance(entry.get("policy"), dict) else {}
        inst = pol.get("installation")
        if inst is None:
            R.warn("codex", tag, "docs say to always include policy.installation")
        elif inst not in CODEX_INSTALLATION:
            R.error("codex", tag, f"policy.installation '{inst}' not one of {sorted(CODEX_INSTALLATION)}")
        if "authentication" not in pol:
            R.warn("codex", tag, "docs say to always include policy.authentication")
        if "category" not in entry:
            R.warn("codex", tag, "docs say to always include 'category'")
    return entries


# --------------------------------------------------------------------------- shared

def check_plugin_entries(root: Path, rel: str, data: dict, tag_name: str,
                         plugin_root: str | None) -> dict[str, dict]:
    """Validate marketplace plugin entries; return {name: {"dir": Path|None, "entry": dict}}."""
    out: dict[str, dict] = {}
    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        if plugins is not None:
            R.error(tag_name, rel, "'plugins' must be an array")
        return out
    for i, entry in enumerate(plugins):
        tag = f"{rel} plugins[{i}]"
        if not isinstance(entry, dict):
            R.error(tag_name, tag, "entry must be an object")
            continue
        name = entry.get("name")
        if not name:
            R.error(tag_name, tag, "missing 'name'")
        elif name in out:
            R.error(tag_name, tag, f"duplicate plugin name '{name}'")
        src = entry.get("source")
        path = None
        if isinstance(src, str):
            path = src
        elif isinstance(src, dict) and src.get("source") == "local":
            path = src.get("path")
        elif src is None:
            R.error(tag_name, tag, "missing 'source'")
        target = None
        if path is not None:
            if path == "":
                R.error(tag_name, tag, "source path must not be empty")
            elif ".." in Path(path).parts:
                R.error(tag_name, tag, f"source path '{path}' must not contain '..'")
            else:
                base = root / plugin_root if (plugin_root and not path.startswith(".")) else root
                target = (base / path).resolve()
                if not target.is_dir():
                    R.error(tag_name, tag, f"source path '{path}' does not exist")
                    target = None
        if name and name not in out:
            out[name] = {"dir": target, "entry": entry}
    return out


def check_consistency(root: Path, claude_pj, compat, root_pj, claude_mk: dict, codex_mk: dict) -> None:
    manifests = {k: v for k, v in {
        ".claude-plugin/plugin.json": claude_pj,
        ".codex-plugin/plugin.json": compat,
        "plugin.json": root_pj if root_pj and str(root_pj.get("$schema", "")).startswith(
            AGENT_PLUGIN_SCHEMA_PREFIX) else None,
    }.items() if v is not None}
    for field in ("name", "version"):
        vals = {k: v.get(field) for k, v in manifests.items() if v.get(field) is not None}
        if len(set(map(str, vals.values()))) > 1:
            R.warn("consistency", "plugin manifests", f"'{field}' differs across platforms: {vals}")

    root_resolved = root.resolve()
    for label, entries, pj_rel in (("Claude marketplace", claude_mk, ".claude-plugin/plugin.json"),
                                   ("Codex marketplace", codex_mk, None)):
        for name, e in entries.items():
            d = e["dir"]
            if d is None:
                continue
            cands = [d / ".claude-plugin/plugin.json"] if pj_rel else [
                d / "plugin.json", d / ".codex-plugin/plugin.json", d / ".claude-plugin/plugin.json"]
            for c in cands:
                if not c.is_file():
                    continue
                try:
                    pj = json.loads(c.read_text(encoding="utf-8"))
                except Exception:  # noqa: BLE001
                    break
                if c.name == "plugin.json" and c.parent == d and not str(pj.get("$schema", "")).startswith(
                        AGENT_PLUGIN_SCHEMA_PREFIX):
                    continue
                if pj.get("name") and pj["name"] != name:
                    R.warn("consistency", label, f"entry '{name}' points to a plugin named '{pj['name']}' "
                           f"({c.relative_to(root_resolved).as_posix()})")
                ev = e["entry"].get("version")
                if ev and pj.get("version") and str(ev) != str(pj["version"]):
                    R.warn("consistency", label, f"entry '{name}' version {ev} differs from manifest "
                           f"version {pj['version']} (manifest wins in Claude Code)")
                break
    both = set(claude_mk) & set(codex_mk)
    if claude_mk and codex_mk and not both:
        R.info("consistency", "marketplaces", "Claude and Codex marketplaces share no plugin names")


# --------------------------------------------------------------------------- main

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    argv = sys.argv[1:]
    strict = "--strict" in argv
    targets = [Path(a).resolve() for a in argv if a != "--strict"] or [Path(".").resolve()]

    for target in targets:
        print(f"== {target}")
        if (target / "SKILL.md").is_file():
            check_skill(target / "SKILL.md", target.parent)
            continue

        skills = sorted(iter_skill_files(target))
        print(f"  {len(skills)} SKILL.md file(s) found")
        infos = [i for i in (check_skill(s, target) for s in skills) if i]
        check_duplicates(infos)

        claude_pj = load_json(target, ".claude-plugin/plugin.json")
        claude_mk_data = load_json(target, ".claude-plugin/marketplace.json")
        root_pj = load_json(target, "plugin.json")
        compat = load_json(target, ".codex-plugin/plugin.json")
        codex_mk_data = load_json(target, ".agents/plugins/marketplace.json")

        if claude_pj is not None:
            check_claude_plugin(target, ".claude-plugin/plugin.json", claude_pj)
        for p in sorted(target.glob("*/**/.claude-plugin/plugin.json")):
            rel = p.relative_to(target).as_posix()
            nested = load_json(target, rel)
            if nested is not None:
                check_claude_plugin(target, rel, nested)
        claude_mk = (check_claude_marketplace(target, ".claude-plugin/marketplace.json", claude_mk_data)
                     if claude_mk_data is not None else {})
        check_codex_manifests(target, root_pj, compat)
        codex_mk = (check_codex_marketplace(target, ".agents/plugins/marketplace.json", codex_mk_data)
                    if codex_mk_data is not None else {})
        check_consistency(target, claude_pj, compat, root_pj, claude_mk, codex_mk)

        declared = set()
        for data in (claude_pj, claude_mk_data):
            for e in ([data] + list((data or {}).get("plugins") or [])) if data else []:
                sk = e.get("skills") if isinstance(e, dict) else None
                for v in (sk if isinstance(sk, list) else [sk] if isinstance(sk, str) else []):
                    declared.add((target / v).resolve())
        check_skills_sh_depth(target, skills, declared)

    c = R.counts
    print(f"\nResult: {c['ERROR']} error(s), {c['WARNING']} warning(s), {c['INFO']} info")
    return 1 if c["ERROR"] or (strict and c["WARNING"]) else 0


if __name__ == "__main__":
    sys.exit(main())
