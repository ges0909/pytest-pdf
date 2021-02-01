from typing import Tuple, Optional, List, Dict

from _pytest.nodes import Item


def pytest_pdf_report_project(item: Item) -> Optional[str]:
    """returns unique project id, e.g. a name"""


def pytest_pdf_report_release(project: str) -> Optional[str]:
    """returns project release"""


def pytest_pdf_report_packages(project: str) -> List[Tuple[str, str]]:
    """returns name and version of tested packages"""


def pytest_pdf_report_additional_info(project: str) -> Dict[str, List[Tuple[str, str]]]:
    """returns additional informations"""
