#!/usr/bin/env python3
"""
OpenAPI YAMLファイルからPDFリンクを抽出し、
PDFをダウンロードしてJSONスキーマに変換するプロセッサー
"""

import asyncio
import json
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
from urllib.parse import urlparse

import aiohttp


class OpenAPIPDFProcessor:
    """OpenAPI YAMLからPDFを処理してJSONスキーマを生成"""
    
    def __init__(self):
        self.openapi_dir = Path("data/openapi")
        self.documentation_dir = Path("data/documentation") 
        self.api_specs_dir = Path("data/api_specs")
        
        # API種類別ディレクトリマッピング
        self.api_dirs = {
            "bousai-orion-openapi.yaml": self.documentation_dir / "bousai-api",
            "bousai-public-facility-orion-openapi.yaml": self.documentation_dir / "public-facility-api", 
            "tiikikasseika-orion-openapi.yaml": self.documentation_dir / "tourism-api"
        }
        
        # ディレクトリを確保
        for dir_path in [self.documentation_dir, self.api_specs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        for api_dir in self.api_dirs.values():
            api_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_pdf_links_from_yaml(self, yaml_file: Path) -> List[Tuple[str, str]]:
        """YAMLファイルからPDFリンクを抽出"""
        print(f"📄 解析中: {yaml_file.name}")
        
        with open(yaml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # PDFリンクの正規表現パターン
        pdf_pattern = r'\* \[(.*?)\]\((https://docs\.smartcity-yaizu\.jp/.*?\.pdf)\)'
        pdf_matches = re.findall(pdf_pattern, content)
        
        print(f"  🔍 PDF発見: {len(pdf_matches)} 個")
        return pdf_matches
    
    async def download_pdf(self, session: aiohttp.ClientSession, name: str, url: str, yaml_filename: str) -> bool:
        """PDFファイルをダウンロード"""
        try:
            # URLからファイル名を抽出
            parsed_url = urlparse(url)
            filename = Path(parsed_url.path).name
            # API種類別ディレクトリに保存
            api_dir = self.api_dirs.get(yaml_filename, self.documentation_dir)
            file_path = api_dir / filename
            
            # 既に存在する場合はスキップ
            if file_path.exists():
                print(f"  ⏭️  既存: {filename}")
                return True
            
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    print(f"  ✅ ダウンロード: {filename} ({len(content):,} bytes)")
                    return True
                else:
                    print(f"  ❌ エラー: {filename} (HTTP {response.status})")
                    return False
        except Exception as e:
            print(f"  ❌ エラー: {name} - {e}")
            return False
    
    def generate_json_schema_from_name(self, name: str, pdf_filename: str) -> Dict[str, Any]:
        """名前からJSONスキーマを生成（基本テンプレート）"""
        # ファイル名からエンティティタイプを推定
        entity_type = Path(pdf_filename).stem
        
        # 基本的なFIWARE NGSIv2スキーマテンプレート
        schema = {
            "dataModelName": name,
            "entityType": entity_type,
            "fiwareService": "smartcity_yaizu",
            "fiwareServicePath": f"/{entity_type}",
            "description": f"{name}の情報を管理するデータモデル",
            "lastUpdated": datetime.now().isoformat(),
            "pdfSource": pdf_filename,
            "attributes": {
                "id": {
                    "type": "string",
                    "description": "エンティティID",
                    "required": True
                },
                "type": {
                    "type": "string", 
                    "description": "エンティティタイプ",
                    "value": entity_type,
                    "required": True
                },
                "location": {
                    "type": "geo:point",
                    "description": "位置情報",
                    "required": False
                },
                "address": {
                    "type": "StructuredValue",
                    "description": "住所情報",
                    "required": False
                },
                "name": {
                    "type": "string",
                    "description": "名称",
                    "required": False
                },
                "dateObserved": {
                    "type": "DateTime",
                    "description": "観測日時",
                    "required": False
                }
            }
        }
        
        # エンティティタイプに応じた属性の追加
        if "Aed" in entity_type:
            schema["attributes"].update({
                "status": {"type": "string", "description": "設置状況"},
                "manufacturer": {"type": "string", "description": "製造元"}
            })
        elif "Camera" in entity_type:
            schema["attributes"].update({
                "imageUrl": {"type": "string", "description": "画像URL"},
                "direction": {"type": "number", "description": "方向"}
            })
        elif "Gauge" in entity_type:
            schema["attributes"].update({
                "value": {"type": "number", "description": "測定値"},
                "unit": {"type": "string", "description": "単位"}
            })
        elif "Evacuation" in entity_type:
            schema["attributes"].update({
                "capacity": {"type": "number", "description": "収容人数"},
                "facilityType": {"type": "string", "description": "施設タイプ"}
            })
        
        return schema
    
    async def process_yaml_file(self, yaml_file: Path) -> Dict[str, Any]:
        """単一のYAMLファイルを処理"""
        pdf_links = self.extract_pdf_links_from_yaml(yaml_file)
        
        if not pdf_links:
            print(f"  ⚠️  PDFリンクが見つかりませんでした: {yaml_file.name}")
            return {"processed": 0, "files": []}
        
        print(f"📥 PDFダウンロード開始: {len(pdf_links)} ファイル")
        
        processed_files = []
        success_count = 0
        
        async with aiohttp.ClientSession() as session:
            for name, url in pdf_links:
                # PDFダウンロード
                if await self.download_pdf(session, name, url, yaml_file.name):
                    success_count += 1
                    
                    # JSONスキーマ生成
                    filename = Path(urlparse(url).path).name
                    json_schema = self.generate_json_schema_from_name(name, filename)
                    
                    # JSONファイル保存
                    json_filename = Path(filename).stem + ".json"
                    json_path = self.api_specs_dir / json_filename
                    
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(json_schema, f, ensure_ascii=False, indent=2)
                    
                    processed_files.append({
                        "name": name,
                        "pdf_file": filename,
                        "json_file": json_filename,
                        "entity_type": json_schema["entityType"]
                    })
        
        print(f"✅ 処理完了: {success_count}/{len(pdf_links)} ファイル")
        return {
            "processed": success_count,
            "total": len(pdf_links),
            "files": processed_files
        }
    
    async def process_all_yaml_files(self) -> Dict[str, Any]:
        """全てのYAMLファイルを処理"""
        print("="*60)
        print("OpenAPI YAML → PDF → JSON 変換プロセッサー")
        print("="*60)
        
        yaml_files = list(self.openapi_dir.glob("*.yaml"))
        if not yaml_files:
            print("❌ OpenAPI YAMLファイルが見つかりません")
            return {"error": "No YAML files found"}
        
        results = {}
        total_processed = 0
        
        for yaml_file in yaml_files:
            print(f"\n🔄 処理中: {yaml_file.name}")
            result = await self.process_yaml_file(yaml_file)
            results[yaml_file.name] = result
            total_processed += result.get("processed", 0)
        
        # サマリー作成
        print(f"\n📊 処理サマリー:")
        print(f"  🗂️  処理したYAMLファイル: {len(yaml_files)} 個")
        print(f"  📄 生成したJSONスキーマ: {total_processed} 個")
        print(f"  📁 保存先:")
        print(f"     PDF: {self.documentation_dir}")
        print(f"     JSON: {self.api_specs_dir}")
        
        # 統合インデックスファイル作成
        index_data = {
            "title": "焼津市スマートシティ API データモデル",
            "description": "OpenAPI仕様から生成されたデータモデルスキーマ",
            "generated_at": datetime.now().isoformat(),
            "total_models": total_processed,
            "yaml_sources": list(results.keys()),
            "models": []
        }
        
        for yaml_name, result in results.items():
            if "files" in result:
                for file_info in result["files"]:
                    index_data["models"].append({
                        "source_yaml": yaml_name,
                        **file_info
                    })
        
        index_path = self.api_specs_dir / "data_models_index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        print(f"  📋 インデックスファイル: {index_path}")
        
        return {
            "success": True,
            "total_processed": total_processed,
            "yaml_files": len(yaml_files),
            "results": results
        }


async def main():
    """メイン実行関数"""
    processor = OpenAPIPDFProcessor()
    result = await processor.process_all_yaml_files()
    
    if result.get("success"):
        print(f"\n🎉 全処理が完了しました！")
    else:
        print(f"\n❌ エラーが発生しました: {result}")


if __name__ == "__main__":
    asyncio.run(main())