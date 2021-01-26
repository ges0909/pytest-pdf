from typing import Tuple

from _pytest.main import Session

# -- hook spec.


def pytest_pdf_report_title(session: Session) -> str:
    """returns the pdf report title"""


def pytest_pdf_tested_software(session: Session) -> Tuple[str, str, list]:
    """returns name, version, etc. of the tested software"""
