from pathlib import Path
from typing import Tuple, Optional, List


def pytest_pdf_report_project(top: Path, bottom: Path) -> Optional[str]:
    """returns project name"""


def pytest_pdf_report_release(project_name: str) -> Optional[str]:
    """returns project relases"""


def pytest_pdf_report_packages(project_name: str) -> List[Tuple[str, str]]:
    """returns name and version of tested project packages"""


def pytest_pdf_report_environment_name(project_name: str) -> Optional[str]:
    """returns project environment name"""


def pytest_pdf_report_environment_data(environment_name: str) -> List[Tuple[str, str]]:
    """returns key and value of environment data to be added to report"""
