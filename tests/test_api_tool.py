#!/usr/bin/env python3
"""
MCPサーバーのexecute_api_endpointツールをテスト
"""

import asyncio
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server import execute_api_endpoint, get_sample_endpoints
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

async def test_api_tools():
    """API実行ツールをテスト"""
    print("=" * 60)
    print("MCP API実行ツール テスト")
    print("=" * 60)
    
    # APIキーの確認
    api_key = os.getenv('YAIZU_API_KEY')
    if api_key:
        print(f"✅ APIキー設定済み: {api_key[:8]}...\n")
    else:
        print("❌ APIキーが設定されていません\n")
        return
    
    # サンプルエンドポイントの表示
    print("📋 サンプルエンドポイント:")
    print("-" * 40)
    sample_endpoints = await get_sample_endpoints()
    print(sample_endpoints)
    
    # テスト用エンドポイント（実際のAPIエンドポイントが不明なので、カタログページでテスト）
    test_endpoints = [
        "https://city-api-catalog.smartcity-pf.com/yaizu/catalog",
        "https://api.smartcity-yaizu.jp/v1/disaster/shelters",
        "https://city-api-catalog-api.smartcity-pf.com/yaizu/api/v1/test"
    ]
    
    print("\n" + "=" * 60)
    print("APIエンドポイント実行テスト")
    print("=" * 60)
    
    for endpoint in test_endpoints:
        print(f"\n🔍 テスト中: {endpoint}")
        print("-" * 40)
        
        # execute_api_endpointツールを実行
        result = await execute_api_endpoint(
            endpoint_url=endpoint,
            method="GET",
            params=None  # パラメータなし
        )
        
        # 結果の最初の500文字を表示
        print(result[:500])
        
        if "✅ **成功**" in result:
            print("\n✨ このエンドポイントは成功しました！")
            break
        else:
            print("\n❌ このエンドポイントは失敗しました")
    
    # パラメータ付きのテスト
    print("\n" + "=" * 60)
    print("パラメータ付きテスト")
    print("=" * 60)
    
    params_test = json.dumps({"limit": 5, "offset": 0})
    print(f"パラメータ: {params_test}")
    
    result = await execute_api_endpoint(
        endpoint_url="https://api.smartcity-yaizu.jp/v1/facilities/public",
        method="GET",
        params=params_test
    )
    
    print(result[:500])

if __name__ == "__main__":
    asyncio.run(test_api_tools())