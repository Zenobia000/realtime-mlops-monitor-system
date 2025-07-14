#!/bin/bash

# =============================================================================
# Model API 監控系統 - 一鍵服務管理腳本
# =============================================================================
# 功能: 啟動/停止/重啟/健康檢查所有監控服務
# 作者: VibeCoding Assistant
# 版本: v1.0
# 日期: 2024-12-19
# =============================================================================

set -e  # 遇到錯誤立即退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置參數
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
PID_DIR="${SCRIPT_DIR}"

# 服務配置
METRICS_PROCESSING_PORT=5672
MONITORING_API_PORT=8001
TEST_MODEL_API_PORT=8002
FEATURE_GENERATOR_DURATION="3600"  # 1小時

# Docker 服務配置
DOCKER_SERVICES=("platform-timescaledb" "platform-redis" "platform-rabbitmq" "platform-grafana")
DOCKER_PORTS=(5433 6380 5672 3002)

# PID 文件
METRICS_PROCESSING_PID="${PID_DIR}/metrics_processing.pid"
MONITORING_API_PID="${PID_DIR}/monitoring_api.pid"
TEST_MODEL_API_PID="${PID_DIR}/test_model_api.pid"
FEATURE_GENERATOR_PID="${PID_DIR}/feature_generator.pid"

# =============================================================================
# 工具函數
# =============================================================================

# 打印彩色日誌
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%H:%M:%S') $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%H:%M:%S') $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $1"
}

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $(date '+%H:%M:%S') $1"
}

# 創建日誌目錄
create_log_dir() {
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
        log_info "創建日誌目錄: $LOG_DIR"
    fi
}

# 檢查端口是否被佔用
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # 端口被佔用
    else
        return 1  # 端口可用
    fi
}

# 等待端口啟動
wait_for_port() {
    local port=$1
    local timeout=${2:-30}
    local count=0
    
    log_info "等待端口 $port 啟動..."
    while [ $count -lt $timeout ]; do
        if check_port $port; then
            log_success "端口 $port 已啟動"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        if [ $((count % 5)) -eq 0 ]; then
            echo -n "."
        fi
    done
    echo ""
    log_error "端口 $port 啟動超時 (${timeout}秒)"
    return 1
}

# 檢查進程是否運行
is_process_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # 進程運行中
        else
            rm -f "$pid_file"  # 清理無效PID文件
            return 1  # 進程未運行
        fi
    else
        return 1  # PID文件不存在
    fi
}

# 停止進程
stop_process() {
    local pid_file=$1
    local service_name=$2
    
    if is_process_running "$pid_file"; then
        local pid=$(cat "$pid_file")
        log_info "停止 $service_name (PID: $pid)..."
        kill "$pid" 2>/dev/null || true
        
        # 等待進程停止
        local count=0
        while [ $count -lt 10 ] && kill -0 "$pid" 2>/dev/null; do
            sleep 1
            count=$((count + 1))
        done
        
        # 強制終止
        if kill -0 "$pid" 2>/dev/null; then
            log_warning "強制終止 $service_name"
            kill -9 "$pid" 2>/dev/null || true
        fi
        
        rm -f "$pid_file"
        log_success "$service_name 已停止"
    else
        log_info "$service_name 未運行"
    fi
}

# =============================================================================
# Docker 服務檢查
# =============================================================================

check_docker_services() {
    log_step "檢查 Docker 服務狀態..."
    
    local all_healthy=true
    
    for i in "${!DOCKER_SERVICES[@]}"; do
        local service=${DOCKER_SERVICES[$i]}
        local port=${DOCKER_PORTS[$i]}
        
        # 檢查 Docker 容器狀態
        if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$service.*Up"; then
            if check_port $port; then
                log_success "✅ $service (端口 $port) - 運行正常"
            else
                log_warning "⚠️  $service 容器運行，但端口 $port 無響應"
                all_healthy=false
            fi
        else
            log_error "❌ $service - 未運行或不健康"
            all_healthy=false
        fi
    done
    
    if [ "$all_healthy" = true ]; then
        log_success "所有 Docker 服務運行正常"
        return 0
    else
        log_error "部分 Docker 服務異常，請檢查 docker-compose 狀態"
        log_info "提示: 運行 'docker-compose up -d' 啟動基礎服務"
        return 1
    fi
}

