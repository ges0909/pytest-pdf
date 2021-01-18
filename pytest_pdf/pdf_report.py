import logging
import time
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Union, NamedTuple, Dict, List, Optional, Callable

from _pytest.config import ExitCode
from _pytest.main import Session
from _pytest.nodes import Collector
from _pytest.reports import TestReport
from py._path.local import LocalPath

logger = logging.getLogger(__name__)


class Project(NamedTuple):
    root: Path


class PdfReport:
    """collects data for pdf report generation"""

    def __init__(self, report_path: Path):
        self.report_path = report_path
        self.reports: Dict[Project, List[TestReport]] = defaultdict(list)
        self.project = None
        self.title = None
        self.suite_start_time = None

    def _error_text(self, error: str):
        ellipsis_ = "..."
        max_length = 20
        max_length_2 = max_length + len(ellipsis_)
        lines = error.split()
        error_ = " ".join(lines)
        return f"{error_[:max_length]}{ellipsis_}" if len(error_) > max_length_2 else error_

    def _generate_report_statistic(self):
        reports = sum([r for r in self.reports.values()], [])  # sum = flatten
        self.passed = len([r for r in reports if r.when == "call" and r.outcome == "passed"])
        self.failed = len([r for r in reports if r.when == "call" and r.outcome == "failed"])
        self.skipped = len([r for r in reports if r.when == "setup" and r.outcome == "skipped"])

    def _generate_report(self) -> None:
        for project, reports in self.reports.items():
            name = project.root.name if project else "<undefined>"
            for i, r in enumerate(reports):
                case_id, step_id = r.nodeid.split("::")
                error = self._error_text(r.longreprtext)
                print(
                    f"{i}. {name}, {case_id}, {step_id}, {r.when:<8}, {r.outcome:<7}, {error or 'none'}, {r.caplog or 'none'}"
                )

    def _save_report(self) -> None:
        pass

    @lru_cache(maxsize=None)
    def _find(self, path: Path, root: Path, predicate: Callable[[Path], bool]) -> Optional[Path]:
        """finds 'path' bottom-up until 'root'"""
        dir = path.parent.relative_to(root).absolute()
        while True:
            path_ = dir / path
            logger.debug("find file '%s', dir '%s'", str(path), str(path_))
            if predicate(path_):
                return path_
            if dir == root:
                return None
            dir = dir.parent

    def pytest_collect_file(self, path: LocalPath, parent: Session) -> Optional[Collector]:
        """searches project from 'path' bottom-up"""
        root = Path(parent.fspath)
        test_file = Path(path)
        project_dir = test_file.parent.parent / "impl" / "project"
        project_path = self._find(path=project_dir, root=root, predicate=lambda p: p.is_dir())
        self.project = Project(root=project_path.parent.parent) if project_path else None
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

    def pytest_pdf_report_title(self, session: Session) -> str:
        # search 'about' impl. and call it to get the '*.jar'
        return "this is the reurn title returned by a hook"
