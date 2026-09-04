"""Conservative PDF and signature image inspection and profile matching."""

from dataclasses import dataclass
from hashlib import file_digest
from math import isclose, isfinite
from pathlib import Path
from typing import Literal, cast

import pymupdf
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.fields import enumerate_sig_fields

from pdf_signoff.geometry import displayed_cropbox_rect
from pdf_signoff.profile import PageMatch, PlacementProfile

PAGE_SIZE_TOLERANCE_PT = 1.0
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_VALID_ROTATIONS = {0, 90, 180, 270}


class InputInspectionError(ValueError):
    """An input cannot be used safely by the signing workflow."""


class ProfileMismatchError(ValueError):
    """A placement profile does not describe the inspected PDF."""


@dataclass(frozen=True)
class PdfInspection:
    """Stable facts extracted from a readable, supported PDF."""

    sha256: str
    pages: tuple[PageMatch, ...]
    page_text: tuple[str, ...]
    has_cryptographic_signatures: bool

    @property
    def page_count(self) -> int:
        """Return the inspected number of pages."""
        return len(self.pages)


@dataclass(frozen=True)
class SignatureInspection:
    """Dimensions and alpha-channel availability of a decoded PNG."""

    width_px: int
    height_px: int
    has_alpha: bool


def inspect_pdf(path: Path) -> PdfInspection:
    """Inspect a PDF, rejecting files that MuPDF cannot safely consume."""
    try:
        document = pymupdf.open(path)
    except Exception as exc:
        raise InputInspectionError(f"PDF could not be read: {path}: {exc}") from exc

    try:
        with document:
            if not document.is_pdf:
                raise InputInspectionError(f"Input is not a PDF: {path}")
            if document.needs_pass:
                raise InputInspectionError(f"Encrypted PDFs are not supported: {path}")
            if document.is_repaired:
                raise InputInspectionError(
                    f"Malformed PDF required repair and is not supported: {path}"
                )
            if document.page_count == 0:
                raise InputInspectionError(f"PDF contains no pages: {path}")

            pages: list[PageMatch] = []
            page_text: list[str] = []
            for page_index in range(document.page_count):
                page_number = page_index + 1
                page = document.load_page(page_index)
                displayed = displayed_cropbox_rect(page)
                rotation_value = int(page.rotation) % 360
                if (
                    not isfinite(displayed.width)
                    or not isfinite(displayed.height)
                    or displayed.width <= 0
                    or displayed.height <= 0
                    or rotation_value not in _VALID_ROTATIONS
                ):
                    raise InputInspectionError(
                        f"PDF page {page_number} has unsupported displayed geometry"
                    )
                rotation = cast(
                    Literal[0, 90, 180, 270],
                    rotation_value,
                )
                pages.append(
                    PageMatch(
                        page=page_number,
                        width_pt=displayed.width,
                        height_pt=displayed.height,
                        rotation=rotation,
                    )
                )
                page_text.append(page.get_text("text"))
    except InputInspectionError:
        raise
    except Exception as exc:
        raise InputInspectionError(
            f"PDF could not be inspected: {path}: {exc}"
        ) from exc

    try:
        with path.open("rb") as source:
            sha256 = file_digest(source, "sha256").hexdigest()
    except OSError as exc:
        raise InputInspectionError(f"PDF could not be read: {path}: {exc}") from exc

    has_cryptographic_signatures = _has_cryptographic_signatures(path)

    return PdfInspection(
        sha256=sha256,
        pages=tuple(pages),
        page_text=tuple(page_text),
        has_cryptographic_signatures=has_cryptographic_signatures,
    )


def _has_cryptographic_signatures(path: Path) -> bool:
    """Detect filled PDF signature fields without validating their signatures."""
    try:
        with path.open("rb") as source:
            reader = PdfFileReader(source, strict=True)
            signatures = enumerate_sig_fields(reader, filled_status=True)
            return next(signatures, None) is not None
    except OSError as exc:
        raise InputInspectionError(f"PDF could not be read: {path}: {exc}") from exc
    except Exception as exc:
        raise InputInspectionError(
            f"PDF signature structures could not be safely inspected: {path}: {exc}"
        ) from exc


def inspect_signature_png(path: Path) -> SignatureInspection:
    """Read and fully decode a PNG signature asset."""
    try:
        image_bytes = path.read_bytes()
    except OSError as exc:
        raise InputInspectionError(
            f"Signature image could not be read: {path}: {exc}"
        ) from exc

    if not image_bytes.startswith(_PNG_SIGNATURE):
        raise InputInspectionError(f"Signature image is not a PNG: {path}")

    try:
        pixmap = pymupdf.Pixmap(image_bytes)
    except Exception as exc:
        raise InputInspectionError(
            f"Signature PNG could not be decoded: {path}: {exc}"
        ) from exc

    if pixmap.width <= 0 or pixmap.height <= 0:
        raise InputInspectionError(f"Signature PNG has invalid dimensions: {path}")
    return SignatureInspection(
        width_px=pixmap.width,
        height_px=pixmap.height,
        has_alpha=bool(pixmap.alpha),
    )


def validate_profile_match(
    profile: PlacementProfile,
    pdf: PdfInspection,
    *,
    size_tolerance_pt: float = PAGE_SIZE_TOLERANCE_PT,
) -> None:
    """Raise when a profile's reusable coordinates do not match a PDF."""
    if not isfinite(size_tolerance_pt) or size_tolerance_pt < 0:
        raise ValueError("page-size tolerance must be a finite non-negative number")
    if profile.match.page_count != pdf.page_count:
        raise ProfileMismatchError(
            "Profile page count does not match PDF: "
            f"expected {profile.match.page_count}, found {pdf.page_count}"
        )

    for expected in profile.match.pages:
        actual = pdf.pages[expected.page - 1]
        if not (
            isclose(
                expected.width_pt,
                actual.width_pt,
                rel_tol=0,
                abs_tol=size_tolerance_pt,
            )
            and isclose(
                expected.height_pt,
                actual.height_pt,
                rel_tol=0,
                abs_tol=size_tolerance_pt,
            )
        ):
            raise ProfileMismatchError(
                f"Profile page {expected.page} displayed size does not match PDF: "
                f"expected {expected.width_pt:g} x {expected.height_pt:g} pt, "
                f"found {actual.width_pt:g} x {actual.height_pt:g} pt"
            )
        if expected.rotation != actual.rotation:
            raise ProfileMismatchError(
                f"Profile page {expected.page} rotation does not match PDF: "
                f"expected {expected.rotation}, found {actual.rotation}"
            )

    document_text = _normalize_whitespace("\n".join(pdf.page_text))
    for condition in profile.match.required_text or []:
        required = _normalize_whitespace(condition.text)
        available = (
            document_text
            if condition.page is None
            else _normalize_whitespace(pdf.page_text[condition.page - 1])
        )
        if required not in available:
            scope = "document" if condition.page is None else f"page {condition.page}"
            raise ProfileMismatchError(
                f"Profile required text was not found in PDF {scope}: "
                f"{condition.text!r}"
            )


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())
