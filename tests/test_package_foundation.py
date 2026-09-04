"""Tests for the package and dependency foundation."""

from importlib import import_module
from importlib.metadata import version
from pathlib import Path

import pytest

from pdf_signoff.server import PACKAGED_FRONTEND


@pytest.mark.parametrize(
    "module_name",
    [
        "config",
        "profile",
        "geometry",
        "inspection",
        "stamping",
        "crypto",
        "output",
        "server",
    ],
)
def test_domain_module_is_importable(module_name: str) -> None:
    assert import_module(f"pdf_signoff.{module_name}") is not None


@pytest.mark.parametrize(
    "distribution_name",
    [
        "fastapi",
        "uvicorn",
        "pymupdf",
        "pyhanko",
        "pydantic",
        "pytest",
        "pytest-cov",
    ],
)
def test_required_distribution_is_installed(distribution_name: str) -> None:
    assert version(distribution_name)


def test_pydantic_v2_is_installed() -> None:
    major_version = int(version("pydantic").partition(".")[0])

    assert major_version == 2


def test_built_frontend_is_available_inside_the_python_package() -> None:
    assert PACKAGED_FRONTEND == Path(PACKAGED_FRONTEND)
    assert (PACKAGED_FRONTEND / "index.html").is_file()
    assets = PACKAGED_FRONTEND / "assets"
    assert assets.is_dir()
    assert any(path.suffix == ".js" for path in assets.iterdir())
    assert any(path.suffix == ".css" for path in assets.iterdir())
