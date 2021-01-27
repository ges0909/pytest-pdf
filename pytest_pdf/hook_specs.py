from pathlib import Path
from typing import Tuple, Optional, List


def pytest_pdf_project_name(top: Path, bottom: Path) -> Optional[str]:
    """returns project name"""


def pytest_pdf_project_version(name: str) -> Optional[str]:
    """returns project version"""


def pytest_pdf_environment_name(name: str) -> Optional[str]:
    """returns environment name"""


def pytest_pdf_tested_packages(name: str) -> List[Tuple[str, str]]:
    """returns tested packages consisting of name and version"""
