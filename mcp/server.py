#!/usr/bin/env python3
"""
焼津市スマートシティ MCP サーバー

焼津市のAPIカタログから取得したデータをMCPリソースとして提供
スクレイピング機能と統合したModel Context Protocol サーバー実装
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# scraper モジュールのインポート
try:
    from .scraper import YaizuAPIScraper
except ImportError:
    # 直接実行時の絶対インポート
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from scraper import YaizuAPIScraper

# 環境変数の読み込み
load_dotenv()

# ログ設定（STDIOサーバーではstderrのみ使用）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("yaizu-smartcity-mcp")


class APIDocumentManager:
    """APIドキュメント管理クラス"""
    
    def __init__(self):
        self.data_dir = Path("data/api_specs")
        self.api_docs_dir = Path("data/api_specs")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.api_docs_dir.mkdir(parents=True, exist_ok=True)
        self.scraper = None
    
    async def initialize_scraper(self) -> YaizuAPIScraper:
        """スクレイパーの初期化"""
        if not self.scraper:
            self.scraper = YaizuAPIScraper()
            await self.scraper.__aenter__()
        return self.scraper
    
    async def cleanup(self):
        """リソースのクリーンアップ"""
        if self.scraper:
            await self.scraper.__aexit__(None, None, None)
    
    def load_api_docs(self, filename: str = "api_catalog") -> Optional[Dict[str, Any]]:
        """保存済みのAPIドキュメントを読み込む"""
        try:
            # data/api_specsディレクトリを確認
            specs_filepath = self.data_dir / f"{filename}.json"
            if specs_filepath.exists():
                with open(specs_filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            data_filepath = self.data_dir / f"{filename}.json"
            if data_filepath.exists():
                with open(data_filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            logger.warning(f"APIドキュメントが見つかりません: {filename}")
            return None
                
        except Exception as e:
            logger.error(f"APIドキュメント読み込みエラー: {e}")
            return None
    
    def list_available_docs(self) -> List[str]:
        """利用可能なドキュメントファイルの一覧"""
        try:
            files = set()
            # data/api_specsディレクトリのファイル
            if self.data_dir.exists():
                files.update(f.stem for f in self.data_dir.glob('*.json'))
            return sorted(list(files))
        except Exception as e:
            logger.error(f"ドキュメント一覧取得エラー: {e}")
            return []
    
    def search_apis(self, keyword: str) -> List[Dict[str, Any]]:
        """キーワードでAPIを検索"""
        results = []
        
        # すべてのドキュメントを検索
        for doc_file in self.list_available_docs():
            doc = self.load_api_docs(doc_file)
            if not doc:
                continue
            
            # APIs配列がある場合
            if 'apis' in doc:
                for api in doc['apis']:
                    # 名前と説明で検索
                    if (keyword.lower() in api.get('name', '').lower() or 
                        keyword.lower() in api.get('description', '').lower() or
                        keyword.lower() in api.get('category', '').lower()):
                        results.append({
                            'source_file': doc_file,
                            'api': api
                        })
        
        return results


# グローバルドキュメントマネージャー
doc_manager = APIDocumentManager()

# MCPサーバーのセットアップ
mcp = FastMCP("yaizu-smartcity")


# ========== MCPツール ==========

@mcp.tool()
async def scrape_api_docs() -> str:
    """
    焼津市APIカタログから最新のAPIドキュメントをスクレイピングして保存します。
    認証情報は.envファイルから自動的に読み込まれます。
    
    Returns:
        str: スクレイピング結果のサマリー
    """
    try:
        scraper = await doc_manager.initialize_scraper()
        
        # スクレイピングと保存を実行
        result = await scraper.scrape_and_save_all()
        
        if result['success']:
            summary = f"""# スクレイピング完了

## 結果サマリー
- **総API数**: {result['total_apis']}
- **防災関連API数**: {result['disaster_apis']}
- **保存されたファイル数**: {len(result['saved_files'])}

