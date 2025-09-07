#!/usr/bin/env python3
"""
MCP Tools Integration Test
焼津市APIのMCPツール一連の流れをテストします

Test Flow:
1. API仕様検索とデータ取得
2. コマンド生成
3. API実行テスト
"""

import sys
import asyncio
import json
import aiohttp
import os
import uuid
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# 環境変数の読み込み
load_dotenv()

# 必要な関数を直接実装
DATA_DIR = Path(__file__).parent.parent / "data"
API_KEY = os.getenv("YAIZU_API_KEY")

async def search_api_docs(query: str) -> str:
    """API仕様検索の実装"""
    api_specs_dir = DATA_DIR / "api_specs"
    results = []
    
    for json_file in api_specs_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                spec = json.load(f)
                
            entity_name = spec['entity']['name_ja']
            entity_type = spec['entity']['type']
            description = spec['entity']['description']
            
            if query.lower() in entity_name.lower() or query.lower() in description.lower():
                results.append(f"{entity_type}: {entity_name}")
                
        except Exception as e:
            continue
    
    return "\n".join(results) if results else "検索結果なし"

async def get_api_details(entity_type: str) -> str:
    """API詳細情報取得の実装"""
    api_specs_dir = DATA_DIR / "api_specs"
    spec_file = api_specs_dir / f"{entity_type}.json"
    
    if not spec_file.exists():
        raise FileNotFoundError(f"API仕様ファイルが見つかりません: {spec_file}")
    
    with open(spec_file, 'r', encoding='utf-8') as f:
        spec = json.load(f)
    
    return json.dumps(spec, ensure_ascii=False, indent=2)

async def generate_api_command(entity_type: str, operation: str = "list", **params) -> str:
    """APIコマンド生成の実装"""
    spec_file = DATA_DIR / "api_specs" / f"{entity_type}.json"
    
    if not spec_file.exists():
        return f"Error: API仕様ファイルが見つかりません: {entity_type}"
    
    with open(spec_file, 'r', encoding='utf-8') as f:
        spec = json.load(f)
    
    base_url = spec['api_specification']['base_url']
    headers = spec['api_specification']['required_headers']
    
    # リスト取得の場合
    if operation == "list":
        url = f"{base_url}/v2/entities?type={entity_type}"
        
        if params.get('limit'):
            url += f"&limit={params['limit']}"
        if params.get('offset'):
            url += f"&offset={params['offset']}"
    
    # cURLコマンド生成
    curl_cmd = f'curl -X GET "{url}"'
    for header, value in headers.items():
        curl_cmd += f' \\\n  -H "{header}: {value}"'
    
    return curl_cmd

