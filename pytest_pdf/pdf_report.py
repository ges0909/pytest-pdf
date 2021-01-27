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
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Flowable, PageBreak, TA_CENTER

from pytest_pdf.options import Option

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


class PdfReport:
    """collects test results and generates pdf report"""

    def __init__(self, report_path: Path):
        self.start_dir = None
        self.now = datetime.datetime.now()
        self.reports: Dict[str, List[TestReport]] = defaultdict(list)
        path = Path(report_path)
        self.report_path = path.parent / self.now.strftime(path.name)
        if self.report_path.parent.parts:
            self.report_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _error_text(error: str):
        error_text_ellipsis_max_length = ERROR_TEXT_MAX_LENGTH + len(ELLIPSIS)
        lines = error.split()
        error_ = " ".join(lines)
        return f"{error_[:ERROR_TEXT_MAX_LENGTH]}{ELLIPSIS}" if len(error_) > error_text_ellipsis_max_length else error_

    @staticmethod
    def _statistics(reports: List[TestReport]) -> Tuple[int, int, int]:
        passed = len([r for r in reports if r.when == "call" and r.outcome == "passed"])
        failed = len([r for r in reports if r.when == "call" and r.outcome == "failed"])
        skipped = len([r for r in reports if r.when == "setup" and r.outcome == "skipped"])
        return passed, failed, skipped

    @staticmethod
    def _flatten(reports: Dict[str, List[TestReport]]) -> List[TestReport]:
        return sum([r for r in reports.values()], [])

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

    def _story(self, session: Session) -> List[Flowable]:
        flowables = []

        for name, reports in self.reports.items():

            version = PdfReport.pytest_pdf_project_version(name)
            environment = PdfReport.pytest_pdf_environment_name(name)
            tested_packages = PdfReport.pytest_pdf_tested_packages(name)
            tested_packages_ = [f"{p[0]} ({p[1]})" for p in tested_packages]

            titles = [
                Paragraph(text=f"{name} {version}", style=STYLES["Title"]),
                Paragraph(text="Test report", style=TITLE_STYLE),
                Paragraph(text=f"Environment:  {environment}", style=TITLE_STYLE),
                Paragraph(text=f"Tested software: {', '.join(tested_packages_)}", style=TITLE_STYLE),
                Paragraph(text=f"Generated on: {self.now.strftime('%d %b %Y, %H:%M:%S')}", style=TITLE_STYLE),
            ]

            # if session.config.getoption(Option.LF, None):
            #     step_items = [item for script_item in project.items for item in script_item.children]
            # else:
            #     step_items = [item for script_item in project.items for item in script_item.children if item.selected]

            charts = Drawing(
                500,
                500,
                PieChartWithLegend(
                    title="Test Cases", data=derive_results(config=config, items=project.items), x=0, y=0
                ),
                PieChartWithLegend(
                    title="Test Steps ", data=sum_up_results(config=config, items=step_items), x=250, y=0
                ),
            )

            if session.config.getoption(Option.PDF_SHORT, None):
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

    def __generate_report(self) -> None:
        for name, reports in self.reports.items():
            passed, failed, skipped = PdfReport._statistics(reports=reports)
            for i, r in enumerate(reports):
                case_id, step_id = r.nodeid.split("::")
                error = PdfReport._error_text(r.longreprtext)
                print(
                    f"{i}. {name}, {case_id}, {step_id}, {r.when:<8}, {r.outcome:<7}, {error or '?'}, {r.caplog or '?'}"
                )

    def _generate_report(self, session: Session) -> None:
        doc = self._create_doc()
        doc.multiBuild(story=self._story(session))

    def _save_report(self) -> None:
        pass

    def pytest_runtest_logreport(self, report: TestReport) -> None:
        bottom = self.start_dir / report.fspath
        name = PdfReport.pytest_pdf_project_name(top=self.start_dir, bottom=bottom)
        self.reports[name].append(report)

    def pytest_sessionstart(self, session: Session) -> None:
        self.start_dir = Path(session.fspath)

    def pytest_sessionfinish(self, session: Session, exitstatus: Union[int, ExitCode]) -> None:
        reports = PdfReport._flatten(reports=self.reports)
        passed, failed, skipped = PdfReport._statistics(reports=reports)
        self._generate_report(session)
        self._save_report()

    def pytest_terminal_summary(self, terminalreporter: TerminalReporter):
        terminalreporter.write_sep("--", f"pdf test report: {str(self.report_path)}")

    # -- hook impl.

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
