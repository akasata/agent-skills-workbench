---
name: skill-validator
description: Validates Agent Skills and their distribution layout in a repository — SKILL.md frontmatter against the Agent Skills spec, Claude Code plugin.json / marketplace.json, Codex plugin and marketplace definitions, skills.sh discoverability, and cross-platform consistency (names, versions, duplicated skills). Use when the user asks to validate, check, lint or verify skills, plugins or marketplaces, before publishing or releasing a skill repository, after adding or editing skills or manifests, or asks things like 「Skillを検証したい」「配布構成に問題がないか確認して」「公開前にチェックして」.
license: MIT
---

# Skill Validator

リポジトリ内の Agent Skill と、その配布構成を検証し、問題を**仕様ごと**に報告する。

## 基本原則

- **既定では読み取り専用。** 検証中にファイルを変更しない。修正は、報告を見たユーザーが依頼した場合だけ行う。
- **仕様を混同しない。** 指摘ごとに、どの仕様に基づくかを明示する。仕様の区分は次の 5 つ。
  - Agent Skills 標準
  - Claude Code 固有
  - Codex 固有
  - skills.sh 固有
  - プラットフォーム間の整合性
- **公式ツールを優先する。** 公式の検証ツールが使える場合はそれを使い、同梱のスクリプトは補完として使う。両者の結果が食い違う場合は、公式ツールの結果を優先し、食い違いがあったことも報告する。
- **推測で断定しない。** 規則の出典は `references/checks.md` にある。一次情報で確認できない規則に違反していても、エラーとは断定せず「要確認」として扱う。

## 手順

### 1. 検証対象を把握する

依頼に応じて、検証の範囲を決める。

- リポジトリ全体
- 特定の Skill ディレクトリ
- 特定の manifest

リポジトリに存在するファイルから、どの配布先が関係するかを判断する。存在しない配布先の定義は検証対象にしない。「Codex 用の manifest が無い」のように、存在しないこと自体を問題として報告することもしない。

### 2. 同梱スクリプトで検証する

```bash
python <skill-dir>/scripts/validate.py [--strict] <repo-root | skill-dir ...>
```

`<skill-dir>` はこの `SKILL.md` があるディレクトリ。Claude Code では `${CLAUDE_SKILL_DIR}` で参照できる。

- 出力の各行には、`ERROR` / `WARNING` / `INFO` のレベルと、`[agent-skills]` などの仕様タグが付く。
- 終了コードは、ERROR が 1 件以上あれば 1 になる。`--strict` を付けると、WARNING があっても 1 になる。
- Python 3 の標準ライブラリだけで動く。PyYAML がインストールされていればそれを使う。

### 3. 公式ツールで検証する

インストール済みのツールだけを使う。インストールが必要なもの、ネットワーク接続を伴うもの、ユーザー設定を変更するものは、実行前にユーザーの了承を得る。

| 対象 | コマンド | 備考 |
|---|---|---|
| Claude Code plugin | `claude plugin validate .claude-plugin/plugin.json --strict` | |
| Claude Code marketplace | `claude plugin validate .claude-plugin/marketplace.json --strict` | |
| Claude Code から見た Skill 群 | `claude plugin validate <skills のコンテナ> --strict` | Skill を 1 つだけ含むディレクトリを渡すとエラーになる |
| Agent Skills 標準 | `skills-ref validate <skill-dir>` | |
| skills.sh の探索結果 | `npx skills add <repo-root> --list` | ネットワークに接続する |
| Codex | — | 公式の検証コマンドは未確認（`references/checks.md` 参照） |

### 4. 結果を解釈する

- **仕様を再確認する場合:** 指摘の根拠が `references/checks.md` で「未確認」「ソース由来」とされている場合や、公式ツールと結果が食い違う場合は、一次情報の URL で最新の仕様を確認する。
- **意図的な WARNING:** 例として、Claude Code 専用の Skill であえて固有 frontmatter を使っている場合がある。その場合は、理由を添えて「問題なし」と判断してよい。
- **INFO:** 情報提供だけなので、対応は不要。

### 5. 報告する

次の形式で報告する。

1. **結論:** 公開・リリース可能か、ブロッカーがあるか。
2. **検証した対象とコマンド:** 実行しなかった検証があれば、その理由も書く。
3. **指摘事項:** 仕様ごとにまとめる（Agent Skills / Claude Code / Codex / skills.sh / 整合性）。各指摘には次の 4 点を含める。
   - レベル
   - ファイル
   - 内容
   - 推奨する修正
4. **未確認事項:** 一次情報で確認できなかった点。

修正を依頼された場合は、既存の JSON のエントリや書式を維持したまま、差分として修正する。修正後に、同じ検証をもう一度実行する。
