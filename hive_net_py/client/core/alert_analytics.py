"""
HiveNet 告警统计和分析模块
"""
import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from .event_monitor import Alert, AlertLevel
from .event_store import EventStore

logger = logging.getLogger(__name__)

class TimeRange(Enum):
    """时间范围"""
    HOUR = "1h"
    DAY = "24h"
    WEEK = "7d"
    MONTH = "30d"

@dataclass
class AlertStats:
    """告警统计信息"""
    total_count: int = 0                          # 总告警数
    level_counts: Dict[AlertLevel, int] = field(  # 各级别告警数
        default_factory=lambda: defaultdict(int)
    )
    rule_counts: Dict[str, int] = field(          # 各规则告警数
        default_factory=lambda: defaultdict(int)
    )
    source_counts: Dict[str, int] = field(        # 各来源告警数
        default_factory=lambda: defaultdict(int)
    )
    time_distribution: Dict[str, int] = field(    # 时间分布
        default_factory=lambda: defaultdict(int)
    )

@dataclass
class AlertTrend:
    """告警趋势"""
    timestamps: List[float]                       # 时间戳列表
    counts: List[int]                            # 计数列表
    level_series: Dict[AlertLevel, List[int]]    # 各级别趋势
    rule_series: Dict[str, List[int]]           # 各规则趋势

@dataclass
class AlertPattern:
    """告警模式"""
    rule_name: str                               # 规则名称
    source: str                                  # 告警来源
    level: AlertLevel                           # 告警级别
    frequency: float                            # 频率(次/小时)
    avg_interval: float                         # 平均间隔(秒)
    correlation_score: float                    # 相关性得分

