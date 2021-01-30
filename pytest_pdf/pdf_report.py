import datetime
import logging
import re
from collections import defaultdict, Sequence
from itertools import groupby
from pathlib import Path
from typing import Union, Dict, List, Optional, Tuple, Generator

from _pytest.config import ExitCode, Config
from _pytest.main import Session
from _pytest.nodes import Item
from _pytest.reports import TestReport
from _pytest.runner import CallInfo
from _pytest.terminal import TerminalReporter
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Flowable, Table, KeepTogether, PageBreak

from pytest_pdf.chart import PieChartWithLegend
from pytest_pdf.mkdir import mkdir
from pytest_pdf.options import Option

ELLIPSIS = "..."
ERROR_TEXT_MAX_LENGTH = 60

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

SPACE_AFTER_TABLE = 15

logger = logging.getLogger(__name__)

LABELS = ("passed", "skipped", "failed")
COLORS = (colors.lightgreen, colors.yellow, colors.orangered)


class PdfReport:
    """collects test results and generates pdf report"""

    def __init__(self, config: Config, report_path: Path):
        self.config = config
        self.now = datetime.datetime.now()
        self.reports: Dict[str, List[TestReport]] = defaultdict(list)
        self.nodeid_pattern = re.compile(r"^(.+)::([^][]+)(?:\[.+\])?$")
        path = Path(report_path)
        self.report_path = path.parent / self.now.strftime(path.name)
        mkdir(path=self.report_path)

    def nodeid_parts(self, nodeid: str) -> Sequence[str, str]:
        m = self.nodeid_pattern.match(nodeid)
        return m.groups()

    @staticmethod
    def _error_text(error: str, when: str):
        lines = error.split()
        error_ = " ".join(lines[1:])  # remove prefix
        error_ += when
        max_length = ERROR_TEXT_MAX_LENGTH - len(ELLIPSIS)
        return f"{error_[:max_length]}{ELLIPSIS}" if len(error_) > max_length else error_

    @staticmethod
    def _test_step_results(reports: List[TestReport]) -> Tuple[int, int, int]:
        passed = len([r for r in reports if r.when == "call" and r.outcome == "passed"])
        failed = len([r for r in reports if r.when == "call" and r.outcome == "failed"])
        skipped = len([r for r in reports if r.when == "setup" and r.outcome == "skipped"])
        return passed, skipped, failed

    def _test_case_results(self, reports: List[TestReport]) -> Tuple[int, int, int]:
        passed, skipped, failed = 0, 0, 0
        test_cases = groupby(reports, lambda r: self.nodeid_parts(nodeid=r.nodeid)[0])
        for _, reports_ in test_cases:
            passed_, skipped_, failed_ = self._test_step_results(reports=list(reports_))
            if failed_ > 0:
                failed += 1
            elif passed_ > 0:
                passed += 1
            else:
                skipped += 1
        return passed, skipped, failed

    def _test_case_page(self, reports: List[TestReport], heading: Flowable) -> Flowable:
        table_data = [
            [
                Paragraph("Skript", TABLE_HEADER_CELL_STYLE),
                Paragraph("Test Case Id", TABLE_HEADER_CELL_STYLE),
                Paragraph("Passed", TABLE_HEADER_CELL_STYLE),
                Paragraph("Skipped", TABLE_HEADER_CELL_STYLE),
                Paragraph("Failed", TABLE_HEADER_CELL_STYLE),
            ],
        ]

        test_cases = groupby(reports, lambda r: self.nodeid_parts(nodeid=r.nodeid)[0])

        for test_case_id, reports_ in test_cases:
            passed, skipped, failed = self._test_step_results(reports=list(reports_))
            table_data.append(
                [
                    Paragraph("...", TABLE_CELL_STYLE_LEFT),
                    Paragraph(test_case_id, TABLE_CELL_STYLE_LEFT),
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
            spaceAfter=SPACE_AFTER_TABLE,
        )

        return KeepTogether([heading, table])

    def _test_steps_grouped_by_test_case(
        self,
        reports: List[TestReport],
    ) -> Generator[Tuple[str, Table], None, None]:

        test_cases = groupby(reports, lambda r: self.nodeid_parts(nodeid=r.nodeid)[0])

        for test_case_id, reports_ in test_cases:

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

            previous_test_step_id = None

            for span_to, report in enumerate(reports_, 1):  # 1 = exclude table header
                # colum 'Test Step Id'
                test_step_id = self.nodeid_parts(nodeid=report.nodeid)[1]
                if previous_test_step_id and previous_test_step_id == test_step_id:
                    # 2nd, 3rd, ... row of parameterized test
                    test_step_id_paragraph = Paragraph("", TABLE_CELL_STYLE_LEFT)
                else:
                    test_step_id_paragraph = Paragraph(test_step_id, TABLE_CELL_STYLE_LEFT)
                # column 'Parameter'
                parameters = [f"{key}={value}" for key, value in report.parameters.items()]
                parameter_paragraphs = Paragraph(", ".join(parameters), TABLE_CELL_STYLE_LEFT)
                # column 'Result'
                color = COLORS[LABELS.index(report.outcome)]
                style = ParagraphStyle(
                    name="Normal",
                    fontSize=9,
                    fontName="Courier",
                    alignment=TA_CENTER,
                    backColor=color,
                )
                result_paragraph = Paragraph(report.outcome, style=style)
                # column 'Error/Reason'
                when = ""
                reason = ""
                error_paragraph = None
                if report.outcome == "skipped":
                    reason = report.longrepr[2]
                elif report.outcome == "failed":
                    when = report.when if report.when in ("setup", "teardown") else ""
                    reason = report.longreprtext
                if reason:
                    text_ = self._error_text(error=reason, when=when)
                    error_paragraph = Paragraph(text_, TABLE_CELL_STYLE_LEFT)

                table_data.append([test_step_id_paragraph, parameter_paragraphs, result_paragraph, error_paragraph])

                previous_test_step_id = test_step_id

            yield test_case_id, Table(
                data=table_data,
                colWidths=[180, 140, 50, 90],
                repeatRows=1,
                hAlign="LEFT",
                style=TABLE_STYLE,
                spaceAfter=SPACE_AFTER_TABLE,
            )

    def _test_step_error_pages(self, reports: List[TestReport], heading: Flowable = None) -> List[Flowable]:
        return self._test_step_pages(
            reports=[r for r in reports if r.outcome == "failed"],
            heading=Paragraph("Test Step Errors", style=HEADING_1_STYLE),
        )

    def _test_step_pages(self, reports: List[TestReport], heading: Flowable = None) -> List[Flowable]:
        flowables = []
        not_inserted = True
        for test_case_id, table in self._test_steps_grouped_by_test_case(reports=reports):
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

    def _environment_page(self, name: str, heading: Flowable) -> Flowable:
        table_data = [
            [
                Paragraph("Data key", TABLE_HEADER_CELL_STYLE),
                Paragraph("Value", TABLE_HEADER_CELL_STYLE),
            ],
        ]

        info = self.config.hook.pytest_pdf_report_additional_info(project_name=name)[0]
        data = list(info.values())[0]

        for key, value in data:
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
            spaceAfter=SPACE_AFTER_TABLE,
        )

        return KeepTogether([heading, table])

    @staticmethod
    def _footer(canvas, doc):
        canvas.saveState()  # save state of canvas to draw on it
        footer_paragraph = Paragraph(
            text=str(doc.page),
            style=ParagraphStyle(
                name="footer",
                parent=STYLES["Normal"],
                spaceBefore=6,
            ),
        )
        _, h = footer_paragraph.wrap(
            availWidth=doc.width,
            availHeight=doc.bottomMargin,
        )
        footer_paragraph.drawOn(canvas, x=doc.leftMargin, y=(h * 2))
        canvas.restoreState()

    def _story(self) -> List[Flowable]:
        flowables = []
        for project_name, reports in self.reports.items():

            version = self.config.hook.pytest_pdf_report_release(project_name=project_name)[0]
            info = self.config.hook.pytest_pdf_report_additional_info(project_name=project_name)[0]
            env_name = list(info.keys())[0]
            tested_packages = self.config.hook.pytest_pdf_report_packages(project_name=project_name)
            tested_packages_ = [f"{package[0]} ({package[1]})" for package in tested_packages[0]]

            titles = [
                Paragraph(text=f"{project_name} {version}", style=STYLES["Title"]),
                Paragraph(text="Test report", style=TITLE_STYLE),
                Paragraph(text=f"Environment:  {env_name}", style=TITLE_STYLE),
                Paragraph(text=f"Tested software: {', '.join(tested_packages_)}", style=TITLE_STYLE),
                Paragraph(text=f"Generated on: {self.now.strftime('%d %b %Y, %H:%M:%S')}", style=TITLE_STYLE),
            ]

            charts = Drawing(
                500,
                500,
                PieChartWithLegend(
                    title="Test Cases",
                    data=self._test_case_results(reports),
                    x=0,
                    y=0,
                    labels=LABELS,
                    colors_=COLORS,
                ),
                PieChartWithLegend(
                    title="Test Steps ",
                    data=self._test_step_results(reports),
                    x=250,
                    y=0,
                    labels=LABELS,
                    colors_=COLORS,
                ),
            )

            if self.config.getoption(Option.PDF_SHORT, None):
                result_pages = [
                    self._test_case_page(
                        reports=reports,
                        heading=Paragraph("Test Case Results", style=HEADING_1_STYLE),
                    ),
                    *self._test_step_error_pages(
                        reports=reports,
                        heading=Paragraph("Test Step Errors", style=HEADING_1_STYLE),
                    ),
                ]
            else:
                result_pages = [
                    *self._test_step_pages(
                        reports=reports,
                        heading=Paragraph("Test Step Results", style=HEADING_1_STYLE),
                    )
                ]

            flowables.extend(
                [
                    *titles,
                    charts,
                    PageBreak(),
                    *result_pages,
                    self._environment_page(
                        name=env_name,
                        heading=Paragraph("Environment Data", style=HEADING_1_STYLE),
                    ),
                ]
            )

        return flowables

    def _create_doc(self):
        doc = BaseDocTemplate(
            filename=str(self.report_path),
            pagesize=A4,
            topMargin=27 * mm,
            leftMargin=25 * mm,
            rightMargin=20 * mm,
            bottomMargin=25 * mm,
        )
        frame = Frame(
            x1=getattr(doc, "leftMargin"),
            y1=getattr(doc, "bottomMargin"),
            width=getattr(doc, "width"),
            height=getattr(doc, "height"),
        )
        template = PageTemplate(
            id="report",
            frames=frame,
            onPage=self._footer,
        )
        doc.addPageTemplates([template])
        return doc

    def _generate_report(self) -> None:
        doc = self._create_doc()
        story = self._story()
        doc.multiBuild(story=story)

    # -- pytest hooks

    def pytest_runtest_makereport(self, item: Item, call: CallInfo[None]) -> Optional[TestReport]:
        """returns an empty test report instance with additional attributes"""
        project = self.config.hook.pytest_pdf_report_project(item=item)[0]
        report = TestReport.from_item_and_call(item, call)
        setattr(report, "project", project)
        setattr(report, "parameters", getattr(item, "funcargs", []))
        return report

    def pytest_runtest_logreport(self, report: TestReport) -> None:
        if (report.when == "call") or (report.when == "setup" and report.outcome == "skipped"):
            self.reports[report.project].append(report)

    def pytest_sessionfinish(self, session: Session, exitstatus: Union[int, ExitCode]) -> None:
        self._generate_report()

    def pytest_terminal_summary(self, terminalreporter: TerminalReporter):
        terminalreporter.write_sep("--", f"pdf test report: {str(self.report_path)}")

    # -- plugin hooks impl.

    @staticmethod
    def pytest_pdf_report_project(item: Item) -> Optional[str]:
        return "Project"

    @staticmethod
    def pytest_pdf_report_release(project_name: str) -> Optional[str]:
        return "1.0.0"

    @staticmethod
    def pytest_pdf_report_packages(project_name: str) -> List[Tuple[str, str]]:
        return [
            ("PACKAGE x", "1.0.0"),
            ("PACKAGE y", "1.0.1"),
        ]

    @staticmethod
    def pytest_pdf_report_additional_info(project_name: str) -> Dict[str, List[Tuple[str, str]]]:
        return {
            "dev1": [
                ("enpoint", "http://www.vodafone.de/"),
                ("username", "tester"),
            ]
        }
