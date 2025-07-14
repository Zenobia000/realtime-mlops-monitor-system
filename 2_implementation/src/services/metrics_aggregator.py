"""
指標聚合器服務
實現滑動視窗算法，計算 QPS、延遲統計、錯誤率等關鍵指標
"""

import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import statistics

from ..components.metrics_event import MetricsEvent, EventType

logger = logging.getLogger(__name__)


class TimeWindow:
    """
    時間視窗類別
    
    維護一個時間視窗內的所有事件數據
    """
    
    def __init__(self, window_start: datetime, duration_seconds: int = 5):
        """
        初始化時間視窗
        
        Args:
            window_start: 視窗開始時間
            duration_seconds: 視窗持續時間(秒)
        """
        self.window_start = window_start
        self.window_end = window_start + timedelta(seconds=duration_seconds)
        self.duration_seconds = duration_seconds
        
        # 事件列表
        self.events: List[MetricsEvent] = []
        
        # 統計數據
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.response_times: List[float] = []
        
        # 按服務和端點分組的統計
        self.service_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "request_count": 0,
            "error_count": 0,
            "total_response_time": 0.0,
            "response_times": []
        })
        
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "request_count": 0,
            "error_count": 0,
            "total_response_time": 0.0,
            "response_times": []
        })
    
    def add_event(self, event: MetricsEvent):
        """
        添加事件到視窗
        
        Args:
            event: 監控事件
        """
        # 檢查事件是否在視窗時間範圍內
        event_time = event.timestamp
        if not (self.window_start <= event_time < self.window_end):
            return False
        
        self.events.append(event)
        
        # 更新整體統計
        self.request_count += 1
        
        if event.status_code and event.status_code >= 400:
            self.error_count += 1
        
        if event.response_time_ms:
            self.total_response_time += event.response_time_ms
            self.response_times.append(event.response_time_ms)
        
        # 更新服務級統計
        if event.service_name:
            service_stat = self.service_stats[event.service_name]
            service_stat["request_count"] += 1
            
            if event.status_code and event.status_code >= 400:
                service_stat["error_count"] += 1
            
            if event.response_time_ms:
                service_stat["total_response_time"] += event.response_time_ms
                service_stat["response_times"].append(event.response_time_ms)
        
        # 更新端點級統計
        if event.api_endpoint:
            endpoint_key = f"{event.service_name}:{event.api_endpoint}"
            endpoint_stat = self.endpoint_stats[endpoint_key]
            endpoint_stat["request_count"] += 1
            
            if event.status_code and event.status_code >= 400:
                endpoint_stat["error_count"] += 1
            
            if event.response_time_ms:
                endpoint_stat["total_response_time"] += event.response_time_ms
                endpoint_stat["response_times"].append(event.response_time_ms)
        
        return True
    
    def get_qps(self) -> float:
        """計算每秒請求數"""
        return self.request_count / self.duration_seconds
    
    def get_error_rate(self) -> float:
        """計算錯誤率 (%)"""
        if self.request_count == 0:
            return 0.0
        return (self.error_count / self.request_count) * 100
    
    def get_avg_response_time(self) -> float:
        """計算平均響應時間"""
        if not self.response_times:
            return 0.0
        return statistics.mean(self.response_times)
    
    def get_percentile_response_time(self, percentile: float) -> float:
        """
        計算響應時間百分位數
        
        Args:
            percentile: 百分位數 (0-100)
            
        Returns:
            float: 對應百分位數的響應時間
        """
        if not self.response_times:
            return 0.0
        
        sorted_times = sorted(self.response_times)
        k = (len(sorted_times) - 1) * (percentile / 100)
        floor_k = int(k)
        ceil_k = floor_k + 1
        
        if ceil_k >= len(sorted_times):
            return sorted_times[-1]
        
        # 線性插值
        return sorted_times[floor_k] + (k - floor_k) * (sorted_times[ceil_k] - sorted_times[floor_k])
    
    def get_summary(self) -> Dict[str, Any]:
        """獲取視窗摘要統計"""
        return {
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "duration_seconds": self.duration_seconds,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "qps": self.get_qps(),
            "error_rate": self.get_error_rate(),
            "avg_response_time": self.get_avg_response_time(),
            "p95_response_time": self.get_percentile_response_time(95),
            "p99_response_time": self.get_percentile_response_time(99),
            "service_count": len(self.service_stats),
            "endpoint_count": len(self.endpoint_stats)
        }


