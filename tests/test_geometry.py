"""Tests for normalized displayed-CropBox to PyMuPDF geometry conversion."""

from pathlib import Path
from typing import Literal

import pymupdf
import pytest

from pdf_signoff.geometry import displayed_cropbox_rect, placement_to_pdf_rect
from pdf_signoff.inspection import inspect_pdf
from pdf_signoff.profile import PageMatch, Placement

Rotation = Literal[0, 90, 180, 270]


def _rect_values(rect: pymupdf.Rect) -> tuple[float, float, float, float]:
    return (rect.x0, rect.y0, rect.x1, rect.y1)


def _write_synthetic_pdf(
    path: Path,
    *,
    media_box: pymupdf.Rect,
    crop_box: pymupdf.Rect | None = None,
    rotation: Rotation = 0,
) -> None:
    with pymupdf.open() as document:
        page = document.new_page(width=media_box.width, height=media_box.height)
        page.set_mediabox(media_box)
        if crop_box is not None:
            page.set_cropbox(crop_box)
        page.set_rotation(rotation)
        document.save(path)


@pytest.mark.parametrize(
    ("rotation", "expected_rect", "expected_displayed"),
    [
        (0, (50, 120, 200, 360), (50, 120, 200, 360)),
        (90, (100, 360, 300, 540), (60, 100, 240, 300)),
        (180, (300, 240, 450, 480), (50, 120, 200, 360)),
        (270, (200, 60, 400, 240), (60, 100, 240, 300)),
    ],
)
def test_conversion_handles_every_rotation_on_an_offset_cropbox(
    tmp_path: Path,
    rotation: Rotation,
    expected_rect: tuple[float, float, float, float],
    expected_displayed: tuple[float, float, float, float],
) -> None:
    path = tmp_path / f"rotation-{rotation}.pdf"
    _write_synthetic_pdf(
        path,
        media_box=pymupdf.Rect(10, 20, 610, 820),
        crop_box=pymupdf.Rect(60, 120, 560, 720),
        rotation=rotation,
    )
    placement = Placement(page=1, x=0.1, y=0.2, width=0.3, height=0.4)

    with pymupdf.open(path) as document:
        page = document[0]
        result = placement_to_pdf_rect(page, placement)

        assert _rect_values(result) == pytest.approx(expected_rect)
        assert _rect_values(result * page.rotation_matrix) == pytest.approx(
            expected_displayed
        )


@pytest.mark.parametrize(
    ("case", "media_box", "crop_box", "expected_rect"),
    [
        (
            "a4-portrait",
            pymupdf.Rect(0, 0, 595, 842),
            None,
            (148.75, 168.4, 446.25, 421),
        ),
        (
            "letter-landscape",
            pymupdf.Rect(0, 0, 792, 612),
            None,
            (198, 122.4, 594, 306),
        ),
        (
            "non-a4-wide",
            pymupdf.Rect(0, 0, 1000, 400),
            None,
            (250, 80, 750, 200),
        ),
        (
            "cropbox-smaller-than-mediabox",
            pymupdf.Rect(0, 0, 600, 800),
            pymupdf.Rect(50, 100, 550, 700),
            (125, 120, 375, 300),
        ),
        (
            "non-zero-mediabox-and-cropbox-origins",
            pymupdf.Rect(10, 20, 610, 820),
            pymupdf.Rect(60, 120, 560, 720),
            (125, 120, 375, 300),
        ),
    ],
)
def test_conversion_uses_the_visible_physical_page_dimensions(
    tmp_path: Path,
    case: str,
    media_box: pymupdf.Rect,
    crop_box: pymupdf.Rect | None,
    expected_rect: tuple[float, float, float, float],
) -> None:
    path = tmp_path / f"{case}.pdf"
    _write_synthetic_pdf(path, media_box=media_box, crop_box=crop_box)
    placement = Placement(page=1, x=0.25, y=0.2, width=0.5, height=0.3)

    with pymupdf.open(path) as document:
        result = placement_to_pdf_rect(document[0], placement)

    assert _rect_values(result) == pytest.approx(expected_rect)


@pytest.mark.parametrize(
    ("rotation", "expected_width", "expected_height"),
    [
        (0, 500, 600),
        (90, 600, 500),
        (180, 500, 600),
        (270, 600, 500),
    ],
)
def test_inspection_and_conversion_share_displayed_cropbox_dimensions(
    tmp_path: Path,
    rotation: Rotation,
    expected_width: float,
    expected_height: float,
) -> None:
    path = tmp_path / f"displayed-{rotation}.pdf"
    _write_synthetic_pdf(
        path,
        media_box=pymupdf.Rect(10, 20, 610, 820),
        crop_box=pymupdf.Rect(60, 120, 560, 720),
        rotation=rotation,
    )

    inspected = inspect_pdf(path)
    with pymupdf.open(path) as document:
        displayed = displayed_cropbox_rect(document[0])

    assert displayed == pymupdf.Rect(0, 0, expected_width, expected_height)
    assert inspected.pages == (
        PageMatch(
            page=1,
            width_pt=expected_width,
            height_pt=expected_height,
            rotation=rotation,
        ),
    )