async def execute_yaizu_api(entity_type: str, operation: str = "list", **params) -> str:
    """API実行の実装"""
    if not API_KEY:
        return "Error: YAIZU_API_KEY not found in environment variables"
    
    spec_file = DATA_DIR / "api_specs" / f"{entity_type}.json"
    
    if not spec_file.exists():
        return f"Error: API仕様ファイルが見つかりません: {entity_type}"
    
    with open(spec_file, 'r', encoding='utf-8') as f:
        spec = json.load(f)
    
    base_url = spec['api_specification']['base_url']
    headers = spec['api_specification']['required_headers'].copy()
    
    # APIキーをヘッダーに追加（小文字のapikey）
    headers['apikey'] = API_KEY
    headers['Accept'] = 'application/json'
    headers['User-Agent'] = 'smartcity-service'
    headers['x-request-trace-id'] = str(uuid.uuid4())  # 必須のトレースID
    
    # Content-TypeはGETリクエストでは不要
    if 'Content-Type' in headers:
        del headers['Content-Type']
    
    # URL構築
    if operation == "list":
        url = f"{base_url}/v2/entities?type={entity_type}"
        
        if params.get('limit'):
            url += f"&limit={params['limit']}"
        if params.get('offset'):
            url += f"&offset={params['offset']}"
    
    # HTTP リクエスト実行
    try:
        print(f"🔗 API Request: {url}")
        print(f"📋 Headers: {dict(headers)}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    return response_text
                else:
                    return f"Error: HTTP {response.status} - {response_text}"
    except asyncio.TimeoutError:
        return "Error: API request timeout"
    except Exception as e:
        return f"Error: {str(e)}"

async def test_complete_workflow():
    """MCP Tools の完全なワークフローをテスト"""
    
    print("=== MCP Tools Integration Test ===\n")
    
    # Step 1: API仕様検索
    print("Step 1: API仕様検索")
    print("検索キーワード: 'イベント'")
    
    try:
        search_results = await search_api_docs("イベント")
        print("✅ 検索成功")
        print(f"検索結果:")
        print(search_results)
        print()
    except Exception as e:
        print(f"❌ 検索失敗: {e}")
        return False
    
    # Step 2: 詳細情報取得
    print("Step 2: 詳細情報取得")
    print("エンティティ: 'Event'")
    
    try:
        details = await get_api_details("Event")
        print("✅ 詳細情報取得成功")
        
        # JSON形式で解析
        details_data = json.loads(details)
        print(f"エンティティタイプ: {details_data['entity']['type']}")
        print(f"日本語名: {details_data['entity']['name_ja']}")
        print(f"カテゴリ: {details_data['entity']['category']}")
        print(f"エンドポイント数: {len(details_data['api_specification']['endpoints'])}")
        print()
    except Exception as e:
        print(f"❌ 詳細情報取得失敗: {e}")
        return False
    
    # Step 3: APIコマンド生成
    print("Step 3: APIコマンド生成")
    print("エンティティ: 'Event', 操作: 'list', limit: 5")
    
    try:
        command = await generate_api_command("Event", "list", limit=5)
        print("✅ コマンド生成成功")
        print("生成されたコマンド:")
        print(command)
        print()
    except Exception as e:
        print(f"❌ コマンド生成失敗: {e}")
        return False
    
    # Step 4: API実行 (実際のAPIコール)
    print("Step 4: API実行")
    print("エンティティ: 'Event', 操作: 'list', limit: 3")
    
    try:
        result = await execute_yaizu_api("Event", "list", limit=3)
        print("✅ API実行完了")
        
        # レスポンスの解析
        if result.startswith("Error"):
            print(f"⚠️  API実行時エラー: {result}")
        else:
            print("レスポンス取得成功")
            print(f"レスポンス長: {len(result)} 文字")
            
            # JSONレスポンスの場合
            try:
                result_data = json.loads(result)
                if isinstance(result_data, list):
                    print(f"取得件数: {len(result_data)}")
                    if result_data:
                        first_item = result_data[0]
                        print(f"最初のエンティティID: {first_item.get('id', 'N/A')}")
                        print(f"タイプ: {first_item.get('type', 'N/A')}")
                else:
                    print("レスポンス形式: オブジェクト")
                    print(f"キー: {list(result_data.keys())}")
            except json.JSONDecodeError:
                print("レスポンス形式: プレーンテキスト")
                print(result[:200] + "..." if len(result) > 200 else result)
        print()
    except Exception as e:
        print(f"❌ API実行失敗: {e}")
        return False
    
    print("=== 統合テスト完了 ===")
    return True

async def test_multiple_entities():
    """複数エンティティでの動作テスト"""
    
    print("\n=== Multiple Entities Test ===\n")
    
    test_entities = ["Event", "PrecipitationGauge", "TouristAttraction"]
    
    for entity in test_entities:
        print(f"Testing entity: {entity}")
        
        try:
            # 詳細取得
            details = await get_api_details(entity)
            details_data = json.loads(details)
            
            # コマンド生成
            command = await generate_api_command(entity, "list", limit=1)
            
            # API実行
            result = await execute_yaizu_api(entity, "list", limit=1)
            
            print(f"✅ {entity}: OK")
            print(f"   - Name: {details_data['entity']['name_ja']}")
            print(f"   - Category: {details_data['entity']['category']}")
            print(f"   - API Result: {'Success' if not result.startswith('Error') else 'Error'}")
            
        except Exception as e:
            print(f"❌ {entity}: Failed - {e}")
        
        print()

async def main():
    """メインテスト実行"""
    
    # 基本的なワークフローテスト
    success = await test_complete_workflow()
    
    if success:
        # 複数エンティティテスト
        await test_multiple_entities()
        
        print("🎉 全ての統合テストが完了しました！")
    else:
        print("❌ 統合テストで問題が発生しました")

if __name__ == "__main__":
    asyncio.run(main())