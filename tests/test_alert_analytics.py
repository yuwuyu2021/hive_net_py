"""
告警统计和分析测试
"""
import asyncio
import time
from typing import List
import pytest

from hive_net_py.client.core.event_monitor import Alert, AlertLevel
from hive_net_py.client.core.event_store import JSONEventStore
from hive_net_py.client.core.alert_analytics import (
    TimeRange,
    AlertStats,
    AlertTrend,
    AlertPattern,
    AlertAnalytics,
    AlertAnalysisTask
)

@pytest.fixture
def event_store(tmp_path):
    """创建事件存储"""
    return JSONEventStore(tmp_path / "events.json")

@pytest.fixture
def analytics(event_store):
    """创建告警分析器"""
    return AlertAnalytics(event_store)

@pytest.fixture
async def test_alerts(event_store):
    """创建测试告警"""
    current_time = time.time()
    alerts = [
        # 错误告警组1 - 每小时2次
        Alert(
            rule_name="error_rate",
            level=AlertLevel.ERROR,
            message="High error rate",
            source="service_1",
            timestamp=current_time - 3600 * i / 2,
            events=[],
            context={}
        )
        for i in range(48)  # 24小时内48次
    ] + [
        # 警告告警组 - 每小时1次
        Alert(
            rule_name="cpu_usage",
            level=AlertLevel.WARNING,
            message="High CPU usage",
            source="service_2",
            timestamp=current_time - 3600 * i,
            events=[],
            context={}
        )
        for i in range(24)  # 24小时内24次
    ] + [
        # 错误告警组2 - 不规则间隔
        Alert(
            rule_name="connection_error",
            level=AlertLevel.ERROR,
            message="Connection failed",
            source="service_3",
            timestamp=current_time - i * 1234,  # 不规则间隔
            events=[],
            context={}
        )
        for i in range(10)  # 10次随机间隔
    ]
    
    # 存储告警
    for alert in alerts:
        await event_store.store_event(alert)
    
    return alerts

@pytest.mark.asyncio
async def test_get_stats(analytics, test_alerts):
    """测试获取统计信息"""
    # 获取24小时统计
    stats = await analytics.get_stats(TimeRange.DAY)
    
    # 验证总数
    assert stats.total_count == len(test_alerts)
    
    # 验证级别分布
    assert stats.level_counts[AlertLevel.ERROR] == 58  # 48 + 10
    assert stats.level_counts[AlertLevel.WARNING] == 24
    
    # 验证规则分布
    assert stats.rule_counts["error_rate"] == 48
    assert stats.rule_counts["cpu_usage"] == 24
    assert stats.rule_counts["connection_error"] == 10
    
    # 验证来源分布
    assert stats.source_counts["service_1"] == 48
    assert stats.source_counts["service_2"] == 24
    assert stats.source_counts["service_3"] == 10
    
    # 验证时间分布
    assert len(stats.time_distribution) > 0

@pytest.mark.asyncio
async def test_get_trend(analytics, test_alerts):
    """测试获取趋势"""
    # 获取24小时趋势
    trend = await analytics.get_trend(TimeRange.DAY)
    
    # 验证时间序列
    assert len(trend.timestamps) > 0
    assert len(trend.counts) == len(trend.timestamps)
    
    # 验证级别趋势
    assert AlertLevel.ERROR in trend.level_series
    assert AlertLevel.WARNING in trend.level_series
    assert len(trend.level_series[AlertLevel.ERROR]) == len(trend.timestamps)
    assert len(trend.level_series[AlertLevel.WARNING]) == len(trend.timestamps)
    
    # 验证规则趋势
    assert "error_rate" in trend.rule_series
    assert "cpu_usage" in trend.rule_series
    assert "connection_error" in trend.rule_series

@pytest.mark.asyncio
async def test_get_patterns(analytics, test_alerts):
    """测试获取模式"""
    # 获取告警模式
    patterns = await analytics.get_patterns(min_frequency=1.0)
    
    # 验证模式数量
    assert len(patterns) >= 2  # 至少应该有2个规律模式
    
    # 验证模式属性
    for pattern in patterns:
        assert pattern.frequency > 0
        assert pattern.correlation_score >= 0
        assert pattern.correlation_score <= 1
        
        # error_rate应该是最频繁的模式
        if pattern.rule_name == "error_rate":
            assert pattern.frequency == pytest.approx(2.0, rel=0.1)  # 每小时2次
            assert pattern.correlation_score > 0.8  # 高相关性

