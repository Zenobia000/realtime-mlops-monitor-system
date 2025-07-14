"""
監控攔截器性能測試腳本
驗證監控中間件的性能影響是否符合 WBS 要求 (< 20ms)
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
import aiohttp
import json
from datetime import datetime

# 測試配置
TEST_CONFIG = {
    "base_url": "http://localhost:8002",
    "concurrent_requests": [1, 10, 50, 100],
    "test_endpoints": [
        {"path": "/predict", "method": "POST", "data": {"features": [1.0, 2.0, 3.0]}},
        {"path": "/health", "method": "GET", "data": None},
        {"path": "/models", "method": "GET", "data": None},
        {"path": "/slow_endpoint", "method": "GET", "params": {"delay": 0.1}},
    ],
    "requests_per_test": 100,
    "timeout_seconds": 30
}


class PerformanceTestResult:
    """性能測試結果"""
    
    def __init__(self, endpoint: str, concurrent_users: int):
        self.endpoint = endpoint
        self.concurrent_users = concurrent_users
        self.response_times: List[float] = []
        self.status_codes: List[int] = []
        self.errors: List[str] = []
        self.start_time: float = 0
        self.end_time: float = 0
    
    def add_result(self, response_time: float, status_code: int, error: str = None):
        """添加單個請求結果"""
        self.response_times.append(response_time)
        self.status_codes.append(status_code)
        if error:
            self.errors.append(error)
    
    def get_statistics(self) -> Dict[str, Any]:
        """計算統計數據"""
        if not self.response_times:
            return {"error": "No response times recorded"}
        
        total_time = self.end_time - self.start_time
        successful_requests = sum(1 for code in self.status_codes if 200 <= code < 300)
        
        return {
            "endpoint": self.endpoint,
            "concurrent_users": self.concurrent_users,
            "total_requests": len(self.response_times),
            "successful_requests": successful_requests,
            "failed_requests": len(self.response_times) - successful_requests,
            "success_rate": (successful_requests / len(self.response_times)) * 100,
            "total_test_time_seconds": total_time,
            "requests_per_second": len(self.response_times) / total_time if total_time > 0 else 0,
            "response_times_ms": {
                "min": min(self.response_times) * 1000,
                "max": max(self.response_times) * 1000,
                "mean": statistics.mean(self.response_times) * 1000,
                "median": statistics.median(self.response_times) * 1000,
                "p95": statistics.quantiles(self.response_times, n=20)[18] * 1000,  # 95th percentile
                "p99": statistics.quantiles(self.response_times, n=100)[98] * 1000,  # 99th percentile
            },
            "errors": self.errors[:10],  # 只顯示前 10 個錯誤
            "middleware_overhead_check": {
                "mean_response_time_ms": statistics.mean(self.response_times) * 1000,
                "meets_requirement": statistics.mean(self.response_times) * 1000 < 20,  # WBS 要求 < 20ms
                "requirement": "< 20ms additional overhead"
            }
        }


async def make_request(session: aiohttp.ClientSession, endpoint_config: Dict[str, Any]) -> tuple:
    """
    發送單個 HTTP 請求
    
    Returns:
        tuple: (response_time, status_code, error_message)
    """
    url = f"{TEST_CONFIG['base_url']}{endpoint_config['path']}"
    method = endpoint_config['method']
    data = endpoint_config.get('data')
    params = endpoint_config.get('params')
    
    start_time = time.perf_counter()
    
    try:
        if method == "GET":
            async with session.get(url, params=params, timeout=TEST_CONFIG['timeout_seconds']) as response:
                await response.text()  # 確保完全讀取響應
                response_time = time.perf_counter() - start_time
                return response_time, response.status, None
        
        elif method == "POST":
            headers = {"Content-Type": "application/json"}
            async with session.post(
                url, 
                json=data, 
                headers=headers,
                timeout=TEST_CONFIG['timeout_seconds']
            ) as response:
                await response.text()
                response_time = time.perf_counter() - start_time
                return response_time, response.status, None
                
    except asyncio.TimeoutError:
        response_time = time.perf_counter() - start_time
        return response_time, 408, "Request timeout"
    except Exception as e:
        response_time = time.perf_counter() - start_time
        return response_time, 500, str(e)


async def run_concurrent_test(
    endpoint_config: Dict[str, Any], 
    concurrent_users: int, 
    requests_per_user: int
) -> PerformanceTestResult:
    """
    運行並發性能測試
    
    Args:
        endpoint_config: 端點配置
        concurrent_users: 併發用戶數
        requests_per_user: 每個用戶的請求數
        
    Returns:
        PerformanceTestResult: 測試結果
    """
    result = PerformanceTestResult(endpoint_config['path'], concurrent_users)
    
    print(f"🔄 測試 {endpoint_config['path']} - {concurrent_users} 併發用戶, 每用戶 {requests_per_user} 請求")
    
    async with aiohttp.ClientSession() as session:
        result.start_time = time.perf_counter()
        
        # 創建所有任務
        tasks = []
        for user in range(concurrent_users):
            for request_num in range(requests_per_user):
                task = asyncio.create_task(make_request(session, endpoint_config))
                tasks.append(task)
        
        # 執行所有任務
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        result.end_time = time.perf_counter()
        
        # 處理結果
        for response in responses:
            if isinstance(response, Exception):
                result.add_result(0, 500, str(response))
            else:
                response_time, status_code, error = response
                result.add_result(response_time, status_code, error)
    
    return result


async def test_monitoring_overhead():
    """
    測試監控中間件的性能開銷
    
    這個測試會向測試 API 發送請求，並測量響應時間
    以驗證監控中間件是否符合 < 20ms 額外開銷的要求
    """
    print("🚀 開始監控性能測試")
    print(f"📊 測試目標: 驗證監控中間件額外開銷 < 20ms")
    print(f"🎯 測試服務: {TEST_CONFIG['base_url']}")
    print("-" * 60)
    
    all_results = []
    
    # 測試每個端點
    for endpoint_config in TEST_CONFIG['test_endpoints']:
        print(f"\n📍 測試端點: {endpoint_config['path']}")
        
        # 測試不同併發級別
        for concurrent_users in TEST_CONFIG['concurrent_requests']:
            requests_per_user = max(1, TEST_CONFIG['requests_per_test'] // concurrent_users)
            
            try:
                result = await run_concurrent_test(
                    endpoint_config, 
                    concurrent_users, 
                    requests_per_user
                )
                
                stats = result.get_statistics()
                all_results.append(stats)
                
                # 輸出關鍵指標
                print(f"  併發 {concurrent_users:3d}: "
                      f"平均 {stats['response_times_ms']['mean']:6.2f}ms, "
                      f"P95 {stats['response_times_ms']['p95']:6.2f}ms, "
                      f"成功率 {stats['success_rate']:5.1f}%")
                
                # 檢查是否符合性能要求
                if stats['response_times_ms']['mean'] > 20:
                    print(f"  ⚠️ 警告: 平均響應時間超過 20ms 要求")
                
            except Exception as e:
                print(f"  ❌ 測試失敗: {e}")
    
    # 生成總結報告
    print("\n" + "=" * 60)
    print("📊 測試總結報告")
    print("=" * 60)
    
    generate_summary_report(all_results)
    
    # 保存詳細結果到文件
    save_results_to_file(all_results)


def generate_summary_report(results: List[Dict[str, Any]]):
    """生成測試總結報告"""
    if not results:
        print("❌ 沒有測試結果")
        return
    
    # 計算整體統計
    all_response_times = []
    overhead_violations = []
    high_concurrency_results = []
    
    for result in results:
        if 'response_times_ms' in result:
            all_response_times.append(result['response_times_ms']['mean'])
            
            # 檢查是否違反 20ms 要求
            if result['response_times_ms']['mean'] > 20:
                overhead_violations.append({
                    'endpoint': result['endpoint'],
                    'concurrent_users': result['concurrent_users'],
                    'mean_response_time': result['response_times_ms']['mean']
                })
            
            # 收集高併發測試結果
            if result['concurrent_users'] >= 50:
                high_concurrency_results.append(result)
    
    if all_response_times:
        print(f"📈 整體性能指標:")
        print(f"   平均響應時間: {statistics.mean(all_response_times):.2f}ms")
        print(f"   最低響應時間: {min(all_response_times):.2f}ms")
        print(f"   最高響應時間: {max(all_response_times):.2f}ms")
    
    # 檢查性能要求符合情況
    if overhead_violations:
        print(f"\n⚠️ 性能要求違反 ({len(overhead_violations)} 項):")
        for violation in overhead_violations:
            print(f"   {violation['endpoint']} (併發 {violation['concurrent_users']}): "
                  f"{violation['mean_response_time']:.2f}ms > 20ms")
    else:
        print(f"\n✅ 所有測試都符合 < 20ms 性能要求")
    
    # 高併發性能分析
    if high_concurrency_results:
        print(f"\n🚀 高併發性能分析:")
        for result in high_concurrency_results:
            print(f"   {result['endpoint']} (併發 {result['concurrent_users']}): "
                  f"QPS {result['requests_per_second']:.1f}, "
                  f"成功率 {result['success_rate']:.1f}%")


def save_results_to_file(results: List[Dict[str, Any]]):
    """保存測試結果到文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"monitoring_performance_test_{timestamp}.json"
    
    test_summary = {
        "test_time": datetime.now().isoformat(),
        "test_config": TEST_CONFIG,
        "results": results,
        "summary": {
            "total_tests": len(results),
            "wbs_requirement": "< 20ms additional overhead",
            "test_passed": all(
                r.get('response_times_ms', {}).get('mean', 999) < 20 
                for r in results if 'response_times_ms' in r
            )
        }
    }
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(test_summary, f, indent=2, ensure_ascii=False)
        print(f"\n💾 詳細結果已保存至: {filename}")
    except Exception as e:
        print(f"\n❌ 保存結果失敗: {e}")


async def test_api_availability():
    """測試 API 服務是否可用"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{TEST_CONFIG['base_url']}/health", timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ 測試 API 服務可用: {data.get('service', 'unknown')}")
                    return True
                else:
                    print(f"❌ API 服務回應異常: HTTP {response.status}")
                    return False
    except Exception as e:
        print(f"❌ 無法連接測試 API 服務: {e}")
        print(f"💡 請確保測試服務正在運行: python test_model_api.py")
        return False


if __name__ == "__main__":
    print("🔍 Model API 監控性能測試")
    print(f"📅 測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 WBS 要求: 監控代理延遲 < 20ms")
    
    async def main():
        # 檢查 API 可用性
        if not await test_api_availability():
            return
        
        # 執行性能測試
        await test_monitoring_overhead()
        
        print("\n✅ 測試完成")
    
    # 運行測試
    asyncio.run(main()) 