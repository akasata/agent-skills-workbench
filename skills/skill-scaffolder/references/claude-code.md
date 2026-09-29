# Claude Code 固有仕様

2026-09-29 時点の一次情報の要約。作業時は以下の一次情報で最新版を確認すること。確認には `claude-code-guide` agent も使える。

- Skills: https://code.claude.com/docs/en/skills.md
- Plugin manifest: https://code.claude.com/docs/en/plugins/manifest-reference.md
- Marketplace: https://code.claude.com/docs/en/plugins/marketplace-reference.md
- インストール: https://code.claude.com/docs/en/plugins/install.md

## Skill の配置（Claude Code が読む場所）

| スコープ | パス |
|---|---|
| Personal | `~/.claude/skills/<name>/SKILL.md` |
| Project | `.claude/skills/<name>/SKILL.md`（サブディレクトリの `.claude/skills/` も読まれる） |
| Plugin | `<plugin-root>/skills/<name>/SKILL.md`。`/<plugin-name>:<skill-name>` として呼び出す。 |

- リポジトリ直下の `skills/` は、Plugin として読み込まれた場合にだけ Claude Code から見える。
- `.claude/skills/` への複製は、この目的のためには不要。

### Claude Code 固有の frontmatter

Agent Skills 標準の 6 フィールドに加えて、次のフィールドを使える。いずれも**標準外**なので、`skills-ref validate` ではエラーになる。

`when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `disallowed-tools`, `model`, `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell`

- `name` は Claude Code では任意（ディレクトリ名が既定値）。ただし標準準拠のため、常に書く。
- 文字数の上限は、`description` と `when_to_use` の合計で 1,536 文字。標準側の上限は `description` 単体で 1024 文字なので、1024 以内に収める。

本文内で使える変数:

- `$ARGUMENTS`、`$N`
- `${CLAUDE_SKILL_DIR}`、`${CLAUDE_PROJECT_DIR}`
- `${CLAUDE_PLUGIN_ROOT}`、`${CLAUDE_PLUGIN_DATA}`（この 2 つは plugin 内の Skill でのみ使える）

これらの変数は Claude Code 固有なので、共通 Skill で使う場合は、他のエージェントでは展開されないことに注意する。

## `.claude-plugin/plugin.json`

- **manifest 自体が任意。** 省略した場合、コンポーネントは自動で探索される。
- **必須は `name` のみ**（kebab-case。空白、`@`、`:` は不可）。
- 主な任意フィールド: `$schema`, `displayName`, `version`, `description`, `author{name,email,url}`, `homepage`, `repository`, `license`, `keywords`, `metadata`, `defaultEnabled`, `dependencies`, `userConfig`

### 既定のディレクトリ

plugin root 直下の次のディレクトリが自動で読まれる。

- `skills/<name>/SKILL.md`
- `commands/`
- `agents/`
- `hooks/hooks.json`
- `.mcp.json`
- `.lsp.json`
- `output-styles/`
- `workflows/`
- `bin/`
- `settings.json`

### パスフィールドの挙動

| 挙動 | 対象フィールド |
|---|---|
| 既定ディレクトリに**追加** | `skills` |
| 既定ディレクトリを**置換** | `commands`, `agents`, `outputStyles`, `workflows` |
| 既定の設定と**マージ** | `hooks`, `mcpServers`, `lspServers` |

- パスは `./` で始まる plugin root からの相対パスにする。`..` で外に出ることはできない。
- 既定の `skills/` を使う場合、`skills` フィールドは不要。
- `version` を設定すると、変更するまでそのバージョンに固定される。marketplace エントリにも `version` がある場合、その扱いは次節を参照。

## `.claude-plugin/marketplace.json`

- **必須:** `name`、`owner{name}`、`plugins[]`
- `description` を省略すると `claude plugin validate` が警告を出す。
- 任意フィールド: `version`、`metadata.pluginRoot`（bare name の解決先）、`forceRemoveDeletedPlugins`、`renames` など。
- marketplace の `name` には予約語がある（例: `agent-skills`、`claude-plugins-official`、`github`、`npm`、`skills-dir`、`inline`、`claudeai-*`）。公式ドキュメントで一覧を確認すること。

### plugin エントリ

- **必須:** `name`、`source`
- **任意:** `description`, `version`, `category`, `tags`, `strict`（既定 `true`）, `author`, `homepage`, `repository`, `license`, `keywords`, `dependencies`, `displayName`, `metadata`
- `version` は `plugin.json` 側の値が優先される。

### source の種類

| 種類 | 形式 |
|---|---|
| 相対パス | 文字列 `"./path"`。リポジトリルートなら `"./"` または `"."`（どちらも `claude plugin validate --strict` を通ることを 2026-09-29 に確認）。 |
| GitHub | `{"source":"github","repo":"owner/repo","ref":...,"sha":...}` |
| Git URL | `{"source":"url","url":...}` |
| モノレポ内のサブディレクトリ | `{"source":"git-subdir","url":...,"path":...}` |
| npm | `{"source":"npm","package":...}` |
| アーカイブ | `{"source":"archive","url":...,"sha256":...}` |
| コマンド | `{"source":"command","command":...}` |

- 相対パスは marketplace root（`.claude-plugin/` の親ディレクトリ）から解決される。

### strict

- `strict: true`（既定）: エントリ側のコンポーネントフィールドが、`plugin.json` の内容に追加される。
- `strict: false`: エントリ側にコンポーネントフィールドがあると、衝突エラーになる。
- `plugin.json` が無い場合は、エントリ自体が manifest として扱われる。

## インストールと検証

インストール:

```
/plugin marketplace add owner/repo
/plugin install <plugin>@<marketplace>
claude plugin marketplace add owner/repo
claude plugin install <plugin>@<marketplace>
```

検証:

- `claude plugin validate <path> [--strict] [--json]`
  - 引数は plugin/marketplace の manifest、またはディレクトリ。
  - ディレクトリを渡した場合、`.claude-plugin/marketplace.json` があれば marketplace だけが検証される。`plugin.json` は個別に指定する。
  - Skill 群を検証するときは、Skill を含む**コンテナディレクトリ**（例: `skills/`、`.claude/skills/`）を渡す。個別の Skill ディレクトリを渡すと、"No manifest found" エラーになる（2026-09-29 に確認）。
- `claude plugin eval`: eval スイートの実行。
- `claude plugin details <name>`: コンポーネントの一覧とトークンコストの表示。
