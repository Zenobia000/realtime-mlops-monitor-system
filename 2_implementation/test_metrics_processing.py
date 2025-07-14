#!/usr/bin/env python3
"""
指標處理服務測試腳本
測試 Phase 1.4 開發的指標處理服務功能
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live

from src.services.metrics_processor import MetricsProcessor, create_metrics_processor
from src.components.metrics_event import MetricsEvent, EventType
from src.components.event_publisher import EventPublisher

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()
app = typer.Typer()

# 全局變量
metrics_processor: MetricsProcessor = None


async def create_test_events(event_publisher: EventPublisher, count: int = 20):
    """創建測試事件"""
    services = ["model-api-v1", "model-api-v2", "recommendation-api"]
    endpoints = ["/predict", "/batch_predict", "/health", "/metrics"]
    
    console.print(f"🚀 創建 {count} 個測試事件...")
    
    for i in range(count):
        # 隨機選擇服務和端點
        service_name = services[i % len(services)]
        endpoint = endpoints[i % len(endpoints)]
        
        # 模擬不同的響應時間和狀態碼
        response_time = 50 + (i * 10) % 500  # 50-550ms
        status_code = 200 if i % 10 != 9 else 500  # 10% 錯誤率
        
        # 創建響應事件
        event = MetricsEvent.from_request_response(
            service_name=service_name,
            endpoint=endpoint,
            method="POST",
            status_code=status_code,
            response_time_ms=response_time,
            request_size=1024,
            response_size=2048
        )
        
        # 發送事件
        await event_publisher.publish_metrics_event(event)
        console.print(f"  📤 事件 {i+1}: {service_name}{endpoint} - {response_time}ms - {status_code}")
        
        # 短暫延遲模擬真實場景
        await asyncio.sleep(0.1)
    
    console.print("✅ 測試事件創建完成")


async def test_metrics_aggregation():
    """測試指標聚合功能"""
    console.print("\n📊 測試指標聚合功能...")
    
    # 等待一些處理時間
    await asyncio.sleep(3)
    
    # 獲取當前聚合指標
    current_metrics = await metrics_processor.get_current_metrics()
    
    if current_metrics and current_metrics.get("overall", {}).get("total_requests", 0) > 0:
        console.print("✅ 指標聚合功能正常")
        
        # 顯示聚合結果
        overall = current_metrics["overall"]
        table = Table(title="聚合指標結果")
        table.add_column("指標", style="cyan")
        table.add_column("數值", style="magenta")
        
        table.add_row("總請求數", str(overall.get("total_requests", 0)))
        table.add_row("錯誤數", str(overall.get("total_errors", 0)))
        table.add_row("QPS", f"{overall.get('qps', 0):.2f}")
        table.add_row("錯誤率", f"{overall.get('error_rate', 0):.2f}%")
        table.add_row("平均響應時間", f"{overall.get('avg_response_time', 0):.2f}ms")
        table.add_row("P95 響應時間", f"{overall.get('p95_response_time', 0):.2f}ms")
        table.add_row("P99 響應時間", f"{overall.get('p99_response_time', 0):.2f}ms")
        
        console.print(table)
        
        return True
    else:
        console.print("❌ 指標聚合功能異常：沒有收到數據")
        return False


async def test_storage_functionality():
    """測試存儲功能"""
    console.print("\n💾 測試存儲功能...")
    
    # 等待存儲操作
    await asyncio.sleep(6)
    
    # 檢查 Redis 快取
    cached_metrics = await metrics_processor.get_cached_metrics("overall")
    
    if cached_metrics:
        console.print("✅ Redis 快取功能正常")
        console.print(f"  快取數據: QPS={cached_metrics.get('qps', 0):.2f}, "
                     f"錯誤率={cached_metrics.get('error_rate', 0):.2f}%")
        return True
    else:
        console.print("❌ Redis 快取功能異常")
        return False


async def test_alert_functionality():
    """測試告警功能"""
    console.print("\n🚨 測試告警功能...")
    
    # 獲取告警摘要
    alert_summary = metrics_processor.get_alert_summary()
    
    console.print(f"  告警規則數: {alert_summary.get('total_rules', 0)}")
    console.print(f"  啟用規則數: {alert_summary.get('enabled_rules', 0)}")
    console.print(f"  活躍告警數: {alert_summary.get('active_alerts_count', 0)}")
    
    # 檢查是否有告警被觸發
    active_alerts = metrics_processor.get_active_alerts()
    
    if active_alerts:
        console.print(f"⚠️  檢測到 {len(active_alerts)} 個活躍告警:")
        for alert in active_alerts:
            console.print(f"    - {alert['message']}")
    else:
        console.print("✅ 沒有活躍告警")
    
    return True


async def test_health_status():
    """測試健康狀態檢查"""
    console.print("\n🏥 測試健康狀態檢查...")
    
    health_status = await metrics_processor.get_health_status()
    
    overall_healthy = health_status.get("overall_healthy", False)
    console.print(f"  整體健康狀態: {'✅ 健康' if overall_healthy else '❌ 不健康'}")
    
    # 顯示組件狀態
    components = health_status.get("components", {})
    for component_name, component_info in components.items():
        healthy = component_info.get("healthy", False)
        status_icon = "✅" if healthy else "❌"
        console.print(f"    {component_name}: {status_icon}")
    
    return overall_healthy


def display_comprehensive_stats():
    """顯示綜合統計信息"""
    console.print("\n📈 綜合統計信息")
    
    stats = metrics_processor.get_comprehensive_stats()
    
    # 處理器統計
    processor_stats = stats.get("processor", {})
    table = Table(title="處理器統計")
    table.add_column("項目", style="cyan")
    table.add_column("數值", style="magenta")
    
    table.add_row("總處理事件數", str(processor_stats.get("total_events_processed", 0)))
    table.add_row("存儲操作數", str(processor_stats.get("total_storage_operations", 0)))
    table.add_row("告警檢查數", str(processor_stats.get("total_alert_checks", 0)))
    table.add_row("錯誤次數", str(processor_stats.get("errors_count", 0)))
    table.add_row("運行時間", f"{processor_stats.get('runtime_seconds', 0):.1f}秒")
    table.add_row("事件處理率", f"{processor_stats.get('events_per_second', 0):.2f}/秒")
    
    console.print(table)
    
    # 組件統計
    components_stats = stats.get("components", {})
    for component_name, component_stats in components_stats.items():
        if component_stats:
            console.print(f"\n{component_name.upper()} 統計:")
            for key, value in component_stats.items():
                if isinstance(value, (int, float)):
                    console.print(f"  {key}: {value}")


async def run_performance_test(duration_seconds: int = 30, events_per_second: int = 10):
    """運行性能測試"""
    console.print(f"\n⚡ 性能測試: {duration_seconds}秒, {events_per_second} events/秒")
    
    event_publisher = EventPublisher()
    await event_publisher.connect()
    
    start_time = time.time()
    total_events = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("發送事件中...", total=duration_seconds * events_per_second)
        
        while time.time() - start_time < duration_seconds:
            # 批量發送事件
            batch_size = min(events_per_second, 50)
            
            for i in range(batch_size):
                service_name = f"test-service-{i % 3}"
                endpoint = f"/api/test/{i % 5}"
                response_time = 50 + (i * 5) % 200
                status_code = 200 if i % 20 != 19 else 500  # 5% 錯誤率
                
                event = MetricsEvent.from_request_response(
                    service_name=service_name,
                    endpoint=endpoint,
                    method="POST",
                    status_code=status_code,
                    response_time_ms=response_time
                )
                
                await event_publisher.publish_metrics_event(event)
                total_events += 1
                progress.advance(task)
            
            await asyncio.sleep(1)  # 每秒發送一批
    
    await event_publisher.disconnect()
    
    # 等待處理完成
    await asyncio.sleep(5)
    
    end_time = time.time()
    actual_duration = end_time - start_time
    actual_rate = total_events / actual_duration
    
    console.print(f"✅ 性能測試完成:")
    console.print(f"  總事件數: {total_events}")
    console.print(f"  實際發送率: {actual_rate:.2f} events/秒")
    console.print(f"  實際測試時間: {actual_duration:.1f}秒")
    
    # 顯示處理器性能
    processor_stats = metrics_processor.get_stats()
    processing_rate = processor_stats.get("events_per_second", 0)
    console.print(f"  處理器處理率: {processing_rate:.2f} events/秒")


@app.command()
def test_basic():
    """基礎功能測試"""
    console.print(Panel.fit(
        "🧪 指標處理服務基礎功能測試",
        style="bold blue"
    ))
    
    asyncio.run(_test_basic())


async def _test_basic():
    """基礎測試的異步實現"""
    global metrics_processor
    
    try:
        # 初始化處理器
        console.print("🚀 初始化指標處理器...")
        metrics_processor = await create_metrics_processor()
        
        # 啟動處理器
        console.print("▶️  啟動指標處理器...")
        await metrics_processor.start()
        
        # 創建事件發送器
        event_publisher = EventPublisher()
        await event_publisher.connect()
        
        # 創建測試事件
        await create_test_events(event_publisher, 20)
        
        # 關閉事件發送器
        await event_publisher.disconnect()
        
        # 測試各項功能
        tests_passed = 0
        total_tests = 4
        
        if await test_metrics_aggregation():
            tests_passed += 1
        
        if await test_storage_functionality():
            tests_passed += 1
        
        if await test_alert_functionality():
            tests_passed += 1
        
        if await test_health_status():
            tests_passed += 1
        
        # 顯示統計信息
        display_comprehensive_stats()
        
        # 測試結果
        console.print(f"\n🏆 測試結果: {tests_passed}/{total_tests} 通過")
        
        if tests_passed == total_tests:
            console.print(Panel.fit("✅ 所有測試通過！", style="bold green"))
        else:
            console.print(Panel.fit(f"⚠️  {total_tests - tests_passed} 個測試失敗", style="bold yellow"))
        
    except Exception as e:
        console.print(f"❌ 測試過程中發生錯誤: {e}")
        logger.exception("測試執行錯誤")
    finally:
        # 清理資源
        if metrics_processor:
            console.print("🧹 清理資源...")
            await metrics_processor.stop()


@app.command()
def test_performance(
    duration: int = typer.Option(30, help="測試持續時間(秒)"),
    rate: int = typer.Option(10, help="每秒事件數")
):
    """性能測試"""
    console.print(Panel.fit(
        "⚡ 指標處理服務性能測試",
        style="bold yellow"
    ))
    
    asyncio.run(_test_performance(duration, rate))


async def _test_performance(duration_seconds: int, events_per_second: int):
    """性能測試的異步實現"""
    global metrics_processor
    
    try:
        # 初始化和啟動處理器
        console.print("🚀 初始化指標處理器...")
        metrics_processor = await create_metrics_processor()
        await metrics_processor.start()
        
        # 運行性能測試
        await run_performance_test(duration_seconds, events_per_second)
        
        # 等待處理完成
        console.print("⏳ 等待處理完成...")
        await asyncio.sleep(10)
        
        # 顯示最終統計
        display_comprehensive_stats()
        
        # 檢查健康狀態
        await test_health_status()
        
    except Exception as e:
        console.print(f"❌ 性能測試過程中發生錯誤: {e}")
        logger.exception("性能測試執行錯誤")
    finally:
        if metrics_processor:
            await metrics_processor.stop()


@app.command()
def monitor():
    """實時監控模式"""
    console.print(Panel.fit(
        "📊 指標處理服務實時監控",
        style="bold cyan"
    ))
    
    asyncio.run(_monitor())


async def _monitor():
    """實時監控的異步實現"""
    global metrics_processor
    
    try:
        # 初始化和啟動處理器
        metrics_processor = await create_metrics_processor()
        await metrics_processor.start()
        
        console.print("🔄 進入實時監控模式 (按 Ctrl+C 退出)")
        
        def create_live_table():
            """創建實時表格"""
            current_metrics = asyncio.create_task(metrics_processor.get_current_metrics())
            
            try:
                metrics = current_metrics.result() if current_metrics.done() else {}
                overall = metrics.get("overall", {})
                
                table = Table(title="實時指標監控")
                table.add_column("指標", style="cyan")
                table.add_column("數值", style="magenta")
                table.add_column("狀態", style="green")
                
                table.add_row("QPS", f"{overall.get('qps', 0):.2f}", "📈")
                table.add_row("錯誤率", f"{overall.get('error_rate', 0):.2f}%", "📊")
                table.add_row("平均響應時間", f"{overall.get('avg_response_time', 0):.2f}ms", "⏱️")
                table.add_row("P95 響應時間", f"{overall.get('p95_response_time', 0):.2f}ms", "📏")
                table.add_row("總請求數", str(overall.get('total_requests', 0)), "📊")
                
                # 處理器狀態
                processor_stats = metrics_processor.get_stats()
                table.add_row("處理事件數", str(processor_stats.get('total_events_processed', 0)), "🔄")
                table.add_row("事件處理率", f"{processor_stats.get('events_per_second', 0):.2f}/秒", "⚡")
                
                return table
            except:
                return Table(title="載入中...")
        
        # 實時監控循環
        with Live(create_live_table(), refresh_per_second=2, console=console) as live:
            while True:
                live.update(create_live_table())
                await asyncio.sleep(0.5)
                
    except KeyboardInterrupt:
        console.print("\n👋 退出監控模式")
    except Exception as e:
        console.print(f"❌ 監控過程中發生錯誤: {e}")
        logger.exception("監控執行錯誤")
    finally:
        if metrics_processor:
            await metrics_processor.stop()


if __name__ == "__main__":
    app() 