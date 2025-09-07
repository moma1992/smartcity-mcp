#!/usr/bin/env python3
"""
PDF解析からJSON生成ツール

PDFファイルを詳細解析して、リッチなJSONデータモデルを生成
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# PDF解析ライブラリ
try:
    import PyPDF2
    import fitz  # PyMuPDF
    PDF_LIBRARIES_AVAILABLE = True
except ImportError:
    print("⚠️ PDF解析ライブラリが見つかりません。基本的なテンプレートで生成します。")
    PDF_LIBRARIES_AVAILABLE = False


class PDFToJSONGenerator:
    """PDF解析からJSON生成クラス"""
    
    def __init__(self):
        self.documentation_dir = Path("data/documentation")
        self.api_specs_dir = Path("data/api_specs")
        self.api_specs_dir.mkdir(parents=True, exist_ok=True)
        
        # OpenAPIカテゴリマッピング
        self.category_mapping = {
            "bousai-api": "防災情報API",
            "public-facility-api": "公共施設API", 
            "tourism-api": "観光・産業API"
        }
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """PDFからテキストを抽出"""
        if not PDF_LIBRARIES_AVAILABLE:
            return ""
            
        text = ""
        try:
            # PyMuPDFを使用してテキストを抽出
            doc = fitz.open(pdf_path)
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception as e:
            print(f"  ⚠️ PDF読み込みエラー: {pdf_path.name} - {e}")
            try:
                # フォールバック：PyPDF2を試す
                with open(pdf_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text()
            except Exception as e2:
                print(f"  ❌ PDF読み込み失敗: {pdf_path.name} - {e2}")
        
        return text
    
    def analyze_pdf_content(self, pdf_path: Path, text: str) -> Dict[str, Any]:
        """PDFコンテンツを解析してメタデータを抽出"""
        entity_name = pdf_path.stem
        
        # テキストから情報を抽出
        analysis = {
            "entity_type": entity_name,
            "extracted_fields": self._extract_field_information(text),
            "data_types": self._identify_data_types(text),
            "relationships": self._find_relationships(text),
            "constraints": self._extract_constraints(text),
            "examples": self._extract_examples(text),
            "description": self._generate_description(entity_name, text)
        }
        
        return analysis
    
    def _extract_field_information(self, text: str) -> List[Dict[str, Any]]:
        """テキストからフィールド情報を抽出"""
        fields = []
        
        # 日本語のフィールド名パターンを検索
        field_patterns = [
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([^\n]+)',  # field: description
            r'・\s*([^：\n]+)：([^\n]+)',  # ・フィールド名：説明
            r'項目名\s*[:：]\s*([^\n]+)',  # 項目名: 値
            r'属性\s*[:：]\s*([^\n]+)',   # 属性: 値
        ]
        
        for pattern in field_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                field_name, description = match
                field_name = field_name.strip()
                description = description.strip()
                
                if len(field_name) > 1 and len(description) > 1:
                    # データ型を推定
                    data_type = self._guess_data_type(field_name, description)
                    
                    fields.append({
                        "name": self._normalize_field_name(field_name),
                        "description": description[:200],  # 説明を200文字に制限
                        "type": data_type,
                        "required": self._is_required_field(field_name, description)
                    })
        
        return fields[:10]  # 最大10フィールドに制限
    
    def _normalize_field_name(self, name: str) -> str:
        """フィールド名を正規化"""
        # 日本語をローマ字に変換（簡易版）
        replacements = {
            '名前': 'name',
            '名称': 'name', 
            '住所': 'address',
            '位置': 'location',
            '座標': 'coordinates',
            'ID': 'id',
            '識別子': 'id',
            '種別': 'type',
            '分類': 'category',
            '状態': 'status',
            '状況': 'status',
            '日時': 'dateTime',
            '時刻': 'time',
            '値': 'value',
            '容量': 'capacity',
            '人数': 'capacity'
        }
        
        for jp, en in replacements.items():
            if jp in name:
                return en
                
        # 英数字のみに変換
        normalized = re.sub(r'[^a-zA-Z0-9]', '_', name)
        normalized = re.sub(r'_+', '_', normalized).strip('_')
        
        return normalized.lower() if normalized else 'unknown_field'
    
    def _guess_data_type(self, field_name: str, description: str) -> str:
        """フィールド名と説明からデータ型を推定"""
        text = (field_name + " " + description).lower()
        
        if any(keyword in text for keyword in ['座標', 'coordinate', '緯度', '経度', 'location']):
            return 'geo:json'
        elif any(keyword in text for keyword in ['日時', 'datetime', '時刻', 'time', '日付', 'date']):
            return 'DateTime'
        elif any(keyword in text for keyword in ['数', 'number', '値', 'value', '容量', 'capacity', '人数']):
            return 'Number'
        elif any(keyword in text for keyword in ['true', 'false', 'boolean', '有無', 'フラグ']):
            return 'Boolean'
        elif 'id' in text or '識別' in text:
            return 'Text'
        else:
            return 'Text'
    
    def _is_required_field(self, field_name: str, description: str) -> bool:
        """必須フィールドかどうかを判定"""
        text = (field_name + " " + description).lower()
        
        # 必須と思われるキーワード
        required_keywords = ['必須', 'required', 'id', '識別子', 'type', '種別']
        optional_keywords = ['任意', 'optional', '可能', 'オプション']
        
        if any(keyword in text for keyword in required_keywords):
            return True
        elif any(keyword in text for keyword in optional_keywords):
            return False
        else:
            # IDやtypeっぽいフィールドは必須とする
            return field_name.lower() in ['id', 'type', 'name', '識別子', '種別', '名称']
    
    def _identify_data_types(self, text: str) -> List[str]:
        """テキストから使用されているデータ型を特定"""
        types = set()
        
        if re.search(r'座標|緯度|経度|location|coordinate', text, re.IGNORECASE):
            types.add('geo:json')
        if re.search(r'日時|datetime|timestamp|時刻', text, re.IGNORECASE):
            types.add('DateTime')  
        if re.search(r'数値|number|値|容量|人数', text, re.IGNORECASE):
            types.add('Number')
        if re.search(r'住所|address', text, re.IGNORECASE):
            types.add('PostalAddress')
        if re.search(r'URL|リンク|link', text, re.IGNORECASE):
            types.add('URL')
            
        return list(types)
    
    def _find_relationships(self, text: str) -> List[str]:
        """他のエンティティとの関係を特定"""
        relationships = []
        
        # 関連する可能性のあるエンティティ名を検索
        entity_patterns = [
            r'避難所',
            r'避難場所', 
            r'防災施設',
            r'医療機関',
            r'AED',
            r'センサー',
            r'カメラ',
            r'観光地',
            r'イベント'
        ]
        
        for pattern in entity_patterns:
            if re.search(pattern, text):
                relationships.append(pattern)
                
        return relationships[:5]  # 最大5つに制限
    
    def _extract_constraints(self, text: str) -> Dict[str, Any]:
        """制約条件を抽出"""
        constraints = {}
        
        # 数値制約を検索
        number_patterns = [
            r'最大(\d+)',
            r'最小(\d+)',
            r'上限(\d+)',
            r'下限(\d+)'
        ]
        
        for pattern in number_patterns:
            matches = re.findall(pattern, text)
            if matches:
                constraint_type = pattern.replace(r'(\d+)', '').replace('\\', '')
                constraints[constraint_type] = int(matches[0])
        
        return constraints
    
    def _extract_examples(self, text: str) -> List[str]:
        """例やサンプル値を抽出"""
        examples = []
        
        # 例を示すパターンを検索
        example_patterns = [
            r'例\s*[:：]\s*([^\n]+)',
            r'サンプル\s*[:：]\s*([^\n]+)',
            r'具体例\s*[:：]\s*([^\n]+)'
        ]
        
        for pattern in example_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                examples.append(match.strip()[:100])  # 100文字に制限
                
        return examples[:3]  # 最大3つの例
    
    def _generate_description(self, entity_name: str, text: str) -> str:
        """エンティティの説明を生成"""
        # テキストの最初の数行から説明を抽出
        lines = text.split('\n')[:10]  # 最初の10行
        description_text = ' '.join(line.strip() for line in lines if line.strip())
        
        if len(description_text) > 300:
            description_text = description_text[:300] + "..."
            
        return description_text if description_text else f"{entity_name}に関する情報を管理するエンティティ"
    
    def generate_enhanced_json_schema(self, pdf_path: Path, category: str) -> Dict[str, Any]:
        """PDFから拡張JSONスキーマを生成"""
        entity_type = pdf_path.stem
        entity_name_jp = self._get_japanese_name(entity_type)
        
        # PDFテキストを抽出・解析
        pdf_text = self.extract_text_from_pdf(pdf_path)
        analysis = self.analyze_pdf_content(pdf_path, pdf_text)
        
        # 基本スキーマ
        schema = {
            "schema_version": "2.0.0",
            "generated_at": datetime.now().isoformat(),
            "source": {
                "pdf_file": pdf_path.name,
                "pdf_path": str(pdf_path),
                "api_category": self.category_mapping.get(category, category),
                "text_extraction_success": bool(pdf_text)
            },
            "entity": {
                "type": entity_type,
                "name_ja": entity_name_jp,
                "description": analysis["description"],
                "category": self._classify_entity_category(entity_type),
                "fiware_service": "smartcity_yaizu",
                "fiware_service_path": f"/{entity_type}"
            },
            "attributes": self._build_enhanced_attributes(analysis),
            "api_specification": {
                "base_url": "https://api.smartcity-yaizu.jp",
                "endpoints": self._generate_api_endpoints(entity_type),
                "required_headers": {
                    "Fiware-Service": "smartcity_yaizu",
                    "Fiware-ServicePath": f"/{entity_type}",
                    "Content-Type": "application/json"
                }
            },
            "usage_examples": self._generate_usage_examples(entity_type),
            "relationships": {
                "related_entities": analysis["relationships"],
                "potential_links": self._find_potential_entity_links(entity_type)
            },
            "metadata": {
                "data_quality": self._assess_data_quality(analysis),
                "completeness": len(analysis["extracted_fields"]) > 0,
                "last_updated": datetime.now().isoformat()
            }
        }
        
        return schema
    
    def _get_japanese_name(self, entity_type: str) -> str:
        """エンティティタイプから日本語名を推定"""
        name_mappings = {
            "Aed": "AED設置場所",
            "Event": "イベント一覧", 
            "EventDetail": "イベント詳細",
            "PublicFacility": "公共施設",
            "SightseeingMapStore": "観光施設等一覧",
            "FactoryDirectSalesPlace": "工場併設直売所",
            "WeatherAlert": "警報・注意報",
            "WeatherForecast": "天候",
            "EvacuationShelter": "避難所開設状況",
            "EvacuationSpace": "指定緊急避難場所",
            "PrecipitationGauge": "雨量計",
            "StreamGauge": "河川水位計",
            "CameraInformation": "河川・海岸カメラ"
        }
        
        return name_mappings.get(entity_type, entity_type)
    
    def _classify_entity_category(self, entity_type: str) -> List[str]:
        """エンティティのカテゴリを分類"""
        categories = []
        
        disaster_keywords = ['Evacuation', 'Disaster', 'Weather', 'Alert', 'Flood', 'Tsunami']
        infrastructure_keywords = ['Facility', 'Tank', 'Warehouse', 'Station', 'Building']
        environmental_keywords = ['Gauge', 'Sensor', 'Camera', 'Information']
        tourism_keywords = ['Event', 'Sightseeing', 'Tourism', 'Factory']
        medical_keywords = ['Aed', 'Hospital', 'Aid', 'Relief']
        
        entity_lower = entity_type.lower()
        
        if any(keyword.lower() in entity_lower for keyword in disaster_keywords):
            categories.append("disaster_management")
        if any(keyword.lower() in entity_lower for keyword in infrastructure_keywords):
            categories.append("infrastructure") 
        if any(keyword.lower() in entity_lower for keyword in environmental_keywords):
            categories.append("environmental")
        if any(keyword.lower() in entity_lower for keyword in tourism_keywords):
            categories.append("tourism_industry")
        if any(keyword.lower() in entity_lower for keyword in medical_keywords):
            categories.append("medical_emergency")
            
        return categories if categories else ["general"]
    
    def _build_enhanced_attributes(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """拡張属性を構築"""
        attributes = {
            # 標準FIWARE属性
            "id": {
                "type": "Text",
                "description": "エンティティの一意識別子",
                "required": True,
                "format": "uri",
                "example": f"urn:ngsi-ld:{analysis['entity_type']}:001"
            },
            "type": {
                "type": "Text",
                "description": "エンティティタイプ",
                "required": True,
                "constant": analysis['entity_type']
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
        
        # 位置情報（ほとんどのエンティティに存在）
        attributes["location"] = {
            "type": "geo:json",
            "description": "地理的位置情報",
            "required": False,
            "properties": {
                "type": {"type": "Text", "enum": ["Point"]},
                "coordinates": {"type": "Array", "items": "Number", "minItems": 2, "maxItems": 2}
            }
        }
        
        # 住所情報
        attributes["address"] = {
            "type": "PostalAddress",
            "description": "住所情報", 
            "required": False,
            "properties": {
                "addressCountry": {"type": "Text", "default": "JP"},
                "addressRegion": {"type": "Text", "default": "静岡県"},
                "addressLocality": {"type": "Text", "default": "焼津市"},
                "streetAddress": {"type": "Text"}
            }
        }
        
        # PDFから抽出したフィールドを追加
        for field in analysis.get("extracted_fields", []):
            attributes[field["name"]] = {
                "type": field["type"],
                "description": field["description"],
                "required": field["required"]
            }
            
        return attributes
    
    def _generate_api_endpoints(self, entity_type: str) -> List[Dict[str, Any]]:
        """APIエンドポイント情報を生成"""
        endpoints = [
            {
                "name": "全エンティティ取得",
                "method": "GET",
                "path": "/v2/entities",
                "description": f"全ての{entity_type}エンティティを取得",
                "parameters": {
                    "type": entity_type,
                    "limit": {"type": "integer", "default": 100},
                    "offset": {"type": "integer", "default": 0}
                }
            },
            {
                "name": "ID指定取得",
                "method": "GET", 
                "path": "/v2/entities/{entityId}",
                "description": f"特定の{entity_type}エンティティを取得",
                "path_parameters": {
                    "entityId": {"type": "string", "description": "エンティティID"}
                }
            },
            {
                "name": "地理的検索",
                "method": "GET",
                "path": "/v2/entities",
                "description": f"地理的範囲内の{entity_type}エンティティを検索",
                "parameters": {
                    "type": entity_type,
                    "georel": {"type": "string", "example": "near;maxDistance:1000"},
                    "geometry": {"type": "string", "example": "point"},
                    "coords": {"type": "string", "example": "34.866,138.321"}
                }
            }
        ]
        
        return endpoints
    
    def _generate_usage_examples(self, entity_type: str) -> List[Dict[str, Any]]:
        """使用例を生成"""
        examples = [
            {
                "name": "基本検索",
                "description": f"{entity_type}の一覧を取得",
                "curl_example": f"""curl -X GET "https://api.smartcity-yaizu.jp/v2/entities?type={entity_type}&limit=10" \\
  -H "Fiware-Service: smartcity_yaizu" \\
  -H "Fiware-ServicePath: /{entity_type}" """
            },
            {
                "name": "近隣検索",
                "description": "現在地から1km以内の施設を検索",
                "curl_example": f"""curl -X GET "https://api.smartcity-yaizu.jp/v2/entities?type={entity_type}&georel=near;maxDistance:1000&geometry=point&coords=34.866,138.321" \\
  -H "Fiware-Service: smartcity_yaizu" \\
  -H "Fiware-ServicePath: /{entity_type}" """
            }
        ]
        
        return examples
    
    def _find_potential_entity_links(self, entity_type: str) -> List[str]:
        """潜在的な関連エンティティを特定"""
        relationships = {
            "Aed": ["FirstAidStation", "ReliefHospital", "EvacuationShelter"],
            "EvacuationShelter": ["EvacuationSpace", "Aed", "FirstAidStation"], 
            "WeatherAlert": ["WeatherForecast", "PrecipitationGauge", "StreamGauge"],
            "Event": ["EventDetail", "SightseeingMapStore"],
            "PublicFacility": ["Aed"]
        }
        
        return relationships.get(entity_type, [])
    
    def _assess_data_quality(self, analysis: Dict[str, Any]) -> str:
        """データ品質を評価"""
        score = 0
        
        if len(analysis.get("extracted_fields", [])) > 0:
            score += 30
        if len(analysis.get("data_types", [])) > 0:
            score += 20
        if len(analysis.get("relationships", [])) > 0:
            score += 20
        if len(analysis.get("examples", [])) > 0:
            score += 15
        if len(analysis.get("constraints", {})) > 0:
            score += 15
            
        if score >= 80:
            return "high"
        elif score >= 50:
            return "medium"
        else:
            return "low"
    
    async def process_all_pdfs(self) -> Dict[str, Any]:
        """全PDFファイルを処理してJSONを生成"""
        print("="*60)
        print("PDF→JSON 完全再生成ツール")
        print("="*60)
        
        results = {
            "generated_at": datetime.now().isoformat(),
            "total_generated": 0,
            "by_category": {},
            "generated_files": []
        }
        
        # カテゴリ別にPDFを処理
        for category_dir in self.documentation_dir.iterdir():
            if category_dir.is_dir() and category_dir.name in self.category_mapping:
                category = category_dir.name
                print(f"\n📂 処理中: {category} ({self.category_mapping[category]})")
                
                pdf_files = list(category_dir.glob("*.pdf"))
                print(f"  📄 PDF数: {len(pdf_files)} ファイル")
                
                category_results = []
                
                for pdf_file in pdf_files:
                    print(f"  🔄 生成中: {pdf_file.name}")
                    
                    # JSONスキーマ生成
                    json_schema = self.generate_enhanced_json_schema(pdf_file, category)
                    
                    # JSONファイル保存
                    json_filename = f"{pdf_file.stem}.json"
                    json_path = self.api_specs_dir / json_filename
                    
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(json_schema, f, ensure_ascii=False, indent=2)
                    
                    category_results.append({
                        "pdf_file": pdf_file.name,
                        "json_file": json_filename,
                        "entity_type": pdf_file.stem,
                        "file_size": json_path.stat().st_size
                    })
                    
                    print(f"    ✅ 生成完了: {json_filename} ({json_path.stat().st_size:,} bytes)")
                
                results["by_category"][category] = {
                    "category_name": self.category_mapping[category],
                    "pdf_count": len(pdf_files),
                    "generated_count": len(category_results),
                    "files": category_results
                }
                
                results["total_generated"] += len(category_results)
                results["generated_files"].extend(category_results)
        
        # 統合インデックスファイル生成
        index_file = self.api_specs_dir / "index.json" 
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📊 生成完了サマリー:")
        print(f"  📄 総生成数: {results['total_generated']} ファイル")
        for category, info in results["by_category"].items():
            print(f"  📂 {info['category_name']}: {info['generated_count']} ファイル")
        print(f"  📋 インデックス: {index_file}")
        print(f"  💾 保存先: {self.api_specs_dir}")
        
        return results


async def main():
    """メイン実行関数"""
    generator = PDFToJSONGenerator()
    results = await generator.process_all_pdfs()
    
    print(f"\n🎉 PDF→JSON変換が完了しました！")
    print(f"📊 {results['total_generated']}個のJSONファイルが生成されました。")


if __name__ == "__main__":
    asyncio.run(main())