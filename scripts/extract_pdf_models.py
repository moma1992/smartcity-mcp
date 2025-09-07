#!/usr/bin/env python3
"""
防災APIのPDFからデータモデル情報を抽出してJSONファイルを作成
"""

import json
from pathlib import Path

# データモデル定義（PDFから抽出した情報を基に作成）
data_models = {
    "Aed": {
        "dataModelName": "AED設置場所",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/Aed",
        "entityType": "Aed"
    },
    "DrinkingWaterTank": {
        "dataModelName": "飲料水貯水槽",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/DrinkingWaterTank",
        "entityType": "DrinkingWaterTank"
    },
    "PrecipitationGauge": {
        "dataModelName": "雨量計",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/PrecipitationGauge",
        "entityType": "PrecipitationGauge"
    },
    "SteepSlopeFailureSpecialVigilanceArea": {
        "dataModelName": "がけ崩れ（特別警戒区域）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/SteepSlopeFailureSpecialVigilanceArea",
        "entityType": "SteepSlopeFailureSpecialVigilanceArea"
    },
    "SteepSlopeFailureVigilanceArea": {
        "dataModelName": "がけ崩れ（警戒区域）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/SteepSlopeFailureVigilanceArea",
        "entityType": "SteepSlopeFailureVigilanceArea"
    },
    "CameraInformation": {
        "dataModelName": "河川・海岸カメラ",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/CameraInformation",
        "entityType": "CameraInformation"
    },
    "StreamGauge": {
        "dataModelName": "河川水位計",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/StreamGauge",
        "entityType": "StreamGauge"
    },
    "UnderpassInformation": {
        "dataModelName": "冠水センサー",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/UnderpassInformation",
        "entityType": "UnderpassInformation"
    },
    "FirstAidStation": {
        "dataModelName": "救護所",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/FirstAidStation",
        "entityType": "FirstAidStation"
    },
    "ReliefHospital": {
        "dataModelName": "救護病院",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/ReliefHospital",
        "entityType": "ReliefHospital"
    },
    "WeatherAlert": {
        "dataModelName": "警報・注意報",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/WeatherAlert",
        "entityType": "WeatherAlert"
    },
    "HouseCollapseRiskAreaRiverErosion": {
        "dataModelName": "洪水浸水想定区域（家屋倒壊等：河岸浸食）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/HouseCollapseRiskAreaRiverErosion",
        "entityType": "HouseCollapseRiskAreaRiverErosion"
    },
    "HouseCollapseRiskAreaOverflowing": {
        "dataModelName": "洪水浸水想定区域（家屋倒壊等：氾濫流）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/HouseCollapseRiskAreaOverflowing",
        "entityType": "HouseCollapseRiskAreaOverflowing"
    },
    "FloodRiskAreaPlanScale": {
        "dataModelName": "洪水浸水想定区域（計画規模）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/FloodRiskAreaPlanScale",
        "entityType": "FloodRiskAreaPlanScale"
    },
    "FloodRiskAreaMaxScale": {
        "dataModelName": "洪水浸水想定区域（最大規模）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/FloodRiskAreaMaxScale",
        "entityType": "FloodRiskAreaMaxScale"
    },
    "FloodRiskAreaMaxTime": {
        "dataModelName": "洪水浸水想定区域（浸水継続時間）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/FloodRiskAreaMaxTime",
        "entityType": "FloodRiskAreaMaxTime"
    },
    "TsunamiFloodRiskArea": {
        "dataModelName": "静岡県第4次地震被害想定（レベル２重合せ図）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/TsunamiFloodRiskArea",
        "entityType": "TsunamiFloodRiskArea"
    },
    "LandslideVigilanceArea": {
        "dataModelName": "地すべり（警戒区域）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/LandslideVigilanceArea",
        "entityType": "LandslideVigilanceArea"
    },
    "LandslidePreventionArea": {
        "dataModelName": "地すべり（防止区域）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/LandslidePreventionArea",
        "entityType": "LandslidePreventionArea"
    },
    "EvacuationSpace": {
        "dataModelName": "指定緊急避難場所",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/EvacuationSpace",
        "entityType": "EvacuationSpace"
    },
    "TsunamiEvacuationBuilding": {
        "dataModelName": "指定津波避難ビル等",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/TsunamiEvacuationBuilding",
        "entityType": "TsunamiEvacuationBuilding"
    },
    "FloodHistory": {
        "dataModelName": "浸水履歴",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/FloodHistory",
        "entityType": "FloodHistory"
    },
    "FloodPreventionWarehouse": {
        "dataModelName": "水防倉庫",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/FloodPreventionWarehouse",
        "entityType": "FloodPreventionWarehouse"
    },
    "WeatherForecast": {
        "dataModelName": "天候",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/WeatherForecast",
        "entityType": "WeatherForecast"
    },
    "BroadcastRadioChildStation": {
        "dataModelName": "同報無線子局",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/BroadcastRadioChildStation",
        "entityType": "BroadcastRadioChildStation"
    },
    "RestrictedTrafficAreaInformation": {
        "dataModelName": "道路規制情報",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/RestrictedTrafficAreaInformation",
        "entityType": "RestrictedTrafficAreaInformation"
    },
    "DebrisFlowSpecialVigilanceArea": {
        "dataModelName": "土石流（特別警戒区域）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/DebrisFlowSpecialVigilanceArea",
        "entityType": "DebrisFlowSpecialVigilanceArea"
    },
    "DebrisFlowVigilanceArea": {
        "dataModelName": "土石流（警戒区域）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/DebrisFlowVigilanceArea",
        "entityType": "DebrisFlowVigilanceArea"
    },
    "SandbagStation": {
        "dataModelName": "土のうステーション",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/SandbagStation",
        "entityType": "SandbagStation"
    },
    "SewerFloodRiskArea": {
        "dataModelName": "内水浸水想定区域（公共下水道区域内）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/SewerFloodRiskArea",
        "entityType": "SewerFloodRiskArea"
    },
    "EvacuationInformationFlood": {
        "dataModelName": "発令中の避難情報（洪水）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/EvacuationInformationFlood",
        "entityType": "EvacuationInformationFlood"
    },
    "EvacuationInformationSediment": {
        "dataModelName": "発令中の避難情報（土砂）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/EvacuationInformationSediment",
        "entityType": "EvacuationInformationSediment"
    },
    "EvacuationInformationStormSurge": {
        "dataModelName": "発令中の避難情報（高潮）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/EvacuationInformationStormSurge",
        "entityType": "EvacuationInformationStormSurge"
    },
    "EvacuationInformationEarthquake": {
        "dataModelName": "発令中の避難情報（地震）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/EvacuationInformationEarthquake",
        "entityType": "EvacuationInformationEarthquake"
    },
    "EvacuationInformationTsunami": {
        "dataModelName": "発令中の避難情報（津波）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/EvacuationInformationTsunami",
        "entityType": "EvacuationInformationTsunami"
    },
    "EvacuationInformationNuclearPower": {
        "dataModelName": "発令中の避難情報（原子力）",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/EvacuationInformationNuclearPower",
        "entityType": "EvacuationInformationNuclearPower"
    },
    "EvacuationShelter": {
        "dataModelName": "避難所開設状況",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/EvacuationShelter",
        "entityType": "EvacuationShelter"
    },
    "FirePreventionWaterTank": {
        "dataModelName": "防火水槽",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/FirePreventionWaterTank",
        "entityType": "FirePreventionWaterTank"
    },
    "DisasterPreventionWarehouse": {
        "dataModelName": "防災倉庫",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/DisasterPreventionWarehouse",
        "entityType": "DisasterPreventionWarehouse"
    },
    "DisasterMail": {
        "dataModelName": "防災メール発信コントロール",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/DisasterMail",
        "entityType": "DisasterMail"
    },
    "DisasterPreventionHeliport": {
        "dataModelName": "防災用ヘリポート",
        "fiwareService": "smartcity_yaizu",
        "fiwareServicePath": "/DisasterPreventionHeliport",
        "entityType": "DisasterPreventionHeliport"
    }
}

