"""
自動特徵生成工具
用於產生測試模型預測所需的特徵數據
"""

import random
import time
import asyncio
import aiohttp
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class ModelVersion(Enum):
    """模型版本枚舉"""
    V1_0 = "v1.0"
    V2_0 = "v2.0"


class FeatureType(Enum):
    """特徵類型枚舉"""
    NORMAL = "normal"
    ANOMALY = "anomaly"
    HIGH_LOAD = "high_load"
    ERROR_PRONE = "error_prone"


@dataclass
class ModelFeatures:
    """模型特徵數據結構"""
    # 基礎數值特徵
    feature_1: float
    feature_2: float  
    feature_3: float
    feature_4: float
    feature_5: float
    
    # 類別特徵
    category: str
    region: str
    
    # 時間特徵
    hour_of_day: int
    day_of_week: int
    
    # 元數據
    feature_type: str
    model_version: str
    timestamp: str


class FeatureGenerator:
    """特徵生成器"""
    
    def __init__(self):
        self.categories = ["A", "B", "C", "D", "E"]
        self.regions = ["us-east", "us-west", "eu-west", "ap-south", "ap-east"]
        
    def generate_features(
        self, 
        feature_type: FeatureType = FeatureType.NORMAL,
        model_version: ModelVersion = ModelVersion.V1_0
    ) -> ModelFeatures:
        """生成特徵數據"""
        
        now = datetime.now()
        
        # 根據特徵類型生成不同的數據分佈
        if feature_type == FeatureType.NORMAL:
            features = self._generate_normal_features()
        elif feature_type == FeatureType.ANOMALY:
            features = self._generate_anomaly_features()
        elif feature_type == FeatureType.HIGH_LOAD:
            features = self._generate_high_load_features()
        else:  # ERROR_PRONE
            features = self._generate_error_prone_features()
            
        return ModelFeatures(
            feature_1=features[0],
            feature_2=features[1],
            feature_3=features[2], 
            feature_4=features[3],
            feature_5=features[4],
            category=random.choice(self.categories),
            region=random.choice(self.regions),
            hour_of_day=now.hour,
            day_of_week=now.weekday(),
            feature_type=feature_type.value,
            model_version=model_version.value,
            timestamp=now.isoformat()
        )
    
    def _generate_normal_features(self) -> List[float]:
        """生成正常分佈的特徵"""
        return [
            np.random.normal(0.5, 0.1),  # feature_1: 平均0.5，標準差0.1
            np.random.normal(1.0, 0.2),  # feature_2: 平均1.0，標準差0.2
            np.random.normal(0.8, 0.15), # feature_3: 平均0.8，標準差0.15
            np.random.normal(0.3, 0.05), # feature_4: 平均0.3，標準差0.05
            np.random.normal(0.7, 0.12)  # feature_5: 平均0.7，標準差0.12
        ]
    
    def _generate_anomaly_features(self) -> List[float]:
        """生成異常的特徵（極值）"""
        return [
            np.random.choice([np.random.normal(-1, 0.1), np.random.normal(2, 0.1)]),
            np.random.choice([np.random.normal(-0.5, 0.1), np.random.normal(3, 0.2)]),
            np.random.choice([np.random.normal(-0.2, 0.05), np.random.normal(2.5, 0.1)]),
            np.random.choice([np.random.normal(-0.8, 0.1), np.random.normal(1.5, 0.05)]),
            np.random.choice([np.random.normal(-0.3, 0.05), np.random.normal(2.2, 0.1)])
        ]
    
    def _generate_high_load_features(self) -> List[float]:
        """生成高負載場景的特徵"""
        return [
            np.random.normal(1.5, 0.3),   # 較高的數值
            np.random.normal(2.2, 0.4),
            np.random.normal(1.8, 0.25),
            np.random.normal(1.1, 0.2),
            np.random.normal(1.9, 0.35)
        ]
    
    def _generate_error_prone_features(self) -> List[float]:
        """生成容易出錯的特徵（不穩定）"""
        return [
            np.random.uniform(-2, 3),      # 均勻分佈，範圍大
            np.random.exponential(0.5),    # 指數分佈
            np.random.gamma(2, 0.5),       # Gamma分佈
            np.random.beta(0.5, 0.5),      # Beta分佈
            np.random.lognormal(0, 1)      # 對數正態分佈
        ]