# =============================================================================
# Python 服務管理
# =============================================================================

# 啟動指標處理服務
start_metrics_processing() {
    log_step "啟動指標處理服務..."
    
    if is_process_running "$METRICS_PROCESSING_PID"; then
        log_warning "指標處理服務已在運行"
        return 0
    fi
    
    cd "$SCRIPT_DIR"
    nohup python run_metrics_processing_service.py start > "$LOG_DIR/metrics_processing.log" 2>&1 &
    local pid=$!
    echo $pid > "$METRICS_PROCESSING_PID"
    
    sleep 3
    if is_process_running "$METRICS_PROCESSING_PID"; then
        log_success "指標處理服務已啟動 (PID: $pid)"
        return 0
    else
        log_error "指標處理服務啟動失敗"
        return 1
    fi
}

# 啟動監控 API 服務
start_monitoring_api() {
    log_step "啟動監控 API 服務 (端口 $MONITORING_API_PORT)..."
    
    if is_process_running "$MONITORING_API_PID"; then
        log_warning "監控 API 服務已在運行"
        return 0
    fi
    
    cd "$SCRIPT_DIR"
    nohup uvicorn src.api.main:app --host 0.0.0.0 --port $MONITORING_API_PORT > "$LOG_DIR/monitoring_api.log" 2>&1 &
    local pid=$!
    echo $pid > "$MONITORING_API_PID"
    
    if wait_for_port $MONITORING_API_PORT 30; then
        log_success "監控 API 服務已啟動 (PID: $pid, 端口: $MONITORING_API_PORT)"
        return 0
    else
        stop_process "$MONITORING_API_PID" "監控 API 服務"
        log_error "監控 API 服務啟動失敗"
        return 1
    fi
}

# 啟動測試模型 API
start_test_model_api() {
    log_step "啟動測試模型 API (端口 $TEST_MODEL_API_PORT)..."
    
    if is_process_running "$TEST_MODEL_API_PID"; then
        log_warning "測試模型 API 已在運行"
        return 0
    fi
    
    cd "$SCRIPT_DIR"
    nohup python test_model_api.py > "$LOG_DIR/test_model_api.log" 2>&1 &
    local pid=$!
    echo $pid > "$TEST_MODEL_API_PID"
    
    if wait_for_port $TEST_MODEL_API_PORT 20; then
        log_success "測試模型 API 已啟動 (PID: $pid, 端口: $TEST_MODEL_API_PORT)"
        return 0
    else
        stop_process "$TEST_MODEL_API_PID" "測試模型 API"
        log_error "測試模型 API 啟動失敗"
        return 1
    fi
}

