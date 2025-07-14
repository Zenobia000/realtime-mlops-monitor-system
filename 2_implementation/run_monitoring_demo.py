#!/usr/bin/env python3
"""
監控系統演示啟動腳本
快速啟動和測試 Model API 監控功能
"""

import asyncio
import subprocess
import time
import sys
import os
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
import httpx

app = typer.Typer(help="Model API 監控系統演示工具")
console = Console()

# 配置
DEMO_CONFIG = {
    "api_port": 8002,
    "api_url": "http://localhost:8002",
    "rabbitmq_management": "http://localhost:15672",
    "required_services": ["rabbitmq", "postgres", "redis"]
}


def check_service_status(service_name: str, port: int) -> bool:
    """檢查服務是否在指定端口運行"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            return result == 0
    except:
        return False


def check_dependencies():
    """檢查 Python 依賴是否已安裝"""
    try:
        import fastapi
        import aio_pika
        import aiohttp
        return True
    except ImportError as e:
        console.print(f"❌ 缺少依賴: {e}", style="red")
        console.print("💡 請運行: pip install -r requirements.txt", style="yellow")
        return False


@app.command()
def status():
    """檢查監控系統各組件狀態"""
    console.print(Panel.fit("🔍 監控系統狀態檢查", style="blue"))
    
    # 檢查依賴
    console.print("\n📦 Python 依賴檢查:")
    if check_dependencies():
        console.print("  ✅ 所有依賴已安裝", style="green")
    else:
        console.print("  ❌ 依賴不完整", style="red")
        return
    
    # 檢查外部服務
    console.print("\n🔧 外部服務狀態:")
    services_status = {
        "PostgreSQL": check_service_status("postgres", 5432),
        "RabbitMQ": check_service_status("rabbitmq", 5672),
        "RabbitMQ Management": check_service_status("rabbitmq", 15672),
        "Redis": check_service_status("redis", 6379),
    }
    
    for service, status in services_status.items():
        icon = "✅" if status else "❌"
        style = "green" if status else "red"
        console.print(f"  {icon} {service}", style=style)
    
    # 檢查測試 API
    console.print("\n🎯 測試 API 狀態:")
    api_running = check_service_status("api", DEMO_CONFIG["api_port"])
    if api_running:
        console.print(f"  ✅ Model API 服務運行中 (端口 {DEMO_CONFIG['api_port']})", style="green")
    else:
        console.print(f"  ❌ Model API 服務未運行", style="red")
    
    # 總結
    all_ready = all(services_status.values()) and api_running
    if all_ready:
        console.print("\n🎉 系統已就緒，可以開始演示！", style="bold green")
    else:
        console.print("\n⚠️ 部分服務未就緒，請先啟動相關服務", style="yellow")


@app.command()
def start_services():
    """使用 Docker 啟動必要的外部服務"""
    console.print(Panel.fit("🚀 啟動外部服務", style="blue"))
    
    services = [
        {
            "name": "PostgreSQL", 
            "cmd": ["docker", "run", "-d", "--name", "monitoring-postgres", 
                   "-p", "5432:5432", "-e", "POSTGRES_PASSWORD=password", "postgres:13"]
        },
        {
            "name": "RabbitMQ",
            "cmd": ["docker", "run", "-d", "--name", "monitoring-rabbitmq",
                   "-p", "5672:5672", "-p", "15672:15672", "rabbitmq:3-management"]
        },
        {
            "name": "Redis",
            "cmd": ["docker", "run", "-d", "--name", "monitoring-redis",
                   "-p", "6379:6379", "redis:7"]
        }
    ]
    
    for service in services:
        console.print(f"\n🔄 啟動 {service['name']}...")
        try:
            result = subprocess.run(service["cmd"], capture_output=True, text=True)
            if result.returncode == 0:
                console.print(f"  ✅ {service['name']} 啟動成功", style="green")
            else:
                # 可能容器已存在
                if "already in use" in result.stderr:
                    console.print(f"  ℹ️ {service['name']} 容器已存在", style="yellow")
                else:
                    console.print(f"  ❌ {service['name']} 啟動失敗: {result.stderr}", style="red")
        except Exception as e:
            console.print(f"  ❌ 啟動 {service['name']} 時發生錯誤: {e}", style="red")
    
    console.print("\n⏳ 等待服務完全啟動...")
    time.sleep(5)
    
    # 驗證服務狀態
    console.print("\n🔍 驗證服務狀態:")
    for service_name, port in [("PostgreSQL", 5432), ("RabbitMQ", 5672), ("Redis", 6379)]:
        if check_service_status(service_name.lower(), port):
            console.print(f"  ✅ {service_name} 已就緒", style="green")
        else:
            console.print(f"  ⏳ {service_name} 仍在啟動中...", style="yellow")


@app.command()
def start_api():
    """啟動測試 Model API 服務"""
    console.print(Panel.fit("🎯 啟動測試 Model API", style="blue"))
    
    # 檢查依賴服務
    required_services = [("RabbitMQ", 5672), ("PostgreSQL", 5432), ("Redis", 6379)]
    missing_services = []
    
    for service_name, port in required_services:
        if not check_service_status(service_name.lower(), port):
            missing_services.append(service_name)
    
    if missing_services:
        console.print(f"❌ 以下服務未運行: {', '.join(missing_services)}", style="red")
        console.print("💡 請先運行: python run_monitoring_demo.py start-services", style="yellow")
        return
    
    console.print("✅ 依賴服務已就緒", style="green")
    console.print("\n🚀 啟動測試 API 服務...")
    console.print(f"📍 API 地址: {DEMO_CONFIG['api_url']}")
    console.print(f"📖 API 文檔: {DEMO_CONFIG['api_url']}/docs")
    console.print(f"📊 監控統計: {DEMO_CONFIG['api_url']}/monitoring/stats")
    console.print("\n按 Ctrl+C 停止服務\n")
    
    try:
        # 啟動 API 服務
        subprocess.run([sys.executable, "test_model_api.py"], check=True)
    except KeyboardInterrupt:
        console.print("\n🛑 服務已停止", style="yellow")
    except Exception as e:
        console.print(f"❌ 啟動服務失敗: {e}", style="red")


@app.command()
def test():
    """運行監控功能測試"""
    console.print(Panel.fit("🧪 監控功能測試", style="blue"))
    
    # 檢查 API 是否運行
    if not check_service_status("api", DEMO_CONFIG["api_port"]):
        console.print(f"❌ 測試 API 未運行 (端口 {DEMO_CONFIG['api_port']})", style="red")
        console.print("💡 請先運行: python run_monitoring_demo.py start-api", style="yellow")
        return
    
    console.print("✅ 測試 API 已就緒", style="green")
    
    # 運行基本測試
    console.print("\n🔄 執行基本功能測試...")
    
    async def run_basic_tests():
        async with httpx.AsyncClient(timeout=10.0) as client:
            tests = [
                {"name": "健康檢查", "method": "GET", "url": f"{DEMO_CONFIG['api_url']}/health"},
                {"name": "模型預測", "method": "POST", "url": f"{DEMO_CONFIG['api_url']}/predict", 
                 "json": {"features": [1.0, 2.0, 3.0]}},
                {"name": "監控統計", "method": "GET", "url": f"{DEMO_CONFIG['api_url']}/monitoring/stats"},
                {"name": "錯誤測試", "method": "GET", "url": f"{DEMO_CONFIG['api_url']}/error_endpoint?error_type=client_error"},
            ]
            
            results = []
            for test in tests:
                try:
                    start_time = time.time()
                    
                    if test["method"] == "GET":
                        response = await client.get(test["url"])
                    else:
                        response = await client.post(test["url"], json=test.get("json"))
                    
                    response_time = (time.time() - start_time) * 1000
                    
                    results.append({
                        "name": test["name"],
                        "status": response.status_code,
                        "time": response_time,
                        "success": 200 <= response.status_code < 300 or response.status_code == 400  # 錯誤測試預期 400
                    })
                    
                except Exception as e:
                    results.append({
                        "name": test["name"],
                        "status": "Error",
                        "time": 0,
                        "success": False,
                        "error": str(e)
                    })
            
            return results
    
    # 執行測試
    test_results = asyncio.run(run_basic_tests())
    
    # 顯示結果
    table = Table(title="測試結果")
    table.add_column("測試項目", style="cyan")
    table.add_column("狀態碼", justify="center")
    table.add_column("響應時間", justify="right")
    table.add_column("結果", justify="center")
    
    for result in test_results:
        status_icon = "✅" if result["success"] else "❌"
        time_str = f"{result['time']:.1f}ms" if result['time'] > 0 else "N/A"
        
        table.add_row(
            result["name"],
            str(result["status"]),
            time_str,
            status_icon
        )
    
    console.print(table)
    
    # 測試總結
    success_count = sum(1 for r in test_results if r["success"])
    total_count = len(test_results)
    
    if success_count == total_count:
        console.print(f"\n🎉 所有測試通過 ({success_count}/{total_count})", style="bold green")
    else:
        console.print(f"\n⚠️ 部分測試失敗 ({success_count}/{total_count})", style="yellow")


@app.command()
def performance():
    """運行性能測試"""
    console.print(Panel.fit("⚡ 監控性能測試", style="blue"))
    
    # 檢查 API 是否運行
    if not check_service_status("api", DEMO_CONFIG["api_port"]):
        console.print(f"❌ 測試 API 未運行 (端口 {DEMO_CONFIG['api_port']})", style="red")
        return
    
    console.print("🚀 執行完整性能測試...")
    console.print("📊 這可能需要幾分鐘時間...\n")
    
    try:
        # 運行性能測試腳本
        result = subprocess.run([sys.executable, "test_monitoring_performance.py"], 
                              capture_output=True, text=True, check=True)
        
        # 顯示結果
        console.print(result.stdout)
        
        if "✅ 所有測試都符合 < 20ms 性能要求" in result.stdout:
            console.print("🎉 性能測試通過！監控開銷符合 WBS 要求", style="bold green")
        else:
            console.print("⚠️ 請檢查性能測試結果", style="yellow")
            
    except subprocess.CalledProcessError as e:
        console.print(f"❌ 性能測試失敗: {e}", style="red")
        if e.stdout:
            console.print("標準輸出:", e.stdout)
        if e.stderr:
            console.print("錯誤輸出:", e.stderr)


@app.command()
def demo():
    """運行完整演示流程"""
    console.print(Panel.fit("🎭 完整監控系統演示", style="bold blue"))
    
    console.print("這個演示將引導您完成整個監控系統的設置和測試")
    console.print("包括：服務啟動 → API 測試 → 性能驗證\n")
    
    if not typer.confirm("是否開始演示？"):
        return
    
    # Step 1: 檢查狀態
    console.print("\n" + "="*60)
    console.print("步驟 1: 檢查系統狀態")
    console.print("="*60)
    status()
    
    # Step 2: 啟動服務
    console.print("\n" + "="*60)
    console.print("步驟 2: 啟動外部服務")
    console.print("="*60)
    if typer.confirm("是否啟動 Docker 服務？"):
        start_services()
    
    # Step 3: 基本測試
    console.print("\n" + "="*60)
    console.print("步驟 3: 基本功能測試")
    console.print("="*60)
    console.print("請在另一個終端運行以下命令啟動 API:")
    console.print(f"python run_monitoring_demo.py start-api", style="bold yellow")
    
    if typer.confirm("API 已啟動，是否繼續測試？"):
        test()
    
    # Step 4: 性能測試
    console.print("\n" + "="*60)
    console.print("步驟 4: 性能測試")
    console.print("="*60)
    if typer.confirm("是否運行性能測試？"):
        performance()
    
    # 演示完成
    console.print("\n" + "="*60)
    console.print("🎉 演示完成！", style="bold green")
    console.print("="*60)
    console.print("\n📋 有用的連結:")
    console.print(f"  • API 文檔: {DEMO_CONFIG['api_url']}/docs")
    console.print(f"  • 監控統計: {DEMO_CONFIG['api_url']}/monitoring/stats")
    console.print(f"  • RabbitMQ 管理: {DEMO_CONFIG['rabbitmq_management']}")
    console.print("\n📖 詳細說明請參考: MONITORING_SETUP.md")


@app.command()
def clean():
    """清理 Docker 容器"""
    console.print(Panel.fit("🧹 清理 Docker 容器", style="blue"))
    
    containers = ["monitoring-postgres", "monitoring-rabbitmq", "monitoring-redis"]
    
    for container in containers:
        console.print(f"🗑️ 移除容器: {container}")
        try:
            subprocess.run(["docker", "rm", "-f", container], 
                         capture_output=True, check=False)
            console.print(f"  ✅ {container} 已移除", style="green")
        except Exception as e:
            console.print(f"  ⚠️ 移除 {container} 時發生錯誤: {e}", style="yellow")
    
    console.print("\n✅ 清理完成", style="green")


if __name__ == "__main__":
    app() 