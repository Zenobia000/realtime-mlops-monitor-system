#!/usr/bin/env python3
"""
環境設置腳本
根據 Docker Compose 配置生成 .env 文件
"""

import os
import shutil

def create_env_file():
    """創建 .env 文件"""
    
    env_content = """# Model API 監控系統 - 環境變數配置
# 基於現有 platform-* 服務配置

# 資料庫配置 (TimescaleDB)
DATABASE_URL=postgresql://admin:admin123@localhost:5433/platform_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=platform_db
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin123

# Redis 配置
REDIS_URL=redis://:admin123@localhost:6380
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_PASSWORD=admin123
REDIS_MAX_MEMORY=2gb

# RabbitMQ 配置
RABBITMQ_URL=amqp://admin:admin123@localhost:5672/
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=admin123
RABBITMQ_DEFAULT_USER=admin
RABBITMQ_DEFAULT_PASS=admin123
RABBITMQ_DEFAULT_VHOST=/
RABBITMQ_MANAGEMENT_PORT=15672

# API 配置
API_KEY=monitor_api_key_dev_2025
API_HOST=0.0.0.0
API_PORT=8001
API_WORKERS=4
API_SECRET_KEY=your-secret-key-change-in-production
INTERNAL_API_URL=http://localhost:8000

# Grafana 配置
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=admin123
GF_SERVER_ROOT_URL=http://10.234.14.225:3002

# pgAdmin 配置
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin123

# TimescaleDB 調優配置
TS_TUNE_MEMORY=4GB
TS_TUNE_NUM_CPUS=4

# Streamlit Web 配置
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_THEME_BASE=light

# 批次處理配置
BATCH_SIZE=100
SIMULATOR_CONFIG_FILE=/app/config/simulator.yaml

# 指標處理服務配置
WINDOW_SIZE_SECONDS=60
AGGREGATION_INTERVAL=5
METRICS_QUEUE_NAME=metrics.api_requests
ALERTS_QUEUE_NAME=alerts.notifications

# 告警閾值配置
P95_LATENCY_THRESHOLD=500
P99_LATENCY_THRESHOLD=1000
ERROR_RATE_THRESHOLD=0.05
QPS_LOW_THRESHOLD=1

# 日誌配置
LOG_LEVEL=INFO
LOG_FORMAT=json

# 開發環境特定配置
DEBUG=true
ENVIRONMENT=development
"""
    
    # 寫入 .env 文件
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ .env 文件已創建")
    print("📂 位置:", os.path.abspath('.env'))

def copy_env_example():
    """複製 env.example 到 .env"""
    env_example_path = '../config/env.example'
    
    if os.path.exists(env_example_path):
        shutil.copy2(env_example_path, '.env')
        print("✅ 已從 config/env.example 複製 .env 文件")
    else:
        print("⚠️ config/env.example 不存在，使用內建配置")
        create_env_file()

def main():
    """主函數"""
    print("🔧 設置環境變數...")
    
    # 檢查是否已有 .env 文件
    if os.path.exists('.env'):
        response = input("⚠️ .env 文件已存在，是否覆蓋? (y/N): ")
        if response.lower() != 'y':
            print("❌ 取消操作")
            return
    
    create_env_file()
    
    print("\n🎯 環境配置完成！")
    print("📋 服務配置摘要:")
    print("  - PostgreSQL (TimescaleDB): localhost:5433")
    print("  - Redis: localhost:6380") 
    print("  - RabbitMQ: localhost:5672 (Management: 15672)")
    print("  - API 服務: localhost:8001")
    print("  - Grafana: localhost:3002")
    print("  - pgAdmin: localhost:5050")
    print("\n🔐 認證資訊:")
    print("  - 資料庫: admin/admin123")
    print("  - Redis: admin123")
    print("  - RabbitMQ: admin/admin123")
    print("  - Grafana: admin/admin123")
    print("  - pgAdmin: admin@example.com/admin123")

if __name__ == "__main__":
    main() 