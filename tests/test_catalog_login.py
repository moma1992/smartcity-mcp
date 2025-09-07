#!/usr/bin/env python3
"""
APIカタログサイトへのログインとカタログ選択画面の動作確認
"""

import asyncio
import base64
import json
import os
from pathlib import Path
from typing import Dict, List
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://city-api-catalog.smartcity-pf.com/yaizu"
EMAIL = os.getenv("YAIZU_API_EMAIL")
PASSWORD = os.getenv("YAIZU_API_PASSWORD")


class CatalogLoginTester:
    """APIカタログのログインと画面遷移をテスト"""
    
    def __init__(self):
        self.session = None
        self.auth_headers = {}
        self.cookies = {}
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_access(self):
        """1. サイトへの初期アクセス"""
        print("\n" + "="*50)
        print("ステップ1: APIカタログサイトへアクセス")
        print("="*50)
        print(f"URL: {BASE_URL}")
        
        try:
            async with self.session.get(BASE_URL) as response:
                print(f"✅ ステータス: {response.status}")
                print(f"   Content-Type: {response.headers.get('content-type')}")
                
                # クッキーを保存
                self.cookies = {k: v.value for k, v in response.cookies.items()}
                if self.cookies:
                    print(f"   クッキー取得: {list(self.cookies.keys())}")
                
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')
                
                # ページタイトル確認
                title = soup.find('title')
                if title:
                    print(f"   ページタイトル: {title.get_text(strip=True)}")
                
                # ログインリンクを探す
                login_links = soup.find_all('a', href=lambda x: x and 'login' in x.lower())
                if login_links:
                    print(f"   ログインリンク発見: {len(login_links)} 個")
                    for link in login_links[:3]:
                        print(f"     - {link.get('href')}: {link.get_text(strip=True)}")
                
                return True
        except Exception as e:
            print(f"❌ エラー: {e}")
            return False
    
    async def test_login(self):
        """2. ログイン処理"""
        print("\n" + "="*50)
        print("ステップ2: ログイン認証")
        print("="*50)
        print(f"ユーザー: {EMAIL}")
        
        # Basic認証ヘッダーを作成
        credentials = f"{EMAIL}:{PASSWORD}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.auth_headers = {
            "Authorization": f"Basic {encoded}",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        # documentationページに認証付きでアクセス
        print(f"\n認証付きでアクセス: {BASE_URL}/documentation")
        
        try:
            async with self.session.get(
                f"{BASE_URL}/documentation", 
                headers=self.auth_headers
            ) as response:
                print(f"✅ ステータス: {response.status}")
                
                if response.status == 200:
                    print("   ✅ ログイン成功！")
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # ページタイトル
                    title = soup.find('title')
                    if title:
                        print(f"   ページタイトル: {title.get_text(strip=True)}")
                    
                    return True
                    
                elif response.status == 401:
                    print("   ❌ 認証失敗（401 Unauthorized）")
                    print("   ユーザー名またはパスワードが正しくない可能性があります")
                    return False
                else:
                    print(f"   ⚠️ 予期しないステータス: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ エラー: {e}")
            return False
    
    async def explore_catalog(self):
        """3. カタログ選択画面の探索"""
        print("\n" + "="*50)
        print("ステップ3: APIカタログ選択画面の確認")
        print("="*50)
        
        # documentationページを詳しく調べる
        async with self.session.get(
            f"{BASE_URL}/documentation",
            headers=self.auth_headers
        ) as response:
            if response.status != 200:
                print("❌ アクセスできません")
                return
            
            html = await response.text()
            soup = BeautifulSoup(html, 'lxml')
            
            # デバッグ用にHTMLを保存
            debug_file = Path("debug_documentation.html")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"📄 デバッグ用HTML保存: {debug_file}")
            
            # APIカタログ要素を探す
            print("\n🔍 APIカタログ要素を探索中...")
            
            # 1. サービス一覧を探す
            service_elements = soup.find_all(['div', 'article'], 
                                            class_=lambda x: x and any(k in str(x).lower() 
                                                                      for k in ['service', 'api', 'catalog']))
            if service_elements:
                print(f"📦 サービス要素発見: {len(service_elements)} 個")
                for i, elem in enumerate(service_elements[:5], 1):
                    # 名前を探す
                    name = elem.find(['h1', 'h2', 'h3', 'h4', 'a'])
                    if name:
                        print(f"   {i}. {name.get_text(strip=True)}")
            
            # 2. リンクから探す
            api_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text(strip=True)
                if text and any(keyword in text.lower() or keyword in href.lower() 
                              for keyword in ['api', 'service', 'spec', 'document']):
                    api_links.append((text, href))
            
            if api_links:
                print(f"\n📎 API関連リンク発見: {len(api_links)} 個")
                for text, href in api_links[:10]:
                    print(f"   - {text[:50]}: {href}")
            
            # 3. JavaScriptデータを探す
            print("\n🔍 JavaScriptデータを探索中...")
            for script in soup.find_all('script'):
                if script.string:
                    # APIデータが含まれているか確認
                    if 'services' in script.string or 'apis' in script.string:
                        print("📊 JavaScriptにAPIデータ発見")
                        
                        # window.変数の形でデータが定義されているか確認
                        import re
                        window_vars = re.findall(r'window\.(\w+)\s*=\s*', script.string)
                        if window_vars:
                            print(f"   window変数: {window_vars[:5]}")
                        
                        # JSON形式のデータを探す
                        json_pattern = re.findall(r'\{[^{}]*"(?:service|api|route|spec)[^{}]*\}', script.string)
                        if json_pattern:
                            print(f"   JSONデータブロック発見: {len(json_pattern)} 個")
            
            # 4. フォームやボタンを探す
            forms = soup.find_all('form')
            buttons = soup.find_all(['button', 'input'], type=['submit', 'button'])
            
            if forms:
                print(f"\n📝 フォーム発見: {len(forms)} 個")
                for form in forms:
                    action = form.get('action', 'なし')
                    method = form.get('method', 'GET')
                    print(f"   - Action: {action}, Method: {method}")
            
            if buttons:
                print(f"\n🔘 ボタン発見: {len(buttons)} 個")
                for btn in buttons[:5]:
                    text = btn.get_text(strip=True) or btn.get('value', '')
                    if text:
                        print(f"   - {text}")
    
    async def check_api_endpoints(self):
        """4. APIエンドポイントの確認"""
        print("\n" + "="*50)
        print("ステップ4: APIエンドポイントの確認")
        print("="*50)
        
        # APIエンドポイントをテスト
        api_base = BASE_URL.replace('city-api-catalog', 'city-api-catalog-api')
        
        endpoints = [
            f"{api_base}/services",
            f"{api_base}/routes",
            f"{api_base}/specs",
            f"{BASE_URL}/api/services",
            f"{BASE_URL}/api/catalog"
        ]
        
        for endpoint in endpoints:
            print(f"\n🔍 テスト: {endpoint}")
            try:
                headers = {
                    **self.auth_headers,
                    "Accept": "application/json"
                }
                
                async with self.session.get(endpoint, headers=headers) as response:
                    print(f"   ステータス: {response.status}")
                    content_type = response.headers.get('content-type', '')
                    print(f"   Content-Type: {content_type}")
                    
                    if response.status == 200:
                        if 'application/json' in content_type:
                            data = await response.json()
                            print(f"   ✅ JSONデータ取得成功")
                            
                            # データ構造を表示
                            if isinstance(data, dict):
                                print(f"   キー: {list(data.keys())[:5]}")
                                if 'data' in data and isinstance(data['data'], list):
                                    print(f"   データ件数: {len(data['data'])}")
                            elif isinstance(data, list):
                                print(f"   配列件数: {len(data)}")
                        else:
                            text = await response.text()
                            print(f"   レスポンス長: {len(text)} 文字")
                    
            except Exception as e:
                print(f"   ❌ エラー: {e}")


async def main():
    """メイン実行"""
    print("="*60)
    print("焼津市APIカタログ - ログイン動作確認テスト")
    print("="*60)
    
    async with CatalogLoginTester() as tester:
        # 1. 初期アクセス
        if not await tester.test_access():
            print("\n❌ 初期アクセスに失敗しました")
            return
        
        # 2. ログイン
        if not await tester.test_login():
            print("\n❌ ログインに失敗しました")
            return
        
        # 3. カタログ画面探索
        await tester.explore_catalog()
        
        # 4. APIエンドポイント確認
        await tester.check_api_endpoints()
        
        print("\n" + "="*60)
        print("✅ テスト完了")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())