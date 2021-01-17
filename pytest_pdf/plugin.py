from _pytest.config import Config, PytestPluginManager
from _pytest.config.argparsing import Parser

from pytest_pdf.pdf_report import PdfReport


def pytest_addhooks(pluginmanager: PytestPluginManager) -> None:
    from pytest_pdf import hooks

    pluginmanager.add_hookspecs(hooks)


def pytest_addoption(parser: Parser, pluginmanager: PytestPluginManager) -> None:
    group = parser.getgroup("terminal reporting")
    group.addoption(
        "--pdf",
        action="store",
        default=None,
        help="create pdf report file at given path",
    )
    group.addoption(
        "--pdf-short",
        action="store_true",
        help="create a pdf report containing failed tests only",
    )


def pytest_configure(config: Config):
    if pdf_report_path := config.getoption(name="--pdf", default=None):
        config._pdf = PdfReport(pdf_report_path, config)
        config.pluginmanager.register(config._pdf)


def pytest_unconfigure(config: Config):
    if config.getoption("--pdf", None):
        config.pluginmanager.unregister(config._pdf)
        del config._pdf
