import logging
import time
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Union, Dict, List, Optional, Callable, Tuple

from _pytest.config import ExitCode
from _pytest.main import Session
from _pytest.reports import TestReport

logger = logging.getLogger(__name__)


class PdfReport:
    """collects data for pdf report generation"""

    def __init__(self, report_path: Path):
        self.report_path = report_path
        self.start_dir = None
        self.session_start_time = None
        self.reports: Dict[Path, List[TestReport]] = defaultdict(list)

    @staticmethod
    def _error_text(error: str):
        ellipsis_ = "..."
        max_length = 20
        max_length_2 = max_length + len(ellipsis_)
        lines = error.split()
        error_ = " ".join(lines)
        return f"{error_[:max_length]}{ellipsis_}" if len(error_) > max_length_2 else error_

    @staticmethod
    def _statistics(reports: List[TestReport]) -> Tuple[int, int, int]:
        passed = len([r for r in reports if r.when == "call" and r.outcome == "passed"])
        failed = len([r for r in reports if r.when == "call" and r.outcome == "failed"])
        skipped = len([r for r in reports if r.when == "setup" and r.outcome == "skipped"])
        return passed, failed, skipped

    def _generate_report(self) -> None:
        for project_path, reports in self.reports.items():
            name = project_path.parent.parent.name
            passed, failed, skipped = PdfReport._statistics(reports=reports)
            for i, r in enumerate(reports):
                case_id, step_id = r.nodeid.split("::")
                error = PdfReport._error_text(r.longreprtext)
                print(
                    f"{i}. {name}, {case_id}, {step_id}, {r.when:<8}, {r.outcome:<7}, {error or '?'}, {r.caplog or '?'}"
                )

    def _save_report(self) -> None:
        pass

    @lru_cache(maxsize=None)
    def _find(self, top: Path, bottom: Path, rel_path: Path, predicate: Callable[[Path], bool]) -> Optional[Path]:
        """try to find 'rel_path' from 'bottom' to 'top' dir."""
        dir_ = top / bottom.relative_to(top)
        while True:
            path_ = dir_ / rel_path
            logger.debug("find file '%s', dir '%s'", str(bottom), str(path_))
            if predicate(path_):
                return path_
            if dir_ == top:
                return None
            dir_ = dir_.parent

    def pytest_runtest_logreport(self, report: TestReport) -> None:
        bottom = (self.start_dir / report.fspath).parent.parent
        rel_path = Path("impl/project")
        proj_path = (
            self._find(top=self.start_dir, bottom=bottom, rel_path=rel_path, predicate=lambda p: p.is_dir()) or ""
        )
        self.reports[proj_path].append(report)

    def pytest_sessionstart(self, session: Session) -> None:
        logger.info("test session started")
        self.start_dir = Path(session.fspath)
        self.session_start_time = time.time()

    def pytest_sessionfinish(self, session: Session, exitstatus: Union[int, ExitCode]) -> None:
        logger.info("test session finished")
        title = session.config.hook.pytest_pdf_report_title(session=session)
        version = session.config.hook.pytest_pdf_tested_software(session=session)
        reports = sum([r for r in self.reports.values()], [])  # sum = flatten
        passed, failed, skipped = PdfReport._statistics(reports=reports)
        self._generate_report()
        self._save_report()

    def pytest_terminal_summary(self, terminalreporter):
        terminalreporter.write_sep("--", f"pdf test report: {str(self.report_path)}")

    def pytest_pdf_report_title(self, session: Session) -> str:
        return "this is the return title returned by a hook"

    def pytest_pdf_tested_software(self, session: Session) -> Tuple[str]:
        # search 'about' impl. and call it to get the '*.jar'
        return ("",)
