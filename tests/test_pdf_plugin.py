pytest_plugins = (
    "pytester",
    # "pytest_pdf.plugin",
)


# @pytest.mark.skip
def test_pytest_pdf_plugin(testdir, request):
    testdir.makepyfile(
        r"""
        import logging
        
        logger = logging.getLogger(__name__)
        
        import pytest
        
        def test_1():
            logger.info("test_1 ...")
            assert True
            
        def test_2():
            logger.info("test_2 ...")
            assert False
        
        @pytest.mark.skip(reason="no way of currently testing this")
        def test_3():
            logger.info("test_3 ...")
            assert False
        """
    )
    report_path = testdir.tmpdir.join("report.pdf")
    args = ["--pdf", report_path]  # "--log-cli-level", "DEBUG"
    if not request.config.pluginmanager.hasplugin("pytest_pdf.plugin"):
        args.extend(["-p", "pytest_pdf.plugin"])
    result = testdir.runpytest(*args)  # !!! remove 'pytest_pdf.egg-info/'
    result.assert_outcomes(passed=1, failed=1, skipped=1)
