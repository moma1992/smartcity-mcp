#!/usr/bin/env python3
"""
OpenAPIファイルから抽出した防災関連PDFを全てダウンロード
"""

import asyncio
import re
import yaml
from pathlib import Path
from urllib.parse import urljoin

import aiohttp


async def main():
    print("="*60)
    print("防災関連PDFの一括ダウンロード")
    print("="*60)
    
    # OpenAPIファイルを読み込み
    openapi_file = Path("/Users/mamo/smartcity-mcp/data/openapi/bousai-orion-openapi.yaml")
    data_dir = Path("/Users/mamo/smartcity-mcp/data/documentation")
    
    print(f"📄 OpenAPIファイル読み込み: {openapi_file}")
    
    with open(openapi_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # PDFリンクを抽出
    pdf_pattern = r'\* \[(.*?)\]\((https://docs\.smartcity-yaizu\.jp/.*?\.pdf)\)'
    pdf_matches = re.findall(pdf_pattern, content)
    
    print(f"🔍 PDF発見: {len(pdf_matches)} 個")
    
    # PDFリストを表示
    for name, url in pdf_matches:
        print(f"  📄 {name}: {url}")
    
    if not pdf_matches:
        print("❌ PDFリンクが見つかりませんでした")
        return
    
    # ダウンロード開始
    print(f"\n📥 ダウンロード開始: {len(pdf_matches)} ファイル")
    
    success_count = 0
    failed_count = 0
    
    async with aiohttp.ClientSession() as session:
        
        for i, (name, url) in enumerate(pdf_matches, 1):
            # ファイル名を生成（URLから抽出）
            filename = url.split('/')[-1]
            filepath = data_dir / filename
            
            print(f"\n[{i}/{len(pdf_matches)}] {name}")
            print(f"  ファイル: {filename}")
            print(f"  URL: {url}")
            
            # 既存ファイルをチェック
            if filepath.exists():
                size_kb = filepath.stat().st_size / 1024
                print(f"  ⏭️ スキップ（既存 {size_kb:.1f} KB）")
                success_count += 1
                continue
            
            try:
                async with session.get(url, timeout=30) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        
                        # PDFかどうか確認
                        if content[:4] == b'%PDF':
                            with open(filepath, 'wb') as f:
                                f.write(content)
                            
                            size_kb = len(content) / 1024
                            print(f"  ✅ ダウンロード成功: {size_kb:.1f} KB")
                            success_count += 1
                        else:
                            print(f"  ⚠️ PDFではありません (Content-Type: {resp.headers.get('content-type')})")
                            failed_count += 1
                    
                    elif resp.status == 404:
                        print(f"  ❌ ファイルが見つかりません (404)")
                        failed_count += 1
                    
                    elif resp.status == 403:
                        print(f"  ❌ アクセス拒否 (403)")
                        failed_count += 1
                    
                    else:
                        print(f"  ❌ ダウンロード失敗: ステータス {resp.status}")
                        failed_count += 1
                        
            except asyncio.TimeoutError:
                print(f"  ⏰ タイムアウト")
                failed_count += 1
            except Exception as e:
                print(f"  ❌ エラー: {e}")
                failed_count += 1
            
            # レート制限対策
            await asyncio.sleep(0.3)
    
    # 結果レポート
    print("\n" + "="*60)
    print("📊 ダウンロード完了レポート")
    print("="*60)
    
    print(f"\n📈 結果:")
    print(f"  総数: {len(pdf_matches)} ファイル")
    print(f"  成功: {success_count} ファイル")
    print(f"  失敗: {failed_count} ファイル")
    print(f"  成功率: {success_count / len(pdf_matches) * 100:.1f}%")
    
    # data/documentationフォルダの最終状態
    all_files = sorted(data_dir.glob("*.pdf"))
    print(f"\n📁 {data_dir} の全PDFファイル: {len(all_files)} 個")
    
    total_size = 0
    for pdf_file in all_files:
        size_mb = pdf_file.stat().st_size / (1024 * 1024)
        total_size += size_mb
        print(f"  - {pdf_file.name} ({size_mb:.2f} MB)")
    
    print(f"\n📊 合計サイズ: {total_size:.2f} MB")
    
    # 失敗したファイルがある場合
    if failed_count > 0:
        print(f"\n⚠️ {failed_count} ファイルのダウンロードに失敗しました")
        print("これらのファイルは現在公開されていないか、アクセス権限が必要な可能性があります")


if __name__ == "__main__":
    asyncio.run(main())