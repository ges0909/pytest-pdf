from typing import NamedTuple, List, Tuple, Optional, Dict


class ReportTitle(NamedTuple):
    title: Optional[str]
    project: Optional[str]
    release: Optional[str]
    packages: List[Tuple[str, str]]
    context: Optional[Dict[str, List[Tuple[str, str]]]]
