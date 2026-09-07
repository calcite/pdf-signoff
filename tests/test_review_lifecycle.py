"""CLI orchestration tests for the interactive one-shot review lifecycle."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Thread
from typing import Any
from urllib.parse import urlsplit

import httpx2 as httpx
import pymupdf
import pytest
from click.testing import CliRunner

from pdf_signoff import cli
from pdf_signoff.profile import PlacementProfile


@pytest.fixture
def review_files(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    input_pdf = tmp_path / "review.pdf"
    signature = tmp_path / "signature.png"
    profile = tmp_path / "profile.json"
    output = tmp_path / "approved.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=600, height=800)
        page.insert_text((50, 50), "Approval form")
        document.save(input_pdf)
    pixels = bytes((10, 40, 160, 255)) * (80 * 20)
    signature.write_bytes(
        pymupdf.Pixmap(pymupdf.csRGB, 80, 20, pixels, True).tobytes("png")
    )
    profile.write_text(
        json.dumps(
            {
                "version": 1,
                "created_from": {"sha256": "informational"},
                "match": {
                    "page_count": 1,
                    "pages": [
                        {
                            "page": 1,
                            "width_pt": 600,
                            "height_pt": 800,
                            "rotation": 0,
                        }
                    ],
                    "required_text": [{"page": 1, "text": "Approval form"}],
                },
                "placements": [
                    {
                        "page": 1,
                        "x": 0.15,
                        "y": 0.2,
                        "width": 0.25,
                        "height": 0.046875,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return input_pdf, signature, profile, output


def test_review_cli_validates_preload_opens_browser_and_emits_edited_result(
    review_files: tuple[Path, Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_pdf, signature, profile, output = review_files
    edited = {
        "page": 1,
        "x": 0.42,
        "y": 0.5,
        "width": 0.2,
        "height": 0.0375,
    }
    browser_urls: list[str] = []
    responses: list[tuple[int, dict[str, Any], bool]] = []
    worker_errors: list[BaseException] = []
    worker: Thread | None = None

    def browser_open(url: str) -> bool:
        nonlocal worker
        browser_urls.append(url)

        def save_from_browser() -> None:
            try:
                with httpx.Client(follow_redirects=True, trust_env=False) as client:
                    bootstrap = client.get(url)
                    metadata = client.get(
                        f"{urlsplit(url).scheme}://{urlsplit(url).netloc}/api/session"
                    )
                    assert bootstrap.status_code == 200
                    assert metadata.json()["initialPlacements"][0]["x"] == 0.15
                    response = client.post(
                        f"{urlsplit(url).scheme}://{urlsplit(url).netloc}/api/save",
                        json={"placements": [edited]},
                    )
                    responses.append(
                        (response.status_code, response.json(), output.is_file())
                    )
            except BaseException as exc:  # pragma: no cover - asserted in main thread
                worker_errors.append(exc)

        worker = Thread(target=save_from_browser)
        worker.start()
        return True

    monkeypatch.setattr(cli.webbrowser, "open", browser_open)
    result = CliRunner().invoke(
        cli.main,
        [
            str(input_pdf),
            "--signature",
            str(signature),
            "--coords",
            str(profile),
            "--output",
            str(output),
            "--general--log-level",
            "DEBUG",
        ],
    )
    if worker is not None:
        worker.join(timeout=5)

    assert worker_errors == []
    assert result.exit_code == 0
    assert len(browser_urls) == 1
    assert "token=" in browser_urls[0]
    assert responses == [(200, {"ok": True}, True)]
    assert result.stdout.endswith("\n")
    assert result.stdout.count("\n") == 1
    emitted = PlacementProfile.model_validate_json(result.stdout)
    assert emitted.placements[0].model_dump() == edited
    assert output.is_file()
    assert "Review session opened in the browser; waiting for Save." in result.stderr
    assert result.stderr.endswith(f"Saved signed PDF: {output}\n")
    assert browser_urls[0].split("token=", 1)[1] not in result.stderr


def test_invalid_preload_fails_before_browser_or_server_start(
    review_files: tuple[Path, Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_pdf, signature, profile, output = review_files
    data = json.loads(profile.read_text(encoding="utf-8"))
    data["match"]["pages"][0]["rotation"] = 90
    profile.write_text(json.dumps(data), encoding="utf-8")
    opened = False

    def browser_open(_url: str) -> bool:
        nonlocal opened
        opened = True
        return True

    monkeypatch.setattr(cli.webbrowser, "open", browser_open)
    result = CliRunner().invoke(
        cli.main,
        [
            str(input_pdf),
            "--signature",
            str(signature),
            "--coords",
            str(profile),
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "rotation does not match" in result.stderr
    assert opened is False
    assert not output.exists()


class _InterruptingSession:
    def wait_for_result(self) -> None:
        raise KeyboardInterrupt


class _TrackedServer:
    url = "http://127.0.0.1:1234/?token=secret"

    def __init__(self) -> None:
        self.exited = False

    def __enter__(self) -> _TrackedServer:
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.exited = True


def test_ctrl_c_uses_click_interrupt_status_and_closes_server(
    review_files: tuple[Path, Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_pdf, signature, _profile, output = review_files
    session = _InterruptingSession()
    server = _TrackedServer()
    monkeypatch.setattr(cli, "prepare_review_session", lambda **_kwargs: session)
    monkeypatch.setattr(cli, "create_review_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(cli, "ReviewServer", lambda *_args, **_kwargs: server)

    result = CliRunner().invoke(
        cli.main,
        [
            str(input_pdf),
            "--signature",
            str(signature),
            "--output",
            str(output),
            "--open-browser",
            "false",
        ],
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr == (
        "Review session started; browser opening is disabled.\n"
        "Review interrupted; no profile was emitted.\n"
        "\n"
        "Aborted!\n"
    )
    assert server.exited
    assert not output.exists()
    assert not list(output.parent.glob(f".{output.name}.*.tmp"))


def test_failed_browser_open_keeps_session_waiting_and_emits_on_save(
    review_files: tuple[Path, Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_pdf, signature, _profile, output = review_files
    final = PlacementProfile.model_validate(
        {
            "version": 1,
            "match": {
                "page_count": 1,
                "pages": [
                    {"page": 1, "width_pt": 600, "height_pt": 800, "rotation": 0}
                ],
            },
            "placements": [
                {
                    "page": 1,
                    "x": 0.2,
                    "y": 0.2,
                    "width": 0.2,
                    "height": 0.0375,
                }
            ],
        }
    )

    class SavedSession:
        def wait_for_result(self) -> PlacementProfile:
            return final

    server = _TrackedServer()
    monkeypatch.setattr(cli, "prepare_review_session", lambda **_kwargs: SavedSession())
    monkeypatch.setattr(cli, "create_review_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(cli, "ReviewServer", lambda *_args, **_kwargs: server)
    monkeypatch.setattr(cli.webbrowser, "open", lambda _url: False)

    result = CliRunner().invoke(
        cli.main,
        [str(input_pdf), "--signature", str(signature), "--output", str(output)],
    )

    assert result.exit_code == 0
    assert PlacementProfile.model_validate_json(result.stdout) == final
    assert "browser could not be opened" in result.stderr
    assert server.exited


def test_browser_controller_error_is_a_clean_failure(
    review_files: tuple[Path, Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_pdf, signature, _profile, output = review_files
    server = _TrackedServer()
    monkeypatch.setattr(cli, "prepare_review_session", lambda **_kwargs: object())
    monkeypatch.setattr(cli, "create_review_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(cli, "ReviewServer", lambda *_args, **_kwargs: server)

    def fail_open(_url: str) -> bool:
        raise cli.webbrowser.Error("controller unavailable")

    monkeypatch.setattr(cli.webbrowser, "open", fail_open)
    result = CliRunner().invoke(
        cli.main,
        [str(input_pdf), "--signature", str(signature), "--output", str(output)],
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Could not open the review browser: controller unavailable" in result.stderr
    assert server.exited


def test_session_close_without_save_is_a_clean_failure(
    review_files: tuple[Path, Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_pdf, signature, _profile, output = review_files

    class ClosedSession:
        def wait_for_result(self) -> None:
            return None

    server = _TrackedServer()
    monkeypatch.setattr(
        cli, "prepare_review_session", lambda **_kwargs: ClosedSession()
    )
    monkeypatch.setattr(cli, "create_review_app", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(cli, "ReviewServer", lambda *_args, **_kwargs: server)
    result = CliRunner().invoke(
        cli.main,
        [
            str(input_pdf),
            "--signature",
            str(signature),
            "--output",
            str(output),
            "--open-browser",
            "false",
        ],
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Review session ended without saving" in result.stderr
    assert server.exited
