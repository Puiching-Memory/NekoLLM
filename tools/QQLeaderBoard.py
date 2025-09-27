import jsonl
from pyecharts.charts import Line
from pyecharts import options as opts

raw_data = jsonl.load("group_765049040.jsonl")

# 按日期统计消息数
def get_message_count_by_date(data):
    """
    按日期统计消息数量
    
    Args:
        data: 原始数据列表
    
    Returns:
        按日期统计的消息数量字典
    """
    date_count = {}
    for message in data:
        # 提取日期部分（忽略时间）
        message_date = message['datetime'].split('T')[0]
        date_count[message_date] = date_count.get(message_date, 0) + 1
    
    # 按日期排序
    sorted_dates = sorted(date_count.items(), key=lambda x: x[0])
    return sorted_dates

# 按日期统计的图表，支持日期范围选择
date_stats = get_message_count_by_date(raw_data)
dates = [item[0] for item in date_stats]
counts = [item[1] for item in date_stats]

# 创建折线图并添加DataZoom组件
line = Line()
line.add_xaxis(dates)
line.add_yaxis("每日消息数", counts, is_smooth=True)
line.set_global_opts(
    title_opts=opts.TitleOpts(title="每日消息数量统计"),
    xaxis_opts=opts.AxisOpts(
        type_="category", 
        name="日期",
        axislabel_opts=opts.LabelOpts(rotate=45)  # 旋转标签以避免重叠
    ),
    yaxis_opts=opts.AxisOpts(
        type_="value",
        name="消息数",
    ),
    datazoom_opts=[
        opts.DataZoomOpts(
            is_show=True,
            type_="slider",
            range_start=0,
            range_end=100,
            orient="horizontal"
        ),
        opts.DataZoomOpts(
            is_show=True,
            type_="inside",
            range_start=0,
            range_end=100,
        ),
    ],
    tooltip_opts=opts.TooltipOpts(
        is_show=True,
        trigger="axis", 
        trigger_on="mousemove|click"
    )
)

# 渲染图表
line.render("date_stats.html")

print("已生成图表文件：date_stats.html")
print("打开此HTML文件即可使用pyecharts提供的交互式日期范围选择功能")
print("可以通过底部的滑动条或在图表区域内鼠标滚轮操作来选择日期范围")