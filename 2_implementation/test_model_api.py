"""
測試用 Model API 服務
用於驗證監控攔截器的功能和性能
"""

import asyncio
import random
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
import uvicorn

from src.components import add_monitoring_to_app
from src.api.config import get_settings

# 創建測試 API 應用
app = FastAPI(
    title="測試 Model API",
    description="用於驗證監控功能的模擬機器學習 API",
    version="1.0.0"
)

# 添加監控功能
monitor = add_monitoring_to_app(
    app, 
    service_name="test-model-api",
    config={
        "enable_detailed_logging": True,
        "exclude_paths": ["/health", "/docs", "/redoc", "/openapi.json"]
    }
)

# 請求/響應模型
class PredictionRequest(BaseModel):
    """預測請求模型"""
    features: List[float] = Field(..., description="特徵向量(5個數值)", example=[0.5, 1.0, 0.8, 0.3, 0.7])
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="元數據信息")
    model_version: Optional[str] = Field(default="v1.0", description="模型版本")


class PredictionResponse(BaseModel):
    """預測響應模型"""
    predictions: List[float] = Field(..., description="預測結果")
    model_version: str = Field(..., description="使用的模型版本")
    processing_time_ms: float = Field(..., description="處理時間(毫秒)")
    timestamp: str = Field(..., description="預測時間")
    request_id: str = Field(..., description="請求ID")


class ModelInfo(BaseModel):
    """模型信息"""
    name: str
    version: str
    description: str
    input_features: int
    output_classes: int
    accuracy: float
    last_trained: str


class BatchPredictionRequest(BaseModel):
    """批量預測請求"""
    samples: List[List[float]] = Field(..., description="樣本列表")
    model_version: Optional[str] = Field(default="v1.0", description="模型版本")


# 模擬數據
MOCK_MODELS = {
    "v1.0": ModelInfo(
        name="Linear Classifier",
        version="v1.0",
        description="簡單線性分類模型 - 快速推理",
        input_features=5,
        output_classes=2,
        accuracy=0.85,
        last_trained="2025-06-01T10:00:00Z"
    ),
    "v2.0": ModelInfo(
        name="Deep Neural Network", 
        version="v2.0",
        description="深度神經網路分類模型 - 高精度推理",
        input_features=5,
        output_classes=2,
        accuracy=0.92,
        last_trained="2025-06-15T14:30:00Z"
    )
}


def simulate_model_inference(features: List[float], model_version: str = "v1.0", metadata: Dict[str, Any] = None) -> List[float]:
    """
    模擬模型推理過程
    
    Args:
        features: 輸入特徵 (5個數值)
        model_version: 模型版本
        metadata: 元數據信息
        
    Returns:
        List[float]: 預測結果 [probability_class_0, probability_class_1]
    """
    # 驗證特徵向量
    if len(features) != 5:
        raise ValueError("特徵向量必須包含 5 個元素")
    
    # 模擬不同模型的處理時間和行為
    if model_version == "v1.0":
        # 簡單模型，快速響應，較低準確度
        time.sleep(random.uniform(0.008, 0.025))  # 8-25ms
        weights = [0.15, 0.25, 0.20, 0.10, 0.30]  # 簡單權重
        bias = 0.1
    elif model_version == "v2.0":
        # 複雜模型，較慢響應，較高準確度
        time.sleep(random.uniform(0.040, 0.120))  # 40-120ms
        weights = [0.22, 0.18, 0.24, 0.16, 0.20]  # 更平衡的權重
        bias = 0.05
    else:
        raise ValueError(f"不支援的模型版本: {model_version}")
    
    # 根據元數據調整預測行為
    if metadata:
        feature_type = metadata.get("feature_type", "normal")
        
        # 針對不同特徵類型模擬不同的推理結果
        if feature_type == "error_prone":
            # 增加一些隨機性以模擬不穩定的預測
            noise = random.uniform(-0.1, 0.1)
            bias += noise
        elif feature_type == "anomaly":
            # 異常特徵可能導致極端預測
            if random.random() < 0.3:  # 30% 機率產生極端結果
                return [random.choice([0.05, 0.95]), random.choice([0.05, 0.95])]
    
    # 線性組合計算
    linear_combination = sum(f * w for f, w in zip(features, weights)) + bias
    
    # Sigmoid 激活函數
    probability_class_1 = 1 / (1 + abs(linear_combination))
    probability_class_0 = 1 - probability_class_1
    
    # 確保概率和為1且在合理範圍內
    total = probability_class_0 + probability_class_1
    probability_class_0 /= total
    probability_class_1 /= total
    
    return [round(probability_class_0, 4), round(probability_class_1, 4)]


@app.get("/", tags=["根目錄"])
async def root():
    """API 根目錄"""
    return {
        "service": "Test Model API",
        "version": "1.0.0",
        "description": "用於驗證監控功能的模擬機器學習 API",
        "endpoints": {
            "predict": "/predict",
            "batch_predict": "/batch_predict",
            "models": "/models",
            "health": "/health"
        }
    }


@app.get("/health", tags=["健康檢查"])
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "service": "test-model-api",
        "timestamp": datetime.utcnow().isoformat(),
        "models_available": list(MOCK_MODELS.keys())
    }


