from pathlib import Path
from typing import Tuple, Optional, List


def pytest_pdf_project_name(top: Path, bottom: Path) -> Optional[str]:
    """returns project name"""


def pytest_pdf_project_version(project_name: str) -> Optional[str]:
    """returns project version"""


def pytest_pdf_environment_name(project_name: str) -> Optional[str]:
    """returns project environment name"""


def pytest_pdf_environment_data(environment_name: str) -> List[Tuple[str, str]]:
    """returns key and value of environment data to be added to report"""


def pytest_pdf_tested_packages(project_name: str) -> List[Tuple[str, str]]:
    """returns name and version of tested project packages"""


def pytest_pdf_skip_reason(nodeid: str) -> Optional[str]:
    """returns skip reason of test with 'nodeid'"""
