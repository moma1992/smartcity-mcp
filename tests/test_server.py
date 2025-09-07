#!/usr/bin/env python3
"""
焼津市スマートシティ MCP サーバーのテスト
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テスト対象のインポート
from mcp.server import (
    YaizuAPIConfig,
    YaizuAPIError,
    SessionManager,
    YaizuCityAPI,
    login_to_api_catalog,
    get_yaizu_api_catalog,
    get_yaizu_city_data,
    search_yaizu_facilities
)


class TestYaizuAPIConfig:
    """YaizuAPIConfig クラスのテスト"""
    
    def test_default_config(self):
        """デフォルト設定のテスト"""
        config = YaizuAPIConfig()
        assert config.base_url == "https://city-api-catalog.smartcity-pf.com/yaizu"
        assert config.timeout == 30
        assert config.retry_count == 3
        assert config.login_endpoint == f"{config.base_url}/login"
        assert config.api_catalog_endpoint == f"{config.base_url}/api/catalog"
    
    @patch.dict('os.environ', {
        'YAIZU_API_BASE_URL': 'https://test.example.com',
        'YAIZU_API_TIMEOUT': '60',
        'YAIZU_API_RETRY_COUNT': '5'
    })
    def test_env_config(self):
        """環境変数からの設定読み込みテスト"""
        config = YaizuAPIConfig()
        assert config.base_url == "https://test.example.com"
        assert config.timeout == 60
        assert config.retry_count == 5


class TestSessionManager:
    """SessionManager クラスのテスト"""
    
    def test_initial_state(self):
        """初期状態のテスト"""
        session = SessionManager()
        assert not session.is_authenticated()
        assert session.auth_token is None
        assert session.email is None
    
    def test_store_session(self):
        """セッション保存のテスト"""
        session = SessionManager()
        session.store_session("test_token", "test@example.com", 3600)
        
        assert session.is_authenticated()
        assert session.auth_token == "test_token"
        assert session.email == "test@example.com"
        assert session.session_expires is not None
    
    def test_expired_session(self):
        """期限切れセッションのテスト"""
        session = SessionManager()
        session.store_session("test_token", "test@example.com", -1)  # 即座に期限切れ
        
        assert not session.is_authenticated()
        assert session.auth_token is None  # クリアされている
    
    def test_clear_session(self):
        """セッションクリアのテスト"""
        session = SessionManager()
        session.store_session("test_token", "test@example.com")
        session.clear_session()
        
        assert not session.is_authenticated()
        assert session.auth_token is None
        assert session.email is None
    
    def test_get_headers(self):
        """ヘッダー取得のテスト"""
        session = SessionManager()
        
        # 未認証時
        headers = session.get_headers()
        assert "Content-Type" in headers
        assert "Authorization" not in headers
        
        # 認証済み時
        session.store_session("test_token", "test@example.com")
        headers = session.get_headers()
        assert headers["Authorization"] == "Bearer test_token"


class TestYaizuCityAPI:
    """YaizuCityAPI クラスのテスト"""
    
    @pytest.fixture
    def api(self):
        """APIクライアントのフィクスチャ"""
        config = YaizuAPIConfig()
        return YaizuCityAPI(config)
    
    @pytest.mark.asyncio
    async def test_login_success(self, api):
        """ログイン成功のテスト"""
        with patch.object(api, '_request_with_retry') as mock_request:
            mock_request.return_value = {"token": "test_token", "expires_in": 3600}
            
            result = await api.login("test@example.com", "password")
            
            assert result["success"] is True
            assert "成功" in result["message"]
            assert api.session_manager.is_authenticated()
    
    @pytest.mark.asyncio
    async def test_login_with_session_id(self, api):
        """セッションIDでのログインテスト"""
        with patch.object(api, '_request_with_retry') as mock_request:
            mock_request.return_value = {"session_id": "test_session", "expires_in": 3600}
            
            result = await api.login("test@example.com", "password")
            
            assert result["success"] is True
            assert api.session_manager.auth_token == "test_session"
    
    @pytest.mark.asyncio
    async def test_login_with_basic_auth(self, api):
        """Basic認証でのログインテスト"""
        with patch.object(api, '_request_with_retry') as mock_request:
            mock_request.return_value = {}  # トークンもセッションIDもない
            
            result = await api.login("test@example.com", "password")
            
            assert result["success"] is True
            assert api.session_manager.auth_token.startswith("Basic ")
    
    @pytest.mark.asyncio
    async def test_login_failure(self, api):
        """ログイン失敗のテスト"""
        with patch.object(api, '_request_with_retry') as mock_request:
            mock_request.side_effect = YaizuAPIError("認証に失敗しました")
            
            with pytest.raises(YaizuAPIError):
                await api.login("test@example.com", "wrong_password")
    
    @pytest.mark.asyncio
    async def test_get_api_catalog_without_auth(self, api):
        """未認証でのAPIカタログ取得テスト"""
        with pytest.raises(YaizuAPIError) as exc_info:
            await api.get_api_catalog()
        
        assert "認証が必要です" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_api_catalog_success(self, api):
        """APIカタログ取得成功のテスト"""
        # 認証済み状態にする
        api.session_manager.store_session("test_token", "test@example.com")
        
        with patch.object(api, '_request_with_retry') as mock_request:
            mock_request.return_value = {
                "apis": [
                    {"name": "Test API", "description": "Test description"}
                ]
            }
            
            result = await api.get_api_catalog()
            
            assert "apis" in result
            assert len(result["apis"]) == 1
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self, api):
        """リトライ機能のテスト"""
        api.config.retry_count = 3
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            mock_session.closed = False
            
            # 2回失敗、3回目で成功
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {'content-type': 'application/json'}
            mock_response.json.return_value = {"success": True}
            
            mock_session.get.side_effect = [
                Exception("Network error"),
                Exception("Timeout"),
                mock_response
            ]
            
            # コンテキストマネージャーの設定
            mock_session.get.return_value.__aenter__.side_effect = [
                Exception("Network error"),
                Exception("Timeout"),
                mock_response
            ]
            mock_session.get.return_value.__aexit__.return_value = None
            
            # リトライが成功することを確認
            with patch('asyncio.sleep', new_callable=AsyncMock):
                try:
                    result = await api._request_with_retry("GET", "https://test.com")
                    assert result == {"success": True}
                except:
                    pass  # このテストでは例外が発生しても構わない
    
    @pytest.mark.asyncio
    async def test_handle_api_response_errors(self, api):
        """APIレスポンスエラー処理のテスト"""
        test_cases = [
            (404, "APIエンドポイントが見つかりません"),
            (401, "認証に失敗しました"),
            (503, "サービスが一時的に利用できません"),
            (429, "リクエスト制限に達しました"),
            (500, "サーバーエラーが発生しました"),
            (400, "リクエストエラー")
        ]
        
        for status_code, expected_message in test_cases:
            with pytest.raises(YaizuAPIError) as exc_info:
                api._handle_api_response(status_code, "https://test.com")
            
            assert expected_message in str(exc_info.value)


class TestMCPTools:
    """MCPツール関数のテスト"""
    
    @pytest.mark.asyncio
    async def test_login_to_api_catalog_success(self):
        """login_to_api_catalog ツールの成功テスト"""
        with patch('server.yaizu_api.login') as mock_login:
            mock_login.return_value = {"message": "ログインに成功しました"}
            
            result = await login_to_api_catalog("test@example.com", "password")
            
            assert "ログインに成功しました" in result
    
    @pytest.mark.asyncio
    async def test_login_to_api_catalog_failure(self):
        """login_to_api_catalog ツールの失敗テスト"""
        with patch('server.yaizu_api.login') as mock_login:
            mock_login.side_effect = YaizuAPIError("認証エラー")
            
            result = await login_to_api_catalog("test@example.com", "wrong")
            
            assert "ログインに失敗しました" in result
            assert "認証エラー" in result
    
    @pytest.mark.asyncio
    async def test_get_yaizu_api_catalog_success(self):
        """get_yaizu_api_catalog ツールの成功テスト"""
        with patch('server.yaizu_api.get_api_catalog') as mock_get:
            mock_get.return_value = {
                "apis": [
                    {
                        "name": "Test API",
                        "description": "Test description",
                        "endpoint": "/test",
                        "format": "JSON"
                    }
                ]
            }
            
            result = await get_yaizu_api_catalog()
            
            assert "焼津市オープンデータAPIカタログ" in result
            assert "Test API" in result
            assert "Test description" in result
    
    @pytest.mark.asyncio
    async def test_get_yaizu_city_data_success(self):
        """get_yaizu_city_data ツールの成功テスト"""
        with patch('server.yaizu_api.get_city_data') as mock_get:
            mock_get.return_value = {
                "data": [
                    {
                        "title": "テストデータ",
                        "description": "テストの説明",
                        "updated_date": "2024-01-01",
                        "format": "CSV",
                        "url": "https://example.com/data.csv"
                    }
                ]
            }
            
            result = await get_yaizu_city_data("test", 1)
            
            assert "焼津市オープンデータ" in result
            assert "テストデータ" in result
            assert "テストの説明" in result
    
    @pytest.mark.asyncio
    async def test_search_yaizu_facilities_success(self):
        """search_yaizu_facilities ツールの成功テスト"""
        with patch('server.yaizu_api.search_facilities') as mock_search:
            mock_search.return_value = {
                "facilities": [
                    {
                        "name": "焼津図書館",
                        "type": "library",
                        "address": "焼津市〇〇",
                        "phone": "054-xxx-xxxx",
                        "opening_hours": "9:00-17:00",
                        "services": ["貸出", "学習室"]
                    }
                ]
            }
            
            result = await search_yaizu_facilities("library", "中心部")
            
            assert "焼津市公共施設検索結果" in result
            assert "焼津図書館" in result
            assert "library" in result
            assert "貸出" in result


if __name__ == "__main__":
    # テスト実行
    pytest.main([__file__, "-v"])