# レイアウトの選択肢

既存リポジトリに構成がある場合は、その構成を優先する。以下は、構成がない場合に選ぶときの判断材料。

## 基本パターン A: 単一リポジトリ = 単一 Plugin（既定）

```
repo/
├─ .claude-plugin/
│  ├─ plugin.json          # Claude Code（必要時）
│  └─ marketplace.json     # Claude Code marketplace（必要時）。plugins[].source = "./"
├─ plugin.json             # Codex 推奨形式（必要時）。互換形式 .codex-plugin/plugin.json とはどちらか一方にする（references/codex.md 参照）
├─ .agents/plugins/marketplace.json   # Codex marketplace（必要時）
├─ skills/
│  └─ <skill-name>/SKILL.md   # 正本。すべての配布定義がここを参照する
└─ README.md
```

- **Claude Code:** plugin root がリポジトリルートなので、既定の `skills/` 探索で Skill が読まれる。
- **Codex:** 推奨形式（ルートの `plugin.json`）でも互換形式（`.codex-plugin/`）でも、`skills/` を参照できる。
- **skills.sh:** `skills/` を直接探索する。
- **Agent Skills 標準:** `skills/<name>/` 自体が標準準拠の Skill なので、追加の定義は要らない。

## 基本パターン B: 単一リポジトリ = 複数 Plugin

```
repo/
├─ .claude-plugin/marketplace.json   # plugins[].source = "./plugins/<p>"
└─ plugins/
   └─ <plugin>/
      ├─ .claude-plugin/plugin.json
      └─ skills/<skill-name>/SKILL.md
```

- Skill 群を、独立してインストールできる単位に分けたい場合に使う。
- Codex の marketplace でも、各エントリの `source.path` を `./plugins/<p>` にすれば同じ実体を参照できる。
- skills.sh は 3 階層を超える深さを自動では探索しない。その場合は、`.claude-plugin` の manifest（`plugins[].skills` など）で宣言されていれば検出される。導入前に `references/skills-sh.md` を再確認すること。

## 配布定義を置かないケース

- **「Skill を 1 つ追加したい」だけの依頼:** 既存の `skills/`（または既存の規約の場所）に Skill を置くだけでよい。
- **リポジトリ内だけで使う Claude Code 専用の Skill:** `.claude/skills/<name>/` に置く。配布用の `skills/` とは用途が違うので、両方に置かない。

## Codex で直接探索させたい場合（plugin を使わない場合）

Codex は `.agents/skills/` を探索するが、`skills/` は探索しない。選択肢は次の 3 つ。

1. **plugin として配布する（推奨）。** 正本は `skills/` のままでよい。
2. **正本自体を `.agents/skills/` に置く。** Claude Code plugin の場合は、`skills` フィールドで `./.agents/skills` を追加指定する（`skills` は既定ディレクトリへの追加として働く）。ただし、隠しディレクトリを正本にすると可読性が下がる。
3. **`.agents/skills` → `skills` の symlink を作る。** Windows では権限や `core.symlinks` の設定が必要で、clone 環境によっては壊れる。**導入前に必ずユーザーに確認する。**

コピーによる二重管理は採用しない。

## 共通 Skill と固有設定の境界

| 置き場所 | 内容 |
|---|---|
| `SKILL.md` | Agent Skills 標準の frontmatter と、エージェント非依存の本文 |
| `agents/openai.yaml`（Skill 内） | Codex の UI やポリシーの設定。本体とは分離されている |
| `.claude-plugin/`、`plugin.json`、`.agents/plugins/` | 配布定義 |

Claude Code 固有の frontmatter を共通 Skill に入れる必要がある場合は、互換性への影響をユーザーに説明してから入れる。代替案として、Claude Code 専用の薄いラッパー Skill を作り、共通 Skill を参照させる方法もある。
