# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

焼津市のオープンデータを活用したスマートシティAIエージェント用のMCPサーバー。Claude Desktop/Code向けのModel Context Protocol実装により、焼津市の公開データにアクセスする機能を提供します。

## Development Setup

### 必要な環境
- Python 3.13.7 (推奨最新安定版)
- uv 0.8.13以上 (Rustベースの高速パッケージマネージャー)

### セットアップ手順
```bash
# uvのインストール (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# プロジェクト初期化
uv init smartcity-mcp
cd smartcity-mcp

# MCP Python SDK のインストール
uv add "mcp[cli]"
```

## Build and Test Commands

```bash
# 開発サーバー起動とデバッグ
uv run mcp dev mcp/server.py

# MCPサーバーのインストール（Claude Desktop用）
uv run mcp install mcp/server.py

# 依存関係の更新
uv sync

# Python実行
uv run python mcp/server.py

# データ処理スクリプト実行
uv run python scripts/openapi_pdf_processor.py
```

## Architecture Notes

### MCPサーバー構成
- **FastMCP**: MCP Python SDKのフレームワーク使用
- **焼津市API連携**: https://city-api-catalog-api.smartcity-pf.com/yaizu
- **認証方式**: Basic Authentication
- **対象クライアント**: Claude Desktop, Claude Code

### 主要コンポーネント
1. **ツール群** (`@mcp.tool()`): 焼津市データ取得機能
2. **リソース群** (`@mcp.resource()`): 構造化データ提供
3. **プロンプト群** (`@mcp.prompt()`): スマートシティ関連のプロンプトテンプレート

### Claude Desktop設定
```json
{
  "mcpServers": {
    "yaizu-smartcity": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/smartcity-mcp",
        "run",
        "mcp/server.py"
      ]
    }
  }
}
```

### 重要な実装ノート
- STDIOベースサーバーではstdoutへの出力禁止（JSON-RPC通信を破損）
- エラーハンドリングでログレベル適切に設定
- 非同期処理でAPI レスポンス待機時間を考慮