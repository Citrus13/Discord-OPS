# Discord-Ops 運用マニュアル・使用手順書

本システムは、YAML 設定ファイルおよび CSV 名簿をもとに Discord サーバーのインフラ（ロール、カテゴリー、チャンネル、設定、絵文字）を一括プロビジョニング・状態管理する IaC CLI ツールです。

---

## 1. ディレクトリ構造

```text
Discord/
├── config/
│   ├── server_config.example.yaml # 構成定義サンプル
│   └── members.example.csv        # メンバー名簿サンプル
├── src/                           # ソースコード本体
│   ├── cli.py                     # メインCLIエントリーポイント
│   ├── config_parser.py           # YAMLパーサー・検証
│   ├── discord_client.py          # Discord API クライアント
│   ├── state_differ.py            # 状態差分エンジン
│   ├── rollback_engine.py         # ロールバックエンジン
│   ├── audit_logger.py            # 監査ログ記録モジュール
│   └── managers/                  # 各種リソースマネージャー
├── requirements.txt               # 依存ライブラリ一覧
├── .env.example                   # 環境変数設定テンプレート
├── .gitignore                     # Git 除外設定
└── usage.md                       # 本使用手順書
```

---

## 2. セットアップ手順

### 2.1 Bot Token および サーバー ID (Guild ID) の設定
本ツールでは、コード内に認証情報やサーバーIDを直接記述せず、環境変数ファイル（.env）から読み込みます。

1. テンプレートファイル（.env.example）をコピーして `.env` を作成します。
   ```powershell
   Copy-Item .env.example .env
   ```

2. `.env` ファイルを開き、以下の2項目を設定します。
   ```env
   # Discord Developer Portal から取得した Bot Token
   DISCORD_BOT_TOKEN=your_bot_token_here

   # 対象 Discord サーバーの Guild ID (サーバーID)
   DISCORD_GUILD_ID=123456789012345678
   ```

> [!NOTE]
> Bot Token の取得方法:
> 1. Discord Developer Portal (https://discord.com/developers/applications) にアクセス
> 2. 対象の Bot アプリケーションを選択し、「Bot」メニューから「Reset Token」を押下してトークンをコピー
> 3. 「Privileged Gateway Intents」の「Server Members Intent」を有効化（ロール・メンバー同期に必要）

---

### 2.2 依存パッケージのインストール
Python 仮想環境（venv）を作成し、必要なライブラリをインストールします。

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 3. 主要コマンド一覧

### 3.1 構成の事前検証・計画表示 (plan)
サーバーに対して変更を行わず、差分計画を確認します。

```powershell
.\venv\Scripts\python.exe src/cli.py plan --config config/server_config.yaml
```

特定の Guild ID を指定して実行する場合（.env より優先）:
```powershell
.\venv\Scripts\python.exe src/cli.py plan --config config/server_config.yaml --guild-id <GUILD_ID>
```

---

### 3.2 構成の適用 (apply)
事前スナップショット（snapshots/）を自動取得した上で、設定ファイルの内容を Discord サーバーに適用します。全操作は logs/audit_*.jsonl に記録されます。

```powershell
.\venv\Scripts\python.exe src/cli.py apply --config config/server_config.yaml --yes
```

---

### 3.3 サーバー現況の表示 (status)
現在の Discord サーバーの基本情報、ロール一覧、カテゴリー・チャンネルの階層構造を出力します。

```powershell
.\venv\Scripts\python.exe src/cli.py status
```

---

### 3.4 メンバー名簿の同期 (members sync)
CSV 名簿（config/members.csv）に基づいて、ユーザーへのロール一括付与およびニックネームの変更を行います。

```powershell
.\venv\Scripts\python.exe src/cli.py members sync --config config/server_config.yaml --source config/members.csv
```

---

### 3.5 絵文字アセットの一括アップロード (assets upload)
assets/emojis/ ディレクトリ内の画像ファイルを絵文字として一括作成・アップロードします。

```powershell
.\venv\Scripts\python.exe src/cli.py assets upload --dir assets/emojis/
```

---

### 3.6 状態のロールバック (rollback)
指定した監査ログ (.jsonl) を反転読み込みし、前回の apply 操作の原状復帰を行います。

```powershell
.\venv\Scripts\python.exe src/cli.py rollback --log logs/audit_YYYYMMDD_HHMMSS.jsonl
```

---

## 4. Git コミット・セキュリティに関する注意
- `.env`、`config/members.csv`、`config/server_config.yaml`、`logs/`、`snapshots/` は機密情報保護のため `.gitignore` によりコミット対象外となっています。
- ツールを共有・公開する際は、`.env.example` や `config/server_config.example.yaml`、`config/members.example.csv` のサンプルファイルをご利用ください。
