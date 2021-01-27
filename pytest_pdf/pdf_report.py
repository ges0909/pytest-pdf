import datetime
import logging
from collections import defaultdict
from pathlib import Path
from typing import Union, Dict, List, Optional, Tuple

from _pytest.config import ExitCode
from _pytest.main import Session
from _pytest.reports import TestReport
from _pytest.terminal import TerminalReporter
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Flowable

from pytest_pdf.chart import PieChartWithLegend
from pytest_pdf.group_by_key import group_by_key
from pytest_pdf.mkdir import mkdir
from pytest_pdf.result import Result

ELLIPSIS = "..."
ERROR_TEXT_MAX_LENGTH = 20

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

logger = logging.getLogger(__name__)

LABELS = (Result.passed, Result.skipped, Result.failed)
COLORS = (colors.lightgreen, colors.yellow, colors.orangered)


class PdfReport:
    """collects test results and generates pdf report"""

    def __init__(self, report_path: Path):
        self.start_dir = None
        self.now = datetime.datetime.now()
        self.reports: Dict[str, List[TestReport]] = defaultdict(list)
        path = Path(report_path)
        self.report_path = path.parent / self.now.strftime(path.name)
        mkdir(path=self.report_path)

    @staticmethod
    def _error_text(error: str):
        error_text_ellipsis_max_length = ERROR_TEXT_MAX_LENGTH + len(ELLIPSIS)
        lines = error.split()
        error_ = " ".join(lines)
        return f"{error_[:ERROR_TEXT_MAX_LENGTH]}{ELLIPSIS}" if len(error_) > error_text_ellipsis_max_length else error_

    @staticmethod
    def _test_step_results(reports: List[TestReport]) -> Tuple[int, int, int]:
        passed = len([r for r in reports if r.when == "call" and r.outcome == "passed"])
        failed = len([r for r in reports if r.when == "call" and r.outcome == "failed"])
        skipped = len([r for r in reports if r.when == "setup" and r.outcome == "skipped"])
        return passed, failed, skipped

    @staticmethod
    def _test_case_results(reports: List[TestReport]) -> Tuple[int, int, int]:
        test_cases = group_by_key(things=reports, key=lambda r: r.nodeid.split("::")[0])
        passed, skipped, failed = 0, 0, 0
        for _, reports_ in test_cases.items():
            _passed, _skipped, _failed = PdfReport._test_step_results(reports=reports_)
            if _failed > 0:
                failed += 1
            elif _passed > 0:
                passed += 1
            else:
                skipped += 1
        return passed, skipped, failed

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

    def _story(self, session: Session) -> List[Flowable]:
        flowables = []
        for project, reports in self.reports.items():

            version = PdfReport.pytest_pdf_project_version(project)
            environment = PdfReport.pytest_pdf_environment_name(project)
            tested_packages = PdfReport.pytest_pdf_tested_packages(project)
            tested_packages_ = [f"{package[0]} ({package[1]})" for package in tested_packages]

            titles = [
                Paragraph(text=f"{project} {version}", style=STYLES["Title"]),
                Paragraph(text="Test report", style=TITLE_STYLE),
                Paragraph(text=f"Environment:  {environment}", style=TITLE_STYLE),
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

            # if session.config.getoption(Option.PDF_SHORT, None):
            #     result_pages = [
            #         get_test_case_result_page(
            #             config=config,
            #             items=project.items,
            #             heading=Paragraph("Overview Test Case Results", style=HEADING_1_STYLE),
            #         ),
            #         PageBreak(),
            #         *get_test_step_result_pages(
            #             items=[item for item in step_items if item.error],
            #             heading=Paragraph("Test Step Errors", style=HEADING_1_STYLE),
            #         ),
            #     ]
            # else:
            #     result_pages = [
            #         *get_test_step_result_pages(
            #             items=step_items,
            #             heading=Paragraph("Test Step Results", style=HEADING_1_STYLE),
            #         ),
            #     ]

            flowables.extend(
                [
                    *titles,
                    charts,
                    # PageBreak(),
                    # *result_pages,
                    # get_environment_page(
                    #     env=project.items[0].env,  # take 1st script item, because all use the same env
                    #     heading=Paragraph("Environment Data", style=HEADING_1_STYLE),
                    # ),
                    # PageBreak(),
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

    def _generate_report(self, session: Session) -> None:
        doc = self._create_doc()
        doc.multiBuild(story=self._story(session))

    # -- pytest hooks

    def pytest_runtest_logreport(self, report: TestReport) -> None:
        bottom = self.start_dir / report.fspath
        name = PdfReport.pytest_pdf_project_name(top=self.start_dir, bottom=bottom)
        self.reports[name].append(report)

    def pytest_sessionstart(self, session: Session) -> None:
        self.start_dir = Path(session.fspath)

    def pytest_sessionfinish(self, session: Session, exitstatus: Union[int, ExitCode]) -> None:
        self._generate_report(session)

    def pytest_terminal_summary(self, terminalreporter: TerminalReporter):
        terminalreporter.write_sep("--", f"pdf test report: {str(self.report_path)}")

    # -- plugin hooks impl.

    @staticmethod
    def pytest_pdf_project_name(top: Path, bottom: Path) -> Optional[str]:
        return "Test Project"

    @staticmethod
    def pytest_pdf_project_version(name: str) -> Optional[str]:
        return "1.0.0"

    @staticmethod
    def pytest_pdf_environment_name(name: str) -> Optional[str]:
        return "DEV1"

    @staticmethod
    def pytest_pdf_tested_packages(name: str) -> List[Tuple[str, str]]:
        return [
            ("SOFTWARE", "1.0.0"),
        ]
