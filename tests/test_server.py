"""Security, API, and lifecycle tests for one-shot review sessions."""

from __future__ import annotations

import base64
import socket
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

import httpx2 as httpx
import pymupdf
import pytest
from fastapi.testclient import TestClient

import pdf_signoff.server as server_module
from pdf_signoff.crypto import L1SigningError
from pdf_signoff.inspection import ProfileMismatchError
from pdf_signoff.output import OutputExistsError
from pdf_signoff.profile import (
    CreatedFrom,
    MatchSpec,
    PageMatch,
    Placement,
    PlacementProfile,
    RequiredText,
)
from pdf_signoff.server import (
    SESSION_COOKIE,
    ReviewServer,
    ReviewSession,
    SessionInactiveError,
    create_review_app,
    prepare_review_session,
)
from pdf_signoff.stamping import StampingError


@pytest.fixture
def review_paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    input_pdf = tmp_path / "selected.pdf"
    signature_png = tmp_path / "selected.png"
    output_pdf = tmp_path / "selected_signed.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=400, height=600)
        page.insert_text((40, 40), "Approval form")
        document.save(input_pdf)
    pixels = bytes((255, 0, 0, 255)) * (40 * 20)
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, 40, 20, pixels, True)
    signature_png.write_bytes(pixmap.tobytes("png"))
    return input_pdf, signature_png, output_pdf


@pytest.fixture
def input_profile() -> PlacementProfile:
    return PlacementProfile(
        version=1,
        created_from=CreatedFrom(sha256="informational-only"),
        match=MatchSpec(
            page_count=1,
            pages=[PageMatch(page=1, width_pt=400, height_pt=600, rotation=0)],
            required_text=[RequiredText(page=1, text="Approval form")],
        ),
        placements=[Placement(page=1, x=0.25, y=0.25, width=0.5, height=1 / 6)],
    )


@pytest.fixture
def frontend_directory(tmp_path: Path) -> Path:
    frontend = tmp_path / "frontend"
    assets = frontend / "assets"
    assets.mkdir(parents=True)
    (frontend / "index.html").write_text(
        '<script src="/assets/app.js"></script>', encoding="utf-8"
    )
    (assets / "app.js").write_text("window.ready = true;", encoding="utf-8")
    (frontend / "private.txt").write_text("not an asset", encoding="utf-8")
    return frontend


@pytest.fixture
def review_session(
    review_paths: tuple[Path, Path, Path],
    input_profile: PlacementProfile,
) -> ReviewSession:
    input_pdf, signature_png, output_pdf = review_paths
    return prepare_review_session(
        input_pdf=input_pdf,
        signature_png=signature_png,
        output_pdf=output_pdf,
        input_profile=input_profile,
        default_signature_width=0.2,
    )


@pytest.fixture
def client(
    review_session: ReviewSession,
    frontend_directory: Path,
) -> TestClient:
    return TestClient(
        create_review_app(review_session, frontend_directory=frontend_directory)
    )


def bearer(session: ReviewSession) -> dict[str, str]:
    return {"Authorization": f"Bearer {session.token}"}


def valid_save_body() -> dict[str, object]:
    return {
        "placements": [{"page": 1, "x": 0.25, "y": 0.25, "width": 0.5, "height": 1 / 6}]
    }


def test_session_token_has_256_bits_of_random_input_and_is_not_in_repr(
    review_session: ReviewSession,
) -> None:
    padded = review_session.token + "=" * (-len(review_session.token) % 4)
    decoded = base64.urlsafe_b64decode(padded)

    assert len(decoded) == server_module.SESSION_TOKEN_BYTES
    assert review_session.token not in repr(review_session)
    assert review_session.matches_token(review_session.token)
    assert not review_session.matches_token(None)
    assert not review_session.matches_token("wrong")


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/"),
        ("get", "/assets/app.js"),
        ("get", "/api/document"),
        ("get", "/api/signature"),
        ("get", "/api/session"),
        ("post", "/api/save"),
        ("get", "/openapi.json"),
    ],
)
def test_every_route_rejects_unauthorized_requests(
    client: TestClient,
    method: str,
    path: str,
) -> None:
    response = client.request(method, path, json=valid_save_body())

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid review session."}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "access-control-allow-origin" not in response.headers


def test_api_and_error_responses_include_framing_safe_csp(
    client: TestClient,
    review_session: ReviewSession,
) -> None:
    api_response = client.get("/api/session", headers=bearer(review_session))
    error_response = client.get("/api/session")

    for response in (api_response, error_response):
        assert response.headers["content-security-policy"] == (
            server_module.CONTENT_SECURITY_POLICY
        )
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_url_bootstrap_establishes_hardened_cookie_and_removes_token(
    client: TestClient,
    review_session: ReviewSession,
) -> None:
    invalid = client.get("/?token=wrong", follow_redirects=False)
    response = client.get(
        "/", params={"token": review_session.token}, follow_redirects=False
    )

    assert invalid.status_code == 401
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    cookie = response.headers["set-cookie"]
    assert f"{SESSION_COOKIE}=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert review_session.token not in response.headers["location"]
    assert client.get("/").text == '<script src="/assets/app.js"></script>'
    assert client.get("/assets/app.js").text == "window.ready = true;"