class MetricsAggregator:
    """
    指標聚合器主類別
    
    實現滑動視窗算法：
    - 60 秒總視窗，包含 12 個 5 秒子視窗
    - 計算 QPS、延遲統計、錯誤率
    - 支援服務級和端點級聚合
    """
    
    def __init__(self, 
                 window_size_seconds: int = 60,
                 sub_window_seconds: int = 5):
        """
        初始化指標聚合器
        
        Args:
            window_size_seconds: 總視窗大小 (秒)
            sub_window_seconds: 子視窗大小 (秒)
        """
        self.window_size_seconds = window_size_seconds
        self.sub_window_seconds = sub_window_seconds
        self.num_sub_windows = window_size_seconds // sub_window_seconds
        
        # 滑動視窗佇列
        self.windows: deque[TimeWindow] = deque(maxlen=self.num_sub_windows)
        
        # 當前視窗
        self.current_window: Optional[TimeWindow] = None
        self.last_window_start: Optional[datetime] = None
        
        # 統計信息
        self.total_events_processed = 0
        self.aggregator_start_time = datetime.utcnow()
        
        logger.info(f"MetricsAggregator 已初始化 - 視窗: {window_size_seconds}s/{sub_window_seconds}s")
    
    def _get_window_start_time(self, event_time: datetime) -> datetime:
        """
        計算事件所屬視窗的開始時間
        
        Args:
            event_time: 事件時間
            
        Returns:
            datetime: 視窗開始時間
        """
        # 將時間對齊到子視窗邊界
        timestamp = int(event_time.timestamp())
        aligned_timestamp = (timestamp // self.sub_window_seconds) * self.sub_window_seconds
        return datetime.fromtimestamp(aligned_timestamp)
    
    def _ensure_current_window(self, event_time: datetime) -> TimeWindow:
        """
        確保當前視窗存在且正確
        
        Args:
            event_time: 事件時間
            
        Returns:
            TimeWindow: 當前視窗
        """
        window_start = self._get_window_start_time(event_time)
        
        # 如果當前視窗不存在或時間不匹配，創建新視窗
        if (not self.current_window or 
            self.current_window.window_start != window_start):
            
            # 保存舊視窗
            if self.current_window:
                self.windows.append(self.current_window)
            
            # 創建新視窗
            self.current_window = TimeWindow(window_start, self.sub_window_seconds)
            self.last_window_start = window_start
            
            logger.debug(f"創建新視窗: {window_start}")
        
        return self.current_window
    
    def add_event(self, event: MetricsEvent):
        """
        添加事件到聚合器
        
        Args:
            event: 監控事件
        """
        try:
            # 只處理 API 響應事件
            if event.event_type != EventType.API_RESPONSE:
                return
            
            # 確保當前視窗存在
            window = self._ensure_current_window(event.timestamp)
            
            # 添加事件到視窗
            if window.add_event(event):
                self.total_events_processed += 1
                logger.debug(f"事件已添加到視窗: {event.event_id}")
            else:
                logger.warning(f"事件時間超出視窗範圍: {event.event_id}")
                
        except Exception as e:
            logger.error(f"添加事件時發生錯誤: {e}")
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        獲取當前聚合指標
        
        Returns:
            Dict: 聚合指標數據
        """
        all_windows = list(self.windows)
        if self.current_window:
            all_windows.append(self.current_window)
        
        if not all_windows:
            return self._empty_metrics()
        
        # 聚合所有視窗的數據
        total_requests = sum(w.request_count for w in all_windows)
        total_errors = sum(w.error_count for w in all_windows)
        all_response_times = []
        
        for window in all_windows:
            all_response_times.extend(window.response_times)
        
        # 計算總體指標
        overall_qps = total_requests / self.window_size_seconds
        overall_error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0.0
        
        avg_response_time = statistics.mean(all_response_times) if all_response_times else 0.0
        p95_response_time = self._calculate_percentile(all_response_times, 95)
        p99_response_time = self._calculate_percentile(all_response_times, 99)
        
        # 收集服務級統計
        service_metrics = self._aggregate_service_metrics(all_windows)
        
        # 收集端點級統計
        endpoint_metrics = self._aggregate_endpoint_metrics(all_windows)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "window_size_seconds": self.window_size_seconds,
            "active_windows": len(all_windows),
            "overall": {
                "qps": round(overall_qps, 2),
                "error_rate": round(overall_error_rate, 2),
                "avg_response_time": round(avg_response_time, 2),
                "p95_response_time": round(p95_response_time, 2),
                "p99_response_time": round(p99_response_time, 2),
                "total_requests": total_requests,
                "total_errors": total_errors
            },
            "services": service_metrics,
            "endpoints": endpoint_metrics,
            "window_details": [w.get_summary() for w in all_windows[-5:]]  # 最近 5 個視窗
        }
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """返回空的指標數據"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "window_size_seconds": self.window_size_seconds,
            "active_windows": 0,
            "overall": {
                "qps": 0.0,
                "error_rate": 0.0,
                "avg_response_time": 0.0,
                "p95_response_time": 0.0,
                "p99_response_time": 0.0,
                "total_requests": 0,
                "total_errors": 0
            },
            "services": {},
            "endpoints": {},
            "window_details": []
        }
    
    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """計算百分位數"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * (percentile / 100)
        floor_k = int(k)
        ceil_k = floor_k + 1
        
        if ceil_k >= len(sorted_values):
            return sorted_values[-1]
        
        return sorted_values[floor_k] + (k - floor_k) * (sorted_values[ceil_k] - sorted_values[floor_k])
    
    def _aggregate_service_metrics(self, windows: List[TimeWindow]) -> Dict[str, Any]:
        """聚合服務級指標"""
        service_aggregated = defaultdict(lambda: {
            "request_count": 0,
            "error_count": 0,
            "response_times": []
        })
        
        # 聚合所有視窗的服務數據
        for window in windows:
            for service_name, stats in window.service_stats.items():
                service_agg = service_aggregated[service_name]
                service_agg["request_count"] += stats["request_count"]
                service_agg["error_count"] += stats["error_count"]
                service_agg["response_times"].extend(stats["response_times"])
        
        # 計算服務級指標
        result = {}
        for service_name, stats in service_aggregated.items():
            response_times = stats["response_times"]
            request_count = stats["request_count"]
            
            result[service_name] = {
                "qps": round(request_count / self.window_size_seconds, 2),
                "error_rate": round((stats["error_count"] / request_count * 100) if request_count > 0 else 0.0, 2),
                "avg_response_time": round(statistics.mean(response_times) if response_times else 0.0, 2),
                "p95_response_time": round(self._calculate_percentile(response_times, 95), 2),
                "p99_response_time": round(self._calculate_percentile(response_times, 99), 2),
                "total_requests": request_count,
                "total_errors": stats["error_count"]
            }
        
        return result
    
    def _aggregate_endpoint_metrics(self, windows: List[TimeWindow]) -> Dict[str, Any]:
        """聚合端點級指標"""
        endpoint_aggregated = defaultdict(lambda: {
            "request_count": 0,
            "error_count": 0,
            "response_times": []
        })
        
        # 聚合所有視窗的端點數據
        for window in windows:
            for endpoint_key, stats in window.endpoint_stats.items():
                endpoint_agg = endpoint_aggregated[endpoint_key]
                endpoint_agg["request_count"] += stats["request_count"]
                endpoint_agg["error_count"] += stats["error_count"]
                endpoint_agg["response_times"].extend(stats["response_times"])
        
        # 計算端點級指標
        result = {}
        for endpoint_key, stats in endpoint_aggregated.items():
            response_times = stats["response_times"]
            request_count = stats["request_count"]
            
            result[endpoint_key] = {
                "qps": round(request_count / self.window_size_seconds, 2),
                "error_rate": round((stats["error_count"] / request_count * 100) if request_count > 0 else 0.0, 2),
                "avg_response_time": round(statistics.mean(response_times) if response_times else 0.0, 2),
                "p95_response_time": round(self._calculate_percentile(response_times, 95), 2),
                "p99_response_time": round(self._calculate_percentile(response_times, 99), 2),
                "total_requests": request_count,
                "total_errors": stats["error_count"]
            }
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取聚合器統計信息"""
        runtime = datetime.utcnow() - self.aggregator_start_time
        
        return {
            "total_events_processed": self.total_events_processed,
            "active_windows": len(self.windows) + (1 if self.current_window else 0),
            "max_windows": self.num_sub_windows,
            "window_config": {
                "total_window_seconds": self.window_size_seconds,
                "sub_window_seconds": self.sub_window_seconds,
                "num_sub_windows": self.num_sub_windows
            },
            "runtime_seconds": runtime.total_seconds(),
            "events_per_second": (self.total_events_processed / runtime.total_seconds()) if runtime.total_seconds() > 0 else 0.0,
            "current_window_start": self.last_window_start.isoformat() if self.last_window_start else None
        } 