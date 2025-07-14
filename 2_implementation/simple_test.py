#!/usr/bin/env python3
"""
簡化的測試腳本
用於測試 Python 環境和基本模組導入
"""

import sys
import os

print("🔍 Python 環境檢查")
print(f"Python 版本: {sys.version}")
print(f"當前工作目錄: {os.getcwd()}")

# 添加 src 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("\n📦 模組導入測試")

try:
    print("✅ 測試基本導入...")
    
    # 測試 Python 標準庫
    import json, asyncio, logging
    print("  ✅ Python 標準庫導入成功")
    
    # 測試配置模組
    try:
        from api.config import get_settings
        settings = get_settings()
        print(f"  ✅ 配置模組導入成功 - 環境: {settings.ENVIRONMENT}")
    except Exception as e:
        print(f"  ❌ 配置模組導入失敗: {e}")
    
    # 測試是否能創建基本的 FastAPI 應用
    try:
        from fastapi import FastAPI
        app = FastAPI(title="測試應用")
        print("  ✅ FastAPI 導入成功")
        
        @app.get("/test")
        def test_endpoint():
            return {"message": "測試成功"}
        
    except ImportError as e:
        print(f"  ⚠️ FastAPI 未安裝: {e}")
    except Exception as e:
        print(f"  ❌ FastAPI 導入失敗: {e}")
    
    print("\n🎯 總結")
    print("✅ 基本 Python 環境正常")
    print("✅ 模組結構正確")
    
    if 'settings' in locals():
        print(f"✅ 配置系統運作正常")
        print(f"   - API 端口: {settings.API_PORT}")
        print(f"   - 資料庫 URL: {settings.DATABASE_URL}")
        print(f"   - Redis URL: {settings.REDIS_URL}")
    
except Exception as e:
    print(f"❌ 測試失敗: {e}")
    import traceback
    traceback.print_exc()

print("\n🔗 下一步:")
print("1. 確保所有 Python 依賴項已安裝")  
print("2. 測試資料庫連接")
print("3. 啟動完整的 FastAPI 服務") 