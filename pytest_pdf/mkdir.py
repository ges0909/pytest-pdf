from pathlib import Path


def mkdir(path: Path) -> None:
    if path.parent.parts:
        path.parent.mkdir(parents=True, exist_ok=True)
