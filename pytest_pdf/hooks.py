from _pytest.main import Session


def pytest_pdf_register_project(ession: Session) -> None:
    """called to register a project in collection"""


def pytest_pdf_report_title(session: Session) -> str:
    """called before adding the title to the report"""
