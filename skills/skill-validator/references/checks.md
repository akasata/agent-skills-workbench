# 検証ルール一覧

`scripts/validate.py` が実装している検証ルールと、その根拠となる一次情報の一覧。内容は 2026-09-29 時点のもの。

**根拠列の凡例**

| 表記 | 意味 |
|---|---|
| doc | 公式ドキュメントに記載がある |
| src | ソースコードで確認した（ドキュメントには記載なし） |
| 観測 | 公式 CLI の実際の挙動で確認した |

仕様が変わった場合は、このファイルと `scripts/validate.py` をあわせて更新すること。

## 一次情報

| 区分 | URL |
|---|---|
| Agent Skills 標準 | https://agentskills.io/specification |
| Claude Code | https://code.claude.com/docs/en/plugins/manifest-reference.md 、https://code.claude.com/docs/en/plugins/marketplace-reference.md 、https://code.claude.com/docs/en/skills.md |
| Codex | https://developers.openai.com/plugins/build/plugins 、https://learn.chatgpt.com/docs/build-skills 、https://github.com/openai/codex （`codex-rs/core-plugins/src/manifest.rs`、`marketplace.rs`、`loader.rs`） |
| skills.sh | https://github.com/vercel-labs/skills 、https://www.skills.sh/docs |

## [agent-skills]

| ルール | レベル | 根拠 |
|---|---|---|
| frontmatter が `---` で区切られた YAML である | ERROR | doc |
| 標準外のフィールドがない（許可されるのは `name` `description` `license` `compatibility` `metadata` `allowed-tools` の 6 つ） | ERROR。ただし Claude Code 固有のフィールドは WARNING | doc。skills-ref はすべて拒否する |
| `name`: 1–64 文字、`[a-z0-9-]`、先頭・末尾の `-` と連続する `--` は不可、ディレクトリ名と一致 | ERROR | doc |
| `description`: 1–1024 文字 | ERROR | doc |
| `compatibility`: 1–500 文字 | ERROR | doc |
| `metadata` が文字列から文字列への map である | 型違いは ERROR、値が文字列でない場合は WARNING | doc |
| `allowed-tools` がスペース区切りの文字列である | WARNING | doc（Experimental） |
| 本文が 500 行以内である | WARNING | doc（推奨） |
| 本文中の `references/`・`scripts/`・`assets/` への参照先が実在する | ERROR | このツール独自 |
| 空の補助ディレクトリがない | WARNING | このツール独自 |

## [claude-code]

| ルール | レベル | 根拠 |
|---|---|---|
| `plugin.json` に `name` がある | ERROR | doc |
| `plugin.json` の `name` が kebab-case で、空白・`@`・`:` を含まない | WARNING | doc |
| `author` がオブジェクトで、`name` を持つ | ERROR | doc |
| パス系フィールドが `./` で始まり、`..` を含まず、実在する（`skills` のみ `"."` / `"./"` を許可） | ERROR | doc |
| `marketplace.json` に `name`・`owner`・`plugins` がある | ERROR | doc |
| `owner` がオブジェクトで、`name` を持つ | ERROR | doc |
| marketplace 名が予約名でない（主な予約名のみ実装。完全な一覧は公式ドキュメントを参照） | ERROR | doc。ただし `claude plugin validate` は検出しない（観測、2026-09-29）。追加時に拒否されると思われる |
| marketplace に `description` がある | WARNING | doc（`claude plugin validate` も警告を出す） |
| 各エントリに `name` と `source` があり、`name` が重複しない | ERROR | doc |
| 相対 `source` が実在し、`..` を含まない（`"./"` と `"."` は可） | ERROR | doc / 観測 |

## [codex]

| ルール | レベル | 根拠 |
|---|---|---|
| ルートの `plugin.json` が Agent Plugins の `$schema` を宣言し、`name` を持つ | ERROR | doc |
| ルートの `plugin.json` と `.codex-plugin/plugin.json` が併存していない（併存するとルートの方が優先される） | WARNING | src |
| `.codex-plugin/plugin.json` に、Codex が無視するフィールドがない | INFO | src（未知のフィールドは無視される） |
| `.codex-plugin` のパス系フィールドが `./` で始まり、`./` 単体でも `..` でもない | WARNING（Codex は不正なパスを無視する） | src |
| 同じパス系フィールドの参照先が実在する | ERROR | src |
| `interface.defaultPrompt` が 3 件以内で、各 128 文字以内である | WARNING | src |
| marketplace に `name` と `plugins` がある | ERROR | doc |
| 各エントリに `policy.installation`・`policy.authentication`・`category` がある | WARNING | doc（「常に含める」） |
| `policy.installation` の値が `AVAILABLE` / `INSTALLED_BY_DEFAULT` / `NOT_AVAILABLE` のいずれか | ERROR | doc |
| local `source` が空でなく、実在する（`"./"` は可） | ERROR | src |

Codex 公式の manifest 検証コマンドは、2026-09-29 時点で**未確認**。

## [skills.sh]

| ルール | レベル | 根拠 |
|---|---|---|
| `skills/` 配下の深さが 3 階層以内である（`.claude-plugin` の manifest で宣言されていれば除外） | WARNING | doc |
| `metadata.internal: true` が付いている Skill は非表示になることを通知 | INFO | doc |

## [consistency]

| ルール | レベル | 根拠 |
|---|---|---|
| 同名の Skill、または同一内容の SKILL.md が複数の場所にない | WARNING | このツール独自（正本を 1 つにする方針） |
| プラットフォームごとの plugin manifest で `name` / `version` が一致する | WARNING | このツール独自 |
| marketplace エントリの `name` が、参照先の manifest の `name` と一致する | WARNING | doc（`claude plugin tag` が一致を検証する） |
| marketplace エントリの `version` が、manifest の `version` と一致する | WARNING | doc（Claude Code では manifest 側が優先される） |
