#!/usr/bin/env python3
"""
MCPサーバーのscrape_api_docsツールをテスト
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server import doc_manager
from mcp.scraper import YaizuAPIScraper
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

async def test_scraping():
    """スクレイピング機能をテスト"""
    try:
        print("=" * 60)
        print("MCPサーバー スクレイピングテスト")
        print("=" * 60)
        
        # APIキーの確認
        api_key = os.getenv('YAIZU_API_KEY')
        if api_key:
            print(f"✅ APIキー設定済み: {api_key[:8]}...")
        else:
            print("❌ APIキーが設定されていません")
            return
        
        # スクレイパー初期化
        print("\n📊 スクレイパー初期化中...")
        scraper = await doc_manager.initialize_scraper()
        
        # ログイン（APIキー認証）
        print("🔑 APIキー認証中...")
        login_success = await scraper.login()
        
        if login_success:
            print("✅ 認証成功！")
        else:
            print("❌ 認証失敗")
            return
        
        # スクレイピング実行
        print("\n🔄 APIドキュメントをスクレイピング中...")
        result = await scraper.scrape_and_save_all()
        
        if result['success']:
            print("\n✅ スクレイピング成功！")
            print(f"- 総API数: {result['total_apis']}")
            print(f"- 防災関連API数: {result['disaster_apis']}")
            print(f"- 保存されたファイル数: {len(result['saved_files'])}")
            print("\n保存されたファイル:")
            for filename in result['saved_files']:
                print(f"  - {filename}")
        else:
            print("❌ スクレイピング失敗")
            if 'error' in result:
                print(f"エラー: {result['error']}")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # クリーンアップ
        await doc_manager.cleanup()
        print("\n✅ クリーンアップ完了")

if __name__ == "__main__":
    asyncio.run(test_scraping())