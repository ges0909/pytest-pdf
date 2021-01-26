from _pytest.config import Config, PytestPluginManager
from _pytest.config.argparsing import Parser

from pytest_pdf.options import Option
from pytest_pdf.pdf_report import PdfReport


def pytest_addhooks(pluginmanager: PytestPluginManager) -> None:
    from pytest_pdf import hook_specs

    pluginmanager.add_hookspecs(hook_specs)


def pytest_addoption(parser: Parser, pluginmanager: PytestPluginManager) -> None:
    group = parser.getgroup("terminal reporting")
    group.addoption(
        f"--pdf",
        dest=Option.PDF,
        action="store",
        default=None,
        required=False,
        help="create pdf report file at given path",
    )
    group.addoption(
        f"--pdf-short",
        dest=Option.PDF_SHORT,
        action="store_true",
        default=False,
        required=False,
        help="lists failed test steps only in test report",
    )


def pytest_configure(config: Config):
    if report_path := config.getoption(name=Option.PDF, default=None):
        pdf_plugin = PdfReport(report_path)
        config.pluginmanager.register(pdf_plugin)


def pytest_unconfigure(config: Config):
    if config.getoption(Option.PDF, None):
        pdf_plugin = config.pluginmanager.getplugin("pytest_pdf.plugin")
        config.pluginmanager.unregister(pdf_plugin)
