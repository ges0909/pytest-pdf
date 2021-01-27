from dataclasses import dataclass


@dataclass(frozen=True)
class Result:
    passed = "passed"
    failed = "failed"
    skipped = "skipped"