def test_bearer_authorization_is_case_insensitive_and_malformed_header_fails(
    client: TestClient,
    review_session: ReviewSession,
) -> None:
    accepted = client.get(
        "/api/session", headers={"Authorization": f"bEaReR {review_session.token}"}
    )
    rejected = client.get(
        "/api/session", headers={"Authorization": review_session.token}
    )

    assert accepted.status_code == 200
    assert rejected.status_code == 401


def test_session_metadata_is_exactly_the_safe_ui_contract(
    client: TestClient,
    review_session: ReviewSession,
    review_paths: tuple[Path, Path, Path],
) -> None:
    response = client.get("/api/session", headers=bearer(review_session))

    assert response.status_code == 200
    assert response.json() == {
        "pageCount": 1,
        "documentName": "selected.pdf",
        "initialPlacements": [
            {
                "page": 1,
                "x": 0.25,
                "y": 0.25,
                "width": 0.5,
                "height": 1 / 6,
            }
        ],
        "defaultSignatureWidth": 0.2,
    }
    serialized = response.text
    for path in review_paths:
        assert str(path) not in serialized
    _input_pdf, signature_png, output_pdf = review_paths
    assert signature_png.name not in serialized
    assert output_pdf.name not in serialized
    assert "sha256" not in serialized


def test_only_selected_files_and_frontend_assets_are_served(
    client: TestClient,
    review_session: ReviewSession,
    review_paths: tuple[Path, Path, Path],
    frontend_directory: Path,
) -> None:
    input_pdf, signature_png, _output_pdf = review_paths
    headers = bearer(review_session)

    document = client.get("/api/document", headers=headers)
    signature = client.get("/api/signature", headers=headers)

    assert document.status_code == 200
    assert document.headers["content-type"] == "application/pdf"
    assert document.content == input_pdf.read_bytes()
    assert signature.status_code == 200
    assert signature.headers["content-type"] == "image/png"
    assert signature.content == signature_png.read_bytes()
    assert client.get("/api/document/anything", headers=headers).status_code == 404
    generic_file = client.get("/api/file", params={"path": input_pdf}, headers=headers)
    assert generic_file.status_code == 404
    assert client.get("/private.txt", headers=headers).status_code == 404
    traversal = client.get("/assets/%2e%2e/private.txt", headers=headers)
    assert traversal.status_code == 404
    assert traversal.text != (frontend_directory / "private.txt").read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"placements": []},
        {"placements": [{"page": 2, "x": 0, "y": 0, "width": 0.1, "height": 0.1}]},
        {"placements": [{"page": 1, "x": -1, "y": 0, "width": 0.1, "height": 0.1}]},
        {**valid_save_body(), "output": "/tmp/attacker.pdf"},
        {**valid_save_body(), "input_pdf": "/etc/passwd"},
        {**valid_save_body(), "signature": "/tmp/other.png"},
    ],
)
def test_malformed_or_path_bearing_save_requests_are_safely_rejected(
    client: TestClient,
    review_session: ReviewSession,
    body: dict[str, object],
) -> None:
    response = client.post("/api/save", json=body, headers=bearer(review_session))

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request."} or response.json() == {
        "detail": "Invalid placements."
    }
    assert "/tmp" not in response.text
    assert "/etc" not in response.text
    assert review_session.is_active


