import asyncio
import datetime
import logging
import re
from collections import defaultdict
from itertools import groupby
from typing import List, Tuple, Generator
from typing import Optional, Dict, Any

from _pytest.config import Config
from flatten_dict import flatten
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String, Group
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Table,
    Paragraph,
    Flowable,
    PageTemplate,
    BaseDocTemplate,
    Frame,
    PageBreak,
    KeepTogether,
)
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from pytaf.options import Option
from pytaf.pytaf import Script, Step, Const, Keyword, Projects
from pytaf.result import Result

logger = logging.getLogger(__name__)

STYLES = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    name="Title",
    parent=STYLES["Normal"],
    fontSize=11,
    alignment=TA_CENTER,
    spaceBefore=5,
    spaceAfter=10,
)

HEADING_1_STYLE = ParagraphStyle(
    name="h1",
    parent=STYLES["Heading1"],
    fontSize=11,
    leading=12,
    spaceAfter=15,
)

HEADING_2_STYLE = ParagraphStyle(
    name="h1",
    parent=STYLES["Heading1"],
    fontSize=8,
    leading=12,
)

TABLE_HEADER_CELL_STYLE = ParagraphStyle(
    name="header",
    fontSize=8,
    fontName="Courier-Bold",
    alignment=TA_CENTER,
)

TABLE_CELL_STYLE_LEFT = ParagraphStyle(
    name="cell",
    fontSize=8,
    fontName="Courier",
    alignment=TA_LEFT,
)

TABLE_CELL_STYLE_CENTER = ParagraphStyle(
    name="cell",
    fontSize=8,
    fontName="Courier",
    alignment=TA_CENTER,
)

TABLE_STYLE = [
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("BOX", (0, 0), (-1, -1), 0.1, colors.black),
    ("INNERGRID", (0, 0), (-1, -1), 0.1, colors.black),
]

LABELS = (Result.passed, Result.skipped, Result.failed)
COLORS = (colors.lightgreen, colors.yellow, colors.orangered)


def result_style(color):
    return ParagraphStyle(name="Normal", fontSize=9, fontName="Courier", alignment=TA_CENTER, backColor=color)


def remove_prefix(string_: str, prefix: str) -> Optional[str]:
    if string_.startswith(prefix):
        return string_[len(prefix) :]
    return None


def percent(dividend, divisor) -> float:
    return (dividend / divisor if divisor else 0) * 100


def sum_up_results(config: Config, items: List[Step]) -> Tuple[int, int, int]:
    if config.getoption(Option.LF, None):
        passed = [item for item in items if item.result == LABELS[0]]
        skipped = [item for item in items if item.result == LABELS[1]]
        failed = [item for item in items if item.result == LABELS[2]]
    else:
        passed = [item for item in items if item.selected and item.result == LABELS[0]]
        skipped = [item for item in items if item.selected and item.result == LABELS[1]]
        failed = [item for item in items if item.selected and item.result == LABELS[2]]
    return len(passed), len(skipped), len(failed)


def derive_results(config: Config, items: List[Script]) -> Tuple[int, int, int]:
    passed, skipped, failed = 0, 0, 0
    for item in items:
        _passed, _skipped, _failed = sum_up_results(config=config, items=item.children)
        if _failed > 0:
            failed += 1
        elif _passed > 0:
            passed += 1
        else:
            skipped += 1
    return passed, skipped, failed


# see: https://stackoverflow.com/questions/38252507/how-can-i-get-comments-from-a-yaml-file-using-ruamel-yaml-in-python
def _comment(data):
    def is_report(comment_: str) -> bool:
        return re.match(r"^#[\s]*report[\s]*$", comment_) is not None

    values: Dict[str, Any] = defaultdict(dict)
    for key, value in data.items():
        if isinstance(value, dict):
            if isinstance(value, CommentedMap):
                if value.ca.comment and is_report(value.ca.comment[0].value):  # CommentToken
                    values[key] = value
                else:
                    for key_, comment in value.ca.items.items():
                        if comment[2] and is_report(comment[2].value):
                            values[key][key_] = value[key_]
            else:
                values[key] = _comment(value)
        elif isinstance(value, list):
            if isinstance(value, CommentedSeq):
                pass
    return values


