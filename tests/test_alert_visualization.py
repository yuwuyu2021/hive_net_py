"""
HiveNet 告警可视化模块测试
"""
import os
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import plotly.graph_objects as go

from hive_net_py.client.core.alert_analytics import (
    AlertAnalytics,
    AlertPattern,
    AlertStats,
    AlertTrend,
    TimeRange
)
from hive_net_py.client.core.event_monitor import AlertLevel
from hive_net_py.client.core.alert_visualization import AlertVisualization, AlertReport

@pytest.fixture
def mock_analytics():
    analytics = AsyncMock(spec=AlertAnalytics)
    
    # 模拟统计数据
    stats = AlertStats(
        total_count=100,
        level_counts={
            AlertLevel.INFO: 40,
            AlertLevel.WARNING: 30,
            AlertLevel.ERROR: 20,
            AlertLevel.CRITICAL: 10
        },
        time_distribution={
            "00:00": 10,
            "06:00": 20,
            "12:00": 40,
            "18:00": 30
        }
    )
    analytics.get_stats.return_value = stats
    
    # 模拟趋势数据
    trend = AlertTrend(
        timestamps=[
            datetime(2024, 1, 1, 0, 0).timestamp(),
            datetime(2024, 1, 1, 6, 0).timestamp(),
            datetime(2024, 1, 1, 12, 0).timestamp(),
            datetime(2024, 1, 1, 18, 0).timestamp()
        ],
        counts=[10, 20, 40, 30],
        level_series={
            AlertLevel.INFO: [4, 8, 16, 12],
            AlertLevel.WARNING: [3, 6, 12, 9],
            AlertLevel.ERROR: [2, 4, 8, 6],
            AlertLevel.CRITICAL: [1, 2, 4, 3]
        }
    )
    analytics.get_trend.return_value = trend
    
    # 模拟模式数据
    patterns = [
        AlertPattern(
            rule_name="CPU使用率过高",
            source="server-01",
            frequency=0.5,
            avg_interval=300,
            correlation_score=0.8
        ),
        AlertPattern(
            rule_name="内存使用率过高",
            source="server-02",
            frequency=0.3,
            avg_interval=600,
            correlation_score=0.6
        )
    ]
    analytics.get_patterns.return_value = patterns
    
    # 模拟TOP数据
    analytics.get_top_sources.return_value = [
        ("server-01", 50),
        ("server-02", 30),
        ("server-03", 20)
    ]
    analytics.get_top_rules.return_value = [
        ("CPU使用率过高", 40),
        ("内存使用率过高", 30),
        ("磁盘使用率过高", 30)
    ]
    
    return analytics

@pytest.mark.asyncio
async def test_create_overview_dashboard(mock_analytics):
    """测试创建概览仪表板"""
    visualization = AlertVisualization(mock_analytics)
    fig = await visualization.create_overview_dashboard(TimeRange.LAST_24H)
    
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    assert fig.layout.title.text == "告警概览 (last_24h)"

@pytest.mark.asyncio
async def test_create_trend_dashboard(mock_analytics):
    """测试创建趋势仪表板"""
    visualization = AlertVisualization(mock_analytics)
    fig = await visualization.create_trend_dashboard(TimeRange.LAST_24H)
    
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    assert fig.layout.title.text == "告警趋势分析 (last_24h)"

@pytest.mark.asyncio
async def test_create_pattern_dashboard(mock_analytics):
    """测试创建模式仪表板"""
    visualization = AlertVisualization(mock_analytics)
    fig = await visualization.create_pattern_dashboard()
    
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    assert fig.layout.title.text == "告警模式分析"

def test_save_html(mock_analytics, tmp_path):
    """测试保存HTML文件"""
    visualization = AlertVisualization(mock_analytics)
    fig = go.Figure()
    filename = str(tmp_path / "test.html")
    
    visualization.save_html(fig, filename)
    assert os.path.exists(filename)

def test_save_image(mock_analytics, tmp_path):
    """测试保存图片文件"""
    visualization = AlertVisualization(mock_analytics)
    fig = go.Figure()
    filename = str(tmp_path / "test.png")
    
    with patch("plotly.graph_objects.Figure.write_image") as mock_write:
        visualization.save_image(fig, filename)
        mock_write.assert_called_once()

@pytest.mark.asyncio
async def test_generate_html_report(mock_analytics, tmp_path):
    """测试生成HTML报表"""
    report = AlertReport(mock_analytics)
    await report.generate_html_report(TimeRange.LAST_24H, str(tmp_path))
    
    assert os.path.exists(tmp_path / f"alert_overview_{TimeRange.LAST_24H.value}.html")
    assert os.path.exists(tmp_path / f"alert_trend_{TimeRange.LAST_24H.value}.html")
    assert os.path.exists(tmp_path / "alert_pattern.html")

@pytest.mark.asyncio
async def test_generate_pdf_report(mock_analytics, tmp_path):
    """测试生成PDF报表"""
    report = AlertReport(mock_analytics)
    
    with patch("plotly.graph_objects.Figure.write_image") as mock_write:
        await report.generate_pdf_report(TimeRange.LAST_24H, str(tmp_path))
        assert mock_write.call_count == 3 