## 保存されたファイル
"""
            for filename in result['saved_files']:
                summary += f"- {filename}\n"
            
            summary += "\n✅ APIドキュメントの更新が完了しました。"
            return summary
        else:
            return "❌ スクレイピングに失敗しました。認証情報を確認してください。"
            
    except Exception as e:
        logger.error(f"スクレイピングエラー: {e}")
        return f"❌ エラーが発生しました: {str(e)}"


@mcp.tool()
async def generate_api_command(entity_type: str) -> str:
    """
    指定したエンティティタイプに対するAPI実行コマンドを生成します。
    APIカタログの情報を基に適切なパラメータを提案します。
    
    Args:
        entity_type: エンティティタイプ（例: Aed, EvacuationShelter）
    
    Returns:
        str: 使用可能なAPIコマンド例
    """
    try:
        # APIカタログからエンティティ情報を取得
        doc = doc_manager.load_api_docs(entity_type)
        
        if not doc:
            available_types = doc_manager.list_available_docs()
            return f"❌ エンティティタイプ '{entity_type}' の情報が見つかりません。\n\n利用可能なエンティティ: {', '.join(available_types)}"
        
        output = f"# {entity_type} API コマンド生成\n\n"
        output += f"## 基本情報\n"
        output += f"- **データモデル名**: {doc.get('dataModelName', 'N/A')}\n"
        output += f"- **Fiware-Service**: `{doc.get('fiwareService', 'smartcity_yaizu')}`\n"
        output += f"- **Fiware-ServicePath**: `{doc.get('fiwareServicePath', '/')}`\n\n"
        
        output += f"## 基本的な取得コマンド\n```\n"
        output += f"execute_yaizu_api(\"{entity_type}\", limit=10)\n```\n\n"
        
        output += f"## パラメータ付きコマンド例\n"
        output += f"```\n"
        output += f"# 件数指定\nexecute_yaizu_api(\"{entity_type}\", limit=50)\n\n"
        
        # 属性情報からクエリ例を生成
        if 'attributes' in doc:
            attributes = doc['attributes']
            
            # 地理的属性がある場合の例
            has_location = any('Latitude' in str(attr) or 'Longitude' in str(attr) for attr in attributes.values())
            if has_location:
                output += f"# 地理的範囲指定（焼津駅周辺1kmの例）\n"
                output += f"execute_yaizu_api(\"{entity_type}\", params='{{\"georel\":\"near;maxDistance:1000\",\"geometry\":\"point\",\"coords\":\"34.8675,138.3236\"}}', limit=20)\n\n"
            
            # ID指定の例
            output += f"# 特定ID指定\n"
            output += f"execute_yaizu_api(\"{entity_type}\", params='{{\"id\":\"jp.smartcity-yaizu.{entity_type}.001\"}}', limit=1)\n\n"
            
            # 属性フィルタリングの例
            text_attrs = [k for k, v in attributes.items() if v.get('type') == 'Text']
            if text_attrs:
                first_attr = text_attrs[0]
                output += f"# 属性フィルタリング（例: {first_attr}に「焼津」を含む）\n"
                output += f"execute_yaizu_api(\"{entity_type}\", params='{{\"q\":\"{first_attr}~=.*焼津.*\"}}', limit=30)\n\n"
            
            # 複数条件の例
            output += f"# 複数条件組み合わせ\n"
            output += f"execute_yaizu_api(\"{entity_type}\", params='{{\"limit\":\"100\",\"options\":\"count\",\"orderBy\":\"Identification\"}}', limit=100)\n\n"
        
        output += f"```\n\n"
        
        output += f"## 利用可能な主な属性\n"
        if 'attributes' in doc:
            for attr_key, attr_info in list(doc['attributes'].items())[:10]:  # 最初の10個のみ表示
                output += f"- **{attr_key}** ({attr_info.get('name', '')}): {attr_info.get('description', '')} [{attr_info.get('type', '')}]\n"
            if len(doc['attributes']) > 10:
                output += f"- ... 他 {len(doc['attributes']) - 10} 個の属性\n"
        
        output += f"\n## NGSIv2クエリ詳細\n"
        output += f"- **type**: エンティティタイプ指定\n"
        output += f"- **id**: 特定IDでフィルタ\n"
        output += f"- **q**: 属性値による条件指定\n"
        output += f"- **georel**: 地理的関係指定 (near, coveredBy, intersects等)\n"
        output += f"- **geometry**: 地理領域指定 (point, polygon等)\n"
        output += f"- **coords**: 座標指定\n"
        output += f"- **limit**: 取得件数制限 (1-1000)\n"
        output += f"- **offset**: オフセット指定\n"
        output += f"- **attrs**: 取得属性限定\n"
        output += f"- **orderBy**: ソート順指定\n"
        output += f"- **options**: 追加オプション (count, keyValues等)\n"
        
        return output
        
    except Exception as e:
        logger.error(f"コマンド生成エラー: {e}")
        return f"❌ エラーが発生しました: {str(e)}"


@mcp.tool()
async def execute_api_endpoint(endpoint_url: str, method: str = "GET", params: Optional[str] = None) -> str:
    """
    【非推奨】汎用エンドポイント実行ツール（互換性のために保持）
    新しいコードでは execute_yaizu_api() を使用してください。
    
    Args:
        endpoint_url: APIエンドポイントのURL
        method: HTTPメソッド（GET, POST, PUT, DELETE）
        params: クエリパラメータまたはJSONボディ（JSON文字列形式）
    
    Returns:
        str: APIレスポンス
    """
    return "⚠️ この機能は非推奨です。\n\n焼津市APIを使用する場合は、`execute_yaizu_api()` 関数を使用してください。\n\n例:\n```\nexecute_yaizu_api(\"Aed\", limit=10)\n```\n\nコマンド生成には `generate_api_command()` を使用してください。"


@mcp.tool()
async def search_api_docs(keyword: str) -> str:
    """
    保存済みのAPIドキュメントから特定のキーワードでAPIを検索します。
    
    Args:
        keyword: 検索キーワード（API名、説明、カテゴリで検索）
    
    Returns:
        str: 検索結果
    """
    try:
        results = doc_manager.search_apis(keyword)
        
        if not results:
            return f"「{keyword}」に一致するAPIが見つかりませんでした。"
        
        output = f"# 検索結果: 「{keyword}」\n\n"
        output += f"**{len(results)}件** のAPIが見つかりました:\n\n"
        
        for i, result in enumerate(results, 1):
            api = result['api']
            output += f"## {i}. {api.get('name', '名称不明')}\n"
            output += f"- **説明**: {api.get('description', '説明なし')}\n"
            output += f"- **カテゴリ**: {api.get('category', '未分類')}\n"
            output += f"- **防災関連**: {'はい' if api.get('is_disaster_related') else 'いいえ'}\n"
            output += f"- **ソースファイル**: {result['source_file']}.json\n"
            
            if api.get('endpoints'):
                output += f"- **エンドポイント**: {', '.join(api['endpoints'][:3])}\n"
            
            output += "\n"
        
        return output
        
    except Exception as e:
        logger.error(f"検索エラー: {e}")
        return f"❌ 検索中にエラーが発生しました: {str(e)}"


@mcp.tool()
async def get_api_details(api_name: str) -> str:
    """
    特定のAPIの詳細情報を取得します。
    
    Args:
        api_name: API名またはファイル名（拡張子なし）
    
    Returns:
        str: API詳細情報
    """
    try:
        # まずファイル名として検索
        doc = doc_manager.load_api_docs(api_name)
        
        if not doc:
            # API名で検索
            results = doc_manager.search_apis(api_name)
            if results:
                api = results[0]['api']
                doc = api
            else:
                return f"「{api_name}」というAPIが見つかりませんでした。"
        
        # 詳細情報の整形
        output = f"# API詳細情報\n\n"
        
        if isinstance(doc, dict):
            # データモデル形式の場合
            if 'dataModelName' in doc:
                output += f"## {doc['dataModelName']}\n\n"
                output += f"**FIWAREサービス**: {doc.get('fiwareService', '')}\n"
                output += f"**サービスパス**: {doc.get('fiwareServicePath', '')}\n"
                output += f"**エンティティタイプ**: {doc.get('entityType', '')}\n"
                output += f"**エンティティIDパターン**: {doc.get('entityIdPattern', '')}\n\n"
                
                # 属性情報
                if 'attributes' in doc:
                    output += f"### 属性 ({len(doc['attributes'])}個)\n"
                    for attr_key, attr_info in doc['attributes'].items():
                        output += f"- **{attr_key}** ({attr_info.get('name', '')}): {attr_info.get('description', '')} - {attr_info.get('type', '')}\n"
                    output += "\n"
                
                # リクエスト例
                if 'example_request' in doc:
                    output += "### リクエスト例\n```json\n"
                    output += json.dumps(doc['example_request'], ensure_ascii=False, indent=2)
                    output += "\n```\n\n"
                
                # レスポンス例
                if 'example_response' in doc:
                    output += "### レスポンス例\n```json\n"
                    output += json.dumps(doc['example_response'], ensure_ascii=False, indent=2)[:2000]
                    output += "\n```\n\n"
                
                return output
            
            # 従来形式の場合
            # タイトル
            if 'title' in doc:
                output += f"## {doc['title']}\n\n"
            elif 'name' in doc:
                output += f"## {doc['name']}\n\n"
            
            # 基本情報
            if 'description' in doc:
                output += f"**説明**: {doc['description']}\n\n"
            
            if 'category' in doc:
                output += f"**カテゴリ**: {doc['category']}\n\n"
            
            # エンドポイント
            if 'endpoints' in doc and doc['endpoints']:
                output += "### エンドポイント\n"
                for endpoint in doc['endpoints']:
                    output += f"- `{endpoint}`\n"
                output += "\n"
            
            # データモデル
            if 'data_models' in doc and doc['data_models']:
                output += "### データモデル\n```json\n"
                output += json.dumps(doc['data_models'], ensure_ascii=False, indent=2)
                output += "\n```\n\n"
            
            # パラメータ
            if 'parameters' in doc and doc['parameters']:
                output += "### パラメータ\n"
                for param in doc['parameters']:
                    if isinstance(param, dict):
                        output += f"- **{param.get('name', 'unknown')}**: {param.get('description', '')}\n"
                output += "\n"
            
            # APIs配列がある場合
            if 'apis' in doc:
                output += f"### 含まれるAPI ({len(doc['apis'])}個)\n"
                for api in doc['apis'][:10]:  # 最大10個まで表示
                    output += f"- {api.get('name', '名称不明')}: {api.get('description', '')[:50]}...\n"
                output += "\n"
            
            # メタデータ
            if 'metadata' in doc:
                output += "### メタデータ\n"
                output += f"- **取得日時**: {doc['metadata'].get('scraped_at', '不明')}\n"
                output += f"- **ソースURL**: {doc['metadata'].get('source_url', '不明')}\n"
                output += f"- **バージョン**: {doc['metadata'].get('version', '不明')}\n"
        
        return output
        
    except Exception as e:
        logger.error(f"詳細取得エラー: {e}")
        return f"❌ API詳細の取得中にエラーが発生しました: {str(e)}"


@mcp.tool()
async def execute_yaizu_api(entity_type: str, params: Optional[str] = None, limit: int = 10) -> str:
    """
    焼津市のFIWARE NGSIv2 APIからエンティティデータを取得します。
    APIカタログの情報を基に適切なエンドポイント設定を自動で行います。
    
    Args:
        entity_type: エンティティタイプ（例: Aed, EvacuationShelter, DisasterMail）
        params: 追加のクエリパラメータ（JSON文字列形式）
        limit: 取得件数制限（1-1000、デフォルト10）
    
    Returns:
        str: APIレスポンス
    """
    import aiohttp
    import uuid
    
    try:
        # APIキーを環境変数から取得
        api_key = os.getenv('YAIZU_API_KEY')
        if not api_key:
            return "❌ エラー: APIキーが設定されていません。.envファイルにYAIZU_API_KEYを設定してください。"
        
        # エンティティタイプに応じたサービスパス決定
        service_paths = {
            "Aed": "/Aed",
            "EvacuationShelter": "/EvacuationShelter", 
            "DisasterMail": "/DisasterMail",
            "WeatherAlert": "/WeatherAlert",
            "WeatherForecast": "/WeatherForecast",
            "FloodRiskAreaMaxScale": "/FloodRiskAreaMaxScale",
            "TsunamiEvacuationBuilding": "/TsunamiEvacuationBuilding",
            "DrinkingWaterTank": "/DrinkingWaterTank",
            "PrecipitationGauge": "/PrecipitationGauge",
            "CameraInformation": "/CameraInformation",
            "StreamGauge": "/StreamGauge",
            "FirstAidStation": "/FirstAidStation",
            "ReliefHospital": "/ReliefHospital"
        }
        
        service_path = service_paths.get(entity_type, "/")
        
        # クエリパラメータの構築
        query_params = {
            "type": entity_type,
            "limit": str(min(max(1, limit), 1000))  # 1-1000の範囲に制限
        }
        
        # 追加パラメータの処理
        if params:
            try:
                if isinstance(params, str):
                    additional_params = json.loads(params)
                else:
                    additional_params = params
                query_params.update(additional_params)
            except json.JSONDecodeError:
                return "❌ エラー: パラメータはJSON形式で指定してください。"
        
        # ヘッダーの設定（curlコマンドと完全一致）
        headers = {
            "Accept": "application/json",
            "apikey": api_key,  # 小文字のapikey
            "Fiware-Service": "smartcity_yaizu",
            "Fiware-ServicePath": service_path,
            "x-request-trace-id": str(uuid.uuid4()),  # UUIDトレースID
            "User-Agent": "smartcity-service"  # WAF対策
            # 重要: Content-Typeヘッダーは含めない（GETリクエストでは不要、curlでも送信していない）
        }
        
        # エンドポイントURL（検証済みベースURL）
        endpoint_url = "https://api.smartcity-yaizu.jp/v2/entities"
        
        # APIリクエスト実行
        async with aiohttp.ClientSession() as session:
            logger.info(f"焼津市API実行: {entity_type} エンティティ取得")
            
            # NGSIv2 GETリクエスト実行
            async with session.get(endpoint_url, headers=headers, params=query_params, timeout=30) as response:
                status = response.status
                response_text = await response.text()
                
                # レート制限情報を取得
                rate_limit = response.headers.get('x-ratelimit-remaining-minute', 'N/A')
                rate_limit_reset = response.headers.get('ratelimit-reset', 'N/A')
            
            # レスポンスの処理
            output = f"# 焼津市API実行結果\n\n"
            output += f"**エンティティタイプ**: `{entity_type}`\n"
            output += f"**エンドポイント**: `{endpoint_url}`\n"
            output += f"**サービスパス**: `{service_path}`\n"
            output += f"**ステータスコード**: {status}\n"
            output += f"**レート制限残り**: {rate_limit}\n\n"
            
            if query_params:
                output += f"**クエリパラメータ**:\n```json\n{json.dumps(query_params, ensure_ascii=False, indent=2)}\n```\n\n"
            
            if status == 200:
                output += "✅ **成功**\n\n"
                try:
                    # JSONレスポンスをパース
                    json_data = json.loads(response_text)
                    data_count = len(json_data) if isinstance(json_data, list) else 1
                    output += f"**取得件数**: {data_count}件\n\n"
                    
                    # データサマリー表示（最初の3件のみ要約）
                    if isinstance(json_data, list) and len(json_data) > 0:
                        output += "**データサマリー**:\n"
                        for i, item in enumerate(json_data[:3]):
                            name = "名称不明"
                            address = "住所不明" 
                            position = ""
                            
                            # 名称取得
                            if 'Name' in item and 'value' in item['Name']:
                                name = item['Name']['value']
                            
                            # 住所取得
                            if 'EquipmentAddress' in item and 'value' in item['EquipmentAddress']:
                                addr = item['EquipmentAddress']['value']
                                if isinstance(addr, dict):
                                    if 'FullAddress' in addr:
                                        if isinstance(addr['FullAddress'], dict) and 'value' in addr['FullAddress']:
                                            address = addr['FullAddress']['value']
                                        elif isinstance(addr['FullAddress'], str):
                                            address = addr['FullAddress']
                                    
                            # 設置位置取得
                            if 'InstallationPosition' in item and 'value' in item['InstallationPosition']:
                                position = f" ({item['InstallationPosition']['value']})"
                            
                            output += f"- **{i+1}. {name}**: {address}{position}\n"
                            output += f"  - ID: `{item.get('id', 'N/A')}`\n"
                        
                        if len(json_data) > 3:
                            output += f"- ... 他{len(json_data) - 3}件\n"
                    
                    output += "\n**完全なレスポンスデータ**:\n```json\n"
                    output += json.dumps(json_data, ensure_ascii=False, indent=2)[:4000]  # 最大4000文字
                    if len(json.dumps(json_data, ensure_ascii=False)) > 4000:
                        output += "\n... (データが大きすぎるため省略)"
                    output += "\n```"
                except json.JSONDecodeError:
                    output += f"**レスポンス**:\n```\n{response_text[:2000]}\n```"
            elif status == 401:
                output += "❌ **認証エラー**: APIキーが無効か、権限がありません。\n"
                output += f"詳細: {response_text}"
            elif status == 403:
                output += "❌ **アクセス拒否**: APIキーの権限またはFiwareサービス設定を確認してください。\n"
                output += f"詳細: {response_text}"
            elif status == 404:
                output += "❌ **Not Found**: エンティティタイプまたはエンドポイントが見つかりません。\n"
                output += f"詳細: {response_text}"
            elif status == 429:
                output += "❌ **レート制限超過**: APIリクエスト数が制限を超えました。しばらく待ってから再試行してください。\n"
                output += f"詳細: {response_text}"
            else:
                output += f"❌ **エラー**: {status}\n"
                output += f"詳細: {response_text[:1000]}"
            
            return output
            
    except asyncio.TimeoutError:
        return "❌ タイムアウトエラー: APIへのリクエストがタイムアウトしました。"
    except aiohttp.ClientError as e:
        return f"❌ 接続エラー: {str(e)}"
    except Exception as e:
        logger.error(f"API実行エラー: {e}")
        return f"❌ 予期しないエラー: {str(e)}"


@mcp.tool()
async def get_sample_endpoints() -> str:
    """
    焼津市スマートシティAPIの主要なエンドポイント例を提供します。
    
    Returns:
        str: エンドポイント例の一覧
    """
    return """# 焼津市スマートシティAPI エンドポイント例

