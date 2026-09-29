# skills.sh / `npx skills` 固有仕様

2026-09-29 時点の一次情報の要約。作業時は以下の一次情報で最新版を確認すること。

- CLI: https://github.com/vercel-labs/skills
- サイト: https://www.skills.sh/docs 、https://www.skills.sh/docs/faq

skills.sh は Vercel の CLI（`npx skills`）と、そのリーダーボードサイトを指す。**Agent Skills 標準そのものではない。** 独自に定めているのは、探索規則とごく少数のメタデータだけ。

## `npx skills add owner/repo` の探索対象

- リポジトリルート（ルートに `SKILL.md` がある場合）
- `skills/`、`skills/.curated/`、`skills/.experimental/`、`skills/.system/`
- 各エージェントの Skill ディレクトリ（`.claude/skills/`、`.agents/skills/` など）

探索の細部:

- 各コンテナは 3 階層まで探索される。浅い階層で見つかった `SKILL.md` は、その配下の `SKILL.md` を隠す。
- 標準の場所に Skill がなければ、再帰探索に切り替わる。
- `.claude-plugin/marketplace.json` または `.claude-plugin/plugin.json` があれば、そこで宣言された Skill も探索される（`metadata.pluginRoot` や `plugins[].skills` など）。
- `.agents/plugins/marketplace.json` を読むかどうかは**未確認**。

## 固有メタデータ

- 必須は `name` と `description`（Agent Skills 標準と同じ）。
- skills.sh 固有のキーは `metadata.internal: true` だけ。これを付けた Skill は、`INSTALL_INTERNAL_SKILLS=1` を設定しない限り表示されない。

## インストール先

| エージェント | プロジェクト | グローバル |
|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| Codex | `.agents/skills/` | `~/.codex/skills/` |

Codex のグローバル先 `~/.codex/skills/` は、Codex 側のソースで deprecated と明記されている。

## リーダーボード

- 申請手続きは不要。公開リポジトリに対して `npx skills add <owner/repo>` が実行されると、匿名テレメトリーによって自動で掲載される。
- README 用のバッジ（任意）:

```markdown
[![skills.sh](https://skills.sh/b/owner/repo)](https://skills.sh/owner/repo)
```

## このスキルでの扱い

- **追加ファイルは原則不要。** `skills/<name>/SKILL.md` に置けば、そのまま探索される。
- README にインストール例を書く場合は、実際のリポジトリの owner/repo を使う:

```bash
npx skills add <owner>/<repo>
```

- ローカルでの確認には `npx skills add <path> --list` を使う（ネットワークに接続するため、実行前にユーザーの了承を得る）。
