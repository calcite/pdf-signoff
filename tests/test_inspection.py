"""Tests for conservative PDF/PNG inspection and profile matching."""

from hashlib import sha256
from pathlib import Path

import pymupdf
import pytest

import pdf_signoff.inspection as inspection_module
from pdf_signoff.inspection import (
    InputInspectionError,
    PdfInspection,
    ProfileMismatchError,
    SignatureInspection,
    inspect_pdf,
    inspect_signature_png,
    validate_profile_match,
)
from pdf_signoff.profile import (
    CreatedFrom,
    MatchSpec,
    PageMatch,
    PlacementProfile,
    RequiredText,
)


def _write_pdf(
    path: Path,
    *,
    rotations: tuple[int, ...] = (0,),
    text: str | None = None,
) -> None:
    with pymupdf.open() as document:
        for rotation in rotations:
            page = document.new_page(width=600, height=800)
            page.set_cropbox(pymupdf.Rect(50, 100, 550, 800))
            page.set_rotation(rotation)
            if text is not None:
                page.insert_textbox(
                    pymupdf.Rect(80, 140, 500, 300),
                    text,
                    fontsize=12,
                )
        document.save(path)


def _write_png(path: Path, *, alpha: bool = True) -> bytes:
    pixmap = pymupdf.Pixmap(
        pymupdf.csRGB,
        pymupdf.IRect(0, 0, 4, 3),
        alpha,
    )
    pixmap.clear_with(0)
    image_bytes = pixmap.tobytes("png")
    path.write_bytes(image_bytes)
    return image_bytes


