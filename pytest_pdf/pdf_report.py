import datetime
import logging
from collections import defaultdict
from itertools import groupby
from pathlib import Path
from typing import Union, Dict, List, Optional, Tuple, Generator

from _pytest.config import ExitCode, Config
from _pytest.main import Session
from _pytest.reports import TestReport
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
        self.start_dir = None
        self.now = datetime.datetime.now()
        self.reports: Dict[str, List[TestReport]] = defaultdict(list)
        path = Path(report_path)
        self.report_path = path.parent / self.now.strftime(path.name)
        mkdir(path=self.report_path)

    @staticmethod
    def _error_text(error: str, when: str, prefix: str = "FAILED "):
        lines = error.split()
        error_ = " ".join(lines)
        if error_.startswith(prefix):
            error_ = error_[len(prefix) :]  # remove prefix
        error_ += when
        length = ERROR_TEXT_MAX_LENGTH - len(ELLIPSIS)
        return f"{error_[:length]}{ELLIPSIS}" if len(error_) > length else error_

    @staticmethod
    def _test_step_results(reports: List[TestReport]) -> Tuple[int, int, int]:
        passed = len([r for r in reports if r.when == "call" and r.outcome == "passed"])
        failed = len([r for r in reports if r.when == "call" and r.outcome == "failed"])
        skipped = len([r for r in reports if r.when == "setup" and r.outcome == "skipped"])
        return passed, failed, skipped

    @staticmethod
    def _test_case_results(reports: List[TestReport]) -> Tuple[int, int, int]:
        test_cases = groupby(reports, lambda r: r.nodeid.split("::")[0])
        passed, skipped, failed = 0, 0, 0
        for _, reports_ in test_cases:
            _passed, _skipped, _failed = PdfReport._test_step_results(reports=reports_)
            if _failed > 0:
                failed += 1
            elif _passed > 0:
                passed += 1
            else:
                skipped += 1
        return passed, skipped, failed

    @staticmethod
    def _result_style(color_):
        return ParagraphStyle(name="Normal", fontSize=9, fontName="Courier", alignment=TA_CENTER, backColor=color_)

    @staticmethod
    def _test_case_result_page(reports: List[TestReport], heading: Flowable) -> Flowable:
        table_data = [
            [
                Paragraph("Skript", TABLE_HEADER_CELL_STYLE),
                Paragraph("Test Case Id", TABLE_HEADER_CELL_STYLE),
                Paragraph("Passed", TABLE_HEADER_CELL_STYLE),
                Paragraph("Skipped", TABLE_HEADER_CELL_STYLE),
                Paragraph("Failed", TABLE_HEADER_CELL_STYLE),
            ],
        ]

        for report in reports:
            passed, skipped, failed = PdfReport._test_step_results(reports=reports)
            table_data.append(
                [
                    Paragraph("to be added", TABLE_CELL_STYLE_LEFT),
                    Paragraph(report.nodeid.split("::")[0], TABLE_CELL_STYLE_LEFT),
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

    def _test_step_result_tables_grouped_by_test_case(
        self,
        reports: List[TestReport],
    ) -> Generator[Tuple[str, Table], None, None]:

        test_cases = groupby(reports, lambda r: r.nodeid.split("::")[0])

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

            previous_nodeid = None

            for span_to, report in enumerate(reports_, 1):  # 1 = exclude table header
                # colum 1
                if previous_nodeid and previous_nodeid == report.nodeid:
                    test_step_id_paragraph = Paragraph("", TABLE_CELL_STYLE_LEFT)
                else:
                    test_step_id_paragraph = Paragraph(report.nodeid.split("::")[1], TABLE_CELL_STYLE_LEFT)
                # column 2
                # TODO
                parameters = self.config.hook.pytest_pdf_test_parameters(nodeid=report.nodeid)
                parameter_paragraphs = [Paragraph(p, TABLE_CELL_STYLE_LEFT) for p in parameters[0]]
                # column 3
                result_paragraph = Paragraph(
                    report.outcome, PdfReport._result_style(COLORS[LABELS.index(report.outcome)])
                )
                # column 4
                when = ""
                text = ""
                error_paragraph = None
                if report.outcome == "skipped":
                    text = self.config.hook.pytest_pdf_skip_reason(nodeid=report.nodeid)[0]
                elif report.outcome == "failed":
                    when = report.when if report.when in ("setup", "teardown") else ""
                    text = report.longreprtext
                if text:
                    error_text = PdfReport._error_text(error=text, when=when)
                    error_paragraph = Paragraph(error_text, TABLE_CELL_STYLE_LEFT)

                table_data.append([test_step_id_paragraph, parameter_paragraphs, result_paragraph, error_paragraph])

                previous_nodeid = report.nodeid

            yield test_case_id, Table(
                data=table_data,
                colWidths=[180, 140, 50, 90],
                repeatRows=1,
                hAlign="LEFT",
                style=TABLE_STYLE,
                spaceAfter=SPACE_AFTER_TABLE,
            )

    def _test_step_result_pages(self, reports: List[TestReport], heading: Flowable = None) -> List[Flowable]:
        flowables = []
        not_inserted = True
        for test_case_id, table in self._test_step_result_tables_grouped_by_test_case(reports=reports):
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

        data = self.config.hook.pytest_pdf_environment_data(environment_name=name)

        for key, value in data[0]:
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
        for name, reports in self.reports.items():

            version = self.config.hook.pytest_pdf_project_version(project_name=name)
            environment_name = self.config.hook.pytest_pdf_environment_name(project_name=name)
            tested_packages = self.config.hook.pytest_pdf_tested_packages(project_name=name)
            tested_packages_ = [f"{package[0]} ({package[1]})" for package in tested_packages[0]]

            titles = [
                Paragraph(text=f"{name} {version[0]}", style=STYLES["Title"]),
                Paragraph(text="Test report", style=TITLE_STYLE),
                Paragraph(text=f"Environment:  {environment_name[0]}", style=TITLE_STYLE),
                Paragraph(text=f"Tested software: {', '.join(tested_packages_)}", style=TITLE_STYLE),
                Paragraph(text=f"Generated on: {self.now.strftime('%d %b %Y, %H:%M:%S')}", style=TITLE_STYLE),
            ]

            test_case_results = PdfReport._test_case_results(reports)
            test_step_results = PdfReport._test_step_results(reports)

            charts = Drawing(
                500,
                500,
                PieChartWithLegend(
                    title="Test Cases",
                    data=test_case_results,
                    x=0,
                    y=0,
                    labels=LABELS,
                    colors_=COLORS,
                ),
                PieChartWithLegend(
                    title="Test Steps ",
                    data=test_step_results,
                    x=250,
                    y=0,
                    labels=LABELS,
                    colors_=COLORS,
                ),
            )

            if self.config.getoption(Option.PDF_SHORT, None):
                result_pages = [
                    self._test_case_result_page(
                        reports=reports,
                        heading=Paragraph("Test Case Results", style=HEADING_1_STYLE),
                    ),
                    *self._test_step_result_pages(
                        reports=[r for r in reports if r.outcome == "failed"],
                        heading=Paragraph("Test Step Errors", style=HEADING_1_STYLE),
                    ),
                ]
            else:
                result_pages = [
                    *self._test_step_result_pages(
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
                        name=environment_name,
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
            onPage=PdfReport._footer,
        )
        doc.addPageTemplates([template])
        return doc

    def _generate_report(self) -> None:
        doc = self._create_doc()
        doc.multiBuild(story=self._story())

    # -- pytest hooks

    def pytest_runtest_logreport(self, report: TestReport) -> None:
        bottom = self.start_dir / report.fspath
        name = self.config.hook.pytest_pdf_project_name(top=self.start_dir, bottom=bottom)
        self.reports[name[0]].append(report)

    def pytest_sessionstart(self, session: Session) -> None:
        self.start_dir = Path(session.fspath)

    def pytest_sessionfinish(self, session: Session, exitstatus: Union[int, ExitCode]) -> None:
        self._generate_report()

    def pytest_terminal_summary(self, terminalreporter: TerminalReporter):
        terminalreporter.write_sep("--", f"pdf test report: {str(self.report_path)}")

    def pytest_make_parametrize_id(self, config: Config, val: object, argname: str) -> Optional[str]:
        return f"{argname}={val}"

    # -- plugin hooks impl.

    @staticmethod
    def pytest_pdf_project_name(top: Path, bottom: Path) -> Optional[str]:
        return "Test Project"

    @staticmethod
    def pytest_pdf_project_version(project_name: str) -> Optional[str]:
        return "1.0.0"

    @staticmethod
    def pytest_pdf_environment_name(project_name: str) -> Optional[str]:
        return "DEV1"

    @staticmethod
    def pytest_pdf_environment_data(environment_name: str) -> List[Tuple[str, str]]:
        return [
            ("enpoint", "http://www.vodafone.de/"),
            ("username", "tester"),
        ]

    @staticmethod
    def pytest_pdf_tested_packages(project_name: str) -> List[Tuple[str, str]]:
        return [
            ("PACKAGE x", "1.0.0"),
            ("PACKAGE y", "1.0.1"),
        ]

    @staticmethod
    def pytest_pdf_skip_reason(nodeid: str) -> Optional[str]:
        return "not implemented"
