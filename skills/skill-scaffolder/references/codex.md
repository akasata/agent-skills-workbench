# Codex（OpenAI）固有仕様

2026-09-29 時点の一次情報の要約。**Codex の plugin 仕様は変化が速い**。manifest や marketplace を作成する前に、必ず以下の一次情報で最新版を確認すること。

- Skills: https://learn.chatgpt.com/docs/build-skills （旧 developers.openai.com/codex/skills からリダイレクト）
- Plugins: https://developers.openai.com/plugins/build/plugins 、https://learn.chatgpt.com/docs/plugins
- ソース: https://github.com/openai/codex

## Skill の探索場所（ドキュメント記載分）

| スコープ | パス |
|---|---|
| REPO | `$CWD/.agents/skills` から親ディレクトリを遡り、`$REPO_ROOT/.agents/skills` まで |
| USER | `$HOME/.agents/skills` |
| ADMIN | `/etc/codex/skills` |
| SYSTEM | Codex に同梱された Skill |

- symlink された Skill フォルダも辿られる。
- 同名の Skill がある場合、マージされずに両方が表示される。
- **リポジトリ直下の `skills/` は、Skill の探索対象ではない。** Codex から使うには、次のいずれかが必要になる（選び方は `layouts.md` を参照）。
  - plugin として配布する
  - `.agents/skills/` に配置する
  - `npx skills add` でインストールしてもらう
- ソース上では `~/.codex/skills`（deprecated と明記）と `.codex/skills` も読まれているが、ドキュメントに記載がないため、**新規構成では使わない**。
- `SKILL.md` の必須項目は `name` と `description`。Skill 一覧はコンテキストの約 2%（または 8,000 文字）に収まるよう切り詰められるので、description の前半にトリガー語を置く。

### 任意の `agents/openai.yaml`

Skill ディレクトリ内に置く、Codex 固有のメタデータファイル。

- `interface`: `display_name`, `short_description`, `icon_small`, `icon_large`, `brand_color`, `default_prompt`
- `policy.allow_implicit_invocation`: 既定は `true`
- `dependencies.tools[]`: MCP 依存など

Codex 固有の見た目や依存関係が本当に必要な場合だけ作る。`SKILL.md` 本体は変更しない。

## Plugin manifest（2 形式）

### 1. 推奨: ルートの `plugin.json`（Agent Plugins 形式）

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "<kebab-case>",
  "version": "…",
  "description": "…"
}
```

- 任意フィールド: `author{name,email,url}`, `homepage`, `repository`, `license`, `keywords`
- Skill は `skills/` 固定で読まれるので、`skills` フィールドは不要。
- MCP サーバーは `mcp.json` 固定。
- OpenAI 固有の設定は `extensions["com.openai"]` の下に置く（`apps`, `hooks`, `interface`）。
- ファイル名は `.claude-plugin/plugin.json` とは別だが、内容はほぼ重なる。

### 2. 互換: `.codex-plugin/plugin.json`

- 公式ドキュメント上、「互換フォールバックとして引き続きサポート」と記載されている。
- フィールド: `name`, `version`, `description`, `keywords`, `skills`（`./` で始まるパス）, `mcpServers`, `apps`, `hooks`, `interface`, `extensions`

ソース（`codex-rs/core-plugins/src/manifest.rs`、`loader.rs`）で確認できた挙動（2026-09-29 時点）:

- **すべてのフィールドが任意。** `name` が空の場合は、plugin root のディレクトリ名が使われる。
- **未知のフィールドはエラーにならず、無視される。** `author`、`license`、`homepage`、`repository` などは読まれないので、書いても効果はない。
- **`skills` を省略すると、`<plugin-root>/skills` が既定で探索される。** 明示した場合は既定を置き換える（Claude Code の「追加」とは挙動が違う）。
- **パスの制約:** `./` で始めること、`./` 単体は不可、`..` は不可。不正なパスはエラーにならず、警告を出して無視される。
- **形式の優先順位:** plugin root に `plugin.json`（Agent Plugins 形式）がある場合は、そちらが優先される。互換形式を使うときは、ルートに `plugin.json` を置かないこと。

### manifest の探索順

ソース（`DISCOVERABLE_PLUGIN_MANIFEST_PATHS`）から確認した順序は次のとおり。

1. ルートの `plugin.json`（Agent Plugins の `$schema` を宣言している場合のみ）
2. `.codex-plugin/plugin.json`
3. `.claude-plugin/plugin.json`
4. `.cursor-plugin/plugin.json`

`.claude-plugin/plugin.json` へのフォールバックは**ソース由来で、ドキュメントでは未確認**。これに依存して Codex 用 manifest を省略する場合は、その旨をユーザーに明示する。

### どちらの形式を使うか

1. 既存リポジトリが採用している形式を優先する。
2. 既存の形式がない場合は、公式ドキュメントで推奨形式を再確認する。
3. ユーザーが `.codex-plugin/` を明示した場合は、互換形式であることを伝えたうえで従う。

## Marketplace

リポジトリ用は `$REPO_ROOT/.agents/plugins/marketplace.json`、個人用は `~/.agents/plugins/marketplace.json` に置く。

```json
{
  "name": "…",
  "interface": { "displayName": "…" },
  "plugins": [
    {
      "name": "…",
      "source": { "source": "local", "path": "./" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    }
  ]
}
```

- 各エントリには `policy.installation`、`policy.authentication`、`category` を必ず含める（ドキュメントの指示）。
- `source` の種類: `local`（オブジェクト、または `"./path"` 文字列）、`url`、`git-subdir`、`npm`
- パスは marketplace root からの相対パスで、`./` で始める。
- ChatGPT desktop は、互換として `.claude-plugin/marketplace.json` も読むとドキュメントに記載がある。どこまで互換かは**未確認**なので、Codex 用に別途用意するかどうかを判断すること。

ソース（`codex-rs/core-plugins/src/marketplace.rs`）で確認できた挙動（2026-09-29 時点）:

- **local source に `"./"` または `"."` を指定できる。** marketplace root（= リポジトリルート）がそのまま plugin root になるので、単一リポジトリ = 単一 Plugin の構成が成立する。不可なのは空文字だけ。
- **marketplace ファイルの探索順:** `.agents/plugins/marketplace.json` → `.agents/plugins/api_marketplace.json` → `.claude-plugin/marketplace.json` → `.cursor-plugin/marketplace.json`

## インストール

```bash
codex plugin marketplace add owner/repo    # @ref, --ref, --sparse にも対応
```

- 追加後は、Codex CLI の `/plugins`、または ChatGPT desktop の Plugins タブからインストールする。
- IDE 拡張では plugin を利用できない。
- 公式の manifest 検証コマンドは、2026-09-29 時点で**未確認**。存在を確認できない場合は、JSON 構文と必須項目のチェックにとどめ、報告に明記する。
