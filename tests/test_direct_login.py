#!/usr/bin/env python3
"""
APIカタログサイトへの直接ログインテスト
ログインページ経由でフォーム認証を行う
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://city-api-catalog.smartcity-pf.com/yaizu"
LOGIN_URL = "https://city-api-catalog.smartcity-pf.com/yaizu/login"
EMAIL = os.getenv("YAIZU_API_EMAIL")
PASSWORD = os.getenv("YAIZU_API_PASSWORD")


class DirectLoginTester:
    """ログインページ経由での認証テスト"""
    
    def __init__(self):
        self.session = None
        self.logged_in = False
    
    async def __aenter__(self):
        # クッキーを保持するセッションを作成
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_login_page(self):
        """ログインページを取得してフォーム情報を解析"""
        print("\n" + "="*50)
        print("ステップ1: ログインページの解析")
        print("="*50)
        print(f"URL: {LOGIN_URL}")
        
        try:
            async with self.session.get(LOGIN_URL) as response:
                print(f"ステータス: {response.status}")
                
                if response.status != 200:
                    print("❌ ログインページにアクセスできません")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')
                
                # ページタイトル
                title = soup.find('title')
                if title:
                    print(f"ページタイトル: {title.get_text(strip=True)}")
                
                # フォームを探す
                forms = soup.find_all('form')
                print(f"\nフォーム数: {len(forms)}")
                
                login_form = None
                for form in forms:
                    # ログインフォームを特定
                    inputs = form.find_all('input')
                    has_email = any(inp.get('type') == 'email' or 
                                  inp.get('name') in ['email', 'username', 'user'] 
                                  for inp in inputs)
                    has_password = any(inp.get('type') == 'password' or 
                                     inp.get('name') in ['password', 'pass'] 
                                     for inp in inputs)
                    
                    if has_email or has_password:
                        login_form = form
                        print("✅ ログインフォーム発見")
                        
                        # フォーム詳細
                        action = form.get('action', '')
                        method = form.get('method', 'GET').upper()
                        print(f"  Action: {action}")
                        print(f"  Method: {method}")
                        
                        # 入力フィールド
                        print("\n入力フィールド:")
                        for inp in inputs:
                            input_type = inp.get('type', 'text')
                            input_name = inp.get('name', '')
                            required = 'required' in inp.attrs
                            if input_name:
                                print(f"  - {input_name}: type={input_type}, required={required}")
                        
                        # hidden フィールド（CSRFトークンなど）
                        hidden_fields = {}
                        for inp in inputs:
                            if inp.get('type') == 'hidden' and inp.get('name'):
                                hidden_fields[inp['name']] = inp.get('value', '')
                        
                        if hidden_fields:
                            print(f"\nHiddenフィールド: {list(hidden_fields.keys())}")
                        
                        return {
                            'action': action,
                            'method': method,
                            'inputs': [(inp.get('name'), inp.get('type')) for inp in inputs if inp.get('name')],
                            'hidden_fields': hidden_fields
                        }
                
                if not login_form:
                    print("❌ ログインフォームが見つかりません")
                    
                    # デバッグ: すべてのフォームの情報を表示
                    for i, form in enumerate(forms, 1):
                        print(f"\nフォーム{i}:")
                        print(f"  Action: {form.get('action')}")
                        inputs = form.find_all('input')
                        for inp in inputs:
                            print(f"  - {inp.get('name')}: {inp.get('type')}")
                
                return None
                
        except Exception as e:
            print(f"❌ エラー: {e}")
            return None
    
    async def perform_login(self, form_info: Dict):
        """フォームを使用してログイン"""
        print("\n" + "="*50)
        print("ステップ2: ログイン実行")
        print("="*50)
        
        if not form_info:
            print("❌ フォーム情報がありません")
            return False
        
        # ログインデータを準備
        login_data = {
            **form_info.get('hidden_fields', {})
        }
        
        # メール/ユーザー名フィールドを探す
        for field_name, field_type in form_info['inputs']:
            if field_name and field_name.lower() in ['email', 'username', 'user', 'login']:
                login_data[field_name] = EMAIL
                print(f"📧 {field_name}: {EMAIL}")
            elif field_name and field_name.lower() in ['password', 'pass', 'pwd']:
                login_data[field_name] = PASSWORD
                print(f"🔒 {field_name}: ****")
        
        # ログインURLを構築
        action = form_info['action']
        if not action.startswith('http'):
            login_endpoint = urljoin(LOGIN_URL, action) if action else LOGIN_URL
        else:
            login_endpoint = action
        
        print(f"\n📮 送信先: {login_endpoint}")
        print(f"メソッド: {form_info['method']}")
        
        try:
            # ログインリクエストを送信
            if form_info['method'] == 'POST':
                async with self.session.post(
                    login_endpoint,
                    data=login_data,
                    allow_redirects=True
                ) as response:
                    print(f"\nレスポンスステータス: {response.status}")
                    print(f"最終URL: {response.url}")
                    
                    # リダイレクトされた場合は成功の可能性が高い
                    if str(response.url) != login_endpoint:
                        print("✅ リダイレクト検出 - ログイン成功の可能性")
                        self.logged_in = True
                    
                    # レスポンスを確認
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # エラーメッセージを探す
                    error_elements = soup.find_all(['div', 'span', 'p'], 
                                                  class_=lambda x: x and 'error' in str(x).lower())
                    if error_elements:
                        print("⚠️ エラーメッセージ検出:")
                        for err in error_elements:
                            print(f"  {err.get_text(strip=True)}")
                    
                    # ログイン成功の兆候を探す
                    if any(keyword in html.lower() for keyword in ['logout', 'ログアウト', 'dashboard', 'catalog']):
                        print("✅ ログイン成功を示すキーワード検出")
                        self.logged_in = True
                    
                    return self.logged_in
            
            else:  # GET method
                async with self.session.get(
                    login_endpoint,
                    params=login_data,
                    allow_redirects=True
                ) as response:
                    print(f"\nレスポンスステータス: {response.status}")
                    return response.status == 200
                    
        except Exception as e:
            print(f"❌ ログインエラー: {e}")
            return False
    
    async def check_catalog_access(self):
        """ログイン後のカタログアクセス確認"""
        print("\n" + "="*50)
        print("ステップ3: カタログページへのアクセス確認")
        print("="*50)
        
        catalog_urls = [
            f"{BASE_URL}/documentation",
            f"{BASE_URL}/catalog",
            f"{BASE_URL}/services",
            f"{BASE_URL}/dashboard"
        ]
        
        for url in catalog_urls:
            print(f"\n🔍 アクセステスト: {url}")
            try:
                async with self.session.get(url, allow_redirects=False) as response:
                    print(f"  ステータス: {response.status}")
                    
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'lxml')
                        
                        # ページタイトル
                        title = soup.find('title')
                        if title:
                            print(f"  タイトル: {title.get_text(strip=True)}")
                        
                        # API関連の要素を探す
                        api_elements = soup.find_all(['div', 'article', 'section'], 
                                                    class_=lambda x: x and any(k in str(x).lower() 
                                                                             for k in ['api', 'service', 'catalog']))
                        if api_elements:
                            print(f"  ✅ API要素発見: {len(api_elements)} 個")
                            
                            # 最初の数個を表示
                            for elem in api_elements[:3]:
                                name = elem.find(['h1', 'h2', 'h3', 'a'])
                                if name:
                                    print(f"    - {name.get_text(strip=True)[:50]}")
                        
                        # リンクを探す
                        links = soup.find_all('a', href=True)
                        api_links = [link for link in links 
                                   if any(k in link.get('href', '').lower() or k in link.get_text(strip=True).lower()
                                         for k in ['api', 'spec', 'document', 'service'])]
                        
                        if api_links:
                            print(f"  📎 API関連リンク: {len(api_links)} 個")
                            for link in api_links[:5]:
                                text = link.get_text(strip=True)
                                href = link.get('href', '')
                                if text:
                                    print(f"    - {text[:30]}: {href[:50]}")
                        
                        # 成功したURLでHTMLを保存（デバッグ用）
                        if api_elements or api_links:
                            debug_file = Path(f"debug_{url.split('/')[-1]}.html")
                            with open(debug_file, 'w', encoding='utf-8') as f:
                                f.write(html)
                            print(f"  💾 デバッグ用HTML保存: {debug_file}")
                            
                            return True
                    
                    elif response.status == 302 or response.status == 301:
                        location = response.headers.get('Location', '')
                        print(f"  リダイレクト先: {location}")
                        if 'login' in location.lower():
                            print(f"  ⚠️ ログインページへのリダイレクト - 認証が必要")
                    
            except Exception as e:
                print(f"  ❌ エラー: {e}")
        
        return False


async def main():
    """メイン実行"""
    print("="*60)
    print("焼津市APIカタログ - 直接ログインテスト")
    print("="*60)
    print(f"ログインURL: {LOGIN_URL}")
    print(f"ユーザー: {EMAIL}")
    
    async with DirectLoginTester() as tester:
        # 1. ログインページの解析
        form_info = await tester.get_login_page()
        
        if form_info:
            # 2. ログイン実行
            login_success = await tester.perform_login(form_info)
            
            if login_success:
                # 3. カタログアクセス確認
                await tester.check_catalog_access()
            else:
                print("\n❌ ログインに失敗しました")
        else:
            print("\n❌ ログインフォームの解析に失敗しました")
        
        print("\n" + "="*60)
        print("テスト完了")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())