class _PieChart(Pie):
    def __init__(self, data, x, y, width, height):
        super().__init__()
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.data = data
        self.labels = LABELS
        for index, color in enumerate(COLORS):
            self.slices[index].fillColor = color
        self.slices.strokeWidth = 3
        self.slices.strokeColor = colors.white
        self.slices.fontSize = 12
        self.slices[LABELS.index(Result.failed)].popout = 5


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
    def __init__(self, data: Tuple[int, int, int], x, y, font_size, font_color, sub_cols, alignment):
        super().__init__()
        self.x = x
        self.y = y
        self.alignment = alignment  # color flag position in legend

        sum_ = sum(data)
        colors_ = COLORS + (None,)
        labels_ = LABELS + ("Sum",)
        counts_ = tuple([str(count) for count in data]) + (str(sum_),)
        percents_ = tuple([str(round(percent(count, sum_), 2)) for count in data]) + (str(100.0),)

        self.columnMaximum = len(labels_)

        series = list(zip(labels_, counts_, percents_))
        self.colorNamePairs = list(zip(colors_, series))

        self.fontName = "Times-Roman"
        self.fontSize = font_size
        self.fillColor = font_color

        for index, sub_col in enumerate(sub_cols):
            self.subCols[index].minWidth = sub_col[0]
            self.subCols[index].align = sub_col[1]
            self.subCols[index].dx = sub_col[2]


class PieChartWithLegend(Group):
    def __init__(self, title: str, data: Tuple[int, int, int], x, y, *elements, **keywords):
        super().__init__(*elements, **keywords)
        sub_cols = ((50, "left", 0), (40, "right", -10), (50, "right", -10))
        pie_chart = _PieChart(data=data, x=x, y=y + 200, width=180, height=180)
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


def get_test_case_result_page(config: Config, items: List[Script], heading: Flowable) -> Flowable:
    table_data = [
        [
            Paragraph("Skript", TABLE_HEADER_CELL_STYLE),
            Paragraph("Test Case Id", TABLE_HEADER_CELL_STYLE),
            Paragraph("Passed", TABLE_HEADER_CELL_STYLE),
            Paragraph("Skipped", TABLE_HEADER_CELL_STYLE),
            Paragraph("Failed", TABLE_HEADER_CELL_STYLE),
        ],
    ]

    for item in items:
        passed, skipped, failed = sum_up_results(config=config, items=item.children)
        table_data.append(
            [
                Paragraph(item.script_path.name, TABLE_CELL_STYLE_LEFT),
                Paragraph(item.case, TABLE_CELL_STYLE_LEFT),
                Paragraph(str(passed), TABLE_CELL_STYLE_CENTER),
                Paragraph(str(skipped), TABLE_CELL_STYLE_CENTER),
                Paragraph(str(failed), TABLE_CELL_STYLE_CENTER),
            ]
        )

    table = Table(
        data=table_data,
        colWidths=[110, 200, 50, 50, 50],
        hAlign="LEFT",
        style=TABLE_STYLE,
    )

    return KeepTogether([heading, table])


def get_test_step_result_tables_grouped_by_test_case(steps: List[Step]) -> Generator[Tuple[str, Table], None, None]:
    for script_item, step_items in groupby(steps, lambda item_: item_.parent):
        table_data = [
            [
                Paragraph("Test Step Id", TABLE_HEADER_CELL_STYLE),
                Paragraph("Parameter", TABLE_HEADER_CELL_STYLE),
                Paragraph("Result", TABLE_HEADER_CELL_STYLE),
                Paragraph("Error/Reason", TABLE_HEADER_CELL_STYLE),
            ],
        ]

        # If spanned table cell height can't be displayed on one page and therefore the table must be
        # continued on next page, then the error "...  too large on page ... in frame' will be raised.
        # There is no solution: https://groups.google.com/forum/#!topic/reportlab-users/wlIN3Fsg2VA

        previous_item = None

        for span_to, item in enumerate(step_items, 1):  # 1 = exclude table header
            if previous_item and previous_item.step_id == item.step_id:
                step_id_paragraph = Paragraph("", TABLE_CELL_STYLE_LEFT)
            else:
                step_id_paragraph = Paragraph(item.step_id, TABLE_CELL_STYLE_LEFT)
            parameter_paragraphs = [Paragraph(p, TABLE_CELL_STYLE_LEFT) for p in item.parameters_repr]
            result_paragraph = Paragraph(item.result, result_style(COLORS[LABELS.index(item.result)]))
            error_paragraph = None
            if item.reason:
                error_paragraph = Paragraph(item.reason, TABLE_CELL_STYLE_LEFT)
            elif item.error:
                when = item.when if item.when in ("setup", "teardown") else ""
                error = when + (remove_prefix(item.error, Const.FAILED) or item.error)
                error = (error[:64] + " ...") if len(error) > 64 else error  # truncate to maximum length
                error_paragraph = Paragraph(error, TABLE_CELL_STYLE_LEFT)
            table_data.append([step_id_paragraph, parameter_paragraphs, result_paragraph, error_paragraph])
            previous_item = item

        yield script_item.case, Table(
            data=table_data,
            colWidths=[180, 140, 50, 90],
            repeatRows=1,
            hAlign="LEFT",
            style=TABLE_STYLE,
            spaceAfter=15,
        )


