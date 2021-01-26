import datetime
import logging
import time
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Union, Dict, List, Optional, Callable, Tuple

from _pytest.config import ExitCode
from _pytest.main import Session
from _pytest.reports import TestReport
from _pytest.terminal import TerminalReporter

logger = logging.getLogger(__name__)

ELLIPSIS = "..."
ERROR_TEXT_MAX_LENGTH = 20


class PdfReport:
    """collects data for pdf report generation"""

    def __init__(self, report_path: Path):
        path = Path(report_path)
        now = datetime.datetime.now()
        self.report_path = path.parent / now.strftime(path.name)
        self.start_dir = None
        self.session_start_time = None
        self.reports: Dict[Path, List[TestReport]] = defaultdict(list)
        self.title = None
        self.sw_infos = None

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
    def _flatten(reports: Dict[Path, List[TestReport]]) -> List[TestReport]:
        return sum([r for r in reports.values()], [])

    def _generate_report(self) -> None:
        for project_path, reports in self.reports.items():
            name = project_path.parent.parent.name if project_path else "Default project"
            passed, failed, skipped = PdfReport._statistics(reports=reports)
            for i, r in enumerate(reports):
                case_id, step_id = r.nodeid.split("::")
                error = PdfReport._error_text(r.longreprtext)
                print(
                    f"{i}. {name}, {case_id}, {step_id}, {r.when:<8}, {r.outcome:<7}, {error or '?'}, {r.caplog or '?'}"
                )

    def _save_report(self) -> None:
        pass

    def pytest_runtest_logreport(self, report: TestReport) -> None:
        # bottom = (self.start_dir / report.fspath).parent.parent
        bottom = self.start_dir / report.fspath
        project_path = PdfReport.pytest_pdf_project_name(top=self.start_dir, bottom=bottom)
        self.reports[project_path].append(report)

    def pytest_sessionstart(self, session: Session) -> None:
        logger.info("test session started")
        self.start_dir = Path(session.fspath)
        self.session_start_time = time.time()

    def pytest_sessionfinish(self, session: Session, exitstatus: Union[int, ExitCode]) -> None:
        logger.info("test session finished")
        self.title = session.config.hook.pytest_pdf_report_title(session=session)
        self.sw_infos = session.config.hook.pytest_pdf_tested_software(session=session)
        reports = PdfReport._flatten(reports=self.reports)
        passed, failed, skipped = PdfReport._statistics(reports=reports)
        self._generate_report()
        self._save_report()

    def pytest_terminal_summary(self, terminalreporter: TerminalReporter):
        terminalreporter.write_sep("--", f"pdf test report: {str(self.report_path)}")

    # -- hook impl.

    @staticmethod
    def pytest_pdf_project_name(top: Path, bottom: Path) -> Optional[Path]:
        @lru_cache(maxsize=128)
        def _find(path: Path, top_: Path, bottom_: Path, predicate: Callable[[Path], bool]) -> Optional[Path]:
            """try to find 'path' from 'bottom' to 'top' dir."""
            dir_ = top_ / bottom_.relative_to(top)
            while True:
                path_ = dir_ / path
                logger.debug("find file '%s', dir '%s'", str(bottom_), str(path_))
                if predicate(path_):
                    return path_
                if dir_ == top_:
                    return Path(".")
                dir_ = dir_.parent

        return _find(
            path=Path("impl/project"),
            top_=top,
            bottom_=bottom,
            predicate=lambda p: p.is_dir(),
        )

    @staticmethod
    def pytest_pdf_report_title(session: Session) -> str:
        return "Test title"

    @staticmethod
    def pytest_pdf_tested_software(session: Session) -> Tuple[str, str, list]:
        return "Test", "1.0.0", []
