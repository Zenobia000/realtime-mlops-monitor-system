"""
告警管理器服務
負責檢查指標閾值並觸發告警
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """告警嚴重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警狀態"""
    TRIGGERED = "triggered"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class AlertRule:
    """告警規則數據類"""
    id: str
    name: str
    metric_type: str  # 'qps', 'error_rate', 'avg_response_time', 'p95_response_time', 'p99_response_time'
    operator: str     # '>', '<', '>=', '<=', '=='
    threshold: float
    severity: AlertSeverity
    service_name: Optional[str] = None
    endpoint: Optional[str] = None
    duration_seconds: int = 60  # 持續時間
    enabled: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class Alert:
    """告警實例數據類"""
    id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    metric_value: float
    threshold: float
    service_name: Optional[str] = None
    endpoint: Optional[str] = None
    triggered_at: datetime = None
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.triggered_at is None:
            self.triggered_at = datetime.utcnow()


class AlertManager:
    """
    告警管理器
    
    負責：
    1. 管理告警規則
    2. 檢查指標閾值
    3. 觸發和解決告警
    4. 告警通知
    """
    
    def __init__(self):
        """初始化告警管理器"""
        # 告警規則存儲
        self.alert_rules: Dict[str, AlertRule] = {}
        
        # 活躍告警存儲
        self.active_alerts: Dict[str, Alert] = {}
        
        # 告警歷史 (最近 1000 條)
        self.alert_history: List[Alert] = []
        self.max_history_size = 1000
        
        # 告警回調函數
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
        # 統計信息
        self.stats = {
            "total_alerts_triggered": 0,
            "total_alerts_resolved": 0,
            "rule_checks_performed": 0,
            "last_check_time": None,
            "start_time": datetime.utcnow()
        }
        
        # 預設告警規則
        self._setup_default_rules()
        
        logger.info("AlertManager 已初始化")
    
    def _setup_default_rules(self):
        """設置預設告警規則"""
        default_rules = [
            AlertRule(
                id="high_error_rate",
                name="高錯誤率告警",
                metric_type="error_rate",
                operator=">",
                threshold=5.0,  # 5%
                severity=AlertSeverity.HIGH,
                duration_seconds=60
            ),
            AlertRule(
                id="critical_error_rate",
                name="嚴重錯誤率告警",
                metric_type="error_rate",
                operator=">",
                threshold=10.0,  # 10%
                severity=AlertSeverity.CRITICAL,
                duration_seconds=30
            ),
            AlertRule(
                id="high_response_time",
                name="高響應時間告警",
                metric_type="p95_response_time",
                operator=">",
                threshold=1000.0,  # 1000ms
                severity=AlertSeverity.MEDIUM,
                duration_seconds=120
            ),
            AlertRule(
                id="critical_response_time",
                name="嚴重響應時間告警",
                metric_type="p99_response_time",
                operator=">",
                threshold=5000.0,  # 5000ms
                severity=AlertSeverity.CRITICAL,
                duration_seconds=60
            ),
            AlertRule(
                id="low_qps",
                name="低 QPS 告警",
                metric_type="qps",
                operator="<",
                threshold=1.0,  # 1 QPS
                severity=AlertSeverity.LOW,
                duration_seconds=300
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.id] = rule
        
        logger.info(f"已設置 {len(default_rules)} 個預設告警規則")
    
    def add_alert_rule(self, rule: AlertRule) -> bool:
        """
        添加告警規則
        
        Args:
            rule: 告警規則
            
        Returns:
            bool: 是否添加成功
        """
        try:
            if rule.id in self.alert_rules:
                logger.warning(f"告警規則 {rule.id} 已存在，將被覆蓋")
            
            self.alert_rules[rule.id] = rule
            logger.info(f"告警規則已添加: {rule.name}")
            return True
            
        except Exception as e:
            logger.error(f"添加告警規則失敗: {e}")
            return False
    
    def remove_alert_rule(self, rule_id: str) -> bool:
        """
        移除告警規則
        
        Args:
            rule_id: 規則 ID
            
        Returns:
            bool: 是否移除成功
        """
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            logger.info(f"告警規則已移除: {rule_id}")
            return True
        else:
            logger.warning(f"告警規則不存在: {rule_id}")
            return False
    
    def get_alert_rules(self) -> List[Dict[str, Any]]:
        """獲取所有告警規則"""
        return [asdict(rule) for rule in self.alert_rules.values()]
    
    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """
        添加告警回調函數
        
        Args:
            callback: 回調函數，接收 Alert 對象
        """
        self.alert_callbacks.append(callback)
        logger.info("告警回調函數已添加")
    
    def check_metrics(self, metrics_data: Dict[str, Any]):
        """
        檢查指標數據並觸發告警
        
        Args:
            metrics_data: 聚合指標數據
        """
        try:
            self.stats["rule_checks_performed"] += 1
            self.stats["last_check_time"] = datetime.utcnow()
            
            # 檢查整體指標
            self._check_overall_metrics(metrics_data.get("overall", {}))
            
            # 檢查服務級指標
            for service_name, service_metrics in metrics_data.get("services", {}).items():
                self._check_service_metrics(service_name, service_metrics)
            
            # 檢查端點級指標
            for endpoint_key, endpoint_metrics in metrics_data.get("endpoints", {}).items():
                self._check_endpoint_metrics(endpoint_key, endpoint_metrics)
            
            logger.debug("指標檢查完成")
            
        except Exception as e:
            logger.error(f"檢查指標時發生錯誤: {e}")
    
    def _check_overall_metrics(self, overall_metrics: Dict[str, Any]):
        """檢查整體指標"""
        for rule in self.alert_rules.values():
            if not rule.enabled or rule.service_name or rule.endpoint:
                continue
            
            self._evaluate_rule(rule, overall_metrics)
    
    def _check_service_metrics(self, service_name: str, service_metrics: Dict[str, Any]):
        """檢查服務級指標"""
        for rule in self.alert_rules.values():
            if (not rule.enabled or 
                (rule.service_name and rule.service_name != service_name) or
                rule.endpoint):
                continue
            
            self._evaluate_rule(rule, service_metrics, service_name=service_name)
    
    def _check_endpoint_metrics(self, endpoint_key: str, endpoint_metrics: Dict[str, Any]):
        """檢查端點級指標"""
        # 解析端點信息
        if ":" in endpoint_key:
            service_name, endpoint = endpoint_key.split(":", 1)
        else:
            service_name, endpoint = None, endpoint_key
        
        for rule in self.alert_rules.values():
            if (not rule.enabled or
                (rule.service_name and rule.service_name != service_name) or
                (rule.endpoint and rule.endpoint != endpoint)):
                continue
            
            self._evaluate_rule(rule, endpoint_metrics, service_name=service_name, endpoint=endpoint)
    
    def _evaluate_rule(self, 
                      rule: AlertRule, 
                      metrics: Dict[str, Any],
                      service_name: Optional[str] = None,
                      endpoint: Optional[str] = None):
        """
        評估單個告警規則
        
        Args:
            rule: 告警規則
            metrics: 指標數據
            service_name: 服務名稱
            endpoint: 端點名稱
        """
        # 獲取指標值
        metric_value = metrics.get(rule.metric_type)
        if metric_value is None:
            return
        
        # 評估條件
        condition_met = self._evaluate_condition(metric_value, rule.operator, rule.threshold)
        
        # 生成告警 ID
        alert_id = self._generate_alert_id(rule, service_name, endpoint)
        
        if condition_met:
            # 觸發告警
            if alert_id not in self.active_alerts:
                alert = Alert(
                    id=alert_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    status=AlertStatus.TRIGGERED,
                    message=self._generate_alert_message(rule, metric_value, service_name, endpoint),
                    metric_value=metric_value,
                    threshold=rule.threshold,
                    service_name=service_name,
                    endpoint=endpoint
                )
                
                self._trigger_alert(alert)
        else:
            # 解決告警
            if alert_id in self.active_alerts:
                self._resolve_alert(alert_id)
    
    def _evaluate_condition(self, value: float, operator: str, threshold: float) -> bool:
        """評估條件"""
        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return abs(value - threshold) < 0.001  # 浮點數比較
        else:
            logger.warning(f"未知操作符: {operator}")
            return False
    
    def _generate_alert_id(self, 
                          rule: AlertRule, 
                          service_name: Optional[str] = None,
                          endpoint: Optional[str] = None) -> str:
        """生成告警 ID"""
        parts = [rule.id]
        
        if service_name:
            parts.append(service_name)
        
        if endpoint:
            parts.append(endpoint)
        
        return ":".join(parts)
    
    def _generate_alert_message(self, 
                               rule: AlertRule, 
                               metric_value: float,
                               service_name: Optional[str] = None,
                               endpoint: Optional[str] = None) -> str:
        """生成告警消息"""
        scope_parts = []
        if service_name:
            scope_parts.append(f"服務 {service_name}")
        if endpoint:
            scope_parts.append(f"端點 {endpoint}")
        
        scope_str = " ".join(scope_parts) if scope_parts else "整體系統"
        
        return (f"{scope_str} {rule.name}: "
                f"{rule.metric_type} = {metric_value:.2f} "
                f"{rule.operator} {rule.threshold} "
                f"(嚴重程度: {rule.severity.value})")
    
    def _trigger_alert(self, alert: Alert):
        """觸發告警"""
        self.active_alerts[alert.id] = alert
        self.alert_history.append(alert)
        
        # 限制歷史記錄大小
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size:]
        
        self.stats["total_alerts_triggered"] += 1
        
        logger.warning(f"🚨 告警觸發: {alert.message}")
        
        # 調用回調函數
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(alert))
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"告警回調執行失敗: {e}")
    
    def _resolve_alert(self, alert_id: str):
        """解決告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            
            # 從活躍告警中移除
            del self.active_alerts[alert_id]
            
            self.stats["total_alerts_resolved"] += 1
            
            logger.info(f"✅ 告警已解決: {alert.message}")
            
            # 調用回調函數
            for callback in self.alert_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(alert))
                    else:
                        callback(alert)
                except Exception as e:
                    logger.error(f"告警回調執行失敗: {e}")
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        確認告警
        
        Args:
            alert_id: 告警 ID
            
        Returns:
            bool: 是否確認成功
        """
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.utcnow()
            
            logger.info(f"告警已確認: {alert.message}")
            return True
        else:
            logger.warning(f"告警不存在或已解決: {alert_id}")
            return False
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """獲取活躍告警列表"""
        return [asdict(alert) for alert in self.active_alerts.values()]
    
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        獲取告警歷史
        
        Args:
            limit: 返回數量限制
            
        Returns:
            List: 告警歷史列表
        """
        # 按時間倒序返回
        sorted_history = sorted(self.alert_history, key=lambda x: x.triggered_at, reverse=True)
        return [asdict(alert) for alert in sorted_history[:limit]]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """獲取告警摘要統計"""
        # 按嚴重程度統計活躍告警
        severity_counts = {}
        for severity in AlertSeverity:
            severity_counts[severity.value] = 0
        
        for alert in self.active_alerts.values():
            severity_counts[alert.severity.value] += 1
        
        # 最近 24 小時告警統計
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        recent_alerts = [a for a in self.alert_history if a.triggered_at >= last_24h]
        
        return {
            "active_alerts_count": len(self.active_alerts),
            "active_alerts_by_severity": severity_counts,
            "total_rules": len(self.alert_rules),
            "enabled_rules": len([r for r in self.alert_rules.values() if r.enabled]),
            "alerts_last_24h": len(recent_alerts),
            "last_check_time": self.stats["last_check_time"].isoformat() if self.stats["last_check_time"] else None,
            "total_alerts_triggered": self.stats["total_alerts_triggered"],
            "total_alerts_resolved": self.stats["total_alerts_resolved"]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取告警管理器統計信息"""
        runtime = datetime.utcnow() - self.stats["start_time"]
        
        return {
            **self.stats,
            "active_alerts_count": len(self.active_alerts),
            "alert_history_size": len(self.alert_history),
            "total_rules": len(self.alert_rules),
            "enabled_rules": len([r for r in self.alert_rules.values() if r.enabled]),
            "runtime_seconds": runtime.total_seconds(),
            "checks_per_minute": (self.stats["rule_checks_performed"] / (runtime.total_seconds() / 60)) if runtime.total_seconds() > 0 else 0.0
        } 