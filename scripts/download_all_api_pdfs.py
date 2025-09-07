#!/usr/bin/env python3
"""
3つのAPIカタログから全PDFドキュメントをダウンロード
"""

import asyncio
import base64
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://city-api-catalog.smartcity-pf.com/yaizu"
EMAIL = os.getenv("YAIZU_API_EMAIL")
PASSWORD = os.getenv("YAIZU_API_PASSWORD")
DATA_DIR = Path("data/documentation")

# 3つのAPI
API_CATALOGS = [
    {
        "name": "観光・産業API",
        "type": "tourism_industry",
        "description": "FIWARE NGSI v2"
    },
    {
        "name": "公共施設API", 
        "type": "public_facility",
        "description": "FIWARE NGSI v2"
    },
    {
        "name": "防災情報API",
        "type": "disaster_info", 
        "description": "FIWARE NGSI v2"
    }
]


class APIDocumentDownloader:
    def __init__(self):
        self.session = None
        self.auth_headers = {}
        self.pdf_urls = set()
        self.downloaded_files = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def authenticate(self):
        """Basic認証でログイン"""
        credentials = f"{EMAIL}:{PASSWORD}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.auth_headers = {
            "Authorization": f"Basic {encoded}",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0"
        }
        
        # 認証確認
        async with self.session.get(f"{BASE_URL}/documentation", headers=self.auth_headers) as resp:
            return resp.status == 200
    
    async def extract_api_detail_urls(self) -> List[Dict]:
        """documentationページから各APIの詳細URLを取得"""
        print("\n🔍 APIカタログの詳細URLを取得中...")
        
        async with self.session.get(f"{BASE_URL}/documentation", headers=self.auth_headers) as resp:
            if resp.status != 200:
                print(f"❌ documentationページにアクセスできません: {resp.status}")
                return []
            
            html = await resp.text()
            soup = BeautifulSoup(html, 'lxml')
            
            api_details = []
            
            # data-json属性からAPI情報を抽出
            catalog_items = soup.find_all(attrs={'data-json': True})
            
            for item in catalog_items:
                try:
                    data = json.loads(item.get('data-json'))
                    info = data.get('info', {})
                    title = info.get('title', '')
                    
                    # APIの種類を特定
                    api_type = None
                    if '観光' in title or '産業' in title:
                        api_type = 'tourism_industry'
                    elif '公共施設' in title:
                        api_type = 'public_facility'
                    elif '防災' in title:
                        api_type = 'disaster_info'
                    
                    if api_type:
                        # 詳細ページのURLを構築
                        # Kong Portalでは通常 /documentation/{service_id} の形式
                        service_id = data.get('id') or data.get('name', '').lower().replace(' ', '-')
                        detail_url = f"{BASE_URL}/documentation/{service_id}"
                        
                        api_details.append({
                            'name': title,
                            'type': api_type,
                            'detail_url': detail_url,
                            'data': data
                        })
                        
                        print(f"  ✅ {title}")
                        print(f"     URL: {detail_url}")
                
                except Exception as e:
                    print(f"  ⚠️ データ解析エラー: {e}")
            
            # HTMLリンクからも探索
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                text = link.get_text(strip=True)
                
                # API詳細ページっぽいリンクを探す
                if href and any(api_name in text for api in API_CATALOGS for api_name in [api['name']]):
                    full_url = urljoin(f"{BASE_URL}/", href)
                    
                    # 既に見つかったものでない場合
                    if not any(detail['detail_url'] == full_url for detail in api_details):
                        api_details.append({
                            'name': text,
                            'type': 'unknown',
                            'detail_url': full_url,
                            'data': {}
                        })
                        print(f"  📎 リンク発見: {text} -> {full_url}")
            
            return api_details
    
    async def explore_api_detail_page(self, api_info: Dict):
        """各APIの詳細ページからPDFやドキュメントを取得"""
        print(f"\n📖 {api_info['name']} の詳細を探索中...")
        print(f"   URL: {api_info['detail_url']}")
        
        try:
            async with self.session.get(api_info['detail_url'], headers=self.auth_headers) as resp:
                print(f"   ステータス: {resp.status}")
                
                if resp.status != 200:
                    print(f"   ⚠️ アクセスできません")
                    return []
                
                html = await resp.text()
                soup = BeautifulSoup(html, 'lxml')
                
                pdf_urls = []
                
                # 1. 直接的なPDFリンクを探す
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    text = link.get_text(strip=True)
                    
                    if href.lower().endswith('.pdf') or '.pdf' in href.lower():
                        full_url = urljoin(api_info['detail_url'], href)
                        pdf_urls.append({
                            'url': full_url,
                            'name': text or f"{api_info['type']}_document",
                            'type': 'direct_link'
                        })
                
                # 2. OpenAPI/Swagger仕様書のダウンロードリンク
                spec_patterns = [
                    r'download.*(?:openapi|swagger|spec)',
                    r'(?:openapi|swagger|spec).*download',
                    r'api.*spec.*pdf',
                    r'specification.*pdf'
                ]
                
                for pattern in spec_patterns:
                    for element in soup.find_all(text=re.compile(pattern, re.I)):
                        parent = element.parent
                        if parent and parent.name == 'a' and parent.get('href'):
                            full_url = urljoin(api_info['detail_url'], parent['href'])
                            pdf_urls.append({
                                'url': full_url,
                                'name': f"{api_info['type']}_openapi_spec",
                                'type': 'openapi_spec'
                            })
                
                # 3. Kong Portal特有の仕様書エンドポイント
                # /specs/{service_id} のようなエンドポイントを試す
                service_id = api_info.get('data', {}).get('id') or api_info['type']
                spec_endpoints = [
                    f"{BASE_URL.replace('city-api-catalog', 'city-api-catalog-api')}/specs/{service_id}",
                    f"{BASE_URL}/specs/{service_id}",
                    f"{api_info['detail_url']}/spec",
                    f"{api_info['detail_url']}/download"
                ]
                
                for endpoint in spec_endpoints:
                    try:
                        async with self.session.get(endpoint, headers=self.auth_headers) as spec_resp:
                            if spec_resp.status == 200:
                                content_type = spec_resp.headers.get('content-type', '')
                                
                                if 'application/pdf' in content_type:
                                    pdf_urls.append({
                                        'url': endpoint,
                                        'name': f"{api_info['type']}_specification",
                                        'type': 'api_endpoint'
                                    })
                                elif 'application/json' in content_type or 'application/yaml' in content_type:
                                    # OpenAPI/Swaggerの場合、PDFに変換可能なリンクがあるか確認
                                    spec_data = await spec_resp.text()
                                    if 'openapi' in spec_data.lower() or 'swagger' in spec_data.lower():
                                        # 仕様書データを保存（後でPDF変換用）
                                        spec_file = DATA_DIR / f"{api_info['type']}_openapi.json"
                                        with open(spec_file, 'w', encoding='utf-8') as f:
                                            f.write(spec_data)
                                        print(f"   💾 OpenAPI仕様保存: {spec_file}")
                    except:
                        continue
                
                # 4. JavaScriptから埋め込まれたドキュメントURLを探す
                for script in soup.find_all('script'):
                    if script.string:
                        # PDF URLパターンを検索
                        pdf_patterns = re.findall(
                            r'["\']([^"\']*\.pdf[^"\']*)["\']', 
                            script.string, 
                            re.IGNORECASE
                        )
                        for pattern in pdf_patterns:
                            if not pattern.startswith('http'):
                                pattern = urljoin(api_info['detail_url'], pattern)
                            pdf_urls.append({
                                'url': pattern,
                                'name': f"{api_info['type']}_embedded",
                                'type': 'javascript_embedded'
                            })
                
                print(f"   📄 PDFリンク発見: {len(pdf_urls)} 個")
                for pdf in pdf_urls:
                    print(f"     - {pdf['name']}: {pdf['url']}")
                
                return pdf_urls
                
        except Exception as e:
            print(f"   ❌ エラー: {e}")
            return []
    
    async def download_pdf(self, pdf_info: Dict, api_name: str):
        """PDFファイルをダウンロード"""
        url = pdf_info['url']
        base_name = pdf_info['name']
        
        # ファイル名を生成
        safe_api_name = re.sub(r'[^a-zA-Z0-9_-]', '_', api_name)[:20]
        safe_doc_name = re.sub(r'[^a-zA-Z0-9_-]', '_', base_name)[:30]
        filename = f"{safe_api_name}_{safe_doc_name}.pdf"
        filepath = DATA_DIR / filename
        
        # 既存チェック
        if filepath.exists():
            print(f"    ⏭️ スキップ（既存）: {filename}")
            return True
        
        print(f"    📥 ダウンロード中: {filename}")
        print(f"       URL: {url}")
        
        try:
            async with self.session.get(url, headers=self.auth_headers) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    
                    # PDFかどうか確認
                    if content[:4] == b'%PDF':
                        with open(filepath, 'wb') as f:
                            f.write(content)
                        
                        size_kb = len(content) / 1024
                        print(f"    ✅ 保存完了: {filepath} ({size_kb:.1f} KB)")
                        self.downloaded_files.append({
                            'filename': filename,
                            'api': api_name,
                            'size_kb': size_kb,
                            'url': url
                        })
                        return True
                    else:
                        print(f"    ⚠️ PDFではありません（Content-Type: {resp.headers.get('content-type', 'unknown')}）")
                        
                        # HTMLやJSONの場合、PDFへの直接リンクがないか確認
                        if resp.headers.get('content-type', '').startswith('text/html'):
                            html_content = content.decode('utf-8', errors='ignore')
                            soup_content = BeautifulSoup(html_content, 'lxml')
                            
                            # PDF直接リンクを探す
                            pdf_links = soup_content.find_all('a', href=lambda x: x and '.pdf' in x.lower())
                            if pdf_links:
                                print(f"    📎 HTMLから{len(pdf_links)}個のPDFリンク発見")
                                for link in pdf_links[:3]:
                                    href = link.get('href')
                                    if href:
                                        nested_url = urljoin(url, href)
                                        await self.download_pdf({
                                            'url': nested_url,
                                            'name': f"nested_{base_name}"
                                        }, api_name)
                        
                        return False
                else:
                    print(f"    ❌ ダウンロード失敗: {resp.status}")
                    return False
                    
        except Exception as e:
            print(f"    ❌ エラー: {e}")
            return False
    
    async def process_all_apis(self):
        """全APIを処理"""
        print("="*60)
        print("焼津市APIカタログ - 全PDF取得")
        print("="*60)
        
        if not await self.authenticate():
            print("❌ 認証失敗")
            return
        
        print("✅ 認証成功")
        
        # API詳細URLを取得
        api_details = await self.extract_api_detail_urls()
        
        if not api_details:
            print("❌ API詳細情報が取得できませんでした")
            # フォールバック: 既知のパターンで試行
            api_details = [
                {
                    'name': '観光・産業API（FIWARE NGSI v2）',
                    'type': 'tourism_industry', 
                    'detail_url': f"{BASE_URL}/documentation/tourism-industry-api"
                },
                {
                    'name': '公共施設API（FIWARE NGSI v2）',
                    'type': 'public_facility',
                    'detail_url': f"{BASE_URL}/documentation/public-facility-api"  
                },
                {
                    'name': '防災情報API（FIWARE NGSI v2）',
                    'type': 'disaster_info',
                    'detail_url': f"{BASE_URL}/documentation/disaster-info-api"
                }
            ]
        
        # 各APIを処理
        for api in api_details:
            print(f"\n" + "="*50)
            print(f"📋 {api['name']} の処理")
            print("="*50)
            
            # 詳細ページからPDFを探索
            pdf_list = await self.explore_api_detail_page(api)
            
            # PDFをダウンロード
            if pdf_list:
                print(f"\n📥 PDFダウンロード開始: {len(pdf_list)} ファイル")
                for pdf in pdf_list:
                    await self.download_pdf(pdf, api['name'])
                    await asyncio.sleep(0.5)  # レート制限対策
            else:
                print("\n⚠️ PDFファイルが見つかりませんでした")
            
            # 追加: Kong APIエンドポイントから直接取得を試行
            await self.try_direct_api_access(api)
    
    async def extract_api_detail_urls(self) -> List[Dict]:
        """documentationページからAPI詳細URLを抽出"""
        async with self.session.get(f"{BASE_URL}/documentation", headers=self.auth_headers) as resp:
            html = await resp.text()
            soup = BeautifulSoup(html, 'lxml')
            
            api_details = []
            
            # data-json属性を持つ要素から抽出
            catalog_items = soup.find_all(attrs={'data-json': True})
            
            for item in catalog_items:
                try:
                    data = json.loads(item.get('data-json'))
                    title = data.get('info', {}).get('title', '')
                    
                    if title:
                        # クリック可能な要素を探す
                        clickable = item.find('a', href=True)
                        if clickable:
                            detail_url = urljoin(f"{BASE_URL}/", clickable['href'])
                        else:
                            # IDから推測
                            service_id = data.get('id', title.lower().replace(' ', '-').replace('（', '').replace('）', ''))
                            detail_url = f"{BASE_URL}/documentation/{service_id}"
                        
                        api_details.append({
                            'name': title,
                            'type': self._classify_api_type(title),
                            'detail_url': detail_url,
                            'data': data
                        })
                
                except Exception as e:
                    continue
            
            return api_details
    
    def _classify_api_type(self, title: str) -> str:
        """APIタイトルから種類を分類"""
        title_lower = title.lower()
        if '観光' in title_lower or '産業' in title_lower:
            return 'tourism_industry'
        elif '公共施設' in title_lower:
            return 'public_facility'
        elif '防災' in title_lower:
            return 'disaster_info'
        else:
            return 'unknown'
    
    async def explore_api_detail_page(self, api_info: Dict) -> List[Dict]:
        """API詳細ページからPDF URLを取得"""
        try:
            async with self.session.get(api_info['detail_url'], headers=self.auth_headers) as resp:
                if resp.status != 200:
                    return []
                
                html = await resp.text()
                soup = BeautifulSoup(html, 'lxml')
                
                pdf_urls = []
                
                # PDFリンクを探す
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    text = link.get_text(strip=True)
                    
                    if '.pdf' in href.lower() or any(keyword in text.lower() 
                                                   for keyword in ['pdf', 'download', 'spec', '仕様書', 'ダウンロード']):
                        full_url = urljoin(api_info['detail_url'], href)
                        pdf_urls.append({
                            'url': full_url,
                            'name': text or 'document',
                            'type': 'detail_page'
                        })
                
                # Swagger UI から仕様書を探す
                swagger_elements = soup.find_all(['div', 'section'], class_=re.compile(r'swagger|openapi'))
                for element in swagger_elements:
                    # data属性から仕様書URLを取得
                    spec_url = element.get('data-url') or element.get('data-spec-url')
                    if spec_url:
                        full_url = urljoin(api_info['detail_url'], spec_url)
                        pdf_urls.append({
                            'url': full_url,
                            'name': f"{api_info['type']}_swagger_spec",
                            'type': 'swagger_spec'
                        })
                
                return pdf_urls
                
        except Exception as e:
            print(f"   ❌ エラー: {e}")
            return []
    
    async def try_direct_api_access(self, api_info: Dict):
        """Kong APIエンドポイントから直接アクセスを試行"""
        print(f"\n🔧 {api_info['name']} - 直接APIアクセス試行")
        
        api_base = BASE_URL.replace('city-api-catalog', 'city-api-catalog-api')
        service_id = api_info.get('data', {}).get('id') or api_info['type']
        
        direct_endpoints = [
            f"{api_base}/services/{service_id}/documentation",
            f"{api_base}/files?tags={service_id}",
            f"{api_base}/specs/{service_id}",
        ]
        
        for endpoint in direct_endpoints:
            try:
                async with self.session.get(endpoint, headers=self.auth_headers) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get('content-type', '')
                        
                        if 'application/pdf' in content_type:
                            # 直接PDFが返される場合
                            await self.download_pdf({
                                'url': endpoint,
                                'name': f'direct_{service_id}'
                            }, api_info['name'])
                        
                        elif 'application/json' in content_type:
                            data = await resp.json()
                            print(f"     ✅ JSONデータ取得: {endpoint}")
                            
                            # ファイルリストから PDFを探す
                            if isinstance(data, dict) and 'data' in data:
                                files = data['data']
                                if isinstance(files, list):
                                    pdf_files = [f for f in files 
                                               if isinstance(f, dict) and 
                                               (f.get('path', '').lower().endswith('.pdf') or 
                                                'pdf' in f.get('contents', '').lower())]
                                    
                                    if pdf_files:
                                        print(f"       📄 PDFファイル発見: {len(pdf_files)} 個")
                                        for pdf_file in pdf_files:
                                            # ファイル内容を直接ダウンロード
                                            if 'contents' in pdf_file and pdf_file['contents'].startswith('%PDF'):
                                                filename = f"{service_id}_{pdf_file.get('path', 'file').replace('/', '_')}"
                                                filepath = DATA_DIR / filename
                                                
                                                with open(filepath, 'w', encoding='utf-8') as f:
                                                    f.write(pdf_file['contents'])
                                                print(f"       💾 保存: {filepath}")
            except:
                continue


async def main():
    async with APIDocumentDownloader() as downloader:
        await downloader.process_all_apis()
        
        # 結果レポート
        print("\n" + "="*60)
        print("📊 ダウンロード完了レポート")
        print("="*60)
        
        if downloader.downloaded_files:
            print(f"\n✅ ダウンロードしたファイル: {len(downloader.downloaded_files)} 個")
            
            total_size = 0
            for file_info in downloader.downloaded_files:
                print(f"  📄 {file_info['filename']}")
                print(f"     API: {file_info['api']}")
                print(f"     サイズ: {file_info['size_kb']:.1f} KB")
                print(f"     URL: {file_info['url']}")
                total_size += file_info['size_kb']
            
            print(f"\n📊 合計サイズ: {total_size:.1f} KB")
        else:
            print("\n⚠️ 新しいPDFファイルはダウンロードされませんでした")
        
        # フォルダ内のファイル一覧
        all_files = list(DATA_DIR.glob("*.pdf"))
        print(f"\n📁 data/documentation の全PDFファイル: {len(all_files)} 個")
        for pdf_file in sorted(all_files):
            size_mb = pdf_file.stat().st_size / (1024 * 1024)
            print(f"  - {pdf_file.name} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    asyncio.run(main())