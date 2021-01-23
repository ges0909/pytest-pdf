import pytest

pytest_plugins = [
    "pytester",
]


@pytest.mark.skip
def test_pytest_pdf_plugin(testdir):
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
    path = testdir.tmpdir.join("report.pdf")
    result = testdir.runpytest("--log-cli-level", "DEBUG", "--pdf", path)
    result.assert_outcomes(passed=1, failed=1, skipped=1)