## 防災関連API
- `https://api.smartcity-yaizu.jp/v1/disaster/shelters` - 避難所情報
- `https://api.smartcity-yaizu.jp/v1/disaster/alerts` - 災害警報情報
- `https://api.smartcity-yaizu.jp/v1/disaster/hazardmap` - ハザードマップ情報

## 公共施設API
- `https://api.smartcity-yaizu.jp/v1/facilities/public` - 公共施設一覧
- `https://api.smartcity-yaizu.jp/v1/facilities/parks` - 公園情報
- `https://api.smartcity-yaizu.jp/v1/facilities/libraries` - 図書館情報

## 交通・インフラAPI
- `https://api.smartcity-yaizu.jp/v1/transport/buses` - バス路線情報
- `https://api.smartcity-yaizu.jp/v1/transport/parking` - 駐車場情報
- `https://api.smartcity-yaizu.jp/v1/infrastructure/roads` - 道路状況

## 観光・イベントAPI
- `https://api.smartcity-yaizu.jp/v1/tourism/spots` - 観光スポット
- `https://api.smartcity-yaizu.jp/v1/events/calendar` - イベントカレンダー
- `https://api.smartcity-yaizu.jp/v1/tourism/restaurants` - 飲食店情報

## 環境・センサーAPI
- `https://api.smartcity-yaizu.jp/v1/environment/weather` - 気象情報
- `https://api.smartcity-yaizu.jp/v1/environment/air-quality` - 大気質情報
- `https://api.smartcity-yaizu.jp/v1/sensors/water-level` - 水位センサー情報

