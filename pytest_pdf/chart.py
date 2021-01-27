from typing import Tuple

from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Group, String
from reportlab.lib import colors


def percent(dividend, divisor) -> float:
    return (dividend / divisor if divisor else 0) * 100


class _PieChart(Pie):
    def __init__(self, data, x, y, width, height, labels, colors_):
        super().__init__()
        self.data = data
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        for index, color in enumerate(colors_):
            self.slices[index].fillColor = color
        self.slices.strokeWidth = 3
        self.slices.strokeColor = colors.white
        self.slices.fontSize = 12
        self.slices[labels.index("failed")].popout = 5


class _LegendHeader(Legend):
    def __init__(self, x, y, font_size: int, font_color, sub_cols):
        super().__init__()
        self.x = x
        self.y = y
        self.alignment = "right"
        self.colorNamePairs = [("", ("Result", "Count", "Percent"))]
        self.fontName = "Times-Bold"
        self.fontSize = font_size
        self.fillColor = font_color
        self.dividerLines = 2  # 1 = dividers between the rows, | 2 = for extra top, | 4 = for bottom
        self.dividerOffsY = -15
        self.dividerWidth = 0.5
        self.dividerColor = colors.black
        for index, sub_col in enumerate(sub_cols):
            self.subCols[index].minWidth = sub_col[0]
            self.subCols[index].align = sub_col[1]


class _Legend(Legend):
    def __init__(self, data: Tuple[int, int, int], x, y, labels, colors_, font_size, font_color, sub_cols, alignment):
        super().__init__()
        self.x = x
        self.y = y
        self.alignment = alignment  # color flag position in legend
        sum_ = sum(data)
        labels_ = labels + ("Sum",)
        colors__ = colors_ + (None,)
        counts_ = tuple([str(count) for count in data]) + (str(sum_),)
        percents_ = tuple([str(round(percent(count, sum_), 2)) for count in data]) + (str(100.0),)

        self.columnMaximum = len(labels_)

        series = list(zip(labels_, counts_, percents_))
        self.colorNamePairs = list(zip(colors__, series))

        self.fontName = "Times-Roman"
        self.fontSize = font_size
        self.fillColor = font_color

        for index, sub_col in enumerate(sub_cols):
            self.subCols[index].minWidth = sub_col[0]
            self.subCols[index].align = sub_col[1]
            self.subCols[index].dx = sub_col[2]


class PieChartWithLegend(Group):
    def __init__(self, title: str, data: Tuple[int, int, int], x, y, labels, colors_, *elements, **keywords):
        super().__init__(*elements, **keywords)
        sub_cols = ((50, "left", 0), (40, "right", -10), (50, "right", -10))
        pie_chart = _PieChart(data=data, x=x, y=y + 200, width=180, height=180, labels=labels, colors_=colors_)
        legend_header = _LegendHeader(
            x=pie_chart.x + 10,
            y=pie_chart.y - 80,
            font_size=pie_chart.slices.fontSize,
            font_color=pie_chart.slices.fontColor,
            sub_cols=sub_cols,
        )
        legend = _Legend(
            data=data,
            x=legend_header.x + 10,
            y=legend_header.y - 30,
            labels=labels,
            colors_=colors_,
            sub_cols=sub_cols,
            font_size=legend_header.fontSize,
            font_color=legend_header.fillColor,
            alignment=legend_header.alignment,
        )
        title = String(
            x=pie_chart.x + 60,
            y=pie_chart.y + pie_chart.height + 60,
            text=title,
            fontName=legend_header.fontName,
            fontSize=legend_header.fontSize + 1,
            fillColor=legend_header.fillColor,
        )
        self.add(title)
        self.add(pie_chart)
        self.add(legend_header)
        self.add(legend)
