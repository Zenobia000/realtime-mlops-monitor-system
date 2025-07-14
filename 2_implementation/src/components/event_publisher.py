"""
RabbitMQ 事件發送器
負責將監控事件異步發送到 RabbitMQ 佇列
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import aio_pika
from aio_pika import Message, DeliveryMode, connect_robust
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractQueue

from .metrics_event import MetricsEvent, HealthEvent
from ..api.config import get_settings

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    RabbitMQ 事件發送器
    
    負責：
    1. 建立和管理 RabbitMQ 連接
    2. 異步發送監控事件
    3. 實現重試機制
    4. 確保事件發送不影響主要業務邏輯
    """
    
    def __init__(self, rabbitmq_url: Optional[str] = None):
        """
        初始化事件發送器
        
        Args:
            rabbitmq_url: RabbitMQ 連接字串，None 時使用配置文件
        """
        self.settings = get_settings()
        self.rabbitmq_url = rabbitmq_url or self.settings.RABBITMQ_URL
        self.metrics_queue_name = self.settings.METRICS_QUEUE_NAME
        self.alerts_queue_name = self.settings.ALERTS_QUEUE_NAME
        
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.metrics_queue: Optional[AbstractQueue] = None
        self.alerts_queue: Optional[AbstractQueue] = None
        
        self._is_connected = False
        self._connection_lock = asyncio.Lock()
    
    async def connect(self) -> bool:
        """
        建立 RabbitMQ 連接
        
        Returns:
            bool: 連接是否成功
        """
        async with self._connection_lock:
            if self._is_connected:
                return True
            
            try:
                logger.info(f"正在連接 RabbitMQ: {self.rabbitmq_url}")
                
                # 建立連接
                self.connection = await connect_robust(
                    self.rabbitmq_url,
                    heartbeat=60,  # 心跳間隔
                    blocked_connection_timeout=300,  # 阻塞連接超時
                )
                
                # 建立頻道
                self.channel = await self.connection.channel()
                await self.channel.set_qos(prefetch_count=1000)  # 設置 QoS
                
                # 聲明佇列
                await self._declare_queues()
                
                self._is_connected = True
                logger.info("✅ RabbitMQ 連接成功")
                return True
                
            except Exception as e:
                logger.error(f"❌ RabbitMQ 連接失敗: {e}")
                self._is_connected = False
                return False
    
    async def _declare_queues(self):
        """聲明所需的佇列"""
        # 指標事件佇列
        self.metrics_queue = await self.channel.declare_queue(
            self.metrics_queue_name,
            durable=True,  # 持久化佇列
            arguments={
                "x-message-ttl": 86400000,  # 訊息 TTL: 24 小時
                "x-max-length": 100000,     # 最大訊息數量
            }
        )
        
        # 告警事件佇列
        self.alerts_queue = await self.channel.declare_queue(
            self.alerts_queue_name,
            durable=True,
            arguments={
                "x-message-ttl": 604800000,  # 訊息 TTL: 7 天
                "x-max-length": 10000,       # 最大訊息數量
            }
        )
        
        logger.info(f"✅ 佇列聲明完成: {self.metrics_queue_name}, {self.alerts_queue_name}")
    
    async def disconnect(self):
        """斷開 RabbitMQ 連接"""
        async with self._connection_lock:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                logger.info("RabbitMQ 連接已關閉")
            
            self._is_connected = False
            self.connection = None
            self.channel = None
            self.metrics_queue = None
            self.alerts_queue = None
    
    async def is_healthy(self) -> bool:
        """檢查發送器健康狀態"""
        return (
            self._is_connected and 
            self.connection and 
            not self.connection.is_closed and
            self.channel and
            not self.channel.is_closed
        )
    
    async def publish_metrics_event(
        self, 
        event: MetricsEvent, 
        max_retries: int = 3
    ) -> bool:
        """
        發送指標事件
        
        Args:
            event: 要發送的指標事件
            max_retries: 最大重試次數
            
        Returns:
            bool: 發送是否成功
        """
        if not await self.is_healthy():
            # 嘗試重新連接
            if not await self.connect():
                logger.warning("RabbitMQ 連接失敗，事件發送跳過")
                return False
        
        for attempt in range(max_retries + 1):
            try:
                # 準備訊息
                message_body = json.dumps(
                    event.to_rabbitmq_message(),
                    ensure_ascii=False,
                    separators=(',', ':')
                )
                
                message = Message(
                    message_body.encode('utf-8'),
                    delivery_mode=DeliveryMode.PERSISTENT,  # 持久化訊息
                    headers={
                        "event_type": event.event_type,
                        "service_name": event.service_name,
                        "timestamp": event.timestamp.isoformat(),
                        "attempt": attempt + 1
                    }
                )
                
                # 發送訊息
                await self.metrics_queue.channel.default_exchange.publish(
                    message,
                    routing_key=self.metrics_queue_name
                )
                
                logger.debug(
                    f"✅ 指標事件發送成功: {event.service_name}:{event.api_endpoint} "
                    f"(耗時: {event.response_time_ms}ms)"
                )
                return True
                
            except Exception as e:
                logger.warning(
                    f"⚠️ 指標事件發送失敗 (嘗試 {attempt + 1}/{max_retries + 1}): {e}"
                )
                
                if attempt < max_retries:
                    # 重試前等待
                    await asyncio.sleep(0.1 * (2 ** attempt))  # 指數退避
                    
                    # 嘗試重新連接
                    if not await self.is_healthy():
                        await self.connect()
        
        logger.error(f"❌ 指標事件發送徹底失敗: {event.event_id}")
        return False
    
    async def publish_health_event(
        self, 
        event: HealthEvent, 
        max_retries: int = 3
    ) -> bool:
        """
        發送健康事件
        
        Args:
            event: 要發送的健康事件
            max_retries: 最大重試次數
            
        Returns:
            bool: 發送是否成功
        """
        if not await self.is_healthy():
            if not await self.connect():
                return False
        
        for attempt in range(max_retries + 1):
            try:
                message_body = json.dumps(
                    event.dict(),
                    ensure_ascii=False,
                    separators=(',', ':'),
                    default=str
                )
                
                message = Message(
                    message_body.encode('utf-8'),
                    delivery_mode=DeliveryMode.PERSISTENT,
                    headers={
                        "event_type": event.event_type,
                        "service_name": event.service_name,
                        "health_status": event.health_status,
                        "timestamp": event.timestamp.isoformat()
                    }
                )
                
                await self.alerts_queue.channel.default_exchange.publish(
                    message,
                    routing_key=self.alerts_queue_name
                )
                
                logger.debug(f"✅ 健康事件發送成功: {event.service_name}")
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ 健康事件發送失敗 (嘗試 {attempt + 1}): {e}")
                
                if attempt < max_retries:
                    await asyncio.sleep(0.1 * (2 ** attempt))
                    if not await self.is_healthy():
                        await self.connect()
        
        return False
    
    async def publish_batch_events(
        self, 
        events: list[MetricsEvent], 
        batch_size: int = 100
    ) -> int:
        """
        批量發送事件
        
        Args:
            events: 事件列表
            batch_size: 批次大小
            
        Returns:
            int: 成功發送的事件數量
        """
        if not events:
            return 0
        
        success_count = 0
        
        # 分批發送
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            batch_tasks = []
            
            for event in batch:
                task = asyncio.create_task(
                    self.publish_metrics_event(event, max_retries=1)
                )
                batch_tasks.append(task)
            
            # 等待批次完成
            results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # 統計成功數量
            for result in results:
                if isinstance(result, bool) and result:
                    success_count += 1
        
        logger.info(f"📊 批量發送完成: {success_count}/{len(events)} 事件成功")
        return success_count


# 全域事件發送器實例
_global_publisher: Optional[EventPublisher] = None


async def get_event_publisher() -> EventPublisher:
    """
    獲取全域事件發送器實例
    
    Returns:
        EventPublisher: 事件發送器實例
    """
    global _global_publisher
    
    if _global_publisher is None:
        _global_publisher = EventPublisher()
        await _global_publisher.connect()
    
    return _global_publisher


async def publish_metrics_event_async(event: MetricsEvent) -> bool:
    """
    異步發送指標事件的便捷函數
    
    Args:
        event: 指標事件
        
    Returns:
        bool: 是否發送成功
    """
    try:
        publisher = await get_event_publisher()
        return await publisher.publish_metrics_event(event)
    except Exception as e:
        logger.error(f"事件發送失敗: {e}")
        return False 