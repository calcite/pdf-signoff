"""Normalized placement and PDF geometry conversion boundary."""

import pymupdf

from pdf_signoff.profile import Placement


def displayed_cropbox_rect(page: pymupdf.Page) -> pymupdf.Rect:
    """Return the rotated CropBox used by viewers and placement profiles."""
    return pymupdf.Rect(page.rect)


def placement_to_pdf_rect(
    page: pymupdf.Page,
    placement: Placement,
) -> pymupdf.Rect:
    """Convert a displayed normalized placement for use by PyMuPDF page APIs."""
    displayed_page = displayed_cropbox_rect(page)
    displayed_rect = pymupdf.Rect(
        displayed_page.x0 + placement.x * displayed_page.width,
        displayed_page.y0 + placement.y * displayed_page.height,
        displayed_page.x0 + (placement.x + placement.width) * displayed_page.width,
        displayed_page.y0 + (placement.y + placement.height) * displayed_page.height,
    )
    return displayed_rect * page.derotation_matrix