## 使用方法
`execute_api_endpoint`ツールを使用してこれらのエンドポイントにアクセスできます。

例:
```
execute_api_endpoint(
    endpoint_url="https://api.smartcity-yaizu.jp/v1/disaster/shelters",
    method="GET",
    params='{"limit": 10}'
)
```

注: 実際のエンドポイントURLはAPIカタログで確認してください。
"""


@mcp.tool()
async def list_saved_apis() -> str:
    """
    保存済みのAPIドキュメント一覧を表示します。
    
    Returns:
        str: ドキュメント一覧
    """
    try:
        files = doc_manager.list_available_docs()
        
        if not files:
            return "保存済みのAPIドキュメントがありません。`scrape_api_docs`を実行してください。"
        
        output = f"# 保存済みAPIドキュメント\n\n"
        output += f"**{len(files)}個** のドキュメントが利用可能です:\n\n"
        
        for filename in files:
            # ファイルの情報を取得
            doc = doc_manager.load_api_docs(filename)
            if doc:
                title = doc.get('title', filename)
                api_count = len(doc.get('apis', []))
                last_updated = doc.get('last_updated', '不明')
                
                output += f"## 📄 {filename}\n"
                output += f"- **タイトル**: {title}\n"
                output += f"- **API数**: {api_count}\n"
                output += f"- **最終更新**: {last_updated}\n\n"
            else:
                output += f"- {filename}.json\n"
        
        return output
        
    except Exception as e:
        logger.error(f"一覧取得エラー: {e}")
        return f"❌ ドキュメント一覧の取得中にエラーが発生しました: {str(e)}"


# ========== MCPリソース ==========

@mcp.resource("yaizu://api-docs")
async def get_all_api_docs() -> str:
    """すべてのAPIドキュメントのサマリーを提供"""
    try:
        catalog = doc_manager.load_api_docs("api_catalog")
        
        if not catalog:
            return "APIカタログが見つかりません。`scrape_api_docs`を実行してデータを取得してください。"
        
        output = f"# 焼津市APIカタログ\n\n"
        output += f"**最終更新**: {catalog.get('last_updated', '不明')}\n\n"
        
        if 'apis' in catalog:
            output += f"## 利用可能なAPI ({len(catalog['apis'])}個)\n\n"
            
            # カテゴリ別に整理
            categories = {}
            for api in catalog['apis']:
                cat = api.get('category', '未分類')
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(api)
            
            for category, apis in sorted(categories.items()):
                output += f"### {category} ({len(apis)}個)\n"
                for api in apis[:5]:  # 各カテゴリ最大5個まで表示
                    output += f"- **{api.get('name', '名称不明')}**: {api.get('description', '')[:50]}...\n"
                if len(apis) > 5:
                    output += f"- ...他{len(apis) - 5}個\n"
                output += "\n"
        
        return output
        
    except Exception as e:
        logger.error(f"リソース取得エラー: {e}")
        return f"エラー: {str(e)}"


@mcp.resource("yaizu://disaster-apis")
async def get_disaster_apis() -> str:
    """防災関連APIの一覧を提供"""
    try:
        disaster_doc = doc_manager.load_api_docs("disaster_apis")
        
        if not disaster_doc:
            return "防災関連APIドキュメントが見つかりません。`scrape_api_docs`を実行してデータを取得してください。"
        
        output = f"# 焼津市防災関連API\n\n"
        output += f"**最終更新**: {disaster_doc.get('last_updated', '不明')}\n\n"
        
        apis = disaster_doc.get('apis', [])
        output += f"## 防災関連API ({len(apis)}個)\n\n"
        
        for i, api in enumerate(apis, 1):
            output += f"### {i}. {api.get('name', '名称不明')}\n"
            output += f"- **説明**: {api.get('description', '説明なし')}\n"
            output += f"- **カテゴリ**: {api.get('category', '未分類')}\n"
            
            if api.get('endpoints'):
                output += f"- **主要エンドポイント**:\n"
                for endpoint in api['endpoints'][:3]:
                    output += f"  - `{endpoint}`\n"
            
            if api.get('data_models'):
                output += f"- **データモデル数**: {len(api['data_models'])}\n"
            
            if api.get('parameters'):
                output += f"- **パラメータ数**: {len(api['parameters'])}\n"
            
            output += "\n"
        
        return output
        
    except Exception as e:
        logger.error(f"防災APIリソース取得エラー: {e}")
        return f"エラー: {str(e)}"


@mcp.resource("yaizu://info")
async def get_yaizu_info() -> str:
    """焼津市とスマートシティの基本情報を提供"""
    return """# 焼津市スマートシティについて

