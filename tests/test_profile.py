"""Tests for canonical placement profiles."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from pdf_signoff.profile import (
    PageMatch,
    Placement,
    PlacementProfile,
    build_final_profile,
    load_profile,
    serialize_profile,
    validate_placements,
)


def valid_profile_data() -> dict:
    return {
        "version": 1,
        "created_from": {"sha256": "a" * 64},
        "match": {
            "page_count": 2,
            "pages": [
                {
                    "page": 1,
                    "width_pt": 595.276,
                    "height_pt": 841.89,
                    "rotation": 0,
                },
                {
                    "page": 2,
                    "width_pt": 841.89,
                    "height_pt": 595.276,
                    "rotation": 90,
                },
            ],
            "required_text": [
                {"page": 1, "text": "Employee signature:"},
                {"text": "Approval"},
            ],
        },
        "placements": [
            {"page": 1, "x": 0.724, "y": 0.108, "width": 0.137, "height": 0.043}
        ],
    }


def test_load_and_serialize_version_one_profile(tmp_path: Path) -> None:
    data = valid_profile_data()
    path = tmp_path / "placement.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    profile = load_profile(path)

    assert profile.version == 1
    assert profile.placements[0].page == 1
    assert profile.match.required_text is not None
    assert profile.match.required_text[1].page is None
    assert json.loads(serialize_profile(profile, indent=2)) == data


def test_optional_profile_metadata_may_be_absent() -> None:
    data = valid_profile_data()
    del data["created_from"]
    del data["match"]["required_text"]

    profile = PlacementProfile.model_validate(data)
    serialized = json.loads(serialize_profile(profile))

    assert profile.created_from is None
    assert profile.match.required_text is None
    assert "created_from" not in serialized
    assert "required_text" not in serialized["match"]


@pytest.mark.parametrize("version", [0, 2, "1"])
def test_unknown_or_non_numeric_version_is_rejected(version: object) -> None:
    data = valid_profile_data()
    data["version"] = version

    with pytest.raises(ValidationError):
        PlacementProfile.model_validate(data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("x", -0.01),
        ("x", 1.0),
        ("y", -0.01),
        ("y", 1.0),
        ("width", 0.0),
        ("width", 1.01),
        ("height", 0.0),
        ("height", 1.01),
        ("width", 0.3),
        ("height", 0.9),
    ],
)
def test_invalid_normalized_rectangles_are_rejected(field: str, value: float) -> None:
    data = valid_profile_data()
    placement = data["placements"][0]
    placement[field] = value
    if field == "height" and value == 0.9:
        placement["y"] = 0.2

    with pytest.raises(ValidationError):
        PlacementProfile.model_validate(data)


@pytest.mark.parametrize(
    "change",
    [
        ("placement", 0),
        ("placement", 3),
        ("metadata", 0),
        ("metadata", 3),
        ("required_text", 0),
        ("required_text", 3),
    ],
)
def test_invalid_page_numbers_are_rejected(change: tuple[str, int]) -> None:
    target, page = change
    data = valid_profile_data()
    if target == "placement":
        data["placements"][0]["page"] = page
    elif target == "metadata":
        data["match"]["pages"][0]["page"] = page
    else:
        data["match"]["required_text"][0]["page"] = page

    with pytest.raises(ValidationError):
        PlacementProfile.model_validate(data)


@pytest.mark.parametrize(
    ("field", "value"),
    [("width_pt", 0), ("height_pt", -1), ("rotation", 45)],
)
def test_invalid_page_metadata_is_rejected(field: str, value: float) -> None:
    data = valid_profile_data()
    data["match"]["pages"][0][field] = value

    with pytest.raises(ValidationError):
        PlacementProfile.model_validate(data)


def test_profile_rejects_truncated_page_metadata() -> None:
    data = valid_profile_data()
    data["match"]["pages"].pop()

    with pytest.raises(ValidationError, match=r"missing metadata for page\(s\): 2"):
        PlacementProfile.model_validate(data)


def test_profile_rejects_duplicate_page_metadata() -> None:
    data = valid_profile_data()
    data["match"]["pages"][1]["page"] = 1

    with pytest.raises(ValidationError, match="duplicate metadata for page 1"):
        PlacementProfile.model_validate(data)


def test_automatic_loading_rejects_zero_placements(tmp_path: Path) -> None:
    data = valid_profile_data()
    data["placements"] = []
    path = tmp_path / "placement.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    assert load_profile(path).placements == []
    with pytest.raises(ValidationError, match="at least one placement"):
        load_profile(path, auto=True)


def test_shared_validation_accepts_browser_payload_and_rejects_bad_input() -> None:
    raw = [{"page": 2, "x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4}]

    assert validate_placements(raw, page_count=2, require_non_empty=True) == [
        Placement(page=2, x=0.1, y=0.2, width=0.3, height=0.4)
    ]
    with pytest.raises(ValueError, match="beyond page_count"):
        validate_placements(raw, page_count=1)
    with pytest.raises(ValidationError):
        validate_placements([{**raw[0], "width": -1}], page_count=2)


def test_profile_rejects_fields_outside_the_versioned_schema() -> None:
    data = valid_profile_data()
    data["future_field"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PlacementProfile.model_validate(data)


def test_final_profile_refreshes_metadata_and_preserves_required_text() -> None:
    input_profile = PlacementProfile.model_validate(valid_profile_data())
    required_text = deepcopy(input_profile.match.required_text)
    pages = [
        PageMatch(page=1, width_pt=612, height_pt=792, rotation=180),
        PageMatch(page=2, width_pt=792, height_pt=612, rotation=270),
    ]
    placements = [Placement(page=2, x=0.5, y=0.5, width=0.2, height=0.1)]

    final = build_final_profile(
        source_sha256="b" * 64,
        pages=pages,
        placements=placements,
        input_profile=input_profile,
    )

    assert final.created_from is not None
    assert final.created_from.sha256 == "b" * 64
    assert final.match.page_count == 2
    assert final.match.pages == pages
    assert final.match.required_text == required_text
    assert final.placements == placements


def test_final_profile_omits_required_text_without_an_input_profile() -> None:
    final = build_final_profile(
        source_sha256="c" * 64,
        pages=[PageMatch(page=1, width_pt=612, height_pt=792, rotation=0)],
        placements=[Placement(page=1, x=0, y=0, width=1, height=1)],
    )

    assert "required_text" not in json.loads(serialize_profile(final))["match"]
