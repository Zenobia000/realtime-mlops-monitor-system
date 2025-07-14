#!/usr/bin/env python3
"""
API 端點測試腳本
驗證 Phase 2.1 後端 API 端點開發是否完成
"""

import asyncio
import aiohttp
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API 配置
API_BASE_URL = "http://localhost:8000"
API_KEY = "monitor_api_key_dev_2025"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# 測試配置
TEST_TIMEOUT = 10  # 每個請求的超時時間
MAX_RETRIES = 3  # 最大重試次數
RETRY_DELAY = 2  # 重試間隔（秒）

# 測試端點配置
TEST_ENDPOINTS = [
    # 基礎端點
    {"url": "/", "method": "GET", "description": "根目錄", "auth_required": False, "expected_status": 200},
    {"url": "/health", "method": "GET", "description": "健康檢查", "auth_required": False, "expected_status": 200},
    {"url": "/v1", "method": "GET", "description": "API v1 信息", "auth_required": False, "expected_status": 200},
    
    # 指標相關 API
    {"url": "/v1/metrics/summary", "method": "GET", "description": "指標摘要", "auth_required": True, "expected_status": 200},
    {"url": "/v1/metrics/historical", "method": "GET", "description": "歷史指標", "auth_required": True, "expected_status": 200},
    {"url": "/v1/metrics/real-time", "method": "GET", "description": "實時指標", "auth_required": True, "expected_status": 200},
    {"url": "/v1/metrics/services", "method": "GET", "description": "監控服務列表", "auth_required": True, "expected_status": 200},
    
    # 告警相關 API
    {"url": "/v1/alerts/", "method": "GET", "description": "告警列表", "auth_required": True, "expected_status": 200},
    {"url": "/v1/alerts/active", "method": "GET", "description": "活躍告警", "auth_required": True, "expected_status": 200},
    
    # 服務相關 API
    {"url": "/v1/services/", "method": "GET", "description": "服務概覽", "auth_required": True, "expected_status": 200},
    
    # 儀表板相關 API
    {"url": "/v1/dashboards/overview", "method": "GET", "description": "儀表板概覽", "auth_required": True, "expected_status": 200},
    {"url": "/v1/dashboards/metrics/timeseries?metric=qps", "method": "GET", "description": "時間序列數據", "auth_required": True, "expected_status": 200},
    {"url": "/v1/dashboards/realtime", "method": "GET", "description": "實時儀表板", "auth_required": True, "expected_status": 200},
    
    # 錯誤處理測試
    {"url": "/v1/nonexistent", "method": "GET", "description": "不存在的端點", "auth_required": True, "expected_status": 404},
]

