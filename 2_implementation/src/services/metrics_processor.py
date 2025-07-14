"""
指標處理器主服務
協調 EventConsumer、MetricsAggregator、StorageManager 和 AlertManager
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from .event_consumer import EventConsumer
from .metrics_aggregator import MetricsAggregator
from .storage_manager import StorageManager
from .alert_manager import AlertManager
from ..components.metrics_event import MetricsEvent

logger = logging.getLogger(__name__)


class MetricsProcessor:
    """
    指標處理器主類別
    
    負責：
    1. 協調所有組件
    2. 事件處理流程控制
    3. 定期任務調度
    4. 系統健康檢查
    """
    
    def __init__(self,
                 processing_interval_seconds: int = 5,
                 storage_interval_seconds: int = 5,
                 alert_check_interval_seconds: int = 10):
        """
        初始化指標處理器
        
        Args:
            processing_interval_seconds: 處理間隔
            storage_interval_seconds: 存儲間隔  
            alert_check_interval_seconds: 告警檢查間隔
        """
        self.processing_interval = processing_interval_seconds
        self.storage_interval = storage_interval_seconds
        self.alert_check_interval = alert_check_interval_seconds
        
        # 組件實例
        self.event_consumer: Optional[EventConsumer] = None
        self.metrics_aggregator: Optional[MetricsAggregator] = None
        self.storage_manager: Optional[StorageManager] = None
        self.alert_manager: Optional[AlertManager] = None
        
        # 狀態控制
        self._is_running = False
        self._is_stopping = False
        self._processing_tasks = []
        
        # 統計信息
        self.stats = {
            "total_events_processed": 0,
            "total_aggregations": 0,
            "total_storage_operations": 0,
            "total_alert_checks": 0,
            "start_time": None,
            "last_processing_time": None,
            "errors_count": 0
        }
        
        logger.info("MetricsProcessor 已初始化")
    
    async def initialize(self) -> bool:
        """
        初始化所有組件
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.info("🚀 開始初始化 MetricsProcessor...")
            
            # 初始化組件
            self.metrics_aggregator = MetricsAggregator()
            self.storage_manager = StorageManager()
            self.alert_manager = AlertManager()
            self.event_consumer = EventConsumer()
            
            # 初始化存儲管理器
            storage_init_success = await self.storage_manager.initialize()
            if not storage_init_success:
                logger.error("StorageManager 初始化失敗")
                return False
            
            # 連接事件消費者
            consumer_connect_success = await self.event_consumer.connect()
            if not consumer_connect_success:
                logger.error("EventConsumer 連接失敗")
                return False
            
            # 設置事件處理器
            self.event_consumer.set_event_handler(self._handle_event)
            
            # 設置告警回調
            self.alert_manager.add_alert_callback(self._handle_alert)
            
            self.stats["start_time"] = datetime.utcnow()
            
            logger.info("✅ MetricsProcessor 初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ MetricsProcessor 初始化失敗: {e}")
            return False
    
    async def start(self) -> bool:
        """
        啟動指標處理器
        
        Returns:
            bool: 啟動是否成功
        """
        if self._is_running:
            logger.warning("MetricsProcessor 已在運行中")
            return True
        
        try:
            logger.info("🎯 啟動 MetricsProcessor...")
            
            # 啟動事件消費
            consumer_start_success = await self.event_consumer.start_consuming()
            if not consumer_start_success:
                logger.error("EventConsumer 啟動失敗")
                return False
            
            # 啟動定期任務
            self._start_background_tasks()
            
            self._is_running = True
            logger.info("✅ MetricsProcessor 已啟動")
            return True
            
        except Exception as e:
            logger.error(f"❌ MetricsProcessor 啟動失敗: {e}")
            return False
    
    async def stop(self):
        """停止指標處理器"""
        if not self._is_running:
            logger.info("MetricsProcessor 已停止")
            return
        
        logger.info("🛑 停止 MetricsProcessor...")
        self._is_stopping = True
        
        try:
            # 停止事件消費
            if self.event_consumer:
                await self.event_consumer.stop_consuming()
            
            # 取消背景任務
            for task in self._processing_tasks:
                task.cancel()
            
            # 等待任務完成
            if self._processing_tasks:
                await asyncio.gather(*self._processing_tasks, return_exceptions=True)
            
            # 執行最後的存儲操作
            if self.storage_manager:
                await self.storage_manager.force_batch_write()
            
            # 關閉連接
            if self.event_consumer:
                await self.event_consumer.disconnect()
            
            if self.storage_manager:
                await self.storage_manager.close()
            
            self._is_running = False
            self._is_stopping = False
            
            logger.info("✅ MetricsProcessor 已停止")
            
        except Exception as e:
            logger.error(f"❌ 停止 MetricsProcessor 時發生錯誤: {e}")
    
    def _start_background_tasks(self):
        """啟動背景任務"""
        # 定期處理任務
        self._processing_tasks.append(
            asyncio.create_task(self._processing_loop())
        )
        
        # 定期存儲任務
        self._processing_tasks.append(
            asyncio.create_task(self._storage_loop())
        )
        
        # 定期告警檢查任務
        self._processing_tasks.append(
            asyncio.create_task(self._alert_check_loop())
        )
        
        # 健康檢查任務
        self._processing_tasks.append(
            asyncio.create_task(self._health_check_loop())
        )
        
        logger.info("背景任務已啟動")
    
    async def _processing_loop(self):
        """處理循環"""
        logger.info("處理循環已啟動")
        
        while self._is_running and not self._is_stopping:
            try:
                await asyncio.sleep(self.processing_interval)
                
                # 這裡可以添加額外的定期處理邏輯
                self.stats["last_processing_time"] = datetime.utcnow()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"處理循環發生錯誤: {e}")
                self.stats["errors_count"] += 1
                await asyncio.sleep(1)  # 短暫等待後重試
    
    async def _storage_loop(self):
        """存儲循環"""
        logger.info("存儲循環已啟動")
        
        while self._is_running and not self._is_stopping:
            try:
                await asyncio.sleep(self.storage_interval)
                
                # 獲取當前聚合指標
                if self.metrics_aggregator:
                    current_metrics = self.metrics_aggregator.get_current_metrics()
                    
                    # 如果有數據，則存儲
                    if (current_metrics and 
                        current_metrics.get("overall", {}).get("total_requests", 0) > 0):
                        
                        if self.storage_manager:
                            await self.storage_manager.store_metrics(current_metrics)
                            self.stats["total_storage_operations"] += 1
                            logger.debug("指標數據已存儲")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"存儲循環發生錯誤: {e}")
                self.stats["errors_count"] += 1
                await asyncio.sleep(1)
    
    async def _alert_check_loop(self):
        """告警檢查循環"""
        logger.info("告警檢查循環已啟動")
        
        while self._is_running and not self._is_stopping:
            try:
                await asyncio.sleep(self.alert_check_interval)
                
                # 獲取當前聚合指標
                if self.metrics_aggregator and self.alert_manager:
                    current_metrics = self.metrics_aggregator.get_current_metrics()
                    
                    # 檢查告警
                    if current_metrics:
                        self.alert_manager.check_metrics(current_metrics)
                        self.stats["total_alert_checks"] += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"告警檢查循環發生錯誤: {e}")
                self.stats["errors_count"] += 1
                await asyncio.sleep(1)
    
    async def _health_check_loop(self):
        """健康檢查循環"""
        logger.info("健康檢查循環已啟動")
        
        while self._is_running and not self._is_stopping:
            try:
                await asyncio.sleep(30)  # 每 30 秒檢查一次
                
                # 檢查組件健康狀態
                await self._perform_health_check()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康檢查循環發生錯誤: {e}")
                await asyncio.sleep(5)
    
    async def _perform_health_check(self):
        """執行健康檢查"""
        try:
            health_status = await self.get_health_status()
            
            # 記錄健康狀態
            overall_healthy = health_status.get("overall_healthy", False)
            if not overall_healthy:
                logger.warning(f"系統健康檢查失敗: {health_status}")
            else:
                logger.debug("系統健康檢查通過")
                
        except Exception as e:
            logger.error(f"健康檢查執行失敗: {e}")
    
    async def _handle_event(self, event: MetricsEvent):
        """
        處理接收到的事件
        
        Args:
            event: 監控事件
        """
        try:
            # 添加到聚合器
            if self.metrics_aggregator:
                self.metrics_aggregator.add_event(event)
                
            self.stats["total_events_processed"] += 1
            logger.debug(f"事件已處理: {event.event_id}")
            
        except Exception as e:
            logger.error(f"處理事件失敗: {e}")
            self.stats["errors_count"] += 1
    
    async def _handle_alert(self, alert):
        """
        處理告警回調
        
        Args:
            alert: 告警對象
        """
        try:
            # 這裡可以添加告警通知邏輯
            # 例如：發送到 Slack、Email 等
            logger.info(f"告警處理: {alert.status.value} - {alert.message}")
            
        except Exception as e:
            logger.error(f"處理告警回調失敗: {e}")
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """獲取當前聚合指標"""
        if self.metrics_aggregator:
            return self.metrics_aggregator.get_current_metrics()
        return {}
    
    async def get_cached_metrics(self, metric_type: str = "overall") -> Optional[Dict[str, Any]]:
        """獲取快取的指標數據"""
        if self.storage_manager:
            return await self.storage_manager.get_cached_metrics(metric_type)
        return None
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """獲取活躍告警"""
        if self.alert_manager:
            return self.alert_manager.get_active_alerts()
        return []
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """獲取告警摘要"""
        if self.alert_manager:
            return self.alert_manager.get_alert_summary()
        return {}
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        獲取系統健康狀態
        
        Returns:
            Dict: 健康狀態信息
        """
        health_status = {
            "overall_healthy": True,
            "components": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # 檢查事件消費者
            if self.event_consumer:
                consumer_healthy = await self.event_consumer.is_healthy()
                health_status["components"]["event_consumer"] = {
                    "healthy": consumer_healthy,
                    "stats": self.event_consumer.get_stats()
                }
                if not consumer_healthy:
                    health_status["overall_healthy"] = False
            
            # 檢查聚合器
            if self.metrics_aggregator:
                aggregator_stats = self.metrics_aggregator.get_stats()
                health_status["components"]["metrics_aggregator"] = {
                    "healthy": True,  # 聚合器沒有連接依賴
                    "stats": aggregator_stats
                }
            
            # 檢查存儲管理器
            if self.storage_manager:
                storage_stats = self.storage_manager.get_stats()
                storage_healthy = (storage_stats.get("is_postgres_connected", False) and 
                                 storage_stats.get("is_redis_connected", False))
                health_status["components"]["storage_manager"] = {
                    "healthy": storage_healthy,
                    "stats": storage_stats
                }
                if not storage_healthy:
                    health_status["overall_healthy"] = False
            
            # 檢查告警管理器
            if self.alert_manager:
                alert_stats = self.alert_manager.get_stats()
                health_status["components"]["alert_manager"] = {
                    "healthy": True,  # 告警管理器沒有外部依賴
                    "stats": alert_stats
                }
            
            # 處理器狀態
            health_status["components"]["metrics_processor"] = {
                "healthy": self._is_running and not self._is_stopping,
                "stats": self.get_stats()
            }
            
        except Exception as e:
            logger.error(f"獲取健康狀態失敗: {e}")
            health_status["overall_healthy"] = False
            health_status["error"] = str(e)
        
        return health_status
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取處理器統計信息"""
        runtime = datetime.utcnow() - self.stats["start_time"] if self.stats["start_time"] else datetime.utcnow() - datetime.utcnow()
        
        stats = dict(self.stats)
        stats.update({
            "is_running": self._is_running,
            "is_stopping": self._is_stopping,
            "active_tasks": len(self._processing_tasks),
            "runtime_seconds": runtime.total_seconds(),
            "events_per_second": (self.stats["total_events_processed"] / runtime.total_seconds()) if runtime.total_seconds() > 0 else 0.0,
            "processing_interval": self.processing_interval,
            "storage_interval": self.storage_interval,
            "alert_check_interval": self.alert_check_interval
        })
        
        return stats
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """獲取所有組件的綜合統計信息"""
        comprehensive_stats = {
            "processor": self.get_stats(),
            "components": {}
        }
        
        if self.event_consumer:
            comprehensive_stats["components"]["event_consumer"] = self.event_consumer.get_stats()
        
        if self.metrics_aggregator:
            comprehensive_stats["components"]["metrics_aggregator"] = self.metrics_aggregator.get_stats()
        
        if self.storage_manager:
            comprehensive_stats["components"]["storage_manager"] = self.storage_manager.get_stats()
        
        if self.alert_manager:
            comprehensive_stats["components"]["alert_manager"] = self.alert_manager.get_stats()
        
        return comprehensive_stats


# 便捷函數
async def create_metrics_processor() -> MetricsProcessor:
    """
    創建並初始化指標處理器
    
    Returns:
        MetricsProcessor: 初始化的處理器實例
    """
    processor = MetricsProcessor()
    
    # 初始化
    initialized = await processor.initialize()
    if not initialized:
        raise RuntimeError("MetricsProcessor 初始化失敗")
    
    return processor 