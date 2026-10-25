"""Atomic private readiness-file publication and lifecycle cleanup."""

import json
import stat
from pathlib import Path

import pytest

from pdf_signoff.session_info import publish_session_info


@pytest.mark.parametrize("fail", [False, True])
def test_ready_file_is_private_and_removed_after_success_or_failure(
    tmp_path: Path, fail: bool
) -> None:
    path = tmp_path / "session.json"
    url = "http://127.0.0.1:8080/?token=secret"
    try:
        with publish_session_info(path, url):
            assert json.loads(path.read_text(encoding="utf-8")) == {
                "version": 1,
                "url": url,
            }
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
            if fail:
                raise RuntimeError("session failed")
    except RuntimeError:
        assert fail
    assert not path.exists()
    assert list(tmp_path.iterdir()) == []


def test_ready_file_never_replaces_an_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    path.write_text("existing session", encoding="utf-8")
    with pytest.raises(FileExistsError), publish_session_info(path, "secret"):
        pytest.fail("existing session must prevent publication")
    assert path.read_text(encoding="utf-8") == "existing session"
    assert list(tmp_path.iterdir()) == [path]