# 啟動特徵生成器
start_feature_generator() {
    log_step "啟動特徵生成器 (持續 $FEATURE_GENERATOR_DURATION 秒)..."
    
    if is_process_running "$FEATURE_GENERATOR_PID"; then
        log_warning "特徵生成器已在運行"
        return 0
    fi
    
    cd "$SCRIPT_DIR"
    # 修改 feature_generator.py 為永續運行模式
    cat > temp_feature_generator.py << 'EOF'
import sys
import time
import asyncio
import aiohttp
import json
import random
import os
from datetime import datetime

def log_info(message):
    print(f"[INFO] {datetime.now().strftime('%H:%M:%S')} {message}")

async def make_request_with_monitoring():
    """發送帶監控的請求到測試API"""
    url = "http://localhost:8002/predict"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "test-api-key-12345"
    }
    
    # 隨機選擇模型版本和數據
    model_version = random.choice(["v1.0", "v2.0"])
    data = {
        "model_version": model_version,
        "features": [random.uniform(-1, 1) for _ in range(10)],
        "metadata": {
            "request_id": f"req_{int(time.time())}_{random.randint(1000, 9999)}",
            "timestamp": datetime.now().isoformat()
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers, timeout=5) as response:
                result = await response.json()
                
                if response.status == 200:
                    log_info(f"✅ 請求成功 - 模型: {model_version}, 預測: {result.get('prediction', 'N/A')}")
                else:
                    log_info(f"⚠️  請求失敗 - 狀態碼: {response.status}")
                    
                return response.status == 200
                
    except asyncio.TimeoutError:
        log_info("❌ 請求超時")
        return False
    except Exception as e:
        log_info(f"❌ 請求異常: {str(e)}")
        return False

async def continuous_requests():
    """持續發送請求"""
    log_info("🚀 特徵生成器啟動 - 永續運行模式")
    
    request_count = 0
    success_count = 0
    
    try:
        while True:
            success = await make_request_with_monitoring()
            request_count += 1
            if success:
                success_count += 1
            
            # 每100個請求顯示統計
            if request_count % 100 == 0:
                success_rate = (success_count / request_count) * 100
                log_info(f"📊 統計: 總請求 {request_count}, 成功 {success_count}, 成功率 {success_rate:.1f}%")
            
            # 間隔1.5秒 (QPS ≈ 0.67)
            await asyncio.sleep(1.5)
            
    except KeyboardInterrupt:
        log_info("🛑 接收到停止信號")
    except Exception as e:
        log_info(f"❌ 特徵生成器異常: {str(e)}")
    finally:
        success_rate = (success_count / request_count) * 100 if request_count > 0 else 0
        log_info(f"📈 最終統計: 總請求 {request_count}, 成功 {success_count}, 成功率 {success_rate:.1f}%")

if __name__ == "__main__":
    asyncio.run(continuous_requests())
EOF
    
    nohup python temp_feature_generator.py > "$LOG_DIR/feature_generator.log" 2>&1 &
    local pid=$!
    echo $pid > "$FEATURE_GENERATOR_PID"
    
    sleep 3
    if is_process_running "$FEATURE_GENERATOR_PID"; then
        log_success "特徵生成器已啟動 (PID: $pid, 永續運行模式)"
        return 0
    else
        log_error "特徵生成器啟動失敗"
        return 1
    fi
}

# =============================================================================
# 服務健康檢查
# =============================================================================

health_check() {
    log_step "執行服務健康檢查..."
    
    echo ""
    echo -e "${CYAN}=== Docker 服務狀態 ===${NC}"
    check_docker_services
    
    echo ""
    echo -e "${CYAN}=== Python 服務狀態 ===${NC}"
    
    # 檢查指標處理服務
    if is_process_running "$METRICS_PROCESSING_PID"; then
        local pid=$(cat "$METRICS_PROCESSING_PID")
        log_success "✅ 指標處理服務 (PID: $pid)"
    else
        log_error "❌ 指標處理服務未運行"
    fi
    
    # 檢查監控 API
    if is_process_running "$MONITORING_API_PID" && check_port $MONITORING_API_PORT; then
        local pid=$(cat "$MONITORING_API_PID")
        log_success "✅ 監控 API 服務 (PID: $pid, 端口: $MONITORING_API_PORT)"
        
        # API 健康檢查
        if curl -s "http://localhost:$MONITORING_API_PORT/health" >/dev/null 2>&1; then
            log_success "   └─ API 健康檢查通過"
        else
            log_warning "   └─ API 健康檢查失敗"
        fi
    else
        log_error "❌ 監控 API 服務未運行或端口無響應"
    fi
    
    # 檢查測試模型 API
    if is_process_running "$TEST_MODEL_API_PID" && check_port $TEST_MODEL_API_PORT; then
        local pid=$(cat "$TEST_MODEL_API_PID")
        log_success "✅ 測試模型 API (PID: $pid, 端口: $TEST_MODEL_API_PORT)"
        
        # API 健康檢查
        if curl -s "http://localhost:$TEST_MODEL_API_PORT/health" >/dev/null 2>&1; then
            log_success "   └─ API 健康檢查通過"
        else
            log_warning "   └─ API 健康檢查失敗"
        fi
    else
        log_error "❌ 測試模型 API 未運行或端口無響應"
    fi
    
    # 檢查特徵生成器
    if is_process_running "$FEATURE_GENERATOR_PID"; then
        local pid=$(cat "$FEATURE_GENERATOR_PID")
        log_success "✅ 特徵生成器 (PID: $pid)"
    else
        log_error "❌ 特徵生成器未運行"
    fi
    
    echo ""
    echo -e "${CYAN}=== 服務訪問地址 ===${NC}"
    echo -e "監控 API:    ${BLUE}http://localhost:$MONITORING_API_PORT${NC}"
    echo -e "測試模型 API: ${BLUE}http://localhost:$TEST_MODEL_API_PORT${NC}"
    echo -e "Grafana:     ${BLUE}http://localhost:3002${NC} (admin/admin)"
    echo -e "日誌目錄:    ${BLUE}$LOG_DIR${NC}"
}