@app.post("/predict", response_model=PredictionResponse, tags=["預測"])
async def predict(request: PredictionRequest) -> PredictionResponse:
    """
    單個預測端點
    
    這是主要的預測 API，會被監控攔截器監控
    """
    start_time = time.perf_counter()
    
    try:
        # 驗證模型版本
        if request.model_version not in MOCK_MODELS:
            raise HTTPException(
                status_code=400,
                detail=f"不支援的模型版本: {request.model_version}"
            )
        
        # 驗證特徵向量
        if len(request.features) != 5:
            raise HTTPException(
                status_code=400,
                detail="特徵向量必須包含 5 個元素"
            )
        
        # 執行模型推理
        predictions = simulate_model_inference(
            request.features, 
            request.model_version,
            request.metadata
        )
        
        # 計算處理時間
        processing_time = (time.perf_counter() - start_time) * 1000
        
        return PredictionResponse(
            predictions=predictions,
            model_version=request.model_version,
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow().isoformat(),
            request_id=f"req_{int(time.time() * 1000)}"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"預測失敗: {str(e)}")


@app.post("/batch_predict", tags=["預測"])
async def batch_predict(request: BatchPredictionRequest) -> Dict[str, Any]:
    """
    批量預測端點
    
    用於測試高併發和大量數據的監控場景
    """
    start_time = time.perf_counter()
    
    try:
        if not request.samples:
            raise HTTPException(status_code=400, detail="樣本列表不能為空")
        
        if len(request.samples) > 100:
            raise HTTPException(status_code=400, detail="批次大小不能超過 100")
        
        # 驗證模型版本
        if request.model_version not in MOCK_MODELS:
            raise HTTPException(
                status_code=400,
                detail=f"不支援的模型版本: {request.model_version}"
            )
        
        # 批量推理
        results = []
        for i, features in enumerate(request.samples):
            try:
                # 驗證每個樣本的特徵數量
                if len(features) != 5:
                    raise ValueError(f"樣本 {i}: 特徵向量必須包含 5 個元素，實際包含 {len(features)} 個")
                
                prediction = simulate_model_inference(features, request.model_version)
                results.append({
                    "sample_id": i,
                    "predictions": prediction,
                    "status": "success"
                })
            except Exception as e:
                results.append({
                    "sample_id": i,
                    "predictions": None,
                    "status": "error",
                    "error": str(e)
                })
        
        processing_time = (time.perf_counter() - start_time) * 1000
        
        return {
            "results": results,
            "total_samples": len(request.samples),
            "successful_predictions": sum(1 for r in results if r["status"] == "success"),
            "model_version": request.model_version,
            "processing_time_ms": processing_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量預測失敗: {str(e)}")


@app.get("/models", response_model=Dict[str, ModelInfo], tags=["模型管理"])
async def get_models() -> Dict[str, ModelInfo]:
    """獲取可用模型列表"""
    return MOCK_MODELS


@app.get("/models/{model_version}", response_model=ModelInfo, tags=["模型管理"])
async def get_model_info(model_version: str) -> ModelInfo:
    """獲取特定模型信息"""
    if model_version not in MOCK_MODELS:
        raise HTTPException(status_code=404, detail=f"模型版本 {model_version} 不存在")
    
    return MOCK_MODELS[model_version]


@app.get("/slow_endpoint", tags=["測試"])
async def slow_endpoint(delay: float = 2.0):
    """
    慢響應端點，用於測試性能監控
    
    Args:
        delay: 延遲時間(秒)，預設 2 秒
    """
    if delay > 10:
        raise HTTPException(status_code=400, detail="延遲時間不能超過 10 秒")
    
    await asyncio.sleep(delay)
    
    return {
        "message": f"延遲 {delay} 秒後的響應",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/error_endpoint", tags=["測試"])
async def error_endpoint(error_type: str = "server_error"):
    """
    錯誤端點，用於測試錯誤監控
    
    Args:
        error_type: 錯誤類型 (client_error, server_error, timeout)
    """
    if error_type == "client_error":
        raise HTTPException(status_code=400, detail="客戶端錯誤測試")
    elif error_type == "server_error":
        raise HTTPException(status_code=500, detail="伺服器錯誤測試")
    elif error_type == "timeout":
        await asyncio.sleep(30)  # 模擬超時
        return {"message": "不應該到達這裡"}
    else:
        raise HTTPException(status_code=400, detail=f"不支援的錯誤類型: {error_type}")


@app.get("/stress_test", tags=["測試"])
async def stress_test(requests_count: int = 10):
    """
    壓力測試端點，用於測試高併發監控
    
    Args:
        requests_count: 模擬的內部請求數量
    """
    if requests_count > 100:
        raise HTTPException(status_code=400, detail="請求數量不能超過 100")
    
    start_time = time.perf_counter()
    
    # 模擬處理多個內部請求
    tasks = []
    for i in range(requests_count):
        # 隨機延遲
        delay = random.uniform(0.01, 0.1)
        tasks.append(asyncio.sleep(delay))
    
    await asyncio.gather(*tasks)
    
    processing_time = (time.perf_counter() - start_time) * 1000
    
    return {
        "processed_requests": requests_count,
        "total_processing_time_ms": processing_time,
        "avg_time_per_request_ms": processing_time / requests_count,
        "timestamp": datetime.utcnow().isoformat()
    }


# 監控統計端點
@app.get("/monitoring/stats", tags=["監控"])
async def get_monitoring_stats():
    """獲取監控統計信息"""
    health_status = await monitor.get_health_status()
    return health_status


if __name__ == "__main__":
    settings = get_settings()
    
    print("🚀 啟動測試 Model API 服務...")
    print(f"📊 監控功能: 已啟用")
    print(f"🔗 API 文檔: http://localhost:{settings.TEST_MODEL_API_PORT}/docs")
    print(f"📈 監控統計: http://localhost:{settings.TEST_MODEL_API_PORT}/monitoring/stats")
    
    uvicorn.run(
        "test_model_api:app",
        host=settings.API_HOST,
        port=settings.TEST_MODEL_API_PORT,  # 使用配置檔案設定
        reload=settings.DEBUG,
        log_level="info"
    ) 