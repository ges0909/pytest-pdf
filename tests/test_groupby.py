from collections import defaultdict
from typing import List, Any, Dict, Callable


def groupby(elements: List[Any], key: Callable[[Any], Dict[Any, Any]]) -> Dict[Any, Any]:
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
