from collections import defaultdict
from typing import List, Dict, Any, Callable


def group_by_key(things: List[Any], key: Callable[[Any], Dict[str, Any]]) -> Dict[str, List[Any]]:
    """groups elements of a list by key"""
    groups = defaultdict(list)
    for thing in things:
        groups[key(thing)].append(thing)
    return groups
