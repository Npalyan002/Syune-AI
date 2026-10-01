"""Local read-only text perception. No execution, network, or semantic claims."""
from __future__ import annotations

from io import BytesIO
import re
from typing import Protocol
from uuid import NAMESPACE_URL, uuid5

from pypdf import PdfReader

from syune.core import ContentBlockId
from syune.memory import SourceLocator
from .errors import StudyError, StudyErrorCode
from .model import PerceivedBlock, SourceRevisionId, block_fingerprint

PARSER_VERSION = "1"
BLOCK_SCHEME_VERSION = "1"


class SourceParser(Protocol):
    version: str

    def parse(self, data: bytes, revision_id: SourceRevisionId) -> tuple[PerceivedBlock, ...]: ...


def _block(revision_id: SourceRevisionId, order: int, text: str, locator: SourceLocator,
           heading_path: tuple[str, ...] = ()) -> PerceivedBlock:
    key = f"b{order:06d}"
    return PerceivedBlock(
        ContentBlockId(uuid5(NAMESPACE_URL, f"syune:block:{revision_id}:{key}")),
        key, revision_id, "text", text, order, block_fingerprint(text),
        locator, PARSER_VERSION, heading_path,
    )


def _decode_text(data: bytes) -> str:
    if not data:
        raise StudyError(StudyErrorCode.NO_USABLE_TEXT, "empty text source")
    if b"\x00" in data:
        raise StudyError(StudyErrorCode.PARSE_FAILURE, "binary NUL in text source")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise StudyError(StudyErrorCode.PARSE_FAILURE, "source must be UTF-8 text") from exc
    if any(ord(c) < 32 and c not in "\t\n\r\f" for c in text):
        raise StudyError(StudyErrorCode.PARSE_FAILURE, "binary control characters in text source")
    if not text.strip():
        raise StudyError(StudyErrorCode.NO_USABLE_TEXT, "no usable text")
    return text.replace("\r\n", "\n").replace("\r", "\n")


class TxtParser:
    version = PARSER_VERSION

    def parse(self, data: bytes, revision_id: SourceRevisionId) -> tuple[PerceivedBlock, ...]:
        text = _decode_text(data)
        lines = text.splitlines()
        blocks: list[PerceivedBlock] = []
        current: list[str] = []
        start = 1

        def flush(end: int) -> None:
            if current and "\n".join(current).strip():
                content = "\n".join(current).strip()
                order = len(blocks)
                blocks.append(_block(revision_id, order, content,
                    SourceLocator(block=f"b{order:06d}", span=f"lines:{start}-{end}")))
            current.clear()

        for line_number, line in enumerate(lines, 1):
            if not line.strip():
                flush(line_number - 1)
                start = line_number + 1
            else:
                if not current:
                    start = line_number
                current.append(line)
        flush(len(lines))
        return tuple(blocks)


class MarkdownParser:
    version = PARSER_VERSION

    def parse(self, data: bytes, revision_id: SourceRevisionId) -> tuple[PerceivedBlock, ...]:
        lines = _decode_text(data).splitlines()
        blocks: list[PerceivedBlock] = []
        headings: list[str] = []
        current: list[str] = []
        start = 1
        fence: str | None = None

        def flush(end: int) -> None:
            if current and "\n".join(current).strip():
                order = len(blocks)
                blocks.append(_block(revision_id, order, "\n".join(current).strip(),
                    SourceLocator(section=" / ".join(headings) or None,
                                  block=f"b{order:06d}", span=f"lines:{start}-{end}"),
                    tuple(headings)))
            current.clear()

        for line_number, line in enumerate(lines, 1):
            stripped = line.strip()
            fence_match = re.match(r"^(" + chr(96) * 3 + r"|~~~)", stripped)
            if fence is not None:
                current.append(line)
                if stripped.startswith(fence):
                    flush(line_number)
                    fence = None
                continue
            if fence_match:
                flush(line_number - 1)
                start = line_number
                fence = fence_match.group(1)
                current.append(line)
                continue
            heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if heading:
                flush(line_number - 1)
                depth = len(heading.group(1))
                headings[:] = headings[:depth - 1] + [heading.group(2)]
                start = line_number
                current.append(line)
                flush(line_number)
                continue
            if not stripped:
                flush(line_number - 1)
                start = line_number + 1
                continue
            if not current:
                start = line_number
            current.append(line)
        flush(len(lines))
        return tuple(blocks)


class PdfTextParser:
    version = PARSER_VERSION

    def parse(self, data: bytes, revision_id: SourceRevisionId) -> tuple[PerceivedBlock, ...]:
        try:
            reader = PdfReader(BytesIO(data), strict=False)
            if reader.is_encrypted:
                raise StudyError(StudyErrorCode.ENCRYPTED_PDF, "encrypted PDF is unsupported")
            blocks: list[PerceivedBlock] = []
            for page_number, page in enumerate(reader.pages, 1):
                text = (page.extract_text(extraction_mode="plain") or "").strip()
                if not text:
                    continue
                for paragraph in re.split(r"\n\s*\n", text):
                    paragraph = paragraph.strip()
                    if paragraph:
                        order = len(blocks)
                        blocks.append(_block(revision_id, order, paragraph,
                            SourceLocator(page=page_number, block=f"b{order:06d}")))
            if not blocks:
                raise StudyError(StudyErrorCode.NO_USABLE_TEXT, "PDF has no extractable text")
            return tuple(blocks)
        except StudyError:
            raise
        except Exception as exc:
            raise StudyError(StudyErrorCode.PARSE_FAILURE, f"PDF text extraction failed: {type(exc).__name__}") from exc


PARSERS: dict[str, SourceParser] = {
    ".txt": TxtParser(),
    ".md": MarkdownParser(),
    ".markdown": MarkdownParser(),
    ".pdf": PdfTextParser(),
}
