#!/usr/bin/env python3
"""
焼津市APIカタログからPDFファイルをダウンロード
セッションベースの認証を使用してログインし、カタログ内のすべてのPDFをダウンロード
"""

import asyncio
import base64
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# 設定
BASE_URL = "https://city-api-catalog.smartcity-pf.com/yaizu"
API_BASE_URL = "https://city-api-catalog-api.smartcity-pf.com/yaizu"
DATA_DIR = Path("data/documentation")

# 認証情報
EMAIL = os.getenv("YAIZU_API_EMAIL")
PASSWORD = os.getenv("YAIZU_API_PASSWORD")


class CatalogPDFDownloader:
    """APIカタログからPDFをダウンロードするクラス"""
    
    def __init__(self):
        self.email = EMAIL
        self.password = PASSWORD
        self.base_url = BASE_URL
        self.api_base_url = API_BASE_URL
        self.data_dir = DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_headers: Dict[str, str] = {}
        self.is_authenticated = False
        self.pdf_urls: Set[str] = set()
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def login(self) -> bool:
        """カタログサイトにログイン"""
        if not self.email or not self.password:
            print("❌ 認証情報が設定されていません")
            return False
        
        print(f"📝 ログイン中: {self.email}")
        
        try:
            # セッションクッキーを取得
            async with self.session.get(self.base_url) as response:
                print(f"  初期アクセス: ステータス {response.status}")
            
            # Basic認証ヘッダーの作成
            credentials = f"{self.email}:{self.password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            self.auth_headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            # 認証付きでアクセス
            async with self.session.get(
                f"{self.base_url}/documentation",
                headers=self.auth_headers
            ) as response:
                print(f"  認証応答: ステータス {response.status}")
                if response.status == 200:
                    self.is_authenticated = True
                    print("✅ ログイン成功")
                    return True
                else:
                    print(f"❌ ログイン失敗: ステータス {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ ログインエラー: {e}")
            return False
    
    async def find_pdf_urls(self) -> List[str]:
        """カタログページからPDFのURLを探索"""
        if not self.is_authenticated:
            print("❌ 先にログインが必要です")
            return []
        
        print("\n🔍 PDFファイルを探索中...")
        
        # 探索するページのリスト
        pages_to_check = [
            "",
            "/documentation",
            "/catalog",
            "/specs",
            "/api-docs"
        ]
        
        for page_path in pages_to_check:
            url = f"{self.base_url}{page_path}"
            print(f"  📄 チェック中: {url}")
            
            try:
                async with self.session.get(url, headers=self.auth_headers) as response:
                    if response.status != 200:
                        print(f"    スキップ: ステータス {response.status}")
                        continue
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # PDFリンクを探す
                    pdf_links = []
                    
                    # 直接的なPDFリンク
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if href.lower().endswith('.pdf'):
                            pdf_links.append(href)
                        elif 'pdf' in href.lower() or 'document' in href.lower():
                            pdf_links.append(href)
                    
                    # iframeやembedタグ内のPDF
                    for tag in soup.find_all(['iframe', 'embed', 'object']):
                        src = tag.get('src') or tag.get('data')
                        if src and '.pdf' in src.lower():
                            pdf_links.append(src)
                    
                    # JavaScriptから抽出
                    for script in soup.find_all('script'):
                        if script.string:
                            # PDFのURLパターンを検索
                            pdf_patterns = re.findall(r'["\'](.*?\.pdf[^"\']*)["\']', script.string, re.IGNORECASE)
                            pdf_links.extend(pdf_patterns)
                    
                    # API仕様書のリンクを探す（Kong Developer Portal特有のパターン）
                    for spec_link in soup.find_all(['a', 'button'], class_=re.compile(r'spec|download|documentation')):
                        if 'href' in spec_link.attrs:
                            pdf_links.append(spec_link['href'])
                    
                    # 見つかったリンクを処理
                    for link in pdf_links:
                        if not link.startswith('http'):
                            link = urljoin(url, link)
                        self.pdf_urls.add(link)
                    
                    print(f"    ✓ {len(pdf_links)} 個のリンクを発見")
                    
            except Exception as e:
                print(f"    エラー: {e}")
                continue
        
        # API仕様書を直接チェック
        await self._check_api_specs()
        
        pdf_list = list(self.pdf_urls)
        print(f"\n📊 合計 {len(pdf_list)} 個のPDFファイルを発見")
        
        return pdf_list
    
    async def _check_api_specs(self):
        """API仕様書のエンドポイントをチェック"""
        print("  🔍 API仕様書をチェック中...")
        
        # Kong Developer Portalの一般的なエンドポイント
        spec_endpoints = [
            f"{self.api_base_url}/specs",
            f"{self.api_base_url}/documentation",
            f"{self.base_url}/specs",
            f"{self.base_url}/api/specs"
        ]
        
        for endpoint in spec_endpoints:
            try:
                async with self.session.get(endpoint, headers=self.auth_headers) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        
                        # PDFレスポンス
                        if 'application/pdf' in content_type:
                            self.pdf_urls.add(endpoint)
                            print(f"    ✓ PDF発見: {endpoint}")
                        
                        # JSONレスポンス
                        elif 'application/json' in content_type:
                            data = await response.json()
                            if isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict):
                                        # PDFのURLを探す
                                        for key in ['url', 'download_url', 'pdf_url', 'spec_url']:
                                            if key in item and '.pdf' in str(item[key]).lower():
                                                self.pdf_urls.add(item[key])
                        
                        # HTMLレスポンス
                        else:
                            html = await response.text()
                            # OpenAPIやSwagger仕様書のパターンを検索
                            spec_patterns = re.findall(r'["\'](/[^"\']*?(?:openapi|swagger|spec)[^"\']*?\.(?:pdf|json|yaml)[^"\']*)["\']', html, re.IGNORECASE)
                            for pattern in spec_patterns:
                                if pattern.endswith('.pdf'):
                                    full_url = urljoin(endpoint, pattern)
                                    self.pdf_urls.add(full_url)
            
            except Exception as e:
                continue
    
    async def download_pdf(self, url: str, filename: Optional[str] = None) -> bool:
        """PDFファイルをダウンロード"""
        try:
            # ファイル名の決定
            if not filename:
                # URLからファイル名を抽出
                parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path)
                
                # ファイル名が空または拡張子がない場合
                if not filename or not filename.endswith('.pdf'):
                    # URLのハッシュからファイル名を生成
                    import hashlib
                    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                    filename = f"document_{url_hash}.pdf"
            
            filepath = self.data_dir / filename
            
            # 既にダウンロード済みかチェック
            if filepath.exists():
                print(f"  ⏭️  スキップ（既存）: {filename}")
                return True
            
            print(f"  📥 ダウンロード中: {filename}")
            print(f"     URL: {url}")
            
            async with self.session.get(url, headers=self.auth_headers) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # PDFかどうか確認
                    if content[:4] == b'%PDF':
                        with open(filepath, 'wb') as f:
                            f.write(content)
                        print(f"  ✅ 保存完了: {filepath}")
                        return True
                    else:
                        print(f"  ⚠️  PDFではありません: {filename}")
                        return False
                else:
                    print(f"  ❌ ダウンロード失敗: ステータス {response.status}")
                    return False
                    
        except Exception as e:
            print(f"  ❌ エラー: {e}")
            return False
    
    async def download_all_pdfs(self) -> Dict[str, int]:
        """すべてのPDFをダウンロード"""
        # ログイン
        if not await self.login():
            return {"total": 0, "success": 0, "failed": 0}
        
        # PDFのURLを探索
        pdf_urls = await self.find_pdf_urls()
        
        if not pdf_urls:
            print("❌ PDFファイルが見つかりませんでした")
            return {"total": 0, "success": 0, "failed": 0}
        
        # ダウンロード実行
        print(f"\n📦 {len(pdf_urls)} 個のPDFをダウンロード開始...")
        
        results = {"total": len(pdf_urls), "success": 0, "failed": 0}
        
        for i, url in enumerate(pdf_urls, 1):
            print(f"\n[{i}/{len(pdf_urls)}]")
            if await self.download_pdf(url):
                results["success"] += 1
            else:
                results["failed"] += 1
            
            # レート制限対策
            await asyncio.sleep(0.5)
        
        return results


async def main():
    """メイン実行関数"""
    print("=" * 50)
    print("焼津市APIカタログ PDFダウンローダー")
    print("=" * 50)
    
    async with CatalogPDFDownloader() as downloader:
        results = await downloader.download_all_pdfs()
        
        print("\n" + "=" * 50)
        print("📊 ダウンロード完了")
        print(f"  合計: {results['total']} ファイル")
        print(f"  成功: {results['success']} ファイル")
        print(f"  失敗: {results['failed']} ファイル")
        print("=" * 50)
        
        # ダウンロードしたファイルの確認
        pdf_files = list(DATA_DIR.glob("*.pdf"))
        if pdf_files:
            print(f"\n📁 {DATA_DIR} に保存されたファイル:")
            for pdf_file in sorted(pdf_files):
                size_mb = pdf_file.stat().st_size / (1024 * 1024)
                print(f"  - {pdf_file.name} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    asyncio.run(main())