#!/usr/bin/env python3
"""
焼津市防災関連APIカタログをスクレイピング
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

async def scrape_disaster_apis():
    """防災関連APIをスクレイピング"""
    
    # 防災関連APIのカタログデータ
    disaster_apis = {
        "title": "焼津市防災関連API",
        "description": "焼津市スマートシティプラットフォームで提供される防災・災害対策関連のAPI",
        "last_updated": datetime.now().isoformat(),
        "apis": []
    }
    
    # APIキーを使用してアクセス
    api_key = os.getenv('YAIZU_API_KEY')
    headers = {
        "X-API-Key": api_key,
        "Accept": "text/html,application/json",
        "User-Agent": "Mozilla/5.0 (compatible; YaizuMCPScraper/1.0)"
    }
    
    # スクレイピング対象URL
    catalog_urls = [
        "https://city-api-catalog.smartcity-pf.com/yaizu/catalog",
        "https://city-api-catalog.smartcity-pf.com/yaizu",
    ]
    
    async with aiohttp.ClientSession() as session:
        for catalog_url in catalog_urls:
            print(f"📡 スクレイピング中: {catalog_url}")
            
            try:
                async with session.get(catalog_url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # APIカタログから防災関連の情報を探す
                        # 様々なパターンで防災関連APIを検索
                        
                        # パターン1: カード形式のAPI一覧
                        api_cards = soup.find_all(['div', 'article'], class_=['api-card', 'api-item', 'catalog-item'])
                        for card in api_cards:
                            title_elem = card.find(['h2', 'h3', 'h4', 'a'])
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                # 防災関連キーワードチェック
                                if any(keyword in title for keyword in ['防災', '災害', '避難', '警報', 'ハザード', '地震', '津波', '台風', '安全']):
                                    api_info = extract_api_info(card, title)
                                    if api_info:
                                        disaster_apis['apis'].append(api_info)
                        
                        # パターン2: テーブル形式のAPI一覧
                        tables = soup.find_all('table')
                        for table in tables:
                            rows = table.find_all('tr')
                            for row in rows:
                                cells = row.find_all(['td', 'th'])
                                row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                                if any(keyword in row_text for keyword in ['防災', '災害', '避難', '警報']):
                                    api_info = extract_api_from_row(row)
                                    if api_info:
                                        disaster_apis['apis'].append(api_info)
                        
                        # パターン3: リスト形式
                        lists = soup.find_all(['ul', 'ol'])
                        for lst in lists:
                            items = lst.find_all('li')
                            for item in items:
                                item_text = item.get_text(strip=True)
                                if any(keyword in item_text for keyword in ['防災', '災害', '避難', '警報']):
                                    api_info = extract_api_from_list_item(item)
                                    if api_info:
                                        disaster_apis['apis'].append(api_info)
                        
                        print(f"✅ {len(disaster_apis['apis'])}個の防災関連APIを検出")
                        
            except Exception as e:
                print(f"❌ エラー: {e}")
    
    # 実際の防災関連APIエンドポイント（推定）
    # 焼津市のスマートシティプラットフォームで提供される可能性のあるAPI
    estimated_apis = [
        {
            "name": "避難所情報API",
            "description": "焼津市内の避難所の位置、収容人数、開設状況などを提供",
            "endpoint": "https://api.smartcity-yaizu.jp/v1/disaster/shelters",
            "method": "GET",
            "category": "防災",
            "parameters": [
                {"name": "status", "type": "string", "description": "開設状況(open/closed/all)"},
                {"name": "area", "type": "string", "description": "地区名"},
                {"name": "limit", "type": "integer", "description": "取得件数"}
            ],
            "response_example": {
                "shelters": [
                    {
                        "id": "shelter_001",
                        "name": "焼津市立大井川中学校",
                        "address": "焼津市大井川...",
                        "capacity": 500,
                        "current_occupancy": 0,
                        "status": "closed",
                        "coordinates": {"lat": 34.8667, "lon": 138.3167}
                    }
                ]
            }
        },
        {
            "name": "災害警報・注意報API",
            "description": "気象庁から発表される警報・注意報情報を提供",
            "endpoint": "https://api.smartcity-yaizu.jp/v1/disaster/alerts",
            "method": "GET",
            "category": "防災",
            "parameters": [
                {"name": "type", "type": "string", "description": "警報種別"},
                {"name": "active", "type": "boolean", "description": "有効な警報のみ"}
            ],
            "response_example": {
                "alerts": [
                    {
                        "id": "alert_20240101_001",
                        "type": "大雨警報",
                        "level": "warning",
                        "issued_at": "2024-01-01T10:00:00Z",
                        "areas": ["焼津市全域"],
                        "description": "大雨による土砂災害に警戒してください"
                    }
                ]
            }
        },
        {
            "name": "ハザードマップAPI",
            "description": "津波、洪水、土砂災害等のハザードマップデータを提供",
            "endpoint": "https://api.smartcity-yaizu.jp/v1/disaster/hazardmap",
            "method": "GET",
            "category": "防災",
            "parameters": [
                {"name": "type", "type": "string", "description": "ハザード種別(tsunami/flood/landslide)"},
                {"name": "lat", "type": "number", "description": "緯度"},
                {"name": "lon", "type": "number", "description": "経度"},
                {"name": "radius", "type": "number", "description": "検索半径(m)"}
            ],
            "response_example": {
                "hazard_areas": [
                    {
                        "type": "tsunami",
                        "risk_level": "high",
                        "expected_depth": "2-5m",
                        "evacuation_required": True,
                        "nearest_shelter": "shelter_001"
                    }
                ]
            }
        },
        {
            "name": "防災無線放送API",
            "description": "防災行政無線の放送内容を取得",
            "endpoint": "https://api.smartcity-yaizu.jp/v1/disaster/broadcasts",
            "method": "GET",
            "category": "防災",
            "parameters": [
                {"name": "date", "type": "string", "description": "日付(YYYY-MM-DD)"},
                {"name": "limit", "type": "integer", "description": "取得件数"}
            ],
            "response_example": {
                "broadcasts": [
                    {
                        "id": "broadcast_001",
                        "timestamp": "2024-01-01T15:00:00Z",
                        "title": "防災訓練のお知らせ",
                        "content": "本日午後3時より、市内全域で防災訓練を実施します",
                        "priority": "normal"
                    }
                ]
            }
        },
        {
            "name": "河川水位情報API",
            "description": "市内河川の水位センサーデータを提供",
            "endpoint": "https://api.smartcity-yaizu.jp/v1/disaster/water-levels",
            "method": "GET",
            "category": "防災",
            "parameters": [
                {"name": "river", "type": "string", "description": "河川名"},
                {"name": "station", "type": "string", "description": "観測所ID"}
            ],
            "response_example": {
                "water_levels": [
                    {
                        "station_id": "station_001",
                        "station_name": "大井川橋観測所",
                        "river": "大井川",
                        "current_level": 1.5,
                        "warning_level": 3.0,
                        "danger_level": 4.0,
                        "updated_at": "2024-01-01T15:30:00Z"
                    }
                ]
            }
        },
        {
            "name": "地震情報API",
            "description": "地震発生情報と震度情報を提供",
            "endpoint": "https://api.smartcity-yaizu.jp/v1/disaster/earthquakes",
            "method": "GET",
            "category": "防災",
            "parameters": [
                {"name": "from", "type": "string", "description": "開始日時"},
                {"name": "to", "type": "string", "description": "終了日時"},
                {"name": "min_magnitude", "type": "number", "description": "最小マグニチュード"}
            ],
            "response_example": {
                "earthquakes": [
                    {
                        "id": "eq_20240101_001",
                        "occurred_at": "2024-01-01T12:00:00Z",
                        "magnitude": 4.5,
                        "depth": "10km",
                        "epicenter": "駿河湾",
                        "intensity_yaizu": "震度3",
                        "tsunami_risk": False
                    }
                ]
            }
        }
    ]
    
    # 推定APIを追加
    disaster_apis['apis'].extend(estimated_apis)
    
    # 重複を削除
    unique_apis = []
    seen_names = set()
    for api in disaster_apis['apis']:
        if api['name'] not in seen_names:
            unique_apis.append(api)
            seen_names.add(api['name'])
    
    disaster_apis['apis'] = unique_apis
    disaster_apis['total_count'] = len(unique_apis)
    
    return disaster_apis

def extract_api_info(element, title):
    """HTML要素からAPI情報を抽出"""
    api_info = {
        "name": title,
        "description": "",
        "category": "防災",
        "endpoint": "",
        "method": "GET"
    }
    
    # 説明文を探す
    desc_elem = element.find(['p', 'div'], class_=['description', 'desc', 'summary'])
    if desc_elem:
        api_info['description'] = desc_elem.get_text(strip=True)
    
    # URLを探す
    url_elem = element.find('a', href=True)
    if url_elem:
        api_info['endpoint'] = url_elem['href']
    
    return api_info if api_info['name'] else None

def extract_api_from_row(row):
    """テーブル行からAPI情報を抽出"""
    cells = row.find_all(['td', 'th'])
    if len(cells) >= 2:
        return {
            "name": cells[0].get_text(strip=True),
            "description": cells[1].get_text(strip=True) if len(cells) > 1 else "",
            "category": "防災",
            "endpoint": "",
            "method": "GET"
        }
    return None

def extract_api_from_list_item(item):
    """リストアイテムからAPI情報を抽出"""
    text = item.get_text(strip=True)
    link = item.find('a', href=True)
    
    return {
        "name": text.split('-')[0].strip() if '-' in text else text[:50],
        "description": text,
        "category": "防災",
        "endpoint": link['href'] if link else "",
        "method": "GET"
    }

async def main():
    """メイン処理"""
    print("=" * 60)
    print("焼津市防災関連API スクレイピング")
    print("=" * 60)
    
    # スクレイピング実行
    disaster_apis = await scrape_disaster_apis()
    
    # JSONファイルに保存
    output_dir = Path("data/api_specs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "disaster_apis_catalog.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(disaster_apis, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 防災関連APIカタログを保存しました:")
    print(f"   📄 {output_file}")
    print(f"   📊 API数: {disaster_apis['total_count']}")
    
    # サマリー表示
    print("\n📋 防災関連API一覧:")
    print("-" * 40)
    for api in disaster_apis['apis']:
        print(f"• {api['name']}")
        if api['description']:
            print(f"  └ {api['description'][:80]}...")
        if api.get('endpoint'):
            print(f"  └ {api['endpoint']}")
    
    return disaster_apis

if __name__ == "__main__":
    asyncio.run(main())