from io import BytesIO
from uuid import UUID

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from syune.study import (
    MarkdownParser, PdfTextParser, SourceRevisionId, StudyError,
    StudyErrorCode, TxtParser, block_fingerprint, source_fingerprint,
)


def revision():
    return SourceRevisionId(UUID(int=100))


def pdf_bytes(*texts: str, encrypted=False) -> bytes:
    writer = PdfWriter()
    font = writer._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    }))
    for text in texts:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
        })
        stream = DecodedStreamObject()
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream.set_data(f"BT /F1 12 Tf 50 750 Td ({escaped}) Tj ET".encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("secret")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_source_and_block_hash_are_deterministic():
    assert source_fingerprint(b"same") == source_fingerprint(b"same")
    assert source_fingerprint(b"same") != source_fingerprint(b"changed")
    assert block_fingerprint("a\r\nb") == block_fingerprint("a\nb")


def test_txt_parser_blocks_and_line_provenance():
    data = b"First line\ncontinued\n\nSecond paragraph\n"
    blocks = TxtParser().parse(data, revision())
    assert [b.text for b in blocks] == ["First line\ncontinued", "Second paragraph"]
    assert blocks[0].locator.span == "lines:1-2"
    assert blocks[1].locator.span == "lines:4-4"
    assert blocks == TxtParser().parse(data, revision())
    assert blocks[0].fingerprint == block_fingerprint(blocks[0].text)


@pytest.mark.parametrize("data,code", [
    (b"", StudyErrorCode.NO_USABLE_TEXT),
    (b"   \n", StudyErrorCode.NO_USABLE_TEXT),
    (b"hello\x00world", StudyErrorCode.PARSE_FAILURE),
    (b"\xff\xfe", StudyErrorCode.PARSE_FAILURE),
])
def test_txt_rejects_empty_or_binary(data, code):
    with pytest.raises(StudyError) as error:
        TxtParser().parse(data, revision())
    assert error.value.code is code


def test_markdown_heading_order_and_code_is_data():
    fence = chr(96) * 3
    data = f"# Title\n\nParagraph [link](https://example.test)\n\n{fence}python\nprint('never run')\n{fence}\n\n## Child\n\n![image](x.png)\n".encode()
    blocks = MarkdownParser().parse(data, revision())
    assert [b.order for b in blocks] == list(range(len(blocks)))
    assert blocks[1].heading_path == ("Title",)
    assert blocks[2].text.startswith(fence)
    assert "print('never run')" in blocks[2].text
    assert blocks[-1].heading_path == ("Title", "Child")
    assert blocks[-1].locator.section == "Title / Child"
    assert blocks == MarkdownParser().parse(data, revision())


def test_pdf_page_provenance_and_no_text():
    blocks = PdfTextParser().parse(pdf_bytes("Page one", "Page two"), revision())
    assert len(blocks) == 2
    assert [b.locator.page for b in blocks] == [1, 2]
    assert "Page one" in blocks[0].text
    with pytest.raises(StudyError) as error:
        PdfTextParser().parse(pdf_bytes(""), revision())
    assert error.value.code is StudyErrorCode.NO_USABLE_TEXT


def test_pdf_encrypted_rejected():
    with pytest.raises(StudyError) as error:
        PdfTextParser().parse(pdf_bytes("Secret", encrypted=True), revision())
    assert error.value.code is StudyErrorCode.ENCRYPTED_PDF
