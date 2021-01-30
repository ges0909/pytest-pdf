from pathlib import Path
from typing import Tuple, Optional, List, Dict


def pytest_pdf_report_project(top: Path, bottom: Path) -> Optional[str]:
    """returns project name"""


def pytest_pdf_report_release(project_name: str) -> Optional[str]:
    """returns project relases"""


def pytest_pdf_report_packages(project_name: str) -> List[Tuple[str, str]]:
    """returns name and version of tested project packages"""


def pytest_pdf_report_additional_info(project_name: str) -> Dict[str, List[Tuple[str, str]]]:
    """returns additional informations"""