## 概要
焼津市（やいづし）は、静岡県中部に位置する市で、スマートシティ推進に積極的に取り組んでいます。

## 基本データ
- **人口**: 約14万人
- **面積**: 70.31 km²
- **市制施行**: 1951年3月1日

## 特徴
- 日本有数の水産都市
- カツオ・マグロの水揚げ量が多い
- 水産加工業が盛ん
- 温暖な気候

## スマートシティの取り組み
焼津市は、デジタル技術を活用した地域課題の解決と、市民サービスの向上を目指しています。

### APIカタログ
- オープンデータの公開
- 防災情報の提供
- 市民サービスのデジタル化
- 民間連携の促進

### 防災への取り組み
- リアルタイム災害情報の配信
- 避難所情報の提供
- 防災マップのデジタル化
- 市民向け防災アプリの開発

## このMCPサーバーについて
このMCPサーバーは、焼津市のAPIカタログから取得したデータをローカルに保存し、
Claude Desktop/Codeから簡単にアクセスできるようにするためのツールです。

### 主な機能
- APIドキュメントのスクレイピング
- 防災関連APIの特定と抽出
- ローカルデータの検索と閲覧
- 定期的なデータ更新
"""


@mcp.resource("yaizu://status")
async def get_server_status() -> str:
    """サーバーステータスとデータの状態を提供"""
    try:
        files = doc_manager.list_available_docs()
        
        status = {
            "server": "running",
            "version": "2.0.0",
            "data_status": {
                "total_documents": len(files),
                "available_files": files[:10]  # 最大10個まで表示
            }
        }
        
        # 最新のカタログ情報
        catalog = doc_manager.load_api_docs("api_catalog")
        if catalog:
            status["catalog_info"] = {
                "last_updated": catalog.get('last_updated', '不明'),
                "total_apis": len(catalog.get('apis', [])),
                "categories": len(set(api.get('category', '未分類') for api in catalog.get('apis', [])))
            }
        
        # 防災API情報
        disaster_doc = doc_manager.load_api_docs("disaster_apis")
        if disaster_doc:
            status["disaster_apis"] = {
                "count": len(disaster_doc.get('apis', [])),
                "last_updated": disaster_doc.get('last_updated', '不明')
            }
        
        output = f"""# 焼津市MCPサーバーステータス