def _write_zero_page_pdf(path: Path) -> None:
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    objects = (
        b"1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n",
        b"2 0 obj\n<</Type/Pages/Kids[]/Count 0>>\nendobj\n",
    )
    body = bytearray(header)
    offsets = [0]
    for pdf_object in objects:
        offsets.append(len(body))
        body.extend(pdf_object)
    xref_offset = len(body)
    body.extend(b"xref\n0 3\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend(f"{offset:010d} 00000 n \n".encode())
    body.extend(
        b"trailer\n<</Size 3/Root 1 0 R>>\nstartxref\n"
        + str(xref_offset).encode()
        + b"\n%%EOF\n"
    )
    path.write_bytes(body)


def _pdf_inspection() -> PdfInspection:
    return PdfInspection(
        sha256="a" * 64,
        pages=(
            PageMatch(page=1, width_pt=612, height_pt=792, rotation=0),
            PageMatch(page=2, width_pt=792, height_pt=612, rotation=90),
        ),
        page_text=(
            "Employee\n  signature: approved",
            "Quarterly\tApproval",
        ),
        has_cryptographic_signatures=False,
    )


def _profile(
    *,
    page_count: int = 2,
    pages: list[PageMatch] | None = None,
    required_text: list[RequiredText] | None = None,
) -> PlacementProfile:
    return PlacementProfile(
        version=1,
        created_from=CreatedFrom(sha256="different-informational-hash"),
        match=MatchSpec(
            page_count=page_count,
            pages=pages
            if pages is not None
            else [
                PageMatch(page=1, width_pt=612, height_pt=792, rotation=0),
                PageMatch(page=2, width_pt=792, height_pt=612, rotation=90),
            ],
            required_text=required_text,
        ),
        placements=[],
    )


def test_inspect_pdf_reports_displayed_cropboxes_rotations_text_and_hash(
    tmp_path: Path,
) -> None:
    path = tmp_path / "input.pdf"
    _write_pdf(
        path,
        rotations=(0, 90, 180, 270),
        text="Employee signature:",
    )

    result = inspect_pdf(path)

    assert result.page_count == 4
    assert result.sha256 == sha256(path.read_bytes()).hexdigest()
    assert result.has_cryptographic_signatures is False
    assert result.pages == (
        PageMatch(page=1, width_pt=500, height_pt=700, rotation=0),
        PageMatch(page=2, width_pt=700, height_pt=500, rotation=90),
        PageMatch(page=3, width_pt=500, height_pt=700, rotation=180),
        PageMatch(page=4, width_pt=700, height_pt=500, rotation=270),
    )
    assert all("Employee signature:" in text for text in result.page_text)


def test_inspect_pdf_rejects_encrypted_input(tmp_path: Path) -> None:
    path = tmp_path / "encrypted.pdf"
    with pymupdf.open() as document:
        document.new_page()
        document.save(
            path,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="owner",
            user_pw="user",
        )

    with pytest.raises(InputInspectionError, match="Encrypted PDFs"):
        inspect_pdf(path)


def test_inspect_pdf_rejects_zero_page_input(tmp_path: Path) -> None:
    path = tmp_path / "empty.pdf"
    _write_zero_page_pdf(path)

    with pytest.raises(InputInspectionError, match="contains no pages"):
        inspect_pdf(path)


def test_inspect_pdf_rejects_a_non_pdf_document(tmp_path: Path) -> None:
    path = tmp_path / "image.png"
    _write_png(path)

    with pytest.raises(InputInspectionError, match="not a PDF"):
        inspect_pdf(path)


def test_inspect_pdf_rejects_unreadable_malformed_data(tmp_path: Path) -> None:
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF-1.7\ndefinitely not a document")

    with pytest.raises(InputInspectionError, match="could not be read"):
        inspect_pdf(path)


def test_inspect_pdf_rejects_repaired_malformed_data(tmp_path: Path) -> None:
    path = tmp_path / "repaired.pdf"
    _write_pdf(path)
    contents = path.read_bytes()
    path.write_bytes(contents[: contents.rfind(b"startxref")] + b"%%EOF\n")

    with pytest.raises(InputInspectionError, match="required repair"):
        inspect_pdf(path)


def test_inspect_signature_png_returns_decoded_properties(tmp_path: Path) -> None:
    path = tmp_path / "signature.bin"
    _write_png(path)

    assert inspect_signature_png(path) == SignatureInspection(
        width_px=4,
        height_px=3,
        has_alpha=True,
    )


def test_inspect_signature_png_rejects_non_png_and_bad_png(tmp_path: Path) -> None:
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 2, 2), False)
    jpeg_path = tmp_path / "not-png.png"
    jpeg_path.write_bytes(pixmap.tobytes("jpeg"))
    broken_path = tmp_path / "broken.png"
    broken_path.write_bytes(b"\x89PNG\r\n\x1a\nnot decodable")

    with pytest.raises(InputInspectionError, match="is not a PNG"):
        inspect_signature_png(jpeg_path)
    with pytest.raises(InputInspectionError, match="could not be decoded"):
        inspect_signature_png(broken_path)


def test_profile_match_accepts_tolerance_whitespace_and_informational_hash() -> None:
    profile = _profile(
        pages=[
            PageMatch(page=1, width_pt=613, height_pt=791, rotation=0),
            PageMatch(page=2, width_pt=792, height_pt=612, rotation=90),
        ],
        required_text=[
            RequiredText(page=1, text="Employee signature: approved"),
            RequiredText(text="approved Quarterly Approval"),
        ],
    )

    assert validate_profile_match(profile, _pdf_inspection()) is None


def test_profile_match_rejects_page_count() -> None:
    profile = _profile(
        page_count=1,
        pages=[PageMatch(page=1, width_pt=612, height_pt=792, rotation=0)],
    )

    with pytest.raises(ProfileMismatchError, match="page count"):
        validate_profile_match(profile, _pdf_inspection())


@pytest.mark.parametrize(
    ("page", "message"),
    [
        (PageMatch(page=1, width_pt=613.01, height_pt=792, rotation=0), "size"),
        (PageMatch(page=1, width_pt=float("inf"), height_pt=792, rotation=0), "size"),
        (PageMatch(page=1, width_pt=612, height_pt=792, rotation=180), "rotation"),
    ],
)
def test_profile_match_rejects_page_size_or_rotation(
    page: PageMatch,
    message: str,
) -> None:
    profile = _profile(
        pages=[
            page,
            PageMatch(page=2, width_pt=792, height_pt=612, rotation=90),
        ]
    )

    with pytest.raises(ProfileMismatchError, match=message):
        validate_profile_match(profile, _pdf_inspection())


