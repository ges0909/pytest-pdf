from pathlib import Path
from typing import Tuple, Optional

from _pytest.main import Session


def pytest_pdf_project_name(top: Path, bottom: Path) -> Optional[str]:
    """returns the path to the nearest dir. 'impl/project'"""


def pytest_pdf_report_title(session: Session) -> str:
    """returns the pdf report title"""


def pytest_pdf_tested_software(session: Session) -> Tuple[str, str, list]:
    """returns name, version, etc. of the tested software"""
