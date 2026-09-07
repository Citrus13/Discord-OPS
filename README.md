# Discord-Ops

YAML 構成定義ファイルおよび CSV 名簿をもとに、Discord サーバーのインフラ（ロール、カテゴリー、チャンネル、権限オーバーライト、サーバー全体設定、絵文字）を一括プロビジョニング・状態管理する Infrastructure as Code (IaC) CLI ツールです。

---

## 主な機能

- 宣言的インフラ管理: YAML 定義ファイルによるロール・カテゴリー・チャンネル・権限の完全コード化
- 差分計画 (Dry-run): 実際のサーバーへ変更を適用する前に、作成・更新・移動されるリソースの差分プレビューを確認可能
- 自動バックアップ (Snapshot): 適用直前のサーバー状態を YAML スナップショットとして自動保存
- 監査ログ (Audit Log): 全 API 操作の実行結果を JSONL 形式で記録
- ロールバック機能: 監査ログを逆順適用して過去の状態へ原状復帰
- メンバー名簿同期: CSV ファイルをもとにしたロールの一括付与およびニックネームの一括変更
- 絵文字アセット一括同期: 指定ディレクトリ内の画像ファイルを絵文字として一括アップロード
- 不要権限自動クリーンアップ: 以前手動設定された不要な権限オーバーライトを検出し自動同期

---

## ディレクトリ構成

```text
Discord-Ops/
├── config/
│   ├── server_config.example.yaml # サーバー構成定義サンプル
│   └── members.example.csv        # メンバー名簿サンプル
├── src/                           # ソースコード本体
│   ├── cli.py                     # メインCLIエントリーポイント
│   ├── config_parser.py           # YAMLパーサー・検証
│   ├── discord_client.py          # Discord API クライアント
│   ├── state_differ.py            # 状態差分計算エンジン
│   ├── rollback_engine.py         # ロールバックエンジン
│   ├── audit_logger.py            # 監査ログ記録モジュール
│   └── managers/                  # リソース個別マネージャー
├── requirements.txt               # Python 依存パッケージ一覧
├── .env.example                   # 環境変数設定テンプレート
├── .gitignore                     # Git 除外設定
└── usage.md                       # 運用マニュアル・詳細手順書
```

---

## セットアップ手順

### 1. 認証情報・環境変数の設定
`.env.example` をコピーして `.env` を作成し、Bot Token と Guild ID を設定します。

```powershell
Copy-Item .env.example .env
```

`.env` の内容:
```env
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=123456789012345678
```

### 2. 依存パッケージのインストール
Python 仮想環境を作成し、必要なライブラリをインストールします。

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 使い方

### 構成の差分プレビュー (plan)
```powershell
.\venv\Scripts\python.exe src/cli.py plan --config config/server_config.yaml
```

### 構成の適用 (apply)
```powershell
.\venv\Scripts\python.exe src/cli.py apply --config config/server_config.yaml --yes
```

### サーバー現況の表示 (status)
```powershell
.\venv\Scripts\python.exe src/cli.py status
```

### メンバー名簿の同期 (members sync)
```powershell
.\venv\Scripts\python.exe src/cli.py members sync --config config/server_config.yaml --source config/members.csv
```

### 絵文字アセットの一括アップロード (assets upload)
```powershell
.\venv\Scripts\python.exe src/cli.py assets upload --dir assets/emojis/
```

### 状態のロールバック (rollback)
```powershell
.\venv\Scripts\python.exe src/cli.py rollback --log logs/audit_YYYYMMDD_HHMMSS.jsonl
```

詳細は [usage.md](usage.md) をご参照ください。