@pytest.mark.parametrize(
    "required_text",
    [
        [RequiredText(page=1, text="missing")],
        [RequiredText(text="missing")],
        [RequiredText(page=2, text="Employee signature")],
        [
            RequiredText(page=1, text="Employee signature"),
            RequiredText(text="missing"),
        ],
    ],
)
def test_profile_match_rejects_missing_text_at_its_requested_scope(
    required_text: list[RequiredText],
) -> None:
    profile = _profile(required_text=required_text)

    with pytest.raises(ProfileMismatchError, match="required text"):
        validate_profile_match(profile, _pdf_inspection())


@pytest.mark.parametrize("tolerance", [-1, float("nan"), float("inf")])
def test_profile_match_rejects_invalid_tolerance(tolerance: float) -> None:
    with pytest.raises(ValueError, match="finite non-negative"):
        validate_profile_match(
            _profile(), _pdf_inspection(), size_tolerance_pt=tolerance
        )


def test_file_read_failures_are_reported_as_inspection_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "input.pdf"
    _write_pdf(path)
    real_open = Path.open

    def fail_to_hash(self: Path, *args: object, **kwargs: object) -> object:
        if self == path:
            raise OSError("read failed")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_to_hash)
    with pytest.raises(InputInspectionError, match="read failed"):
        inspect_pdf(path)
    with pytest.raises(InputInspectionError, match="read failed"):
        inspect_signature_png(path)


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        (OSError("read failed"), "PDF could not be read"),
        (RuntimeError("invalid form tree"), "could not be safely inspected"),
    ],
)
def test_pdf_signature_structure_inspection_failures_are_conservative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    message: str,
) -> None:
    path = tmp_path / "input.pdf"
    _write_pdf(path)

    def fail_reader(*_args: object, **_kwargs: object) -> None:
        raise failure

    monkeypatch.setattr(inspection_module, "PdfFileReader", fail_reader)
    with pytest.raises(InputInspectionError, match=message):
        inspect_pdf(path)


def test_pdf_page_inspection_failures_are_reported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "input.pdf"
    _write_pdf(path)
    real_get_text = pymupdf.Page.get_text

    def fail_to_extract(page: pymupdf.Page, *args: object, **kwargs: object) -> str:
        del page, args, kwargs
        raise RuntimeError("text failed")

    monkeypatch.setattr(pymupdf.Page, "get_text", fail_to_extract)
    with pytest.raises(InputInspectionError, match="could not be inspected"):
        inspect_pdf(path)
    monkeypatch.setattr(pymupdf.Page, "get_text", real_get_text)


def test_invalid_pdf_page_geometry_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "input.pdf"
    path.write_bytes(b"placeholder")

    class InvalidPage:
        rect = pymupdf.Rect(0, 0, 0, 100)
        rotation = 0

    class InvalidDocument:
        is_pdf = True
        needs_pass = False
        is_repaired = False
        page_count = 1

        def __enter__(self) -> "InvalidDocument":
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def load_page(self, page_index: int) -> InvalidPage:
            assert page_index == 0
            return InvalidPage()

    monkeypatch.setattr(
        inspection_module.pymupdf,
        "open",
        lambda _: InvalidDocument(),
    )
    with pytest.raises(InputInspectionError, match="unsupported displayed geometry"):
        inspect_pdf(path)


def test_invalid_decoded_png_dimensions_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "signature.png"
    _write_png(path)

    class EmptyPixmap:
        width = 0
        height = 3
        alpha = 1

    monkeypatch.setattr(inspection_module.pymupdf, "Pixmap", lambda _: EmptyPixmap())
    with pytest.raises(InputInspectionError, match="invalid dimensions"):
        inspect_signature_png(path)
