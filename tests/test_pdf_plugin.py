from pathlib import Path

pytest_plugins = (
    "pytester",
    # "pytest_pdf.plugin",
)


def test_pytest_pdf_plugin(testdir, request):
    testdir.makepyfile(
        r"""
        import logging
        import pytest
        
        logger = logging.getLogger(__name__)


        # def test_1():
        #     logger.info("test_1 ...")
        #     assert True


        # def test_2():
        #     logger.info("test_2 ...")
        #     assert False
        
        
        # @pytest.mark.skip(reason="no way of currently testing this")
        # def test_3():
        #     logger.info("test_3 ...")
        #     assert False
        
        
        @pytest.mark.parametrize(
            "a,b,c",
            (
                (1, 2, 3),
                (4, 5, 6),
            ),
        )
        def test_4(a: int, b: int, c: int):
            assert True
    """
    )
    report_path = Path(testdir.tmpdir) / "test_report.pdf"
    args = [
        "--pdf",
        report_path,
        # "--pdf-short",
        # "--log-cli-level",
        # "DEBUG",
    ]
    if not request.config.pluginmanager.hasplugin("pytest_pdf.plugin"):
        args.extend(["-p", "pytest_pdf.plugin"])
    result = testdir.runpytest(*args)
    result.assert_outcomes(passed=2, failed=0, skipped=0)
