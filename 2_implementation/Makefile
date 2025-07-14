# Model API 監控系統 Makefile
# 簡化開發流程和環境管理

.PHONY: help install setup test lint format run clean dev docs

# 預設目標
help:
	@echo "🚀 Model API 監控系統開發指令"
	@echo ""
	@echo "📦 環境管理:"
	@echo "  make install     - 安裝 Poetry 並設置 Python 3.10 環境"
	@echo "  make setup       - 完整項目設置 (環境 + 依賴 + .env)"
	@echo "  make env         - 生成 .env 環境配置文件"
	@echo ""
	@echo "🏃 開發服務:"
	@echo "  make dev         - 啟動開發服務器 (熱重載)"
	@echo "  make run         - 啟動生產模式服務器"
	@echo "  make test-api    - 快速測試 API 功能"
	@echo ""
	@echo "🔍 程式碼品質:"
	@echo "  make test        - 運行所有測試"
	@echo "  make lint        - 程式碼檢查 (flake8 + mypy)"
	@echo "  make format      - 程式碼格式化 (black + isort)"
	@echo "  make check       - 完整品質檢查 (lint + test)"
	@echo ""
	@echo "📚 文檔與清理:"
	@echo "  make docs        - 生成API文檔"
	@echo "  make clean       - 清理臨時文件"
	@echo "  make status      - 檢查服務狀態"

# 檢查 Poetry 是否已安裝
check-poetry:
	@which poetry > /dev/null || (echo "❌ Poetry 未安裝！請先安裝 Poetry: curl -sSL https://install.python-poetry.org | python3 -" && exit 1)
	@echo "✅ Poetry 已安裝"

# 安裝 Poetry 環境
install: check-poetry
	@echo "📦 設置 Poetry 環境 (Python 3.10)..."
	poetry env use python3.10
	poetry install
	@echo "✅ Poetry 環境設置完成"

# 完整項目設置
setup: install env
	@echo "🎯 完整項目設置完成！"
	@echo "💡 下一步："
	@echo "   make dev    # 啟動開發服務器"
	@echo "   make test   # 運行測試"

# 生成環境配置
env:
	@echo "🔧 生成環境配置文件..."
	poetry run python setup_env.py
	@echo "✅ 環境配置完成"

# 開發服務器 (熱重載)
dev: check-poetry
	@echo "🚀 啟動開發服務器..."
	poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8001 --reload

# 生產模式服務器
run: check-poetry
	@echo "🏃 啟動生產模式服務器..."
	poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8001 --workers 4

# 快速 API 測試
test-api:
	@echo "🔍 快速測試 API..."
	@echo "健康檢查:"
	@curl -s http://localhost:8001/health | python3 -m json.tool || echo "❌ API 未啟動"
	@echo ""
	@echo "API 資訊:"
	@curl -s http://localhost:8001/v1 | python3 -m json.tool || echo "❌ API 未啟動"

# 運行測試
test: check-poetry
	@echo "🧪 運行測試..."
	poetry run pytest -v --cov=src --cov-report=term-missing

# 程式碼檢查
lint: check-poetry
	@echo "🔍 程式碼檢查..."
	poetry run flake8 src/ --max-line-length=88 --extend-ignore=E203,W503
	poetry run mypy src/

# 程式碼格式化
format: check-poetry
	@echo "🎨 程式碼格式化..."
	poetry run black src/
	poetry run isort src/

# 完整品質檢查
check: format lint test
	@echo "✅ 程式碼品質檢查完成"

# 生成文檔
docs: check-poetry
	@echo "📚 生成 API 文檔..."
	@echo "Swagger UI: http://localhost:8001/docs"
	@echo "ReDoc: http://localhost:8001/redoc"

# 檢查服務狀態
status:
	@echo "📊 檢查相關服務狀態..."
	@echo ""
	@echo "🐳 Docker 服務:"
	@docker ps --filter "name=platform-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "❌ Docker 未運行"
	@echo ""
	@echo "🌐 網路連通性測試:"
	@echo -n "PostgreSQL (5433): "; nc -z localhost 5433 && echo "✅ 連通" || echo "❌ 不可達"
	@echo -n "Redis (6380): "; nc -z localhost 6380 && echo "✅ 連通" || echo "❌ 不可達"  
	@echo -n "RabbitMQ (5672): "; nc -z localhost 5672 && echo "✅ 連通" || echo "❌ 不可達"
	@echo -n "RabbitMQ Management (15672): "; nc -z localhost 15672 && echo "✅ 連通" || echo "❌ 不可達"

# 清理臨時文件
clean:
	@echo "🧹 清理臨時文件..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf dist/ build/ *.egg-info/
	@echo "✅ 清理完成"

# Poetry 環境資訊
info: check-poetry
	@echo "📋 Poetry 環境資訊:"
	poetry env info
	@echo ""
	@echo "📦 已安裝套件:"
	poetry show --tree

# 更新依賴
update: check-poetry
	@echo "⬆️ 更新依賴套件..."
	poetry update
	@echo "✅ 依賴更新完成" 