@pytest.mark.asyncio
async def test_get_top_sources(analytics, test_alerts):
    """测试获取TOP来源"""
    # 获取TOP来源
    top_sources = await analytics.get_top_sources(TimeRange.DAY, limit=2)
    
    # 验证结果
    assert len(top_sources) == 2
    assert top_sources[0][0] == "service_1"  # 最多告警的服务
    assert top_sources[0][1] == 48
    assert top_sources[1][0] == "service_2"
    assert top_sources[1][1] == 24

@pytest.mark.asyncio
async def test_get_top_rules(analytics, test_alerts):
    """测试获取TOP规则"""
    # 获取TOP规则
    top_rules = await analytics.get_top_rules(TimeRange.DAY, limit=2)
    
    # 验证结果
    assert len(top_rules) == 2
    assert top_rules[0][0] == "error_rate"  # 最常触发的规则
    assert top_rules[0][1] == 48
    assert top_rules[1][0] == "cpu_usage"
    assert top_rules[1][1] == 24

@pytest.mark.asyncio
async def test_cache_mechanism(analytics, test_alerts):
    """测试缓存机制"""
    # 第一次调用
    start_time = time.time()
    stats1 = await analytics.get_stats(TimeRange.DAY)
    end_time = time.time()
    first_call_time = end_time - start_time
    
    # 第二次调用（应该走缓存）
    start_time = time.time()
    stats2 = await analytics.get_stats(TimeRange.DAY)
    end_time = time.time()
    second_call_time = end_time - start_time
    
    # 验证缓存生效
    assert second_call_time < first_call_time
    assert stats1.total_count == stats2.total_count

@pytest.mark.asyncio
async def test_analysis_task(analytics):
    """测试分析任务"""
    # 创建分析任务
    task = AlertAnalysisTask(analytics, analysis_interval=1)
    
    try:
        # 启动任务
        await task.start()
        
        # 等待一次分析完成
        await asyncio.sleep(2)
        
        # 验证任务状态
        assert task._running
        assert task._task is not None
        
    finally:
        # 停止任务
        await task.stop()
        assert not task._running
        assert task._task is None

@pytest.mark.asyncio
async def test_time_ranges(analytics, test_alerts):
    """测试不同时间范围"""
    # 测试所有时间范围
    for time_range in TimeRange:
        # 获取统计信息
        stats = await analytics.get_stats(time_range)
        assert stats.total_count > 0
        
        # 获取趋势
        trend = await analytics.get_trend(time_range)
        assert len(trend.timestamps) > 0
        
        # 验证时间间隔
        if time_range == TimeRange.HOUR:
            assert analytics._get_interval(time_range) == 60
        elif time_range == TimeRange.DAY:
            assert analytics._get_interval(time_range) == 3600
        elif time_range == TimeRange.WEEK:
            assert analytics._get_interval(time_range) == 6 * 3600
        else:  # MONTH
            assert analytics._get_interval(time_range) == 24 * 3600

@pytest.mark.asyncio
async def test_correlation_score(analytics):
    """测试相关性得分计算"""
    current_time = time.time()
    
    # 创建高相关性告警组（固定间隔）
    high_corr_alerts = [
        Alert(
            rule_name="test_rule",
            level=AlertLevel.ERROR,
            message="Test error",
            source="test_source",
            timestamp=current_time - i * 3600,  # 每小时一次
            events=[],
            context={}
        )
        for i in range(10)
    ]
    
    # 创建低相关性告警组（随机间隔）
    low_corr_alerts = [
        Alert(
            rule_name="test_rule",
            level=AlertLevel.ERROR,
            message="Test error",
            source="test_source",
            timestamp=current_time - i * 1234,  # 随机间隔
            events=[],
            context={}
        )
        for i in range(10)
    ]
    
    # 计算相关性得分
    high_score = analytics._calculate_correlation_score(high_corr_alerts)
    low_score = analytics._calculate_correlation_score(low_corr_alerts)
    
    # 验证得分
    assert high_score > low_score
    assert high_score > 0.8  # 高相关性
    assert low_score < 0.8  # 低相关性 