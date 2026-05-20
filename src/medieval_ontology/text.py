"""Text segmentation utilities."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Section:
    index: int
    title: str
    text: str


SECTION_RE = re.compile(
    r"^(?P<title>(?:P<articula>|Particula|LIBER|<INCIPIT|Incipit|Quando)\b.*)$",
    re.IGNORECASE,
)
SENTENCE_RE = re.compile(r"(?<=[.!?;:])\s+|\n+")


def normalize_text(text: str) -> str:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def split_sections(text: str) -> list[Section]:
    text = normalize_text(text)
    sections: list[Section] = []
    current_title = "Front Matter"
    current_lines: list[str] = []

    def flush() -> None:
        if current_lines:
            if current_title == "Front Matter" and all(_looks_like_banner(line) for line in current_lines):
                return
            sections.append(
                Section(
                    index=len(sections) + 1,
                    title=current_title,
                    text="\n".join(current_lines).strip(),
                )
            )

    for line in text.splitlines():
        if SECTION_RE.match(line) and current_lines:
            flush()
            current_title = line
            current_lines = []
        elif SECTION_RE.match(line):
            current_title = line
        else:
            current_lines.append(line)
    flush()
    return sections


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_RE.split(text) if part.strip()]


def _looks_like_banner(line: str) -> bool:
    letters = [character for character in line if character.isalpha()]
    return bool(letters) and all(character.isupper() for character in letters)
