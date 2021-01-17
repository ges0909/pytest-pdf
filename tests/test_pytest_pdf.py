from collections import defaultdict
from typing import List, Any, Dict, Callable

pytest_plugins = [
    "pytester",
]


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


# ---


def test_sum():
    list_ = [True, False, True, True]
    assert sum(list_) == 3


# ---


def groupby(
    elements: List[Any],
    key: Callable[[Any], Dict[Any, Any]],
) -> Dict[Any, Any]:
    groups = defaultdict(list)
    for e in elements:
        groups[key(e)].append(e)
    return groups


def test_groupby():
    elements = [
        {"a": 1},
        {"a": 2},
        {"a": 3},
        {"z": 101},
        {"z": 102},
        {"z": 103},
    ]

    groups = groupby(elements=elements, key=lambda e: list(e.keys())[0])

    assert groups == {
        "a": [
            {"a": 1},
            {"a": 2},
            {"a": 3},
        ],
        "z": [
            {"z": 101},
            {"z": 102},
            {"z": 103},
        ],
    }
