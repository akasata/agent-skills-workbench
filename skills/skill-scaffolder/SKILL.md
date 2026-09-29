---
name: skill-scaffolder
description: Creates or extends Agent Skills and their distribution layouts in the current repository — new SKILL.md skills, Claude Code plugins (.claude-plugin/plugin.json), Claude Code plugin marketplaces (marketplace.json), Codex plugin/marketplace definitions, and skills.sh-compatible public repos — while keeping one canonical SKILL.md shared across agents. Use when the user asks to add a new skill, publish skills as a Claude Code plugin or marketplace, make skills Agent Skills compatible, make them usable from Codex, or asks things like 「新しいSkillを追加したい」「Pluginとして公開したい」「Codexでも使える構成にしたい」.
license: MIT
---

# Skill Scaffolder

リポジトリの現状と一次情報の仕様を確認したうえで、Agent Skill 本体と各プラットフォームの配布定義を**必要な分だけ**生成・追加する。

特定のリポジトリ名・Plugin 名・Skill 名・用途を前提にしないこと。名前や説明は、ユーザーの依頼と既存リポジトリの規約から決める。

## 基本原則

- **仕様を混同しない。** Agent Skills 標準、Claude Code 固有、Codex 固有、skills.sh 固有は別物として扱う。各仕様の要点と一次情報 URL は `references/` にある。
- **Skill 本体は 1 つの正本にする。** Agent Skills 互換の `SKILL.md` を 1 か所に置き、各プラットフォームの manifest からそれを参照する。
  - 同じ Skill を `.claude/skills/`・`.agents/skills/`・`skills/` などへコピーしない。
  - symlink や生成スクリプトは最後の手段にする。導入する前にユーザーに確認する。
- **manifest は分離し、本体は結合しない。** プラットフォームごとの manifest や marketplace は別ファイルでよい。ただし Skill 本体にプラットフォーム固有の設定を持ち込むのは最小限にする。
- **既存の構成を優先する。** リポジトリが既に採用している配置・命名・配布方式があれば、それに合わせる。不要な再構成はしない。
- **推測で補完しない。** 一次情報で確認できない必須項目や構造は作らず、「未確認」として報告する。

## 手順

### 1. 対応範囲を決める

依頼に明示された配布先だけを対象にする。依頼にない配布定義は追加しない。

| 依頼の例 | 対象 |
|---|---|
| 「Skill を 1 つ追加したい」 | `SKILL.md` と、必要な補助ファイルだけ。manifest は既存のものが Skill の列挙を必要とする場合だけ更新する。 |
| 「Claude Code Plugin にしたい」 | 上記に加えて `.claude-plugin/plugin.json` |
| 「Marketplace で配布したい」 | 上記に加えて `.claude-plugin/marketplace.json` |
| 「Codex でも使いたい」 | Codex の配布方式を確認してから決める（`references/codex.md` 参照） |
| 「skills.sh でも使いたい」 | 多くの場合は追加ファイル不要。探索対象の位置にあるかだけ確認する（`references/skills-sh.md` 参照）。 |

範囲の判断が結果を大きく変えるのに依頼から決められない場合は、ユーザーに質問する。たとえば Codex の manifest 形式や、symlink を導入するかどうか。

### 2. リポジトリを調べる

```bash
python <skill-dir>/scripts/inspect_repo.py <repo-root>
```

`<skill-dir>` はこの `SKILL.md` があるディレクトリ。Claude Code では `${CLAUDE_SKILL_DIR}` で参照できる。他のエージェントでは、この `SKILL.md` の場所から解決する。

このスクリプトは次のものを一覧化する。

- 既存の `SKILL.md`
- 各種 manifest
- 同名や同一内容の重複 Skill
- symlink

出力を見たうえで、次のことを確認する。

- 変更対象になりうるファイル（`.claude-plugin/*.json`、`.codex-plugin/plugin.json`、ルートの `plugin.json`、`.agents/plugins/marketplace.json`、既存の `SKILL.md`、README など）は、**変更前に必ず全文を読む**。
- 既存の命名規則を把握する（ケース、接頭辞、カテゴリ階層など）。
- 既存のディレクトリ構成（`skills/<name>/`、`plugins/<plugin>/skills/<name>/` など）と、既存の配布方式を把握する。

### 3. 仕様を確認する

各 reference ファイルは、記載日時点の一次情報の要約にすぎない。次の場合は、reference 内の URL で最新情報を確認する。

