# agent-skills-workbench

Agent Skills を作成・配布するためのスキル集です。Skill 本体は [Agent Skills](https://agentskills.io) 互換の `SKILL.md` として `skills/` に 1 つだけ置き、各プラットフォームの配布定義からそれを参照します。

## Skills

| Skill | 用途 |
|---|---|
| [`skill-scaffolder`](skills/skill-scaffolder/SKILL.md) | Agent Skill の新規作成・追加と、Claude Code Plugin / Marketplace、Codex、skills.sh 向け配布構成の生成（Skill 本体は 1 つの正本を共有） |

## インストール

### Claude Code

```
/plugin marketplace add akasata/agent-skills-workbench
/plugin install agent-skills-workbench@agent-skills-workbench
```

### Codex

```bash
codex plugin marketplace add akasata/agent-skills-workbench
```

追加後、Codex CLI の `/plugins` からインストールします。

### skills.sh（`npx skills`）

```bash
npx skills add akasata/agent-skills-workbench
```

## 構成

```
.
├─ .claude-plugin/
│  ├─ plugin.json          # Claude Code plugin manifest
│  └─ marketplace.json     # Claude Code marketplace（source: "./"）
├─ .codex-plugin/
│  └─ plugin.json          # Codex plugin manifest（互換形式）
├─ .agents/plugins/
│  └─ marketplace.json     # Codex marketplace（source: "./"）
└─ skills/
   └─ <skill-name>/        # Skill 本体（正本）
      ├─ SKILL.md
      ├─ references/
      └─ scripts/
```

## 開発

このリポジトリで作業中にスキルを読み込むには、plugin として起動します。

```bash
claude --plugin-dir .
```

検証:

```bash
python skills/skill-scaffolder/scripts/check_skill.py .
claude plugin validate .claude-plugin/plugin.json --strict
claude plugin validate .claude-plugin/marketplace.json --strict
claude plugin validate skills --strict
```

## License

[MIT](LICENSE)
