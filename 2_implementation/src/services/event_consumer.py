"""
事件消費者服務
負責從 RabbitMQ 佇列消費監控事件，並將其傳遞給指標聚合器
"""

import asyncio
import json
import logging
from typing import Callable, Optional, Dict, Any
from datetime import datetime

import aio_pika
from aio_pika import Message, IncomingMessage

from ..components.metrics_event import MetricsEvent
from ..api.config import get_settings

logger = logging.getLogger(__name__)


class EventConsumer:
    """
    RabbitMQ 事件消費者
    
    負責：
    1. 連接 RabbitMQ 佇列
    2. 消費監控事件
    3. 解析事件數據
    4. 將事件傳遞給處理回調函數
    """
    
    def __init__(self, 
                 queue_name: str = "metrics.api_requests",
                 prefetch_count: int = 10):
        """
        初始化事件消費者
        
        Args:
            queue_name: 要消費的佇列名稱
            prefetch_count: 預取消息數量
        """
        self.settings = get_settings()
        self.queue_name = queue_name
        self.prefetch_count = prefetch_count
        
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queue: Optional[aio_pika.Queue] = None
        
        self._is_consuming = False
        self._consumer_tag: Optional[str] = None
        self._event_handler: Optional[Callable[[MetricsEvent], None]] = None
        
        # 統計信息
        self.stats = {
            "total_consumed": 0,
            "successful_processed": 0,
            "failed_processed": 0,
            "invalid_messages": 0,
            "start_time": None,
            "last_message_time": None
        }
        
        logger.info(f"EventConsumer 已初始化 - 佇列: {queue_name}")
    
    async def connect(self) -> bool:
        """
        連接到 RabbitMQ
        
        Returns:
            bool: 連接是否成功
        """
        try:
            # 建立連接
            self.connection = await aio_pika.connect_robust(
                self.settings.RABBITMQ_URL,
                loop=asyncio.get_event_loop()
            )
            
            # 創建頻道
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=self.prefetch_count)
            
            # 聲明佇列 (確保存在)
            self.queue = await self.channel.declare_queue(
                self.queue_name,
                durable=True,
                arguments={
                    "x-message-ttl": 86400000,  # 24 小時
                    "x-max-length": 100000       # 最大訊息數
                }
            )
            
            logger.info(f"✅ EventConsumer 連接成功 - 佇列: {self.queue_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ EventConsumer 連接失敗: {e}")
            return False
    
    async def disconnect(self):
        """斷開 RabbitMQ 連接"""
        try:
            if self._is_consuming:
                await self.stop_consuming()
            
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            
            logger.info("EventConsumer 連接已關閉")
            
        except Exception as e:
            logger.error(f"EventConsumer 斷開連接時發生錯誤: {e}")
    
    def set_event_handler(self, handler: Callable[[MetricsEvent], None]):
        """
        設置事件處理回調函數
        
        Args:
            handler: 事件處理函數，接收 MetricsEvent 對象
        """
        self._event_handler = handler
        logger.info("事件處理器已設置")
    
    async def start_consuming(self) -> bool:
        """
        開始消費事件
        
        Returns:
            bool: 是否成功開始消費
        """
        if not self.queue:
            logger.error("佇列未初始化，無法開始消費")
            return False
        
        if not self._event_handler:
            logger.error("事件處理器未設置，無法開始消費")
            return False
        
        try:
            # 開始消費
            await self.queue.consume(self._process_message)
            self._is_consuming = True
            self.stats["start_time"] = datetime.utcnow()
            
            logger.info(f"✅ 開始消費事件 - 佇列: {self.queue_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 開始消費失敗: {e}")
            return False
    
    async def stop_consuming(self):
        """停止消費事件"""
        if self._is_consuming and self.queue:
            try:
                await self.queue.cancel(self._consumer_tag)
                self._is_consuming = False
                logger.info("事件消費已停止")
            except Exception as e:
                logger.error(f"停止消費時發生錯誤: {e}")
    
    async def _process_message(self, message: IncomingMessage):
        """
        處理接收到的消息
        
        Args:
            message: 接收到的 RabbitMQ 消息
        """
        async with message.process():
            try:
                self.stats["total_consumed"] += 1
                self.stats["last_message_time"] = datetime.utcnow()
                
                # 解析消息
                try:
                    message_body = message.body.decode('utf-8')
                    event_data = json.loads(message_body)
                    
                    # 創建 MetricsEvent 對象
                    metrics_event = MetricsEvent(**event_data)
                    
                    logger.debug(f"收到監控事件: {metrics_event.event_id}")
                    
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    logger.warning(f"無效消息格式: {e}")
                    self.stats["invalid_messages"] += 1
                    return
                
                # 調用事件處理器
                try:
                    if asyncio.iscoroutinefunction(self._event_handler):
                        await self._event_handler(metrics_event)
                    else:
                        self._event_handler(metrics_event)
                    
                    self.stats["successful_processed"] += 1
                    logger.debug(f"事件處理成功: {metrics_event.event_id}")
                    
                except Exception as e:
                    logger.error(f"事件處理失敗: {e}")
                    self.stats["failed_processed"] += 1
                    # 不 raise，避免消息重新入佇列
                
            except Exception as e:
                logger.error(f"消息處理過程中發生未預期錯誤: {e}")
                # 消息將被拒絕並可能重新入佇列
                raise
    
    def get_stats(self) -> Dict[str, Any]:
        """
        獲取消費者統計信息
        
        Returns:
            Dict: 統計信息
        """
        stats = dict(self.stats)
        
        # 計算運行時間
        if stats["start_time"]:
            runtime = datetime.utcnow() - stats["start_time"]
            stats["runtime_seconds"] = runtime.total_seconds()
            
            # 計算每秒處理量
            if stats["runtime_seconds"] > 0:
                stats["messages_per_second"] = stats["total_consumed"] / stats["runtime_seconds"]
            else:
                stats["messages_per_second"] = 0.0
        
        # 計算成功率
        if stats["total_consumed"] > 0:
            stats["success_rate"] = (stats["successful_processed"] / stats["total_consumed"]) * 100
        else:
            stats["success_rate"] = 0.0
        
        stats.update({
            "queue_name": self.queue_name,
            "is_consuming": self._is_consuming,
            "is_connected": self.connection is not None and not self.connection.is_closed
        })
        
        return stats
    
    async def is_healthy(self) -> bool:
        """
        檢查消費者健康狀態
        
        Returns:
            bool: 是否健康
        """
        try:
            # 檢查連接狀態
            if not self.connection or self.connection.is_closed:
                return False
            
            # 檢查是否正在消費
            if not self._is_consuming:
                return False
            
            # 檢查最近是否有收到消息 (過去 5 分鐘)
            if self.stats["last_message_time"]:
                time_since_last = datetime.utcnow() - self.stats["last_message_time"]
                if time_since_last.total_seconds() > 300:  # 5 分鐘
                    logger.warning("超過 5 分鐘未收到消息")
            
            return True
            
        except Exception as e:
            logger.error(f"健康檢查失敗: {e}")
            return False


# 便捷函數
async def create_event_consumer(
    queue_name: str = "metrics.api_requests",
    event_handler: Optional[Callable[[MetricsEvent], None]] = None
) -> EventConsumer:
    """
    創建並初始化事件消費者
    
    Args:
        queue_name: 佇列名稱
        event_handler: 事件處理函數
        
    Returns:
        EventConsumer: 初始化的消費者實例
    """
    consumer = EventConsumer(queue_name)
    
    # 連接 RabbitMQ
    connected = await consumer.connect()
    if not connected:
        raise RuntimeError("無法連接到 RabbitMQ")
    
    # 設置事件處理器
    if event_handler:
        consumer.set_event_handler(event_handler)
    
    return consumer 