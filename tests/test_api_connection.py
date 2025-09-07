#!/usr/bin/env python3
"""
焼津市スマートシティAPI接続テスト
APIキーを使用してAPIへの接続をテストします
"""

import os
import asyncio
import aiohttp
import json
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

async def test_api_connection():
    """APIキーを使用して焼津市APIへの接続をテスト"""
    
    # APIキーを環境変数から取得
    api_key = os.getenv('YAIZU_API_KEY')
    
    if not api_key:
        print("❌ エラー: YAIZU_API_KEYが.envファイルに設定されていません")
        return False
    
    print(f"✅ APIキー取得: {api_key[:8]}...")
    
    # 焼津市APIのベースURL（複数のエンドポイントを試す）
    endpoints_to_test = [
        "https://city-api-catalog-api.smartcity-pf.com/yaizu/catalog",
        "https://city-api-catalog.smartcity-pf.com/yaizu/catalog",
        "https://api.smartcity-yaizu.jp/v1/catalog",
        "https://city-api-catalog-api.smartcity-pf.com/api/v1/yaizu/catalogs"
    ]
    
    print(f"\n📡 接続テスト開始...")
    
    # 複数のヘッダーパターンを試す
    header_patterns = [
        {'X-API-Key': api_key, 'Accept': 'application/json'},
        {'Authorization': f'Bearer {api_key}', 'Accept': 'application/json'},
        {'Api-Key': api_key, 'Accept': 'application/json'},
        {'x-api-key': api_key, 'Accept': 'application/json'}
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints_to_test:
            print(f"\n🔍 テスト中: {endpoint}")
            
            for headers in header_patterns:
                header_type = list(headers.keys())[0]
                print(f"  ヘッダー: {header_type}")
                
                try:
                    async with session.get(endpoint, headers=headers, timeout=10) as response:
                        print(f"    ステータス: {response.status}")
                        
                        if response.status == 200:
                            data = await response.text()
                            print(f"    ✅ 成功！データ取得: {len(data)} bytes")
                            print(f"    使用ヘッダー: {header_type}")
                            print(f"    エンドポイント: {endpoint}")
                            
                            # JSONかどうか確認
                            try:
                                json_data = json.loads(data)
                                print(f"    📊 JSONデータ:")
                                print(json.dumps(json_data, ensure_ascii=False, indent=2)[:300])
                            except:
                                print(f"    📄 HTMLまたはテキストデータ:")
                                print(data[:300])
                            
                            return True
                        elif response.status == 401:
                            print(f"    ❌ 認証失敗")
                        elif response.status == 404:
                            print(f"    ❌ Not Found")
                        else:
                            print(f"    ❌ エラー: {response.status}")
                            
                except asyncio.TimeoutError:
                    print(f"    ⏱️ タイムアウト")
                except Exception as e:
                    print(f"    ❌ エラー: {str(e)[:50]}")
        
        return False

async def test_basic_auth():
    """既存のBasic認証もテスト（比較用）"""
    email = os.getenv('YAIZU_API_EMAIL')
    password = os.getenv('YAIZU_API_PASSWORD')
    
    if email and password and email != "your_email@example.com":
        print("\n\n📧 Basic認証のテストも実行...")
        
        from aiohttp import BasicAuth
        base_url = "https://city-api-catalog-api.smartcity-pf.com/yaizu"
        test_endpoint = f"{base_url}/api/v1/catalogs"
        
        auth = BasicAuth(email, password)
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(test_endpoint, auth=auth, timeout=30) as response:
                    if response.status == 200:
                        print("✅ Basic認証も成功")
                    else:
                        print(f"❌ Basic認証失敗: ステータス {response.status}")
            except Exception as e:
                print(f"❌ Basic認証エラー: {str(e)}")

async def main():
    """メイン処理"""
    print("=" * 60)
    print("焼津市スマートシティAPI 接続テスト")
    print("=" * 60)
    
    # APIキー認証テスト
    success = await test_api_connection()
    
    # Basic認証テスト（オプション）
    await test_basic_auth()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ APIキー認証での接続テスト成功！")
        print("APIキーは正常に動作しています。")
    else:
        print("❌ APIキー認証での接続テスト失敗")
        print("APIキーまたはエンドポイントを確認してください。")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())