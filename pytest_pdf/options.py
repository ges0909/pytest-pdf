from dataclasses import dataclass


@dataclass(frozen=True)
class Option:
    PDF = "pdf"
    PDF_SHORT = "pdf-short"
