import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Union, NamedTuple, Dict, List, Optional

from _pytest.config import ExitCode
from _pytest.main import Session
from _pytest.nodes import Collector
from _pytest.reports import TestReport
from py._path.local import LocalPath

logger = logging.getLogger(__name__)


class Project(NamedTuple):
    name: str


class PdfReport:
    """collects data for pdf report generation"""

    def __init__(self, report_path: Path):
        self.report_path = report_path
        self.reports: Dict[Project, List[TestReport]] = defaultdict(list)

    def _error_text(self, error: str):
        ellipsis = "..."
        max = 20
        max2 = max + len(ellipsis)
        lines = error.split()
        error_ = " ".join(lines)
        return f"{error_[:max]}{ellipsis}" if len(error_) > max2 else error_

    def _generate_report_statistic(self):
        reports = sum([r for r in self.reports.values()], [])  # sum = flatten
        self.passed = len([r for r in reports if r.when == "call" and r.outcome == "passed"])
        self.failed = len([r for r in reports if r.when == "call" and r.outcome == "failed"])
        self.skipped = len([r for r in reports if r.when == "setup" and r.outcome == "skipped"])

    def _generate_report(self) -> None:
        for project, reports in self.reports.items():
            for i, r in enumerate(reports):
                case_id, step_id = r.nodeid.split("::")
                error = self._error_text(r.longreprtext)
                print(
                    f"{i}. {project.name}, {case_id}, {step_id}, {r.when:<8}, {r.outcome:<7}, {error or 'none'}, {r.caplog or 'none'}"
                )

    def _save_report(self) -> None:
        pass

    def pytest_collect_file(self, path: LocalPath, parent: Session) -> Optional[Collector]:
        """searches project from 'path' bottom-up"""
        start_dir = Path(str(parent.startdir))
        self.project = Project(name=Path(path).parent.name)
        return None

    def pytest_runtest_logreport(self, report: TestReport) -> None:
        self.reports[self.project].append(report)

    def pytest_sessionstart(self, session: Session) -> None:
        logger.info("session start")
        self.suite_start_time = time.time()

    def pytest_sessionfinish(self, session: Session, exitstatus: Union[int, ExitCode]) -> None:
        logger.info("session finish")
        self.title = session.config.hook.pytest_pdf_report_title(session=session)
        self._generate_report_statistic()
        self._generate_report()
        self._save_report()

    def pytest_terminal_summary(self, terminalreporter):
        terminalreporter.write_sep("--", f"pdf test report: {str(self.report_path)}")

    def pytest_pdf_report_title(session: Session) -> str:
        # search 'about' impl. and call it to get the '*.jar'
        return "this is the reurn title returned by a hook"