async def wait_for_service_ready(session: aiohttp.ClientSession, max_wait: int = 30) -> bool:
    """
    等待服務準備就緒
    """
    logger.info("🔍 檢查服務可用性...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            async with session.get(f"{API_BASE_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status in [200, 503]:  # 服務可訪問（即使不健康）
                    logger.info("✅ 服務已可訪問")
                    return True
        except Exception as e:
            logger.debug(f"服務檢查失敗: {e}")
            await asyncio.sleep(1)
    
    logger.error("❌ 服務在指定時間內未能響應")
    return False

async def make_request_with_retry(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    max_retries: int = MAX_RETRIES
) -> Dict[str, Any]:
    """
    帶重試邏輯的 HTTP 請求
    """
    full_url = f"{API_BASE_URL}{url}"
    
    for attempt in range(max_retries + 1):
        try:
            start_time = time.time()
            
            async with session.request(
                method=method,
                url=full_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=TEST_TIMEOUT)
            ) as response:
                response_time = (time.time() - start_time) * 1000  # 轉換為毫秒
                
                try:
                    response_data = await response.json()
                except:
                    response_data = await response.text()
                
                return {
                    "status_code": response.status,
                    "response_time_ms": round(response_time, 2),
                    "response_data": response_data,
                    "error": None
                }
                
        except Exception as e:
            if attempt < max_retries:
                logger.debug(f"請求失敗 (嘗試 {attempt + 1}/{max_retries + 1}): {e}")
                await asyncio.sleep(RETRY_DELAY)
                continue
            else:
                return {
                    "status_code": None,
                    "response_time_ms": 0,
                    "response_data": None,
                    "error": str(e)
                }
    
    return {
        "status_code": None,
        "response_time_ms": 0,
        "response_data": None,
        "error": "最大重試次數已達到"
    }

async def test_endpoint(session: aiohttp.ClientSession, endpoint_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    測試單個端點
    """
    url = endpoint_config["url"]
    method = endpoint_config["method"]
    description = endpoint_config["description"]
    auth_required = endpoint_config["auth_required"]
    expected_status = endpoint_config["expected_status"]
    
    # 準備請求標頭
    headers = {}
    if auth_required:
        headers["X-API-Key"] = API_KEY
    
    # 發送請求
    result = await make_request_with_retry(session, method, url, headers)
    
    # 檢查結果
    success = (
        result["error"] is None and 
        result["status_code"] == expected_status
    )
    
    # 記錄結果
    if success:
        logger.info(f"✅ {method} {url} - {result['status_code']} ({result['response_time_ms']:.2f}ms)")
    elif result["error"]:
        logger.error(f"❌ {method} {url} - 異常: {result['error']}")
    else:
        logger.error(f"❌ {method} {url} - {result['status_code']} (預期: {expected_status})")
    
    return {
        "endpoint": url,
        "method": method,
        "description": description,
        "status_code": result["status_code"],
        "expected_status": expected_status,
        "success": success,
        "response_time_ms": result["response_time_ms"],
        "response_data": result["response_data"],
        "error": result["error"]
    }

async def test_api_key_auth(session: aiohttp.ClientSession) -> bool:
    """
    測試 API Key 認證
    """
    logger.info("🔐 測試 API Key 認證...")
    
    # 測試無 API Key 的請求
    result = await make_request_with_retry(session, "GET", "/v1/metrics/summary")
    
    if result["status_code"] == 401:
        logger.info("✅ API Key 認證正常工作")
        return True
    else:
        logger.error(f"❌ API Key 認證異常: {result}")
        return False

async def run_tests() -> Dict[str, Any]:
    """
    運行所有測試
    """
    logger.info("🚀 開始 API 端點測試...")
    
    # 創建 HTTP 會話
    connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300, use_dns_cache=True)
    timeout = aiohttp.ClientTimeout(total=TEST_TIMEOUT)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # 等待服務準備就緒
        if not await wait_for_service_ready(session):
            logger.error("❌ 服務未能在指定時間內準備就緒，退出測試")
            return {
                "test_summary": {
                    "total_tests": 0,
                    "successful_tests": 0,
                    "failed_tests": 0,
                    "success_rate": 0.0,
                    "avg_response_time_ms": 0.0
                },
                "status_distribution": {},
                "test_results": [],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # 運行端點測試
        test_results = []
        total_response_time = 0
        
        for endpoint_config in TEST_ENDPOINTS:
            # 根據端點類型分組輸出
            if endpoint_config["url"].startswith("/v1/metrics"):
                if len([r for r in test_results if r["endpoint"].startswith("/v1/metrics")]) == 0:
                    logger.info("\n📊 測試指標相關 API...")
            elif endpoint_config["url"].startswith("/v1/alerts"):
                if len([r for r in test_results if r["endpoint"].startswith("/v1/alerts")]) == 0:
                    logger.info("\n🚨 測試告警相關 API...")
            elif endpoint_config["url"].startswith("/v1/services"):
                if len([r for r in test_results if r["endpoint"].startswith("/v1/services")]) == 0:
                    logger.info("\n🔧 測試服務相關 API...")
            elif endpoint_config["url"].startswith("/v1/dashboards"):
                if len([r for r in test_results if r["endpoint"].startswith("/v1/dashboards")]) == 0:
                    logger.info("\n📈 測試儀表板相關 API...")
            elif endpoint_config["description"] == "不存在的端點":
                logger.info("\n🔍 測試錯誤處理...")
            
            result = await test_endpoint(session, endpoint_config)
            test_results.append(result)
            total_response_time += result["response_time_ms"]
        
        # 測試認證
        auth_test_success = await test_api_key_auth(session)
    
    # 統計結果
    successful_tests = sum(1 for r in test_results if r["success"])
    failed_tests = len(test_results) - successful_tests
    success_rate = (successful_tests / len(test_results)) * 100 if test_results else 0
    avg_response_time = total_response_time / len(test_results) if test_results else 0
    
    # 狀態碼分佈
    status_distribution = {}
    for result in test_results:
        if result["error"]:
            status_key = "ERROR"
        else:
            status_key = str(result["status_code"])
        
        status_distribution[status_key] = status_distribution.get(status_key, 0) + 1
    
    return {
        "test_summary": {
            "total_tests": len(test_results),
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": round(success_rate, 2),
            "avg_response_time_ms": round(avg_response_time, 2)
        },
        "status_distribution": status_distribution,
        "test_results": test_results,
        "timestamp": datetime.utcnow().isoformat()
    }

def print_test_summary(results: Dict[str, Any]):
    """
    打印測試摘要
    """
    summary = results["test_summary"]
    
    print("\n" + "=" * 60)
    print("📋 測試報告")
    print("=" * 60)
    print(f"📊 總測試數: {summary['total_tests']}")
    print(f"✅ 成功: {summary['successful_tests']}")
    print(f"❌ 失敗: {summary['failed_tests']}")
    print(f"📈 成功率: {summary['success_rate']:.2f}%")
    print(f"⚡ 平均響應時間: {summary['avg_response_time_ms']:.2f}ms")
    
    print(f"\n📊 狀態碼分佈:")
    for status, count in results["status_distribution"].items():
        print(f"  {status}: {count}")
    
    # 列出失敗的測試
    failed_tests = [r for r in results["test_results"] if not r["success"]]
    if failed_tests:
        print(f"\n❌ 失敗的測試:")
        for test in failed_tests:
            if test["error"]:
                print(f"  {test['method']} {test['endpoint']}: {test['error']}")
            else:
                print(f"  {test['method']} {test['endpoint']}: 狀態碼不匹配: {test['status_code']} != {test['expected_status']}")
    
    # 保存詳細報告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"api_test_report_{timestamp}.json"
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 詳細報告已保存至: {report_filename}")
    
    # 評估整體狀態
    if summary["success_rate"] >= 90:
        print(f"\n🎉 Phase 2.1 後端 API 端點開發 - 通過")
        print(f"   成功率: {summary['success_rate']:.2f}% (≥90%)")
    elif summary["success_rate"] >= 80:
        print(f"\n⚠️ Phase 2.1 後端 API 端點開發 - 基本通過")
        print(f"   成功率: {summary['success_rate']:.2f}% (≥80%)")
    else:
        print(f"\n⚠️ Phase 2.1 後端 API 端點開發 - 需要修復")
        print(f"   成功率: {summary['success_rate']:.2f}% (<80%)")

async def main():
    """
    主函數
    """
    print("=" * 60)
    print("🧪 Model API 監控系統 - Phase 2.1 API 端點測試")
    print("=" * 60)
    
    try:
        results = await run_tests()
        print_test_summary(results)
    except Exception as e:
        logger.error(f"測試運行時發生錯誤: {e}")
        print(f"\n❌ 測試失敗: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 