## サーバー情報
- **ステータス**: {status['server']}
- **バージョン**: {status['version']}

## データステータス
- **保存済みドキュメント数**: {status['data_status']['total_documents']}

### 利用可能なファイル
"""
        for filename in status['data_status']['available_files']:
            output += f"- {filename}.json\n"
        
        if 'catalog_info' in status:
            output += f"""
## APIカタログ情報
- **最終更新**: {status['catalog_info']['last_updated']}
- **総API数**: {status['catalog_info']['total_apis']}
- **カテゴリ数**: {status['catalog_info']['categories']}
"""
        
        if 'disaster_apis' in status:
            output += f"""
## 防災API情報
- **防災関連API数**: {status['disaster_apis']['count']}
- **最終更新**: {status['disaster_apis']['last_updated']}
"""
        
        output += """
## 使い方
1. `scrape_api_docs` - 最新のAPIドキュメントを取得
2. `list_saved_apis` - 保存済みドキュメントの確認
3. `search_api_docs` - キーワードでAPIを検索
4. `get_api_details` - 特定APIの詳細情報を取得
"""
        
        return output
        
    except Exception as e:
        logger.error(f"ステータス取得エラー: {e}")
        return f"エラー: {str(e)}"


@mcp.prompt()
async def analyze_disaster_apis() -> str:
    """防災APIを分析するためのプロンプト"""
    return """あなたは焼津市の防災システム分析の専門家です。

以下の手順で防災関連APIの分析を行ってください：

1. まず `list_saved_apis` ツールで利用可能なドキュメントを確認してください
2. もしドキュメントがない場合は `scrape_api_docs` ツールを実行してください
3. `search_api_docs` ツールで「防災」「災害」「避難」などのキーワードで検索してください
4. 見つかったAPIについて `get_api_details` で詳細情報を取得してください
5. 以下の観点から分析を提供してください：
   - 提供される防災情報の種類
   - データの更新頻度
   - 市民への情報提供方法
   - 改善提案

防災システムの観点から、具体的で実用的な分析と提案を行ってください。
"""


# クリーンアップ処理
async def cleanup():
    """リソースのクリーンアップ"""
    await doc_manager.cleanup()
    logger.info("リソースをクリーンアップしました")


# サーバー起動
if __name__ == "__main__":
    try:
        mcp.run()
    finally:
        asyncio.run(cleanup())