class ModelPredictor:
    """模型預測器 - 發送預測請求"""
    
    def __init__(self, api_base_url: str = "http://localhost:8002"):
        self.api_base_url = api_base_url
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def predict(
        self, 
        features: ModelFeatures,
        endpoint: str = "/predict"
    ) -> Dict[str, Any]:
        """發送預測請求"""
        
        if not self.session:
            raise RuntimeError("ClientSession not initialized. Use async context manager.")
        
        # 準備請求數據
        request_data = {
            "features": [
                features.feature_1, features.feature_2, features.feature_3,
                features.feature_4, features.feature_5
            ],
            "model_version": features.model_version,  # 頂級字段供監控中間件使用
            "metadata": {
                "category": features.category,
                "region": features.region,
                "hour_of_day": features.hour_of_day,
                "day_of_week": features.day_of_week,
                "feature_type": features.feature_type,
                "model_version": features.model_version  # 保留在 metadata 中供 API 使用
            }
        }
        
        try:
            async with self.session.post(
                f"{self.api_base_url}{endpoint}",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                result = await response.json()
                
                return {
                    "status_code": response.status,
                    "response": result,
                    "features": asdict(features),
                    "endpoint": endpoint,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "status_code": 500,
                "error": str(e),
                "features": asdict(features),
                "endpoint": endpoint,
                "timestamp": datetime.now().isoformat()
            }


class AutoFeatureWorker:
    """自動特徵生成工作器"""
    
    def __init__(
        self,
        api_base_url: str = "http://localhost:8002",
        interval_seconds: float = 2.0,
        models: List[ModelVersion] = None
    ):
        self.api_base_url = api_base_url
        self.interval_seconds = interval_seconds
        self.models = models or [ModelVersion.V1_0, ModelVersion.V2_0]
        self.generator = FeatureGenerator()
        self.running = False
        
    async def start(self, duration_seconds: Optional[int] = None):
        """開始自動生成特徵並發送預測請求"""
        
        print(f"🚀 啟動自動特徵生成器...")
        print(f"📡 API 端點: {self.api_base_url}")
        print(f"⏱️ 請求間隔: {self.interval_seconds} 秒")
        print(f"🤖 模型版本: {[m.value for m in self.models]}")
        
        self.running = True
        start_time = datetime.now()
        request_count = 0
        
        async with ModelPredictor(self.api_base_url) as predictor:
            
            while self.running:
                try:
                    # 隨機選擇模型版本
                    model_version = random.choice(self.models)
                    
                    # 隨機選擇特徵類型（80% 正常，20% 其他）
                    feature_type = np.random.choice(
                        list(FeatureType),
                        p=[0.8, 0.1, 0.05, 0.05]  # normal, anomaly, high_load, error_prone
                    )
                    
                    # 生成特徵
                    features = self.generator.generate_features(
                        feature_type=feature_type,
                        model_version=model_version
                    )
                    
                    # 選擇端點（90% 標準預測，10% 其他端點）
                    endpoint = np.random.choice(
                        ["/predict", "/batch_predict", "/health"],
                        p=[0.9, 0.05, 0.05]
                    )
                    
                    # 發送預測請求
                    result = await predictor.predict(features, endpoint)
                    request_count += 1
                    
                    # 輸出結果
                    status = "✅" if result["status_code"] == 200 else "❌"
                    print(f"{status} #{request_count:3d} | {model_version.value} | {feature_type.value:10s} | {endpoint:15s} | {result['status_code']}")
                    
                    # 檢查運行時間
                    if duration_seconds and (datetime.now() - start_time).seconds >= duration_seconds:
                        break
                    
                    # 等待間隔
                    await asyncio.sleep(self.interval_seconds)
                    
                except KeyboardInterrupt:
                    print("\n🛑 收到中斷信號，正在停止...")
                    break
                except Exception as e:
                    print(f"❌ 請求失敗: {e}")
                    await asyncio.sleep(self.interval_seconds)
        
        self.running = False
        elapsed = (datetime.now() - start_time).seconds
        print(f"\n📊 生成總結:")
        print(f"  運行時間: {elapsed} 秒")
        print(f"  總請求數: {request_count}")
        print(f"  平均 QPS: {request_count / elapsed:.2f}" if elapsed > 0 else "")
    
    def stop(self):
        """停止生成器"""
        self.running = False


# 快速測試腳本
async def quick_test():
    """快速測試特徵生成和預測"""
    
    print("🧪 快速測試特徵生成器...")
    
    generator = FeatureGenerator()
    
    # 測試不同類型的特徵生成
    for feature_type in FeatureType:
        for model_version in ModelVersion:
            features = generator.generate_features(feature_type, model_version)
            print(f"  {model_version.value} - {feature_type.value}: {features.feature_1:.3f}, {features.feature_2:.3f}")
    
    print("✅ 特徵生成測試完成")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 快速測試
        asyncio.run(quick_test())
    else:
        # 運行自動生成器
        worker = AutoFeatureWorker(
            interval_seconds=1.5,  # 1.5秒間隔
            models=[ModelVersion.V1_0, ModelVersion.V2_0]
        )
        
        try:
            asyncio.run(worker.start(duration_seconds=None))  # 永續運行
        except KeyboardInterrupt:
            print("\n👋 程序已停止") 