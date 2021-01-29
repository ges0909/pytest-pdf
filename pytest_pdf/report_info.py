from typing import NamedTuple, List, Tuple, Optional, Dict


class ReportInfo(NamedTuple):
    title: Optional[str]
    release: Optional[str]
    packages: List[Tuple[str, str]]
    context: Optional[Dict[str, List[Tuple[str, str]]]]
