from pytest_pdf.group_by_key import group_by_key


def test_groupby():
    things = [
        {"a": 1},
        {"a": 2},
        {"a": 3},
        {"z": 101},
        {"z": 102},
        {"z": 103},
    ]

    groups = group_by_key(things=things, key=lambda e: list(e.keys())[0])

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