def test_malformed_json_is_rejected_without_reflecting_input(
    client: TestClient,
    review_session: ReviewSession,
) -> None:
    response = client.post(
        "/api/save",
        content=b'{"path":"/etc/passwd"',
        headers={**bearer(review_session), "Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request."}
    assert "/etc/passwd" not in response.text


def test_cross_origin_requests_are_rejected_without_cors(
    client: TestClient,
    review_session: ReviewSession,
) -> None:
    cross_origin = client.get(
        "/api/session",
        headers={**bearer(review_session), "Origin": "https://unrelated.example"},
    )
    fetch_metadata = client.get(
        "/api/session",
        headers={**bearer(review_session), "Sec-Fetch-Site": "cross-site"},
    )
    same_origin = client.get(
        "/api/session",
        headers={**bearer(review_session), "Origin": "http://testserver"},
    )

    assert cross_origin.status_code == 403
    assert fetch_metadata.status_code == 403
    assert same_origin.status_code == 200
    for response in (cross_origin, fetch_metadata, same_origin):
        assert "access-control-allow-origin" not in response.headers


def test_successful_save_uses_shared_pipeline_then_consumes_session(
    client: TestClient,
    review_session: ReviewSession,
    review_paths: tuple[Path, Path, Path],
) -> None:
    input_pdf, _signature_png, output_pdf = review_paths
    original_hash = sha256(input_pdf.read_bytes()).hexdigest()

    response = client.post(
        "/api/save", json=valid_save_body(), headers=bearer(review_session)
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert set(response.json()) == {"ok"}
    final_profile = review_session.wait_for_result(timeout=0)
    assert final_profile is not None
    assert final_profile.created_from is not None
    assert final_profile.created_from.sha256 == original_hash
    assert final_profile.match.required_text is not None
    assert final_profile.match.required_text[0].text == "Approval form"
    assert output_pdf.is_file()
    assert sha256(input_pdf.read_bytes()).hexdigest() == original_hash
    with pymupdf.open(output_pdf) as document:
        assert document[0].get_images()

    assert not review_session.is_active
    assert client.get("/api/session", headers=bearer(review_session)).status_code == 401
    repeated_save = client.post(
        "/api/save", json=valid_save_body(), headers=bearer(review_session)
    )
    assert repeated_save.status_code == 401


@pytest.mark.parametrize(
    ("error", "status", "detail"),
    [
        (StampingError("bad aspect"), 422, "Invalid placements."),
        (OutputExistsError("exists"), 409, "Output cannot be written."),
    ],
)
def test_pipeline_failures_are_sanitized_and_allow_retry(
    client: TestClient,
    review_session: ReviewSession,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status: int,
    detail: str,
) -> None:
    def fail_stamp(*_args: object, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr(server_module, "stamp_l0", fail_stamp)
    response = client.post(
        "/api/save", json=valid_save_body(), headers=bearer(review_session)
    )

    assert response.status_code == status
    assert response.json() == {"detail": detail}
    assert str(error) not in response.text
    assert review_session.is_active


def test_cryptographic_failure_is_sanitized_and_allows_retry(
    review_paths: tuple[Path, Path, Path],
    input_profile: PlacementProfile,
    frontend_directory: Path,
) -> None:
    class FailingSigner:
        def sign(self, _path: Path) -> None:
            raise L1SigningError("private signer detail")

    input_pdf, signature_png, output_pdf = review_paths
    session = prepare_review_session(
        input_pdf=input_pdf,
        signature_png=signature_png,
        output_pdf=output_pdf,
        input_profile=input_profile,
        l1_signer=FailingSigner(),  # type: ignore[arg-type]
    )
    protected_client = TestClient(
        create_review_app(session, frontend_directory=frontend_directory)
    )

    response = protected_client.post(
        "/api/save", json=valid_save_body(), headers=bearer(session)
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Cryptographic signing failed."}
    assert "private signer detail" not in response.text
    assert session.is_active
    assert not output_pdf.exists()
    assert not list(output_pdf.parent.glob(f".{output_pdf.name}.*.tmp"))


def test_save_endpoint_handles_a_session_that_becomes_busy(
    client: TestClient,
    review_session: ReviewSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_save(_placements: object) -> PlacementProfile:
        raise SessionInactiveError("race")

    monkeypatch.setattr(review_session, "save", reject_save)
    response = client.post(
        "/api/save", json=valid_save_body(), headers=bearer(review_session)
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Save is already complete."}


def test_session_state_guards_duplicate_save_finish_and_close(
    review_session: ReviewSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(server_module, "stamp_l0", lambda *_args, **_kwargs: None)
    profile = review_session.save(valid_save_body()["placements"])

    with pytest.raises(SessionInactiveError, match="no longer active"):
        review_session.save(valid_save_body()["placements"])
    assert review_session.wait_for_result(timeout=0) is None
    review_session.finish_save(profile)
    review_session.close()
    assert review_session.wait_for_result(timeout=0) == profile
    with pytest.raises(SessionInactiveError, match="no pending save"):
        review_session.finish_save(profile)


def test_closed_unsaved_session_unblocks_waiters_and_rejects_requests(
    review_session: ReviewSession,
    frontend_directory: Path,
) -> None:
    app = create_review_app(review_session, frontend_directory=frontend_directory)
    review_session.close()

    assert review_session.wait_for_result(timeout=0) is None
    response = TestClient(app).get("/api/session", headers=bearer(review_session))
    assert response.status_code == 401
    assert response.json() == {"detail": "Review session is no longer active."}


def test_session_preparation_validates_profile_and_options(
    review_paths: tuple[Path, Path, Path],
    input_profile: PlacementProfile,
) -> None:
    input_pdf, signature_png, output_pdf = review_paths
    mismatched = input_profile.model_copy(deep=True)
    mismatched.match.pages[0].rotation = 90

    with pytest.raises(ProfileMismatchError, match="rotation does not match"):
        prepare_review_session(
            input_pdf=input_pdf,
            signature_png=signature_png,
            output_pdf=output_pdf,
            input_profile=mismatched,
        )
    with pytest.raises(ValueError, match="default signature width"):
        prepare_review_session(
            input_pdf=input_pdf,
            signature_png=signature_png,
            output_pdf=output_pdf,
            default_signature_width=0,
        )


def test_app_can_be_created_without_frontend_and_rejects_invalid_frontend(
    review_session: ReviewSession,
    tmp_path: Path,
) -> None:
    app = create_review_app(review_session)
    response = TestClient(app).get("/", headers=bearer(review_session))

    assert response.status_code == 404
    with pytest.raises(ValueError, match="index.html and assets"):
        create_review_app(review_session, frontend_directory=tmp_path)


def test_server_defaults_to_loopback_uses_ephemeral_port_and_logs_no_token(
    review_session: ReviewSession,
    frontend_directory: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = create_review_app(review_session, frontend_directory=frontend_directory)
    server = ReviewServer(app)
    with pytest.raises(RuntimeError, match="has not started"):
        _ = server.url

    with server:
        assert server.host == "127.0.0.1"
        assert server.requested_port == 0
        assert server.port is not None and server.port > 0
        parsed = urlsplit(server.url)
        assert parsed.hostname == "127.0.0.1"
        assert parsed.port == server.port
        with httpx.Client(trust_env=False) as http_client:
            response = http_client.get(
                f"http://127.0.0.1:{server.port}/api/session",
                headers=bearer(review_session),
            )
        assert response.status_code == 200

        with pytest.raises(RuntimeError, match="already started"):
            server.start()

    assert not review_session.is_active
    captured = capsys.readouterr()
    assert captured.out == ""
    assert review_session.token not in captured.err


def test_server_allows_only_its_bound_host_header(
    review_session: ReviewSession,
    frontend_directory: Path,
) -> None:
    app = create_review_app(review_session, frontend_directory=frontend_directory)

    with ReviewServer(app) as server:
        assert server.port is not None
        url = f"http://{server.host}:{server.port}/api/session"
        with httpx.Client(trust_env=False) as http_client:
            accepted = http_client.get(url, headers=bearer(review_session))
            rejected = http_client.get(
                url,
                headers={**bearer(review_session), "Host": "unrelated.example"},
            )

    assert accepted.status_code == 200
    assert rejected.status_code == 400
    assert rejected.json() == {"detail": "Invalid Host header."}


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"host": "0.0.0.0"}, "loopback"),
        ({"port": -1}, "between 0 and 65535"),
        ({"port": 65536}, "between 0 and 65535"),
        ({"startup_timeout": 0}, "greater than zero"),
    ],
)
def test_server_rejects_unsafe_or_invalid_binding_options(
    review_session: ReviewSession,
    kwargs: dict[str, object],
    message: str,
) -> None:
    app = create_review_app(review_session)
    with pytest.raises(ValueError, match=message):
        ReviewServer(app, **kwargs)  # type: ignore[arg-type]


def test_server_supports_explicit_loopback_port(
    review_session: ReviewSession,
) -> None:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = int(probe.getsockname()[1])
    probe.close()

    with ReviewServer(create_review_app(review_session), port=port) as server:
        assert server.port == port
        assert f":{port}/" in server.url


class _FakeThread:
    def __init__(self, *_args: object, alive: bool, **_kwargs: object) -> None:
        self.alive = alive

    def start(self) -> None:
        pass

    def is_alive(self) -> bool:
        return self.alive

    def join(self, *, timeout: float) -> None:
        del timeout


def test_server_cleans_up_when_worker_exits_during_startup(
    review_session: ReviewSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        server_module,
        "Thread",
        lambda *_args, **_kwargs: _FakeThread(alive=False),
    )
    server = ReviewServer(create_review_app(review_session))

    with pytest.raises(RuntimeError, match="failed to start"):
        server.start()

    assert not review_session.is_active
    assert server._socket is not None
    assert server._socket.fileno() == -1


def test_server_times_out_and_reports_a_worker_that_will_not_stop(
    review_session: ReviewSession,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        server_module,
        "Thread",
        lambda *_args, **_kwargs: _FakeThread(alive=True),
    )
    times = iter((0.0, 2.0))
    monkeypatch.setattr(server_module, "monotonic", lambda: next(times))
    monkeypatch.setattr(server_module, "sleep", lambda _seconds: None)
    server = ReviewServer(create_review_app(review_session), startup_timeout=1)

    with pytest.raises(RuntimeError, match="startup timed out"):
        server.start()

    assert "did not stop cleanly" in caplog.text
    assert not review_session.is_active
