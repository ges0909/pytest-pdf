from pathlib import Path
from typing import Tuple, Optional, List

from pytest_pdf.report_info import ReportInfo


def pytest_pdf_report_project_name(top: Path, bottom: Path) -> Optional[str]:
    """returns project name"""


def pytest_pdf_report_info(name: str) -> Optional[ReportInfo]:
    """returns additional report info"""


def pytest_pdf_skip_reason(nodeid: str) -> Optional[str]:
    """returns skip reason of test with 'nodeid'"""
