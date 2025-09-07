# 焼津市スマートシティ MCP サーバー

焼津市のオープンデータを活用したModel Context Protocol (MCP) サーバー。Claude Desktop および Claude Code から焼津市スマートシティAPIへのアクセスを提供します。

## 特徴

### 提供ツール

1. **search_api_docs**: API仕様検索機能 - 47種類のAPI仕様書から検索
2. **get_api_details**: API詳細情報取得
3. **generate_api_command**: APIコマンド自動生成
4. **execute_yaizu_api**: 焼津市API実行
5. **get_yaizu_api_catalog**: APIカタログ取得
6. **get_yaizu_city_data**: 焼津市基本データ取得
7. **search_yaizu_facilities**: 施設検索
8. **login_yaizu_api_portal**: APIポータルログイン

### 提供リソース

1. **yaizu://info**: 焼津市情報
2. **yaizu://status**: MCPサーバー状態
3. **yaizu://catalog-summary**: APIカタログサマリー
4. **yaizu://catalog-detailed**: APIカタログ詳細

## インストール

### 必要要件

- Python 3.13.7 以上
- uv 0.8.13 以上

### セットアップ

```bash
# リポジトリのクローン
git clone https://github.com/moma1992/smartcity-mcp.git
cd smartcity-mcp

# 依存関係のインストール
uv sync

# 環境変数の設定
cp .env.example .env
# .envファイルを編集してAPIキーを設定
```

### Claude Desktop 設定

1. Claude Desktop の設定ファイルを開く:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. 以下の設定を追加:

```json
{
  "mcpServers": {
    "yaizu-smartcity": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/path/to/smartcity-mcp",
        "run",
        "mcp/server.py"
      ]
    }
  }
}
```

3. パスを実際の環境に合わせて修正

## 使用方法

### 開発・デバッグ

```bash
# MCP Inspector で開発サーバー起動
uv run mcp dev mcp/server.py

# 直接実行
uv run python mcp/server.py

# 統合テスト実行
uv run python tests/test_mcp_integration.py
```

### Claude Desktop での使用

Claude Desktop を起動後、以下のようなコマンドが使用可能:

```
焼津市のイベント情報を検索して
```

```
防災施設を検索して
```

```
観光スポットの一覧を取得して
```

## プロジェクト構成

```
smartcity-mcp/
├── mcp/
│   ├── server.py        # MCPサーバー本体
│   └── scraper.py       # APIカタログスクレイピング
├── scripts/
│   ├── pdf_to_json_generator.py  # PDF→JSON変換
│   └── ...              # その他のデータ処理スクリプト
├── tests/
│   └── test_mcp_integration.py   # 統合テスト
├── data/
│   ├── api_specs/       # 47種類のAPI仕様書（JSON）
│   ├── documentation/   # PDFドキュメント
│   └── openapi/         # OpenAPI仕様書
├── pyproject.toml       # プロジェクト設定
├── CLAUDE.md            # Claude用開発ガイド
└── README.md            # このファイル
```

## API 仕様

### 焼津市API

- 基本URL: `https://api.smartcity-yaizu.jp/v2/entities`
- 認証: APIキー（`apikey`ヘッダー）
- 形式: FIWARE NGSIv2

### 対応エンティティ（一部）

- **防災情報**: Aed, EvacuationShelter, DisasterMail
- **観光情報**: Event, TouristAttraction, SightseeingMapStore
- **環境情報**: PrecipitationGauge, WaterLevelGauge
- **公共施設**: PublicFacility, HospitalAndClinic

## 技術スタック

- **フレームワーク**: FastMCP (MCP Python SDK)
- **非同期処理**: asyncio
- **HTTPクライアント**: aiohttp, httpx
- **PDF処理**: PyMuPDF, PyPDF2
- **環境管理**: python-dotenv
- **パッケージ管理**: uv

## トラブルシューティング

### エラー: "No API key found"
→ `.env`ファイルに`YAIZU_API_KEY`を設定してください

### エラー: "Server disconnected"
→ Claude Desktop設定のパスを確認してください

### エラー: "Module not found"
→ `uv sync`で依存関係をインストールしてください

## ライセンス

MIT License

## 貢献

Issues や Pull Request を歓迎します。

## 関連情報

- [焼津市オープンデータカタログ](https://city-api-catalog.smartcity-pf.com/yaizu)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Claude Desktop](https://claude.ai/)

## サポート

問題が発生した場合は、[Issues](https://github.com/moma1992/smartcity-mcp/issues)で報告してください。