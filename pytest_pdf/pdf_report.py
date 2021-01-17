import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Union

from _pytest.config import Config, ExitCode
from _pytest.main import Session
from _pytest.reports import TestReport, CollectReport

logger = logging.getLogger(__name__)


class PdfReport:
    def __init__(self, path: Path, config: Config):
        self.path = path
        self.config = config
        self.reports = defaultdict(list)

    def _generate_report(self, session):
        # passed = sum(filter(lambda r: r.passed, self.reports))
        # skipped = sum(filter(lambda r: r.skipped, self.reports))  # provided for 'when' == 'setup'
        # failed = sum(filter(lambda r: r.failed, self.reports))
        for _, v in self.reports.items():
            for i, r in enumerate(v):
                case_id, step_id = r.nodeid.split("::")
                errors = r.longreprtext.split()
                print(
                    f"{i}. {case_id}, {step_id}, {r.when:<8}, {r.outcome:<7}, {','.join(errors) or 'none'}, {r.caplog or 'none'}"
                )

    def _save_report(self, report_content):
        pass

    def pytest_runtest_logreport(self, report: Union[TestReport, CollectReport]) -> None:
        self.reports[report.nodeid].append(report)

    # def pytest_collectreport(self, report: CollectReport) -> None:
    #     if report.failed:
    #         self.append_failed(report)

    def pytest_sessionstart(self, session: Session) -> None:
        logger.info("session start")
        self.suite_start_time = time.time()

    def pytest_sessionfinish(self, session: Session, exitstatus: Union[int, ExitCode]) -> None:
        logger.info("session finish")
        result = session.config.hook.pytest_pdf_report_title(session=session)
        # self._post_process_reports()
        print(result)
        report_content = self._generate_report(session)
        self._save_report(report_content)

    def pytest_terminal_summary(self, terminalreporter):
        terminalreporter.write_sep("--", f"generated pdf file: {str(self.path)}")

    def pytest_pdf_register_project(ession: Session) -> None:
        pass

    def pytest_pdf_report_title(session: Session) -> str:
        # search 'about' impl. and call it to get the '*.jar'
        return "this is the reurn title returned by a hook"