class AlertAnalytics:
    """告警分析器"""
    
    def __init__(self, event_store: EventStore):
        """
        初始化告警分析器
        
        Args:
            event_store: 事件存储器
        """
        self.event_store = event_store
        self._stats_cache: Dict[TimeRange, Tuple[float, AlertStats]] = {}
        self._trend_cache: Dict[TimeRange, Tuple[float, AlertTrend]] = {}
        self._pattern_cache: Optional[Tuple[float, List[AlertPattern]]] = None
        self._cache_ttl = 300  # 缓存��效期(秒)
    
    async def get_stats(self, time_range: TimeRange) -> AlertStats:
        """
        获取告警统计信息
        
        Args:
            time_range: 时间范围
            
        Returns:
            告警统计信息
        """
        # 检查缓存
        if time_range in self._stats_cache:
            timestamp, stats = self._stats_cache[time_range]
            if time.time() - timestamp < self._cache_ttl:
                return stats
        
        # 计算时间范围
        end_time = time.time()
        start_time = self._get_start_time(end_time, time_range)
        
        # 获取告警
        alerts = await self.event_store.get_events(
            start_time=start_time,
            end_time=end_time,
            event_types=["Alert"]
        )
        
        # 创建统计信息
        stats = AlertStats()
        stats.total_count = len(alerts)
        
        # 统计各维度数据
        hour_buckets = defaultdict(int)
        for alert in alerts:
            # 转换为Alert类型
            if not isinstance(alert, Alert):
                continue
                
            # 级别统计
            stats.level_counts[alert.level] += 1
            
            # 规则统计
            stats.rule_counts[alert.rule_name] += 1
            
            # 来源统计
            stats.source_counts[alert.source] += 1
            
            # 时间分布(按小时)
            hour = datetime.fromtimestamp(alert.timestamp).strftime("%Y-%m-%d %H:00")
            hour_buckets[hour] += 1
        
        # 排序时间分布
        stats.time_distribution = dict(sorted(hour_buckets.items()))
        
        # 更新缓存
        self._stats_cache[time_range] = (time.time(), stats)
        
        return stats
    
    async def get_trend(self, time_range: TimeRange) -> AlertTrend:
        """
        获取告警趋势
        
        Args:
            time_range: 时间范围
            
        Returns:
            告警趋势
        """
        # 检查缓存
        if time_range in self._trend_cache:
            timestamp, trend = self._trend_cache[time_range]
            if time.time() - timestamp < self._cache_ttl:
                return trend
        
        # 计算时间范围
        end_time = time.time()
        start_time = self._get_start_time(end_time, time_range)
        
        # 获取告警
        alerts = await self.event_store.get_events(
            start_time=start_time,
            end_time=end_time,
            event_types=["Alert"]
        )
        
        # 按时间间隔分组
        interval = self._get_interval(time_range)
        buckets: Dict[int, List[Alert]] = defaultdict(list)
        
        for alert in alerts:
            if not isinstance(alert, Alert):
                continue
            bucket = int(alert.timestamp / interval) * interval
            buckets[bucket].append(alert)
        
        # 生成时间序列
        timestamps = []
        counts = []
        level_series = {level: [] for level in AlertLevel}
        rule_series: Dict[str, List[int]] = defaultdict(list)
        
        current_time = start_time
        while current_time <= end_time:
            bucket = int(current_time / interval) * interval
            bucket_alerts = buckets.get(bucket, [])
            
            # 总数
            timestamps.append(bucket)
            counts.append(len(bucket_alerts))
            
            # 各级别数量
            for level in AlertLevel:
                level_count = sum(1 for a in bucket_alerts if a.level == level)
                level_series[level].append(level_count)
            
            # 各规则数量
            rules = set(a.rule_name for a in bucket_alerts)
            for rule in rules:
                rule_count = sum(1 for a in bucket_alerts if a.rule_name == rule)
                rule_series[rule].append(rule_count)
            
            current_time += interval
        
        # 创建趋势对象
        trend = AlertTrend(
            timestamps=timestamps,
            counts=counts,
            level_series=level_series,
            rule_series=rule_series
        )
        
        # 更新缓存
        self._trend_cache[time_range] = (time.time(), trend)
        
        return trend
    
    async def get_patterns(self, min_frequency: float = 1.0,
                          min_correlation: float = 0.5) -> List[AlertPattern]:
        """
        获取告警模式
        
        Args:
            min_frequency: 最小频率(次/小时)
            min_correlation: 最小相关性得分
            
        Returns:
            告警模式列表
        """
        # 检查缓存
        if self._pattern_cache:
            timestamp, patterns = self._pattern_cache
            if time.time() - timestamp < self._cache_ttl:
                return patterns
        
        # 获取最近24小时的告警
        end_time = time.time()
        start_time = end_time - 24 * 3600
        
        alerts = await self.event_store.get_events(
            start_time=start_time,
            end_time=end_time,
            event_types=["Alert"]
        )
        
        # 按规则和来源分组
        groups: Dict[Tuple[str, str], List[Alert]] = defaultdict(list)
        for alert in alerts:
            if not isinstance(alert, Alert):
                continue
            key = (alert.rule_name, alert.source)
            groups[key].append(alert)
        
        # 分析模式
        patterns = []
        for (rule_name, source), group_alerts in groups.items():
            # 计算频率
            duration = (end_time - start_time) / 3600  # 小时
            frequency = len(group_alerts) / duration
            
            if frequency < min_frequency:
                continue
            
            # 计算平均间隔
            if len(group_alerts) > 1:
                intervals = []
                sorted_alerts = sorted(group_alerts, key=lambda x: x.timestamp)
                for i in range(1, len(sorted_alerts)):
                    interval = sorted_alerts[i].timestamp - sorted_alerts[i-1].timestamp
                    intervals.append(interval)
                avg_interval = sum(intervals) / len(intervals)
            else:
                avg_interval = 0
            
            # 计算相关性得分
            correlation_score = self._calculate_correlation_score(group_alerts)
            
            if correlation_score < min_correlation:
                continue
            
            # 创建模式
            pattern = AlertPattern(
                rule_name=rule_name,
                source=source,
                level=group_alerts[0].level,  # 使用第一个告警的级别
                frequency=frequency,
                avg_interval=avg_interval,
                correlation_score=correlation_score
            )
            patterns.append(pattern)
        
        # 按频率排序
        patterns.sort(key=lambda x: x.frequency, reverse=True)
        
        # 更新缓存
        self._pattern_cache = (time.time(), patterns)
        
        return patterns
    
    async def get_top_sources(self, time_range: TimeRange,
                            limit: int = 10) -> List[Tuple[str, int]]:
        """
        获取告警数最多的来源
        
        Args:
            time_range: 时间范围
            limit: 返回数量
            
        Returns:
            (来源, 告警数)列表
        """
        stats = await self.get_stats(time_range)
        return sorted(
            stats.source_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
    
    async def get_top_rules(self, time_range: TimeRange,
                           limit: int = 10) -> List[Tuple[str, int]]:
        """
        获取触发最多的规则
        
        Args:
            time_range: 时间范��
            limit: 返回数量
            
        Returns:
            (规则名, 告警数)列表
        """
        stats = await self.get_stats(time_range)
        return sorted(
            stats.rule_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
    
    def _get_start_time(self, end_time: float, time_range: TimeRange) -> float:
        """获取开始时间"""
        if time_range == TimeRange.HOUR:
            return end_time - 3600
        elif time_range == TimeRange.DAY:
            return end_time - 24 * 3600
        elif time_range == TimeRange.WEEK:
            return end_time - 7 * 24 * 3600
        else:  # MONTH
            return end_time - 30 * 24 * 3600
    
    def _get_interval(self, time_range: TimeRange) -> float:
        """获取时间间隔"""
        if time_range == TimeRange.HOUR:
            return 60  # 1分钟
        elif time_range == TimeRange.DAY:
            return 3600  # 1小时
        elif time_range == TimeRange.WEEK:
            return 6 * 3600  # 6小时
        else:  # MONTH
            return 24 * 3600  # 1天
    
    def _calculate_correlation_score(self, alerts: List[Alert]) -> float:
        """
        计算告警相关性得分
        
        使用以下因素：
        1. 时间间隔的��致性
        2. 消息内容的相似度
        3. 级别的一致性
        """
        if len(alerts) < 2:
            return 0.0
        
        # 计算时间间隔一致性
        intervals = []
        sorted_alerts = sorted(alerts, key=lambda x: x.timestamp)
        for i in range(1, len(sorted_alerts)):
            interval = sorted_alerts[i].timestamp - sorted_alerts[i-1].timestamp
            intervals.append(interval)
        
        if not intervals:
            return 0.0
        
        avg_interval = sum(intervals) / len(intervals)
        interval_variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)
        interval_score = 1.0 / (1.0 + interval_variance)
        
        # 计算级别一致性
        levels = set(a.level for a in alerts)
        level_score = 1.0 if len(levels) == 1 else 0.5
        
        # 计算最终得分
        return (interval_score + level_score) / 2.0

class AlertAnalysisTask:
    """告警分析任务"""
    
    def __init__(self, analytics: AlertAnalytics,
                 analysis_interval: float = 3600):
        """
        初始化分析任务
        
        Args:
            analytics: 告警分析器
            analysis_interval: 分析间隔(秒)
        """
        self.analytics = analytics
        self.analysis_interval = analysis_interval
        self._task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """启动分析任务"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._analysis_loop())
        logger.info("告警分析任务已启动")
    
    async def stop(self):
        """停止分析任务"""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("告警分析任务已停止")
    
    async def _analysis_loop(self):
        """分析循环"""
        try:
            while self._running:
                try:
                    # 执行分析
                    await self._analyze()
                except Exception as e:
                    logger.error(f"执行告警分析时出错: {e}")
                
                # 等待下一个分析周期
                await asyncio.sleep(self.analysis_interval)
        except asyncio.CancelledError:
            pass
    
    async def _analyze(self):
        """执行分析"""
        # 获取统计信息
        for time_range in TimeRange:
            stats = await self.analytics.get_stats(time_range)
            logger.info(
                f"时间范围 {time_range.value} 的告警统计:\n"
                f"总数: {stats.total_count}\n"
                f"级别分布: {dict(stats.level_counts)}"
            )
        
        # 获取模式
        patterns = await self.analytics.get_patterns()
        if patterns:
            logger.info(
                "检测到的告警模式:\n" +
                "\n".join(
                    f"- {p.rule_name} ({p.source}): "
                    f"频率={p.frequency:.2f}/小时, "
                    f"间隔={p.avg_interval:.1f}秒, "
                    f"相关性={p.correlation_score:.2f}"
                    for p in patterns
                )
            ) 