# =============================================================================
# 主要操作函數
# =============================================================================

start_all_services() {
    log_info "🚀 開始啟動所有監控服務..."
    create_log_dir
    
    # 檢查 Docker 服務
    if ! check_docker_services; then
        log_error "Docker 服務異常，請先啟動基礎服務"
        return 1
    fi
    
    echo ""
    log_step "按序啟動 Python 服務..."
    
    # 依序啟動服務
    if ! start_metrics_processing; then
        log_error "指標處理服務啟動失敗，停止後續啟動"
        return 1
    fi
    
    sleep 2
    
    if ! start_monitoring_api; then
        log_error "監控 API 啟動失敗，停止後續啟動"
        return 1
    fi
    
    sleep 2
    
    if ! start_test_model_api; then
        log_error "測試模型 API 啟動失敗，停止後續啟動"
        return 1
    fi
    
    sleep 2
    
    if ! start_feature_generator; then
        log_error "特徵生成器啟動失敗"
        return 1
    fi
    
    echo ""
    log_success "🎉 所有服務啟動完成！"
    
    # 等待服務穩定
    log_info "等待服務穩定..."
    sleep 5
    
    # 執行健康檢查
    health_check
    
    # 清理臨時文件
    rm -f temp_feature_generator.py
}

stop_all_services() {
    log_info "🛑 停止所有監控服務..."
    
    stop_process "$FEATURE_GENERATOR_PID" "特徵生成器"
    sleep 1
    
    stop_process "$TEST_MODEL_API_PID" "測試模型 API"
    sleep 1
    
    stop_process "$MONITORING_API_PID" "監控 API 服務"
    sleep 1
    
    stop_process "$METRICS_PROCESSING_PID" "指標處理服務"
    
    # 清理臨時文件
    rm -f temp_feature_generator.py
    
    log_success "✅ 所有服務已停止"
}

restart_all_services() {
    log_info "🔄 重啟所有監控服務..."
    stop_all_services
    sleep 3
    start_all_services
}

# =============================================================================
# 主程式入口
# =============================================================================

show_usage() {
    echo -e "${CYAN}Model API 監控系統 - 服務管理腳本${NC}"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start    - 啟動所有監控服務"
    echo "  stop     - 停止所有監控服務"
    echo "  restart  - 重啟所有監控服務"
    echo "  status   - 檢查服務健康狀態"
    echo "  logs     - 顯示服務日誌"
    echo ""
    echo "範例:"
    echo "  $0 start     # 啟動所有服務"
    echo "  $0 status    # 檢查服務狀態"
    echo "  $0 logs      # 查看日誌"
}

show_logs() {
    log_info "📋 顯示最新服務日誌..."
    
    if [ -d "$LOG_DIR" ]; then
        echo -e "${CYAN}=== 最新日誌 (最後10行) ===${NC}"
        for log_file in "$LOG_DIR"/*.log; do
            if [ -f "$log_file" ]; then
                echo -e "\n${YELLOW}=== $(basename "$log_file") ===${NC}"
                tail -n 10 "$log_file" 2>/dev/null || echo "無法讀取日誌文件"
            fi
        done
    else
        log_warning "日誌目錄不存在: $LOG_DIR"
    fi
}

# 主程式邏輯
case "${1:-}" in
    start)
        start_all_services
        ;;
    stop)
        stop_all_services
        ;;
    restart)
        restart_all_services
        ;;
    status)
        health_check
        ;;
    logs)
        show_logs
        ;;
    *)
        show_usage
        exit 1
        ;;
esac

exit 0 