def get_test_step_result_pages(items: List[Step], heading: Flowable = None) -> List[Flowable]:
    flowables = []
    not_inserted = True
    for test_case_id, table in get_test_step_result_tables_grouped_by_test_case(steps=items):
        if heading and not_inserted:
            flowables.append(
                KeepTogether([heading, Paragraph(test_case_id, style=HEADING_2_STYLE), table]),
            )
            not_inserted = False
        else:
            flowables.append(
                KeepTogether([Paragraph(test_case_id, style=HEADING_2_STYLE), table]),
            )
    return flowables


def get_environment_page(env: Dict[str, Any], heading: Flowable) -> Flowable:
    table_data = [
        [
            Paragraph("Data key", TABLE_HEADER_CELL_STYLE),
            Paragraph("Value", TABLE_HEADER_CELL_STYLE),
        ],
    ]

    if commented := _comment(env):
        for key, value in flatten(d=commented, reducer="dot").items():
            table_data.append(
                [
                    Paragraph(key, TABLE_CELL_STYLE_LEFT),
                    Paragraph(value, TABLE_CELL_STYLE_LEFT),
                ],
            )

    table = Table(
        data=table_data,
        colWidths=[180, 280],
        hAlign="LEFT",
        style=TABLE_STYLE,
        spaceBefore=5,
        spaceAfter=15,
    )

    return KeepTogether([heading, table])


def story(config: Config) -> List[Flowable]:
    flowables = []
    now = datetime.datetime.now()

    for project in Projects.projects():

        titles = [
            Paragraph(text=f"{project.about[0]} {project.about[1]}", style=STYLES["Title"]),
            Paragraph(text="Test report", style=TITLE_STYLE),
            Paragraph(text=f"Environment:  {project.items[0].env[Keyword.env].upper()}", style=TITLE_STYLE),
            Paragraph(text=f"Tested software: {', '.join(project.about[2])}", style=TITLE_STYLE),
            Paragraph(text=f"Generated on: {now.strftime('%d %b %Y, %H:%M:%S')}", style=TITLE_STYLE),
        ]

        if config.getoption(Option.LF, None):
            step_items = [item for script_item in project.items for item in script_item.children]
        else:
            step_items = [item for script_item in project.items for item in script_item.children if item.selected]

        charts = Drawing(
            500,
            500,
            PieChartWithLegend(title="Test Cases", data=derive_results(config=config, items=project.items), x=0, y=0),
            PieChartWithLegend(title="Test Steps ", data=sum_up_results(config=config, items=step_items), x=250, y=0),
        )

        if config.getoption(Option.PDF_SHORT, None):
            result_pages = [
                get_test_case_result_page(
                    config=config,
                    items=project.items,
                    heading=Paragraph("Overview Test Case Results", style=HEADING_1_STYLE),
                ),
                PageBreak(),
                *get_test_step_result_pages(
                    items=[item for item in step_items if item.error],
                    heading=Paragraph("Test Step Errors", style=HEADING_1_STYLE),
                ),
            ]
        else:
            result_pages = [
                *get_test_step_result_pages(
                    items=step_items,
                    heading=Paragraph("Test Step Results", style=HEADING_1_STYLE),
                ),
            ]

        flowables.extend(
            [
                *titles,
                charts,
                PageBreak(),
                *result_pages,
                get_environment_page(
                    env=project.items[0].env,  # take 1st script item, because all use the same env
                    heading=Paragraph("Environment Data", style=HEADING_1_STYLE),
                ),
                PageBreak(),
            ]
        )

    return flowables


def footer(canvas, doc):
    canvas.saveState()  # save state of canvas to draw on it
    footer_paragraph = Paragraph(
        text=str(doc.page), style=ParagraphStyle(name="footer", parent=STYLES["Normal"], spaceBefore=6)
    )
    _, h = footer_paragraph.wrap(availWidth=doc.width, availHeight=doc.bottomMargin)
    footer_paragraph.drawOn(canvas, x=doc.leftMargin, y=(h * 2))
    canvas.restoreState()


def generate_pdf_report(config: Config):
    doc = BaseDocTemplate(
        filename=str(config.pdf_report_file_path),
        pagesize=A4,
        topMargin=27 * mm,
        leftMargin=25 * mm,
        rightMargin=20 * mm,
        bottomMargin=25 * mm,
    )
    frame = Frame(x1=doc.leftMargin, y1=doc.bottomMargin, width=doc.width, height=doc.height)
    template = PageTemplate(id="report", frames=frame, onPage=footer)
    doc.addPageTemplates([template])
    doc.multiBuild(story=story(config))


def generate_report(config: Config):
    async def main(tasks_):
        return await asyncio.gather(*tasks_)

    projects = Projects.projects()
    tasks = [project.about_impl for project in projects]
    abouts = asyncio.run(main(tasks))
    for project, about in zip(projects, abouts):
        project.about = about

    if config.getoption(Option.PDF, None):
        path = config.pdf_report_file_path
        if path.parent.parts:
            path.parent.mkdir(parents=True, exist_ok=True)

    generate_pdf_report(config)
