#!/usr/bin/env python3
"""
拡張APIスペック生成ツール

OpenAPI YAMLとPDFを詳細解析して、
より精密なAPI仕様とデータモデルスキーマを生成
"""

import asyncio
import json
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

import aiohttp


class DateTimeEncoder(json.JSONEncoder):
    """datetime オブジェクトをJSON serializable にするエンコーダ"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class EnhancedAPISpecsGenerator:
    """拡張API仕様生成クラス"""
    
    def __init__(self):
        self.openapi_dir = Path("data/openapi")
        self.documentation_dir = Path("data/documentation")
        self.api_specs_dir = Path("data/api_specs")
        
        # ベースURL設定
        self.base_urls = {
            "bousai-orion-openapi.yaml": "https://api.smartcity-yaizu.jp",
            "bousai-public-facility-orion-openapi.yaml": "https://api.smartcity-yaizu.jp", 
            "tiikikasseika-orion-openapi.yaml": "https://api.smartcity-yaizu.jp"
        }
    
    def parse_openapi_spec(self, yaml_file: Path) -> Dict[str, Any]:
        """OpenAPI YAML仕様を詳細解析"""
        print(f"📄 OpenAPI解析: {yaml_file.name}")
        
        with open(yaml_file, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
        
        # 基本情報
        info = spec.get('info', {})
        servers = spec.get('servers', [])
        paths = spec.get('paths', {})
        
        # エンドポイント情報抽出
        endpoints = {}
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() in ['get', 'post', 'put', 'delete']:
                    endpoint_id = f"{method.upper()} {path}"
                    endpoints[endpoint_id] = {
                        "method": method.upper(),
                        "path": path,
                        "summary": details.get('summary', ''),
                        "description": details.get('description', ''),
                        "operationId": details.get('operationId', ''),
                        "parameters": self._extract_parameters(details.get('parameters', [])),
                        "responses": details.get('responses', {}),
                        "tags": details.get('tags', [])
                    }
        
        return {
            "openapi_version": spec.get('openapi', '3.0.3'),
            "info": info,
            "servers": servers,
            "base_url": servers[0]['url'] if servers else self.base_urls.get(yaml_file.name, ''),
            "endpoints": endpoints,
            "total_endpoints": len(endpoints)
        }
    
    def _extract_parameters(self, parameters: List[Dict]) -> Dict[str, Any]:
        """パラメータ詳細を抽出"""
        param_info = {
            "query": {},
            "header": {},
            "path": {},
            "required_params": [],
            "optional_params": []
        }
        
        for param in parameters:
            name = param.get('name', '')
            location = param.get('in', 'query')
            required = param.get('required', False)
            schema = param.get('schema', {})
            
            param_detail = {
                "name": name,
                "type": schema.get('type', 'string'),
                "description": param.get('description', ''),
                "required": required,
                "example": schema.get('example'),
                "enum": schema.get('enum'),
                "format": schema.get('format')
            }
            
            param_info[location][name] = param_detail
            
            if required:
                param_info["required_params"].append(name)
            else:
                param_info["optional_params"].append(name)
        
        return param_info
    
    def extract_pdf_data_models(self, pdf_links: List[tuple]) -> Dict[str, Any]:
        """PDFリンクからデータモデル情報を抽出"""
        models = {}
        
        for name, url in pdf_links:
            filename = Path(urlparse(url).path).name
            entity_type = Path(filename).stem
            
            # より詳細なデータモデル生成
            model = self._generate_enhanced_data_model(name, entity_type, filename, url)
            models[entity_type] = model
            
        return models
    
    def _generate_enhanced_data_model(self, name: str, entity_type: str, 
                                    pdf_filename: str, pdf_url: str) -> Dict[str, Any]:
        """拡張データモデルを生成"""
        
        # カテゴリ分類
        categories = self._classify_entity_category(entity_type, name)
        
        # 基本属性テンプレート
        base_attributes = {
            "id": {
                "type": "string",
                "description": "エンティティの一意識別子",
                "required": True,
                "format": "uri",
                "example": f"urn:ngsi-ld:{entity_type}:001"
            },
            "type": {
                "type": "string", 
                "description": "エンティティタイプ",
                "value": entity_type,
                "required": True,
                "constant": True
            },
            "dateCreated": {
                "type": "DateTime",
                "description": "作成日時",
                "required": False,
                "format": "date-time"
            },
            "dateModified": {
                "type": "DateTime", 
                "description": "更新日時",
                "required": False,
                "format": "date-time"
            }
        }
        
        # カテゴリ別の専用属性を追加
        specialized_attributes = self._get_specialized_attributes(entity_type, categories)
        base_attributes.update(specialized_attributes)
        
        return {
            "dataModelName": name,
            "entityType": entity_type,
            "categories": categories,
            "fiwareService": "smartcity_yaizu",
            "fiwareServicePath": f"/{entity_type}",
            "description": f"{name}のデータを管理するFIWARE NGSIv2エンティティ",
            "version": "1.0.0",
            "lastUpdated": datetime.now().isoformat(),
            "pdfSource": {
                "filename": pdf_filename,
                "url": pdf_url,
                "local_path": f"data/documentation/{self._get_api_category(entity_type)}/{pdf_filename}"
            },
            "attributes": base_attributes,
            "queryExamples": self._generate_query_examples(entity_type),
            "usagePatterns": self._generate_usage_patterns(entity_type, categories),
            "relatedEntities": self._find_related_entities(entity_type, categories)
        }
    
    def _classify_entity_category(self, entity_type: str, name: str) -> List[str]:
        """エンティティのカテゴリ分類"""
        categories = []
        
        # 防災・災害関連
        if any(keyword in name.lower() + entity_type.lower() for keyword in 
               ['disaster', 'emergency', '防災', '災害', '避難', '警戒', '危険', 'evacuation', 'alert']):
            categories.append('disaster_management')
        
        # インフラ・施設
        if any(keyword in name.lower() + entity_type.lower() for keyword in
               ['facility', 'infrastructure', '施設', '設備', 'building', 'warehouse']):
            categories.append('infrastructure')
            
        # 環境・気象
        if any(keyword in name.lower() + entity_type.lower() for keyword in
               ['weather', 'environment', '気象', '環境', '雨量', '水位', 'gauge', 'sensor']):
            categories.append('environmental')
            
        # 交通・道路
        if any(keyword in name.lower() + entity_type.lower() for keyword in
               ['traffic', 'road', '道路', '交通', 'restricted']):
            categories.append('transportation')
            
        # 観光・イベント
        if any(keyword in name.lower() + entity_type.lower() for keyword in
               ['event', 'tourism', 'sightseeing', 'イベント', '観光', '産業']):
            categories.append('tourism_industry')
            
        # 医療・救護
        if any(keyword in name.lower() + entity_type.lower() for keyword in
               ['medical', 'hospital', 'aid', '救護', '医療', 'aed']):
            categories.append('medical_emergency')
        
        return categories if categories else ['general']
    
    def _get_specialized_attributes(self, entity_type: str, categories: List[str]) -> Dict[str, Any]:
        """カテゴリ別の専用属性を生成"""
        attributes = {
            "location": {
                "type": "geo:json",
                "description": "地理的位置情報",
                "required": False,
                "properties": {
                    "type": "Point",
                    "coordinates": {"type": "array", "items": "number"}
                }
            },
            "address": {
                "type": "PostalAddress", 
                "description": "住所情報",
                "required": False,
                "properties": {
                    "addressCountry": {"type": "string", "default": "JP"},
                    "addressRegion": {"type": "string", "default": "静岡県"},
                    "addressLocality": {"type": "string", "default": "焼津市"},
                    "streetAddress": {"type": "string"}
                }
            }
        }
        
        # 災害管理関連
        if 'disaster_management' in categories:
            attributes.update({
                "alertLevel": {
                    "type": "string",
                    "description": "警戒レベル",
                    "enum": ["low", "medium", "high", "critical"],
                    "required": False
                },
                "capacity": {
                    "type": "number", 
                    "description": "収容人数・容量",
                    "minimum": 0,
                    "required": False
                },
                "operationalStatus": {
                    "type": "string",
                    "description": "稼働状況",
                    "enum": ["operational", "maintenance", "closed", "emergency"],
                    "required": False
                }
            })
        
        # 環境・センサー関連
        if 'environmental' in categories:
            attributes.update({
                "measurementValue": {
                    "type": "number",
                    "description": "測定値", 
                    "required": False
                },
                "measurementUnit": {
                    "type": "string",
                    "description": "測定単位",
                    "examples": ["mm", "m", "°C", "hPa"],
                    "required": False
                },
                "observationDateTime": {
                    "type": "DateTime",
                    "description": "観測日時",
                    "format": "date-time", 
                    "required": False
                }
            })
        
        # 施設・インフラ関連
        if 'infrastructure' in categories:
            attributes.update({
                "facilityType": {
                    "type": "string",
                    "description": "施設タイプ",
                    "required": False
                },
                "managedBy": {
                    "type": "string",
                    "description": "管理者",
                    "default": "焼津市",
                    "required": False
                },
                "contactPoint": {
                    "type": "ContactPoint",
                    "description": "連絡先情報",
                    "required": False
                }
            })
        
        return attributes
    
    def _generate_query_examples(self, entity_type: str) -> List[Dict[str, Any]]:
        """クエリ例を生成"""
        examples = [
            {
                "name": "全エンティティ取得",
                "description": f"全ての{entity_type}エンティティを取得",
                "method": "GET",
                "endpoint": "/v2/entities",
                "parameters": {
                    "type": entity_type,
                    "limit": 100
                },
                "headers": {
                    "Fiware-Service": "smartcity_yaizu",
                    "Fiware-ServicePath": f"/{entity_type}"
                }
            },
            {
                "name": "ID指定取得",
                "description": "特定のエンティティをID指定で取得",
                "method": "GET", 
                "endpoint": f"/v2/entities/{{entity_id}}",
                "parameters": {},
                "headers": {
                    "Fiware-Service": "smartcity_yaizu",
                    "Fiware-ServicePath": f"/{entity_type}"
                }
            },
            {
                "name": "地理的範囲検索",
                "description": "指定範囲内のエンティティを検索",
                "method": "GET",
                "endpoint": "/v2/entities",
                "parameters": {
                    "type": entity_type,
                    "georel": "near;maxDistance:1000",
                    "geometry": "point",
                    "coords": "34.866,138.321"  # 焼津市の座標例
                },
                "headers": {
                    "Fiware-Service": "smartcity_yaizu", 
                    "Fiware-ServicePath": f"/{entity_type}"
                }
            }
        ]
        
        return examples
    
    def _generate_usage_patterns(self, entity_type: str, categories: List[str]) -> List[Dict[str, str]]:
        """利用パターンを生成"""
        patterns = []
        
        if 'disaster_management' in categories:
            patterns.extend([
                {
                    "name": "災害時避難所検索",
                    "description": "現在地から最寄りの避難所を検索",
                    "use_case": "災害発生時の避難誘導"
                },
                {
                    "name": "警戒レベル監視",
                    "description": "警戒レベルの変化を監視",
                    "use_case": "防災アラートシステム"
                }
            ])
        
        if 'environmental' in categories:
            patterns.extend([
                {
                    "name": "リアルタイム監視",
                    "description": "センサーデータのリアルタイム取得",
                    "use_case": "環境モニタリングダッシュボード"
                },
                {
                    "name": "履歴データ分析",
                    "description": "過去のデータトレンド分析",
                    "use_case": "予測・分析システム"
                }
            ])
        
        return patterns
    
    def _find_related_entities(self, entity_type: str, categories: List[str]) -> List[str]:
        """関連エンティティを特定"""
        related = []
        
        if 'disaster_management' in categories:
            related.extend(['EvacuationShelter', 'EvacuationSpace', 'WeatherAlert'])
        
        if 'environmental' in categories:
            related.extend(['WeatherForecast', 'WeatherAlert'])
            
        if 'medical_emergency' in categories:
            related.extend(['FirstAidStation', 'ReliefHospital'])
        
        return [r for r in related if r != entity_type]
    
    def _get_api_category(self, entity_type: str) -> str:
        """APIカテゴリを判定"""
        if entity_type in ['Event', 'EventDetail', 'SightseeingMapStore', 'FactoryDirectSalesPlace']:
            return 'tourism-api'
        elif entity_type in ['PublicFacility']:
            return 'public-facility-api' 
        else:
            return 'bousai-api'
    
    async def generate_enhanced_specs(self) -> Dict[str, Any]:
        """拡張API仕様を生成"""
        print("="*60)
        print("拡張API仕様生成ツール")
        print("="*60)
        
        results = {}
        all_models = {}
        all_endpoints = {}
        
        for yaml_file in self.openapi_dir.glob("*.yaml"):
            print(f"\n🔄 処理中: {yaml_file.name}")
            
            # OpenAPI仕様解析
            api_spec = self.parse_openapi_spec(yaml_file)
            
            # PDFリンク抽出
            pdf_pattern = r'\* \[(.*?)\]\((https://docs\.smartcity-yaizu\.jp/.*?\.pdf)\)'
            with open(yaml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            pdf_links = re.findall(pdf_pattern, content)
            
            # データモデル生成
            models = self.extract_pdf_data_models(pdf_links)
            
            results[yaml_file.name] = {
                "api_specification": api_spec,
                "data_models": models,
                "pdf_count": len(pdf_links)
            }
            
            all_models.update(models)
            all_endpoints.update(api_spec["endpoints"])
        
        # 統合インデックス生成
        unified_index = {
            "title": "焼津市スマートシティ 拡張API仕様",
            "description": "OpenAPI仕様とデータモデルの詳細解析結果",
            "version": "2.0.0",
            "generated_at": datetime.now().isoformat(),
            "statistics": {
                "total_apis": len(results),
                "total_models": len(all_models),
                "total_endpoints": len(all_endpoints),
                "categories": list(set([cat for model in all_models.values() 
                                      for cat in model.get('categories', [])]))
            },
            "api_specifications": {name: spec["api_specification"] 
                                 for name, spec in results.items()},
            "data_models": all_models,
            "search_index": self._build_search_index(all_models, all_endpoints)
        }
        
        return unified_index
    
    def _build_search_index(self, models: Dict, endpoints: Dict) -> Dict[str, Any]:
        """検索インデックスを構築"""
        return {
            "by_category": self._index_by_category(models),
            "by_keyword": self._index_by_keyword(models),
            "by_location": self._index_by_location(models),
            "endpoints_by_method": self._index_endpoints_by_method(endpoints)
        }
    
    def _index_by_category(self, models: Dict) -> Dict[str, List[str]]:
        """カテゴリ別インデックス"""
        index = {}
        for entity_type, model in models.items():
            for category in model.get('categories', []):
                if category not in index:
                    index[category] = []
                index[category].append(entity_type)
        return index
    
    def _index_by_keyword(self, models: Dict) -> Dict[str, List[str]]:
        """キーワード別インデックス"""
        index = {}
        for entity_type, model in models.items():
            # 名前と説明からキーワードを抽出
            text = f"{model.get('dataModelName', '')} {model.get('description', '')}"
            keywords = re.findall(r'\w+', text.lower())
            
            for keyword in keywords:
                if len(keyword) > 2:  # 3文字以上
                    if keyword not in index:
                        index[keyword] = []
                    if entity_type not in index[keyword]:
                        index[keyword].append(entity_type)
        return index
    
    def _index_by_location(self, models: Dict) -> List[str]:
        """位置情報を持つエンティティのリスト"""
        return [entity_type for entity_type, model in models.items()
                if 'location' in model.get('attributes', {})]
    
    def _index_endpoints_by_method(self, endpoints: Dict) -> Dict[str, List[str]]:
        """HTTPメソッド別エンドポイントインデックス"""
        index = {}
        for endpoint_id, endpoint in endpoints.items():
            method = endpoint['method']
            if method not in index:
                index[method] = []
            index[method].append(endpoint_id)
        return index


async def main():
    """メイン実行関数"""
    generator = EnhancedAPISpecsGenerator()
    
    # 拡張仕様生成
    enhanced_specs = await generator.generate_enhanced_specs()
    
    # ファイル保存
    output_file = Path("data/api_specs/enhanced_api_specifications.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(enhanced_specs, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
    
    print(f"\n📊 生成完了:")
    print(f"  📄 API仕様: {enhanced_specs['statistics']['total_apis']} 種類")
    print(f"  🏗️  データモデル: {enhanced_specs['statistics']['total_models']} 個")
    print(f"  🔗 エンドポイント: {enhanced_specs['statistics']['total_endpoints']} 個") 
    print(f"  📂 カテゴリ: {len(enhanced_specs['statistics']['categories'])} 種類")
    print(f"  💾 保存先: {output_file}")
    
    return enhanced_specs


if __name__ == "__main__":
    asyncio.run(main())