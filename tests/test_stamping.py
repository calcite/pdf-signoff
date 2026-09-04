"""Integration tests for transactional L0 visual stamping."""

from hashlib import sha256
from pathlib import Path

import pymupdf
import pytest

import pdf_signoff.stamping as stamping_module
from pdf_signoff.inspection import inspect_pdf, inspect_signature_png
from pdf_signoff.profile import PageMatch, Placement
from pdf_signoff.stamping import (
    StampingError,
    stamp_l0,
    validate_signature_aspect_ratios,
)


def _write_pdf(path: Path) -> None:
    with pymupdf.open() as document:
        for rotation in (0, 90):
            page = document.new_page(width=400, height=600)
            page.draw_rect(page.rect, color=(0, 1, 0), fill=(0, 1, 0))
            page.set_rotation(rotation)
        document.save(path)


def _write_rgba_signature(path: Path) -> None:
    samples = bytearray()
    for y in range(20):
        for x in range(40):
            if x < 10:
                samples.extend((255, 0, 0, 0))
            elif y < 10:
                samples.extend((255, 0, 0, 255))
            else:
                samples.extend((0, 0, 255, 255))
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, 40, 20, samples, True)
    path.write_bytes(pixmap.tobytes("png"))


def _matching_placements() -> list[Placement]:
    return [
        Placement(page=1, x=0.25, y=0.2, width=0.5, height=1 / 6),
        Placement(page=1, x=0.25, y=0.6, width=0.5, height=1 / 6),
        Placement(page=2, x=0.25, y=0.25, width=0.5, height=0.375),
    ]


def _assert_signature_rendered(
    page: pymupdf.Page,
    placement: Placement,
) -> None:
    rendered = page.get_pixmap(alpha=False)
    x0 = placement.x * rendered.width
    y0 = placement.y * rendered.height
    width = placement.width * rendered.width
    height = placement.height * rendered.height

    transparent = rendered.pixel(int(x0 + width * 0.1), int(y0 + height * 0.5))
    red = rendered.pixel(int(x0 + width * 0.75), int(y0 + height * 0.25))
    blue = rendered.pixel(int(x0 + width * 0.75), int(y0 + height * 0.75))

    assert transparent == (0, 255, 0)
    assert red == (255, 0, 0)
    assert blue == (0, 0, 255)


def test_l0_stamping_renders_transparent_upright_png_on_multiple_pages(
    tmp_path: Path,
) -> None:
    input_pdf = tmp_path / "input.pdf"
    signature_png = tmp_path / "signature.png"
    output_pdf = tmp_path / "output.pdf"
    _write_pdf(input_pdf)
    _write_rgba_signature(signature_png)
    input_hash = sha256(input_pdf.read_bytes()).hexdigest()
    pdf = inspect_pdf(input_pdf)
    signature = inspect_signature_png(signature_png)
    placements = _matching_placements()

    stamp_l0(
        input_pdf,
        signature_png,
        output_pdf,
        placements,
        pages=pdf.pages,
        signature=signature,
    )

    assert output_pdf.is_file()
    assert sha256(input_pdf.read_bytes()).hexdigest() == input_hash
    with pymupdf.open(output_pdf) as document:
        assert document.page_count == 2
        assert document.get_sigflags() <= 0
        for placement in placements:
            _assert_signature_rendered(document[placement.page - 1], placement)
        assert len(document[0].get_image_rects(document[0].get_images()[0][0])) == 2
        assert len(document[1].get_image_rects(document[1].get_images()[0][0])) == 1

    output_bytes = output_pdf.read_bytes()
    assert b"ADBE_FillSign" not in output_bytes
    assert b"/Type/Sig" not in output_bytes


def test_aspect_validation_accepts_rounding_and_rejects_malformed_rectangles() -> None:
    pages = [PageMatch(page=1, width_pt=600, height_pt=800, rotation=0)]
    signature = stamping_module.SignatureInspection(
        width_px=200,
        height_px=100,
        has_alpha=True,
    )
    close = [Placement(page=1, x=0, y=0, width=0.2, height=0.076)]
    malformed = [Placement(page=1, x=0, y=0, width=0.2, height=0.2)]

    validate_signature_aspect_ratios(close, pages, signature)
    with pytest.raises(StampingError, match="Placement 1.*inconsistent"):
        validate_signature_aspect_ratios(malformed, pages, signature)


@pytest.mark.parametrize("tolerance", [-1, float("nan"), float("inf")])
def test_aspect_validation_rejects_invalid_tolerances(tolerance: float) -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        validate_signature_aspect_ratios(
            [],
            [],
            stamping_module.SignatureInspection(
                width_px=2,
                height_px=1,
                has_alpha=False,
            ),
            relative_tolerance=tolerance,
        )


def test_signature_read_failure_happens_without_creating_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_pdf = tmp_path / "input.pdf"
    signature_png = tmp_path / "signature.png"
    output_pdf = tmp_path / "output.pdf"
    _write_pdf(input_pdf)
    _write_rgba_signature(signature_png)
    pdf = inspect_pdf(input_pdf)
    signature = inspect_signature_png(signature_png)
    real_read_bytes = Path.read_bytes

    def fail_signature_read(self: Path) -> bytes:
        if self == signature_png:
            raise OSError("read failed")
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", fail_signature_read)
    with pytest.raises(StampingError, match="read failed"):
        stamp_l0(
            input_pdf,
            signature_png,
            output_pdf,
            _matching_placements(),
            pages=pdf.pages,
            signature=signature,
        )

    assert not output_pdf.exists()


def test_stamping_failure_removes_partial_output_and_preserves_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_pdf = tmp_path / "input.pdf"
    signature_png = tmp_path / "signature.png"
    output_pdf = tmp_path / "output.pdf"
    _write_pdf(input_pdf)
    _write_rgba_signature(signature_png)
    original = input_pdf.read_bytes()
    pdf = inspect_pdf(input_pdf)
    signature = inspect_signature_png(signature_png)

    def fail_insert(*args: object, **kwargs: object) -> int:
        del args, kwargs
        raise RuntimeError("insertion failed")

    monkeypatch.setattr(stamping_module.pymupdf.Page, "insert_image", fail_insert)
    with pytest.raises(StampingError, match="insertion failed"):
        stamp_l0(
            input_pdf,
            signature_png,
            output_pdf,
            _matching_placements(),
            pages=pdf.pages,
            signature=signature,
        )

    assert input_pdf.read_bytes() == original
    assert not output_pdf.exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "input.pdf",
        "signature.png",
    ]