def create_basic_json(entity_type, model_info):
    """基本的なJSONファイルを作成"""
    return {
        "dataModelName": model_info["dataModelName"],
        "fiwareService": model_info["fiwareService"],
        "fiwareServicePath": model_info["fiwareServicePath"],
        "entityType": model_info["entityType"],
        "entityIdPattern": f"jp.smartcity-yaizu.{entity_type}.[IDの値]",
        "attributes": {
            "id": {
                "name": "ID",
                "description": f"{model_info['dataModelName']}の識別子",
                "type": "Text"
            },
            "type": {
                "name": "タイプ",
                "description": "エンティティタイプ",
                "type": "Text",
                "value": entity_type
            }
        }
    }

def main():
    api_docs_dir = Path("/Users/mamo/smartcity-mcp/data/api_specs")
    api_docs_dir.mkdir(exist_ok=True)
    
    # 既に作成済みのファイル
    created_files = ["Aed", "EvacuationShelter", "WeatherForecast"]
    
    # 残りのデータモデルのJSONファイルを作成
    for entity_type, model_info in data_models.items():
        if entity_type in created_files:
            continue
            
        json_file = api_docs_dir / f"{entity_type}.json"
        json_data = create_basic_json(entity_type, model_info)
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ {json_file.name} 作成完了")
    
    # 統合api_docs.jsonファイルを作成
    all_models = []
    for json_file in sorted(api_docs_dir.glob("*.json")):
        with open(json_file, 'r', encoding='utf-8') as f:
            model_data = json.load(f)
            all_models.append({
                "entityType": model_data["entityType"],
                "dataModelName": model_data["dataModelName"],
                "fiwareService": model_data["fiwareService"],
                "fiwareServicePath": model_data["fiwareServicePath"],
                "entityIdPattern": model_data.get("entityIdPattern", ""),
                "jsonFile": f"data/api_specs/{json_file.name}"
            })
    
    # 統合ファイルを保存
    api_docs_file = Path("/Users/mamo/smartcity-mcp/api_specs.json")
    api_docs_content = {
        "description": "焼津市スマートシティ防災API データモデル仕様",
        "version": "1.0.0",
        "baseUrl": "https://city-api-catalog-api.smartcity-pf.com/yaizu",
        "fiwareService": "smartcity_yaizu",
        "dataModels": all_models
    }
    
    with open(api_docs_file, 'w', encoding='utf-8') as f:
        json.dump(api_docs_content, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 統合ファイル api_specs.json 作成完了")
    print(f"📊 合計 {len(all_models)} 個のデータモデル")

if __name__ == "__main__":
    main()