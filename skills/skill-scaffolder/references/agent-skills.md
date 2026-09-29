# Agent Skills 標準（共通仕様）

このファイルの内容は 2026-09-29 時点の一次情報の要約。作業時は、以下の一次情報で最新版を確認すること。

- 仕様: https://agentskills.io/specification
- リポジトリ / リファレンス validator: https://github.com/agentskills/agentskills （`skills-ref/`）

この仕様が定めるのは「Skill 1 個の形式」だけ。配布方式（plugin、marketplace、インストール先）は範囲外で、各エージェントが個別に定めている。

## ディレクトリ構造

```
<skill-name>/
├─ SKILL.md        # 必須
├─ scripts/        # 任意: 実行可能コード
├─ references/     # 任意: 必要時に読む追加ドキュメント
└─ assets/         # 任意: テンプレート、画像、データなど
```

- 上記以外のファイルを置いてもよい。
- 補助ファイルは、`SKILL.md` からの相対パスで参照する。
- 参照の深さは SKILL.md から 1 段にとどめることが推奨されている。

## frontmatter

| フィールド | 必須 | 制約 |
|---|---|---|
| `name` | Yes | 1–64 文字。小文字英数字と `-` のみ。先頭・末尾の `-` と連続する `--` は不可。**親ディレクトリ名と一致すること**。 |
| `description` | Yes | 1–1024 文字。何をするかと、いつ使うかの両方を書く。 |
| `license` | No | ライセンス名、または同梱したライセンスファイル名。短く書く。 |
| `compatibility` | No | 1–500 文字。環境要件を書く。ほとんどの Skill では不要。 |
| `metadata` | No | 文字列キーから文字列値への map。 |
| `allowed-tools` | No | スペース区切りの文字列（Experimental）。例: `Bash(git:*) Read`。 |

- リファレンス validator（`skills-ref`）は、**上記 6 フィールド以外のキーをエラーにする**（"Unexpected fields in frontmatter"）。
- したがって、Claude Code 固有のフィールド（`context`、`disable-model-invocation`、`argument-hint` など）を入れると、標準準拠の検証には通らない。

## Progressive disclosure

- **メタデータ**（`name` と `description`、約 100 tokens）は、起動時に全 Skill 分が読み込まれる。
- **本文**は、Skill の起動時に読み込まれる。推奨は 5000 tokens 未満、`SKILL.md` は 500 行以内。
- **`scripts/`、`references/`、`assets/`** は、必要になった時点で読み込まれる。
- そのため、大きな資料は本文に詰め込まず `references/` に分け、SKILL.md から「いつ読むか」を示す。

## 検証

`skills-ref` は README 上、ソースからのインストール手順だけが記載されている。

```bash
git clone https://github.com/agentskills/agentskills
cd agentskills/skills-ref
python -m venv .venv
# .venv を有効化してから:
pip install -e .
skills-ref validate path/to/skill
```

- Python 3.11 以上が必要。README には「デモ目的」と書かれている。
- PyPI にも `skills-ref` パッケージは存在するが、README には記載がない（**未確認**）。

ユーザーの許可なくインストールしないこと。代替として、このスキルの `scripts/check_skill.py` で同等の frontmatter 制約を検査できる。

## 書き方の指針

- **description:** 利用者が実際に言いそうな語（日本語と英語など）を前半に置く。Codex などは description が長いと切り詰めることがある。
- **本文:** 手順を細かく固定しない。判断基準と、失敗しやすい点を書く。
- **固有情報:** リポジトリ名や絶対パスなどの固有情報を、ハードコードしない。
