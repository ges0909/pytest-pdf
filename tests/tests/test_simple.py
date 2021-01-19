import pytest


def test_passed():
    assert True


def test_failed():
    assert False


@pytest.mark.skip
def test_skipped():
    assert True
