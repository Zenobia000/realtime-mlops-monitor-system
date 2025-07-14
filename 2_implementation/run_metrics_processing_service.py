#!/usr/bin/env python3
"""
指標處理服務主程式
Phase 1.4 - 指標處理服務開發
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.logging import RichHandler

# 添加 src 目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.metrics_processor import create_metrics_processor, MetricsProcessor
from src.api.config import get_settings

# 設置 Rich 日誌處理器
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)

app = typer.Typer()

# 全局處理器實例
metrics_processor: MetricsProcessor = None


def setup_signal_handlers():
    """設置信號處理器"""
    def signal_handler(signum, frame):
        logger.info(f"收到信號 {signum}，正在關閉服務...")
        asyncio.create_task(shutdown_service())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def shutdown_service():
    """優雅關閉服務"""
    global metrics_processor
    
    if metrics_processor:
        logger.info("正在停止指標處理服務...")
        await metrics_processor.stop()
        logger.info("✅ 指標處理服務已停止")


def display_service_info():
    """顯示服務信息"""
    settings = get_settings()
    
    info_table = Table(title="🚀 指標處理服務配置")
    info_table.add_column("配置項", style="cyan")
    info_table.add_column("數值", style="magenta")
    
    info_table.add_row("PostgreSQL", settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL)
    info_table.add_row("Redis", settings.REDIS_URL)
    info_table.add_row("RabbitMQ", settings.RABBITMQ_URL)
    info_table.add_row("環境", settings.ENVIRONMENT)
    info_table.add_row("日誌級別", settings.LOG_LEVEL)
    
    console.print(info_table)


@app.command()
def start():
    """啟動指標處理服務"""
    console.print(Panel.fit(
        "🎯 指標處理服務 (Phase 1.4)",
        subtitle="Model API 即時監控系統",
        style="bold blue"
    ))
    
    asyncio.run(_start_service())


async def _start_service():
    """啟動服務的異步實現"""
    global metrics_processor
    
    try:
        # 顯示服務信息
        display_service_info()
        
        # 設置信號處理器
        setup_signal_handlers()
        
        # 初始化處理器
        console.print("\n🚀 初始化指標處理器...")
        metrics_processor = await create_metrics_processor()
        
        # 啟動處理器
        console.print("▶️  啟動指標處理器...")
        start_success = await metrics_processor.start()
        
        if not start_success:
            console.print("❌ 服務啟動失敗")
            return
        
        console.print(Panel.fit(
            "✅ 指標處理服務已啟動\n\n" +
            "🔄 正在處理監控事件...\n" +
            "📊 聚合指標數據中...\n" +
            "💾 自動存儲到數據庫...\n" +
            "🚨 監控告警規則...\n\n" +
            "按 Ctrl+C 停止服務",
            style="bold green"
        ))
        
        # 定期顯示統計信息
        last_stats_time = asyncio.get_event_loop().time()
        
        while True:
            await asyncio.sleep(5)
            
            # 每 30 秒顯示一次統計
            current_time = asyncio.get_event_loop().time()
            if current_time - last_stats_time >= 30:
                await display_periodic_stats()
                last_stats_time = current_time
            
    except KeyboardInterrupt:
        console.print("\n🛑 收到停止信號")
    except Exception as e:
        console.print(f"❌ 服務運行錯誤: {e}")
        logger.exception("服務執行錯誤")
    finally:
        await shutdown_service()


async def display_periodic_stats():
    """定期顯示統計信息"""
    try:
        stats = metrics_processor.get_comprehensive_stats()
        processor_stats = stats.get("processor", {})
        
        # 檢查是否有活躍數據
        events_processed = processor_stats.get("total_events_processed", 0)
        storage_ops = processor_stats.get("total_storage_operations", 0)
        alert_checks = processor_stats.get("total_alert_checks", 0)
        
        if events_processed > 0 or storage_ops > 0:
            console.print(f"\n📈 統計更新: 處理事件 {events_processed}, 存儲 {storage_ops}, 告警檢查 {alert_checks}")
            
            # 顯示當前指標
            current_metrics = await metrics_processor.get_current_metrics()
            overall = current_metrics.get("overall", {})
            
            if overall.get("total_requests", 0) > 0:
                console.print(f"📊 當前指標: QPS={overall.get('qps', 0):.2f}, "
                             f"錯誤率={overall.get('error_rate', 0):.2f}%, "
                             f"平均響應時間={overall.get('avg_response_time', 0):.2f}ms")
            
            # 檢查告警
            active_alerts = metrics_processor.get_active_alerts()
            if active_alerts:
                console.print(f"🚨 活躍告警: {len(active_alerts)} 個")
        
    except Exception as e:
        logger.debug(f"統計顯示錯誤: {e}")


@app.command()
def status():
    """檢查服務狀態"""
    console.print(Panel.fit(
        "📊 指標處理服務狀態檢查",
        style="bold cyan"
    ))
    
    asyncio.run(_check_status())


async def _check_status():
    """檢查狀態的異步實現"""
    try:
        # 嘗試初始化處理器檢查依賴
        console.print("🔍 檢查服務依賴...")
        test_processor = await create_metrics_processor()
        
        # 獲取健康狀態
        health_status = await test_processor.get_health_status()
        
        overall_healthy = health_status.get("overall_healthy", False)
        console.print(f"\n整體健康狀態: {'✅ 健康' if overall_healthy else '❌ 不健康'}")
        
        # 顯示組件狀態
        components = health_status.get("components", {})
        
        status_table = Table(title="組件狀態")
        status_table.add_column("組件", style="cyan")
        status_table.add_column("狀態", style="magenta")
        status_table.add_column("詳情", style="yellow")
        
        for component_name, component_info in components.items():
            healthy = component_info.get("healthy", False)
            status = "✅ 正常" if healthy else "❌ 異常"
            
            # 獲取關鍵統計
            stats = component_info.get("stats", {})
            details = ""
            
            if component_name == "event_consumer":
                details = f"連接: {stats.get('is_connected', False)}, 消費: {stats.get('is_consuming', False)}"
            elif component_name == "storage_manager":
                details = f"PG: {stats.get('is_postgres_connected', False)}, Redis: {stats.get('is_redis_connected', False)}"
            elif component_name == "metrics_aggregator":
                details = f"處理事件: {stats.get('total_events_processed', 0)}"
            elif component_name == "alert_manager":
                details = f"規則: {stats.get('total_rules', 0)}, 活躍告警: {stats.get('active_alerts_count', 0)}"
            
            status_table.add_row(component_name, status, details)
        
        console.print(status_table)
        
        # 停止測試處理器
        await test_processor.stop()
        
    except Exception as e:
        console.print(f"❌ 狀態檢查失敗: {e}")
        logger.exception("狀態檢查錯誤")


@app.command()
def test():
    """運行服務測試"""
    console.print(Panel.fit(
        "🧪 指標處理服務測試",
        style="bold green"
    ))
    
    # 調用測試腳本
    import subprocess
    import sys
    
    try:
        result = subprocess.run([
            sys.executable, "test_metrics_processing.py", "test-basic"
        ], cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            console.print("✅ 測試完成")
        else:
            console.print("❌ 測試失敗")
            
    except Exception as e:
        console.print(f"❌ 測試執行錯誤: {e}")


@app.command()
def config():
    """顯示配置信息"""
    console.print(Panel.fit(
        "⚙️  服務配置信息",
        style="bold yellow"
    ))
    
    settings = get_settings()
    
    config_table = Table(title="環境配置")
    config_table.add_column("配置項", style="cyan")
    config_table.add_column("數值", style="magenta")
    config_table.add_column("說明", style="yellow")
    
    config_table.add_row("環境", settings.ENVIRONMENT, "運行環境")
    config_table.add_row("日誌級別", settings.LOG_LEVEL, "日誌輸出級別")
    config_table.add_row("PostgreSQL", "已配置" if settings.DATABASE_URL else "未配置", "主數據庫")
    config_table.add_row("Redis", "已配置" if settings.REDIS_URL else "未配置", "快取數據庫")
    config_table.add_row("RabbitMQ", "已配置" if settings.RABBITMQ_URL else "未配置", "消息佇列")
    
    console.print(config_table)
    
    # 顯示處理器配置
    processor_table = Table(title="處理器配置")
    processor_table.add_column("參數", style="cyan")
    processor_table.add_column("默認值", style="magenta")
    processor_table.add_column("說明", style="yellow")
    
    processor_table.add_row("處理間隔", "5秒", "定期處理任務間隔")
    processor_table.add_row("存儲間隔", "5秒", "數據存儲間隔")
    processor_table.add_row("告警檢查間隔", "10秒", "告警規則檢查間隔")
    processor_table.add_row("滑動視窗", "60秒/12個5秒子視窗", "指標聚合視窗配置")
    processor_table.add_row("批量寫入", "100條或5秒", "PostgreSQL批量寫入配置")
    processor_table.add_row("Redis TTL", "300秒", "快取過期時間")
    
    console.print(processor_table)


@app.callback()
def main():
    """
    指標處理服務 (Phase 1.4)
    
    Model API 即時監控系統 - 指標處理服務開發
    """
    pass


if __name__ == "__main__":
    app() 