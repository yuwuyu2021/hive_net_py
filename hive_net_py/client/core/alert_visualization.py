"""
HiveNet 告警可视化模块
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .alert_analytics import AlertAnalytics, AlertPattern, AlertStats, AlertTrend, TimeRange
from .event_monitor import AlertLevel

logger = logging.getLogger(__name__)

class AlertVisualization:
    """告警可视化"""
    
    def __init__(self, analytics: AlertAnalytics):
        """
        初始化可视化器
        
        Args:
            analytics: 告警分析器
        """
        self.analytics = analytics
    
    async def create_overview_dashboard(self, time_range: TimeRange) -> go.Figure:
        """
        创建概览仪表板
        
        Args:
            time_range: 时间范围
            
        Returns:
            Plotly图表对象
        """
        # 获取数据
        stats = await self.analytics.get_stats(time_range)
        trend = await self.analytics.get_trend(time_range)
        patterns = await self.analytics.get_patterns()
        top_sources = await self.analytics.get_top_sources(time_range, limit=5)
        top_rules = await self.analytics.get_top_rules(time_range, limit=5)
        
        # 创建子图布局
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                '告警趋势', '级别分布',
                'TOP5来源', 'TOP5规则',
                '时间分布', '告警模式'
            ),
            specs=[
                [{"type": "scatter"}, {"type": "pie"}],
                [{"type": "bar"}, {"type": "bar"}],
                [{"type": "bar"}, {"type": "table"}]
            ]
        )
        
        # 1. 告警趋势图
        timestamps = [datetime.fromtimestamp(ts) for ts in trend.timestamps]
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=trend.counts,
                mode='lines+markers',
                name='告警数量'
            ),
            row=1, col=1
        )
        
        # 2. 级别分布饼图
        level_colors = {
            AlertLevel.INFO: 'blue',
            AlertLevel.WARNING: 'orange',
            AlertLevel.ERROR: 'red',
            AlertLevel.CRITICAL: 'purple'
        }
        fig.add_trace(
            go.Pie(
                labels=[level.name for level in stats.level_counts.keys()],
                values=list(stats.level_counts.values()),
                marker=dict(colors=[level_colors[level] for level in stats.level_counts.keys()]),
                name='级别分布'
            ),
            row=1, col=2
        )
        
        # 3. TOP5来源柱状图
        fig.add_trace(
            go.Bar(
                x=[source for source, _ in top_sources],
                y=[count for _, count in top_sources],
                name='告警来源'
            ),
            row=2, col=1
        )
        
        # 4. TOP5规则柱状图
        fig.add_trace(
            go.Bar(
                x=[rule for rule, _ in top_rules],
                y=[count for _, count in top_rules],
                name='告警规则'
            ),
            row=2, col=2
        )
        
        # 5. 时间分布柱状图
        times = list(stats.time_distribution.keys())
        counts = list(stats.time_distribution.values())
        fig.add_trace(
            go.Bar(
                x=times,
                y=counts,
                name='时间分布'
            ),
            row=3, col=1
        )
        
        # 6. 告警模式表格
        if patterns:
            fig.add_trace(
                go.Table(
                    header=dict(
                        values=['规则', '来源', '频率(/小时)', '相关性'],
                        align='left'
                    ),
                    cells=dict(
                        values=[
                            [p.rule_name for p in patterns],
                            [p.source for p in patterns],
                            [f"{p.frequency:.2f}" for p in patterns],
                            [f"{p.correlation_score:.2f}" for p in patterns]
                        ],
                        align='left'
                    )
                ),
                row=3, col=2
            )
        
        # 更新布局
        fig.update_layout(
            height=1200,
            showlegend=True,
            title_text=f"告警概览 ({time_range.value})"
        )
        
        return fig
    
    async def create_trend_dashboard(self, time_range: TimeRange) -> go.Figure:
        """
        创建趋势分析仪表板
        
        Args:
            time_range: 时间范围
            
        Returns:
            Plotly图表对象
        """
        # 获取趋势数据
        trend = await self.analytics.get_trend(time_range)
        
        # 创建子图布局
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('告警总量趋势', '告警级别趋势'),
            specs=[[{"type": "scatter"}], [{"type": "scatter"}]],
            vertical_spacing=0.2
        )
        
        # 1. 总量趋势
        timestamps = [datetime.fromtimestamp(ts) for ts in trend.timestamps]
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=trend.counts,
                mode='lines+markers',
                name='总告警数'
            ),
            row=1, col=1
        )
        
        # 2. 级别趋势
        colors = {
            AlertLevel.INFO: 'blue',
            AlertLevel.WARNING: 'orange',
            AlertLevel.ERROR: 'red',
            AlertLevel.CRITICAL: 'purple'
        }
        
        for level, counts in trend.level_series.items():
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=counts,
                    mode='lines+markers',
                    name=level.name,
                    line=dict(color=colors[level])
                ),
                row=2, col=1
            )
        
        # 更新布局
        fig.update_layout(
            height=800,
            showlegend=True,
            title_text=f"告警趋势分析 ({time_range.value})"
        )
        
        return fig
    
    async def create_pattern_dashboard(self) -> go.Figure:
        """
        创建模式分析仪表板
        
        Returns:
            Plotly图表对象
        """
        # 获取模式数据
        patterns = await self.analytics.get_patterns()
        
        if not patterns:
            return go.Figure()
        
        # 创建子图布局
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                '告警频率分布',
                '相关性得分分布',
                '频率-相关性散点图',
                '告警模式详情'
            ),
            specs=[
                [{"type": "bar"}, {"type": "bar"}],
                [{"type": "scatter"}, {"type": "table"}]
            ]
        )
        
        # 1. 频率分布
        fig.add_trace(
            go.Bar(
                x=[p.rule_name for p in patterns],
                y=[p.frequency for p in patterns],
                name='告警频率'
            ),
            row=1, col=1
        )
        
        # 2. 相关性分布
        fig.add_trace(
            go.Bar(
                x=[p.rule_name for p in patterns],
                y=[p.correlation_score for p in patterns],
                name='相关性得分'
            ),
            row=1, col=2
        )
        
        # 3. 频率-相关性散���图
        fig.add_trace(
            go.Scatter(
                x=[p.frequency for p in patterns],
                y=[p.correlation_score for p in patterns],
                mode='markers+text',
                text=[p.rule_name for p in patterns],
                textposition="top center",
                name='频率-相关性'
            ),
            row=2, col=1
        )
        
        # 4. 模式详情表格
        fig.add_trace(
            go.Table(
                header=dict(
                    values=['规则', '来源', '频率(/小时)', '间隔(秒)', '相关性'],
                    align='left'
                ),
                cells=dict(
                    values=[
                        [p.rule_name for p in patterns],
                        [p.source for p in patterns],
                        [f"{p.frequency:.2f}" for p in patterns],
                        [f"{p.avg_interval:.1f}" for p in patterns],
                        [f"{p.correlation_score:.2f}" for p in patterns]
                    ],
                    align='left'
                )
            ),
            row=2, col=2
        )
        
        # 更新布局
        fig.update_layout(
            height=1000,
            showlegend=True,
            title_text="告警模式分析"
        )
        
        return fig
    
    def save_html(self, fig: go.Figure, filename: str):
        """
        保存图表为HTML文件
        
        Args:
            fig: Plotly图表对象
            filename: 文件名
        """
        try:
            fig.write_html(filename)
            logger.info(f"图表已保存到: {filename}")
        except Exception as e:
            logger.error(f"保存图表失败: {e}")
    
    def save_image(self, fig: go.Figure, filename: str,
                  format: str = 'png', scale: float = 2.0):
        """
        保存图表为图片
        
        Args:
            fig: Plotly图表对象
            filename: 文件名
            format: 图片格式(png/jpeg/svg/pdf)
            scale: 缩放比例
        """
        try:
            fig.write_image(filename, format=format, scale=scale)
            logger.info(f"图表已保存到: {filename}")
        except Exception as e:
            logger.error(f"保存图表失败: {e}")

class AlertReport:
    """告警报表"""
    
    def __init__(self, analytics: AlertAnalytics):
        """
        初始化报表生成器
        
        Args:
            analytics: 告警分析器
        """
        self.analytics = analytics
        self.visualization = AlertVisualization(analytics)
    
    async def generate_html_report(self, time_range: TimeRange,
                                 output_dir: str = '.'):
        """
        生成HTML报表
        
        Args:
            time_range: 时间范围
            output_dir: 输出目录
        """
        try:
            # 生成概览仪表板
            overview_fig = await self.visualization.create_overview_dashboard(time_range)
            self.visualization.save_html(
                overview_fig,
                f"{output_dir}/alert_overview_{time_range.value}.html"
            )
            
            # 生成趋势仪表板
            trend_fig = await self.visualization.create_trend_dashboard(time_range)
            self.visualization.save_html(
                trend_fig,
                f"{output_dir}/alert_trend_{time_range.value}.html"
            )
            
            # 生成模式仪表板
            pattern_fig = await self.visualization.create_pattern_dashboard()
            self.visualization.save_html(
                pattern_fig,
                f"{output_dir}/alert_pattern.html"
            )
            
            logger.info(f"HTML报表已生成到目录: {output_dir}")
            
        except Exception as e:
            logger.error(f"生成HTML报表失败: {e}")
    
    async def generate_pdf_report(self, time_range: TimeRange,
                                output_dir: str = '.'):
        """
        生成PDF报表
        
        Args:
            time_range: 时间范围
            output_dir: 输出目录
        """
        try:
            # 生成概览仪表板
            overview_fig = await self.visualization.create_overview_dashboard(time_range)
            self.visualization.save_image(
                overview_fig,
                f"{output_dir}/alert_overview_{time_range.value}.pdf",
                format='pdf'
            )
            
            # 生成趋势仪表板
            trend_fig = await self.visualization.create_trend_dashboard(time_range)
            self.visualization.save_image(
                trend_fig,
                f"{output_dir}/alert_trend_{time_range.value}.pdf",
                format='pdf'
            )
            
            # 生成模式仪表板
            pattern_fig = await self.visualization.create_pattern_dashboard()
            self.visualization.save_image(
                pattern_fig,
                f"{output_dir}/alert_pattern.pdf",
                format='pdf'
            )
            
            logger.info(f"PDF报表已生成到目录: {output_dir}")
            
        except Exception as e:
            logger.error(f"生成PDF报表失败: {e}") 