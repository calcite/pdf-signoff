"""Canonical placement profile models, loading, and serialization."""

from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationInfo,
    model_validator,
)

PageNumber = Annotated[int, Field(ge=1)]
NormalizedOrigin = Annotated[float, Field(ge=0, lt=1)]
NormalizedSize = Annotated[float, Field(gt=0, le=1)]
PositiveDimension = Annotated[float, Field(gt=0)]


class ProfileModel(BaseModel):
    """Base model that rejects fields outside the versioned schema."""

    model_config = ConfigDict(extra="forbid")


class Placement(ProfileModel):
    """A normalized rectangle on a 1-based displayed PDF page."""

    page: PageNumber
    x: NormalizedOrigin
    y: NormalizedOrigin
    width: NormalizedSize
    height: NormalizedSize

    @model_validator(mode="after")
    def validate_containment(self) -> Self:
        if self.x + self.width > 1:
            raise ValueError("placement extends beyond the page width")
        if self.y + self.height > 1:
            raise ValueError("placement extends beyond the page height")
        return self


class PageMatch(ProfileModel):
    """Displayed dimensions and rotation used to match one PDF page."""

    page: PageNumber
    width_pt: PositiveDimension
    height_pt: PositiveDimension
    rotation: Literal[0, 90, 180, 270]


class RequiredText(ProfileModel):
    """Optional text condition for a page or the whole document."""

    page: PageNumber | None = None
    text: str


class MatchSpec(ProfileModel):
    """Document metadata and optional text conditions for profile reuse."""

    page_count: PageNumber
    pages: list[PageMatch]
    required_text: list[RequiredText] | None = None

    @model_validator(mode="after")
    def validate_page_references(self) -> Self:
        page_numbers: set[int] = set()
        for page in self.pages:
            if page.page > self.page_count:
                raise ValueError("page metadata references a page beyond page_count")
            if page.page in page_numbers:
                raise ValueError(
                    f"match.pages contains duplicate metadata for page {page.page}"
                )
            page_numbers.add(page.page)
        missing_pages = [
            str(page)
            for page in range(1, self.page_count + 1)
            if page not in page_numbers
        ]
        if missing_pages:
            raise ValueError(
                "match.pages is missing metadata for page(s): "
                + ", ".join(missing_pages)
            )
        for condition in self.required_text or []:
            if condition.page is not None and condition.page > self.page_count:
                raise ValueError("required text references a page beyond page_count")
        return self


class CreatedFrom(ProfileModel):
    """Informational source metadata for a placement profile."""

    sha256: str | None = None


class PlacementProfile(ProfileModel):
    """Versioned reusable placement profile."""

    version: Literal[1]
    created_from: CreatedFrom | None = None
    match: MatchSpec
    placements: list[Placement]

    @model_validator(mode="after")
    def validate_placement_pages(self, info: ValidationInfo) -> Self:
        require_placements = bool(
            info.context and info.context.get("require_placements")
        )
        validate_placements(
            self.placements,
            page_count=self.match.page_count,
            require_non_empty=require_placements,
        )
        return self


_PLACEMENTS = TypeAdapter(list[Placement])


def validate_placements(
    placements: object,
    *,
    page_count: int,
    require_non_empty: bool = False,
) -> list[Placement]:
    """Validate raw CLI or browser placements against a document page count."""
    validated = _PLACEMENTS.validate_python(placements)
    if require_non_empty and not validated:
        raise ValueError("at least one placement is required")
    for placement in validated:
        if placement.page > page_count:
            raise ValueError("placement references a page beyond page_count")
    return validated


def load_profile(path: Path, *, auto: bool = False) -> PlacementProfile:
    """Load a UTF-8 JSON profile, requiring a placement in automatic mode."""
    return PlacementProfile.model_validate_json(
        path.read_text(encoding="utf-8"),
        context={"require_placements": auto},
    )


def serialize_profile(profile: PlacementProfile, *, indent: int | None = None) -> str:
    """Serialize a profile while omitting absent optional metadata."""
    return profile.model_dump_json(exclude_none=True, indent=indent)


def build_final_profile(
    *,
    source_sha256: str,
    pages: Sequence[PageMatch],
    placements: Sequence[Placement],
    input_profile: PlacementProfile | None = None,
) -> PlacementProfile:
    """Build a final profile from current metadata and final placements."""
    current_pages = list(pages)
    return PlacementProfile(
        version=1,
        created_from=CreatedFrom(sha256=source_sha256),
        match=MatchSpec(
            page_count=len(current_pages),
            pages=current_pages,
            required_text=(
                input_profile.match.required_text if input_profile is not None else None
            ),
        ),
        placements=list(placements),
    )