- manifest や marketplace を新規作成・変更するとき
- reference に「未確認」「変化が速い」とある項目に触れるとき

仕様ごとの参照先は次のとおり。

- **Agent Skills 標準:** `references/agent-skills.md`（agentskills.io）
- **Claude Code:** `references/claude-code.md`。確認には code.claude.com/docs を参照する（Claude Code 上では `claude-code-guide` agent も使える）。
- **Codex:** `references/codex.md`（OpenAI 公式ドキュメントと openai/codex）
- **skills.sh:** `references/skills-sh.md`（skills.sh と vercel-labs/skills）

一次情報にアクセスできない場合は、reference の内容で作業してよい。ただし、どの仕様を未確認のまま使ったかを最終報告に書く。

### 4. 構成を決める

レイアウトの選択肢と判断基準は `references/layouts.md` にある。既存構成がない場合の既定は次のとおり。

- Skill 本体は `skills/<skill-name>/SKILL.md` に置く。
- Claude Code Plugin は、リポジトリルートを plugin root にして `.claude-plugin/plugin.json` を置く。既定の `skills/` 探索を使うので、`skills` フィールドは書かない。
- Marketplace は `.claude-plugin/marketplace.json` を置き、plugin の `source` を `"./"` にする。
- Codex と skills.sh は、`references/codex.md` と `references/skills-sh.md` の判断に従う。

### 5. 生成・編集する

**Skill 本体**（詳細は `references/agent-skills.md`）

- frontmatter は Agent Skills 標準のフィールドだけで書く。
  - 必須: `name` と `description`
  - 任意: `license`、`compatibility`、`metadata`、`allowed-tools`
  - `name` はディレクトリ名と一致させる。
- `description` には「何をするか」と「いつ使うか」の両方を書く。利用者が実際に使いそうなトリガー語を前半に置く。
- 本文は手順を過度に固定せず、判断基準を示す形にする。目安は 500 行以内。
- 大きな資料は `references/`、機械的な処理は `scripts/`、テンプレートや静的ファイルは `assets/` に分ける。実際に中身を置く場合だけディレクトリを作り、空ディレクトリは作らない。
- Claude Code 固有の frontmatter（`disable-model-invocation`、`context` など）が本当に必要な場合は、ユーザーに説明する。Agent Skills の validator や他のエージェントとの互換性が下がる点を伝えてから使う。

**既存 JSON の変更**

- 既存のエントリ、キーの順序、インデント、未知のフィールドを維持し、必要な項目だけを追加・修正する。ファイル全体を書き直さず、Edit で差分として適用する。
- `version` を上げるかどうかは既存の運用に合わせる。判断できない場合はユーザーに確認する。

**README**

- 利用手順が変わる場合だけ、該当セクションを追記・修正する。既存の文章は保持する。

### 6. 検証する

```bash
python <skill-dir>/scripts/check_skill.py <repo-root>
```

このスクリプトは次の点をまとめて検査する。

- すべての `SKILL.md` の frontmatter が Agent Skills 標準の制約を満たしているか
- JSON manifest が構文的に正しいか
- marketplace の相対 `source` が実在するか

これに加えて、対象に応じて以下を実行する。

- **Claude Code の manifest がある場合:** `claude plugin validate <path> --strict` を、`plugin.json` と `marketplace.json` のそれぞれについて実行する。
- **Claude Code から Skill 群を検証する場合:** Skill のコンテナディレクトリ（`skills/` など）を指定して `claude plugin validate <dir> --strict` を実行する。
- **`skills-ref` がインストール済みの場合:** `skills-ref validate <検証対象の Skill ディレクトリ>` を実行する。ユーザーの許可なくインストールはしない。
- **Codex:** 公式の検証コマンドは、`references/codex.md` の記載どおり確認できたものだけを使う。

エラーは修正する。警告は、意図的なものであれば理由を報告に書く。

### 7. 報告する

作業完了後、次の 8 項目で報告する。該当しない項目は「なし」と書く。

1. 作成したファイル
2. 変更したファイル（何を変えたかも書く）
3. 採用した構成（その構成を選んだ理由も書く）
4. Agent Skills 共通部分
5. Claude Code 固有部分
6. Codex 固有部分
7. skills.sh に関係する部分
8. 未確認、または仕様上不確実な点（参照できなかった一次情報を含める）

最後に、実行した検証とその結果を添える。
