#!/usr/bin/env python3
"""
焼津市APIカタログ スクレイピングモジュール

APIカタログサイトから防災関連のAPIドキュメント情報を取得し、
ローカルに保存する機能を提供
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
import base64

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YaizuAPIScraper:
    """焼津市APIカタログのスクレイピングクラス"""
    
    def __init__(self):
        # 環境変数から認証情報を取得
        # APIカタログ用（メール/パスワード）
        self.email = os.getenv('YAIZU_API_EMAIL')
        self.password = os.getenv('YAIZU_API_PASSWORD')
        
        # API実行用（APIキー）
        self.api_key = os.getenv('YAIZU_API_KEY')
        
        if not self.email or not self.password:
            logger.warning("APIカタログ認証情報（メール/パスワード）が設定されていません。")
        
        if not self.api_key:
            logger.info("API実行用のAPIキーが設定されていません。API実行時に必要となります。")
        
        # URLの設定
        self.base_url = "https://city-api-catalog.smartcity-pf.com/yaizu"
        self.api_base_url = "https://city-api-catalog-api.smartcity-pf.com/yaizu"
        self.login_url = f"{self.base_url}/login"
        
        # データ保存先の設定
        self.data_dir = Path("data/api_specs")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # セッション管理
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_headers: Dict[str, str] = {}
        self.is_authenticated = False
    
    async def __aenter__(self):
        """非同期コンテキストマネージャーの開始"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了"""
        if self.session:
            await self.session.close()
    
    async def login(self) -> bool:
        """APIカタログにログイン（メール/パスワード認証）"""
        # APIカタログはメール/パスワード認証を使用
        if not self.email or not self.password:
            logger.error("APIカタログのログイン認証情報（メール/パスワード）が設定されていません")
            return False
        
        logger.info(f"APIカタログにログイン試行: {self.email}")
        
        try:
            # まず通常のカタログページにアクセスしてセッションクッキーを取得
            async with self.session.get(self.base_url) as response:
                logger.debug(f"カタログページアクセス: {response.status}")
            
            # Basic認証ヘッダーの作成
            credentials = f"{self.email}:{self.password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            self.auth_headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/html"
            }
            
            # カタログページにBasic認証でアクセス
            async with self.session.get(
                f"{self.base_url}/catalog",
                headers=self.auth_headers
            ) as response:
                logger.info(f"認証応答ステータス: {response.status}")
                if response.status == 200:
                    self.is_authenticated = True
                    logger.info("APIカタログへのログインに成功しました")
                    return True
                elif response.status == 401:
                    logger.error("認証に失敗しました。メールアドレスとパスワードを確認してください。")
                    # HTMLレスポンスの一部をログ出力
                    text = await response.text()
                    logger.debug(f"認証エラー応答: {text[:500]}")
                    return False
                else:
                    logger.error(f"ログインに失敗しました。ステータスコード: {response.status}")
                    text = await response.text()
                    logger.debug(f"エラー応答: {text[:500]}")
                    return False
                    
        except Exception as e:
            logger.error(f"ログイン中にエラーが発生しました: {e}")
            return False
    
    async def fetch_api_catalog(self) -> Optional[Dict[str, Any]]:
        """APIカタログ情報を取得"""
        if not self.is_authenticated:
            logger.error("認証されていません。先にloginを実行してください。")
            return None
        
        logger.info("APIカタログを取得中...")
        
        try:
            # まずAPIエンドポイントから直接データを取得
            api_data = await self._fetch_api_endpoint_data()
            
            catalog_data = {
                "title": "焼津市APIカタログ",
                "apis": [],
                "categories": [],
                "last_updated": datetime.now().isoformat(),
                "raw_api_data": api_data
            }
            
            # APIデータからAPI一覧を抽出
            if api_data:
                catalog_data.update(await self._parse_api_data(api_data))
            
            return catalog_data
                
        except Exception as e:
            logger.error(f"APIカタログ取得中にエラーが発生しました: {e}")
            return None
    
    async def _parse_catalog_page(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """カタログページをパースしてAPI情報を抽出"""
        catalog_data = {
            "title": "焼津市APIカタログ",
            "apis": [],
            "categories": [],
            "last_updated": datetime.now().isoformat()
        }
        
        # APIリストの抽出（実際のHTML構造に応じて調整が必要）
        # 以下は仮の実装
        
        # APIセクションを探す
        api_sections = soup.find_all(['div', 'section'], class_=['api-item', 'api-card'])
        for section in api_sections:
            api_info = {}
            
            # API名
            title_elem = section.find(['h2', 'h3', 'a'])
            if title_elem:
                api_info['name'] = title_elem.get_text(strip=True)
            
            # 説明
            desc_elem = section.find(['p', 'div'], class_=['description', 'desc'])
            if desc_elem:
                api_info['description'] = desc_elem.get_text(strip=True)
            
            # カテゴリ（防災関連かどうかをチェック）
            category_elem = section.find(['span', 'div'], class_=['category', 'tag'])
            if category_elem:
                api_info['category'] = category_elem.get_text(strip=True)
            
            # 防災関連のキーワードチェック
            if any(keyword in str(section) for keyword in ['防災', '災害', '避難', '緊急', '地震', '津波', '台風']):
                api_info['is_disaster_related'] = True
            else:
                api_info['is_disaster_related'] = False
            
            # 詳細ページへのリンク
            link_elem = section.find('a', href=True)
            if link_elem:
                api_info['detail_url'] = urljoin(self.base_url, link_elem['href'])
            
            if api_info:
                catalog_data['apis'].append(api_info)
        
        # カテゴリ一覧の抽出
        category_list = soup.find_all(['li', 'div'], class_=['category-item'])
        for cat in category_list:
            catalog_data['categories'].append(cat.get_text(strip=True))
        
        logger.info(f"カタログページから {len(catalog_data['apis'])} 個のAPIを検出しました")
        
        return catalog_data
    
    async def _fetch_api_endpoint_data(self) -> Optional[Dict[str, Any]]:
        """APIエンドポイントから直接データを取得"""
        # 様々なエンドポイントを試行
        endpoints_to_try = [
            f"{self.api_base_url}",
            f"{self.api_base_url}/specs",
            f"{self.api_base_url}/api-catalog",
            f"{self.api_base_url}/services",
            f"{self.api_base_url}/plugins"
        ]
        
        for endpoint in endpoints_to_try:
            try:
                logger.debug(f"エンドポイントにアクセス中: {endpoint}")
                async with self.session.get(
                    endpoint,
                    headers=self.auth_headers
                ) as response:
                    logger.debug(f"エンドポイント応答 {endpoint}: {response.status}")
                    
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        text_content = await response.text()
                        
                        logger.debug(f"コンテンツタイプ: {content_type}")
                        logger.debug(f"レスポンス長さ: {len(text_content)}")
                        
                        # JSONレスポンスの場合
                        if 'application/json' in content_type:
                            try:
                                json_data = json.loads(text_content)
                                logger.info(f"JSONデータを取得しました: {endpoint}")
                                return {"source_endpoint": endpoint, "data": json_data}
                            except json.JSONDecodeError:
                                logger.warning(f"JSON解析に失敗: {endpoint}")
                        
                        # HTMLレスポンスの場合
                        else:
                            soup = BeautifulSoup(text_content, 'lxml')
                            
                            # JSONデータが埋め込まれている場合の抽出
                            script_tags = soup.find_all('script')
                            for script in script_tags:
                                script_text = script.string or script.get_text()
                                if script_text and ('api' in script_text.lower() or 'service' in script_text.lower()):
                                    try:
                                        # JavaScript内のJSONデータを抽出
                                        json_start = script_text.find('{')
                                        json_end = script_text.rfind('}') + 1
                                        if json_start >= 0 and json_end > json_start:
                                            potential_json = script_text[json_start:json_end]
                                            json_data = json.loads(potential_json)
                                            logger.info(f"埋め込みJSONデータを取得: {endpoint}")
                                            return {"source_endpoint": endpoint, "data": json_data}
                                    except:
                                        continue
                            
                            # HTMLからAPI情報を抽出
                            api_info = await self._extract_api_from_html(soup)
                            if api_info:
                                return {"source_endpoint": endpoint, "html_data": api_info}
                    
                    elif response.status == 401:
                        logger.warning(f"認証が必要: {endpoint}")
                    elif response.status == 404:
                        logger.debug(f"エンドポイントが存在しません: {endpoint}")
                    else:
                        logger.warning(f"予期しないステータス {response.status}: {endpoint}")
                        
            except Exception as e:
                logger.debug(f"エンドポイントアクセスエラー {endpoint}: {e}")
                continue
        
        logger.warning("すべてのエンドポイントでデータを取得できませんでした")
        return None
    
    async def _extract_api_from_html(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """HTMLからAPI情報を抽出"""
        api_info = {
            "apis": [],
            "services": [],
            "routes": []
        }
        
        # リンクやテキストからAPIっぽい情報を抽出
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if any(keyword in href.lower() or keyword in text.lower() 
                   for keyword in ['api', 'service', 'endpoint', 'data']):
                api_info['apis'].append({
                    'name': text,
                    'url': href,
                    'type': 'link_discovery'
                })
        
        # テーブルからの情報抽出
        tables = soup.find_all('table')
        for table in tables:
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            if any('api' in h.lower() or 'service' in h.lower() for h in headers):
                for row in table.find_all('tr')[1:]:
                    cells = [td.get_text(strip=True) for td in row.find_all('td')]
                    if cells:
                        api_info['services'].append(dict(zip(headers, cells)))
        
        return api_info if (api_info['apis'] or api_info['services']) else None
    
    async def _parse_api_data(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """取得したAPIデータを解析してAPI一覧を作成"""
        parsed_data = {
            "apis": [],
            "categories": set()
        }
        
        if not api_data:
            return parsed_data
        
        # データ構造に応じて解析
        data = api_data.get('data', api_data)
        
        # Kong API Gateway形式のデータ解析
        if isinstance(data, dict):
            # サービス一覧
            if 'services' in data:
                services = data['services']
                if isinstance(services, list):
                    for service in services:
                        api_info = {
                            'name': service.get('name', 'Unknown Service'),
                            'description': service.get('description', ''),
                            'category': 'service',
                            'endpoints': [service.get('url', '')],
                            'is_disaster_related': self._is_disaster_related(service.get('name', '') + ' ' + service.get('description', ''))
                        }
                        parsed_data['apis'].append(api_info)
                        parsed_data['categories'].add('service')
            
            # ルート一覧
            if 'routes' in data:
                routes = data['routes']
                if isinstance(routes, list):
                    for route in routes:
                        api_info = {
                            'name': route.get('name', f"Route {route.get('id', 'Unknown')}"),
                            'description': f"Path: {', '.join(route.get('paths', []))}",
                            'category': 'route',
                            'endpoints': route.get('paths', []),
                            'methods': route.get('methods', []),
                            'is_disaster_related': self._is_disaster_related(' '.join(route.get('paths', [])))
                        }
                        parsed_data['apis'].append(api_info)
                        parsed_data['categories'].add('route')
            
            # HTMLから抽出したデータ
            if 'html_data' in api_data:
                html_data = api_data['html_data']
                for api in html_data.get('apis', []):
                    api['is_disaster_related'] = self._is_disaster_related(api.get('name', '') + ' ' + api.get('url', ''))
                    parsed_data['apis'].append(api)
                    parsed_data['categories'].add(api.get('type', 'html_discovery'))
        
        parsed_data['categories'] = list(parsed_data['categories'])
        logger.info(f"解析完了: {len(parsed_data['apis'])} 個のAPI, {len(parsed_data['categories'])} 個のカテゴリ")
        
        return parsed_data
    
    def _is_disaster_related(self, text: str) -> bool:
        """テキストが防災関連かどうかを判定"""
        disaster_keywords = ['防災', '災害', '避難', '緊急', '地震', '津波', '台風', '洪水', '土砂災害', '警報', 'disaster', 'emergency', 'evacuation']
        return any(keyword in text.lower() for keyword in disaster_keywords)
    
    async def fetch_disaster_apis(self) -> List[Dict[str, Any]]:
        """防災関連のAPIのみを取得"""
        catalog = await self.fetch_api_catalog()
        if not catalog:
            return []
        
        disaster_apis = []
        for api in catalog.get('apis', []):
            if api.get('is_disaster_related', False):
                # 詳細情報を取得
                if 'detail_url' in api:
                    details = await self._fetch_api_details(api['detail_url'])
                    if details:
                        api.update(details)
                disaster_apis.append(api)
        
        logger.info(f"防災関連のAPI {len(disaster_apis)} 個を検出しました")
        return disaster_apis
    
    async def _fetch_api_details(self, url: str) -> Optional[Dict[str, Any]]:
        """API詳細ページから情報を取得"""
        try:
            async with self.session.get(url, headers=self.auth_headers) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')
                
                details = {
                    "endpoints": [],
                    "data_models": [],
                    "parameters": [],
                    "examples": []
                }
                
                # エンドポイント情報の抽出
                endpoint_sections = soup.find_all(['code', 'pre'], class_=['endpoint', 'url'])
                for endpoint in endpoint_sections:
                    details['endpoints'].append(endpoint.get_text(strip=True))
                
                # データモデルの抽出
                model_sections = soup.find_all(['div', 'section'], class_=['data-model', 'schema'])
                for model in model_sections:
                    model_text = model.get_text(strip=True)
                    # JSON形式の場合はパース
                    try:
                        model_data = json.loads(model_text)
                        details['data_models'].append(model_data)
                    except:
                        details['data_models'].append(model_text)
                
                # パラメータ情報の抽出
                param_tables = soup.find_all('table')
                for table in param_tables:
                    headers = [th.get_text(strip=True) for th in table.find_all('th')]
                    if any(h in headers for h in ['パラメータ', 'Parameter', 'Name']):
                        for row in table.find_all('tr')[1:]:  # ヘッダー行をスキップ
                            cells = [td.get_text(strip=True) for td in row.find_all('td')]
                            if cells:
                                details['parameters'].append(dict(zip(headers, cells)))
                
                return details
                
        except Exception as e:
            logger.error(f"API詳細情報の取得エラー: {e}")
            return None
    
    async def save_api_data(self, api_data: Dict[str, Any], filename: str) -> bool:
        """APIデータをローカルに保存"""
        try:
            filepath = self.data_dir / f"{filename}.json"
            
            # メタデータを追加
            api_data['metadata'] = {
                'scraped_at': datetime.now().isoformat(),
                'source_url': self.base_url,
                'version': '1.0'
            }
            
            # JSONファイルとして保存
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(api_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"APIデータを保存しました: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"データ保存エラー: {e}")
            return False
    
    async def scrape_and_save_all(self) -> Dict[str, Any]:
        """すべてのAPIデータをスクレイピングして保存"""
        result = {
            'success': False,
            'total_apis': 0,
            'disaster_apis': 0,
            'saved_files': []
        }
        
        # ログイン
        if not await self.login():
            logger.error("ログインに失敗しました")
            return result
        
        # APIカタログを取得
        catalog = await self.fetch_api_catalog()
        if catalog:
            # 全体のカタログを保存
            if await self.save_api_data(catalog, 'api_catalog'):
                result['saved_files'].append('api_catalog.json')
            
            result['total_apis'] = len(catalog.get('apis', []))
        
        # 防災関連APIを取得
        disaster_apis = await self.fetch_disaster_apis()
        if disaster_apis:
            disaster_catalog = {
                'title': '焼津市防災関連API',
                'apis': disaster_apis,
                'last_updated': datetime.now().isoformat()
            }
            
            if await self.save_api_data(disaster_catalog, 'disaster_apis'):
                result['saved_files'].append('disaster_apis.json')
            
            result['disaster_apis'] = len(disaster_apis)
            
            # 個別のAPI詳細も保存
            for api in disaster_apis:
                api_name = api.get('name', 'unknown').replace(' ', '_').replace('/', '_')
                if await self.save_api_data(api, f"api_{api_name}"):
                    result['saved_files'].append(f"api_{api_name}.json")
        
        result['success'] = True
        logger.info(f"スクレイピング完了: {result}")
        
        return result
    
    def load_saved_data(self, filename: str) -> Optional[Dict[str, Any]]:
        """保存済みのデータを読み込む"""
        try:
            filepath = self.data_dir / f"{filename}.json"
            if not filepath.exists():
                logger.warning(f"ファイルが見つかりません: {filepath}")
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"データ読み込みエラー: {e}")
            return None
    
    def list_saved_files(self) -> List[str]:
        """保存済みファイルの一覧を取得"""
        try:
            files = [f.stem for f in self.data_dir.glob('*.json')]
            return sorted(files)
        except Exception as e:
            logger.error(f"ファイル一覧取得エラー: {e}")
            return []
    
    async def execute_api(self, api_endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """APIキーを使用して実際のAPIを実行
        
        Args:
            api_endpoint: 実行するAPIのエンドポイントURL
            params: APIパラメータ
        
        Returns:
            APIレスポンス
        """
        if not self.api_key:
            logger.error("API実行にはAPIキーが必要です")
            return {"error": "APIキーが設定されていません"}
        
        # APIキー用のヘッダー
        api_headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.get(
                api_endpoint,
                headers=api_headers,
                params=params
            ) as response:
                logger.info(f"API実行: {api_endpoint} - ステータス: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    return {"success": True, "data": data}
                elif response.status == 401:
                    return {"error": "APIキー認証エラー", "status": 401}
                else:
                    error_text = await response.text()
                    return {"error": f"APIエラー: {response.status}", "details": error_text}
                    
        except Exception as e:
            logger.error(f"API実行エラー: {e}")
            return {"error": f"API実行エラー: {str(e)}"}


async def main():
    """テスト用のメイン関数"""
    async with YaizuAPIScraper() as scraper:
        # スクレイピングと保存を実行
        result = await scraper.scrape_and_save_all()
        print(f"スクレイピング結果: {result}")
        
        # 保存されたファイルの確認
        files = scraper.list_saved_files()
        print(f"保存されたファイル: {files}")
        
        # データの読み込みテスト
        if files:
            data = scraper.load_saved_data(files[0])
            if data:
                print(f"読み込んだデータ: {list(data.keys())}")


if __name__ == "__main__":
    asyncio.run(main())