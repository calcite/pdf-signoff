"""Visual PDF signature stamping boundary."""

from collections.abc import Callable, Sequence
from math import isclose, isfinite
from pathlib import Path

import pymupdf

from pdf_signoff.geometry import placement_to_pdf_rect
from pdf_signoff.inspection import SignatureInspection
from pdf_signoff.output import write_output_atomically
from pdf_signoff.profile import PageMatch, Placement

ASPECT_RATIO_RELATIVE_TOLERANCE = 0.05


class StampingError(Exception):
    """The visual signature cannot be stamped safely."""


def validate_signature_aspect_ratios(
    placements: Sequence[Placement],
    pages: Sequence[PageMatch],
    signature: SignatureInspection,
    *,
    relative_tolerance: float = ASPECT_RATIO_RELATIVE_TOLERANCE,
) -> None:
    """Reject placement rectangles that would visibly distort the signature."""
    if not isfinite(relative_tolerance) or relative_tolerance < 0:
        raise ValueError("aspect-ratio tolerance must be finite and non-negative")

    image_ratio = signature.width_px / signature.height_px
    for placement_number, placement in enumerate(placements, start=1):
        page = pages[placement.page - 1]
        rectangle_ratio = (
            placement.width * page.width_pt / (placement.height * page.height_pt)
        )
        if not isclose(
            rectangle_ratio,
            image_ratio,
            rel_tol=relative_tolerance,
            abs_tol=0,
        ):
            raise StampingError(
                f"Placement {placement_number} on page {placement.page} has "
                f"physical aspect ratio {rectangle_ratio:.3g}, inconsistent with "
                f"signature PNG aspect ratio {image_ratio:.3g}."
            )


def stamp_l0(
    input_pdf: Path,
    signature_png: Path,
    output_pdf: Path,
    placements: Sequence[Placement],
    *,
    pages: Sequence[PageMatch],
    signature: SignatureInspection,
    overwrite: bool = False,
    finalize: Callable[[Path], None] | None = None,
) -> None:
    """Embed each PNG, optionally finalize it, and atomically publish the PDF."""
    validate_signature_aspect_ratios(placements, pages, signature)
    try:
        signature_bytes = signature_png.read_bytes()
    except OSError as exc:
        raise StampingError(
            f"Signature image could not be read: {signature_png}: {exc}"
        ) from exc

    def write_stamped_pdf(temporary_path: Path) -> None:
        try:
            with pymupdf.open(input_pdf) as document:
                image_xref = 0
                for placement in placements:
                    page = document.load_page(placement.page - 1)
                    rectangle = placement_to_pdf_rect(page, placement)
                    if image_xref:
                        page.insert_image(
                            rectangle,
                            xref=image_xref,
                            rotate=page.rotation,
                            keep_proportion=True,
                            overlay=True,
                        )
                    else:
                        image_xref = page.insert_image(
                            rectangle,
                            stream=signature_bytes,
                            rotate=page.rotation,
                            keep_proportion=True,
                            overlay=True,
                        )
                document.save(temporary_path, garbage=3, deflate=True)
        except Exception as exc:
            raise StampingError(f"PDF stamping failed: {exc}") from exc
        if finalize is not None:
            finalize(temporary_path)

    write_output_atomically(output_pdf, write_stamped_pdf, overwrite=overwrite)
