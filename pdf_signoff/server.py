"""Protected, single-invocation local review server boundary."""

from __future__ import annotations

import logging
import secrets
import socket
from ipaddress import ip_address
from pathlib import Path
from threading import Event, Lock, Thread
from time import monotonic, sleep
from typing import Literal
from urllib.parse import quote, urlsplit

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from pydantic import ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp

from pdf_signoff.crypto import L1Signer, L1SigningError
from pdf_signoff.inspection import (
    PdfInspection,
    SignatureInspection,
    inspect_pdf,
    inspect_signature_png,
    validate_profile_match,
)
from pdf_signoff.output import OutputError
from pdf_signoff.profile import (
    Placement,
    PlacementProfile,
    ProfileModel,
    build_final_profile,
    validate_placements,
)
from pdf_signoff.stamping import StampingError, stamp_l0

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 0
PACKAGED_FRONTEND = Path(__file__).with_name("web_dist")
SESSION_TOKEN_BYTES = 32
SESSION_COOKIE = "pdf_signoff_session"

_UVICORN_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": None,
        }
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stderr",
        }
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {
            "handlers": [],
            "level": "WARNING",
            "propagate": False,
        },
    },
}


class SaveRequest(ProfileModel):
    """The browser may submit normalized placements and nothing else."""

    placements: list[Placement]


class SaveResponse(ProfileModel):
    """Minimal successful browser response."""

    ok: Literal[True] = True


class SessionMetadata(ProfileModel):
    """Path-free metadata needed by the placement frontend."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    page_count: int = Field(serialization_alias="pageCount")
    initial_placements: list[Placement] = Field(serialization_alias="initialPlacements")
    default_signature_width: float = Field(serialization_alias="defaultSignatureWidth")


class SessionInactiveError(RuntimeError):
    """The one-shot review session no longer accepts operations."""


class ReviewSession:
    """Private state and shared signing pipeline for one fixed invocation."""

    def __init__(
        self,
        *,
        input_pdf: Path,
        signature_png: Path,
        output_pdf: Path,
        pdf: PdfInspection,
        signature: SignatureInspection,
        input_profile: PlacementProfile | None = None,
        default_signature_width: float = 0.16,
        overwrite: bool = False,
        l1_signer: L1Signer | None = None,
    ) -> None:
        if not 0 < default_signature_width <= 1:
            raise ValueError(
                "default signature width must be greater than 0 and at most 1"
            )
        self._input_pdf = input_pdf
        self._signature_png = signature_png
        self._output_pdf = output_pdf
        self._pdf = pdf
        self._signature = signature
        self._input_profile = input_profile
        self._default_signature_width = default_signature_width
        self._overwrite = overwrite
        self._l1_signer = l1_signer
        self._token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
        self._state: Literal["active", "saving", "saved", "closed"] = "active"
        self._result: PlacementProfile | None = None
        self._lock = Lock()
        self._finished = Event()

    @property
    def token(self) -> str:
        """Return the secret used only to bootstrap the local browser session."""
        return self._token

    @property
    def input_pdf(self) -> Path:
        """Return the fixed PDF selected for this review session."""
        return self._input_pdf

    @property
    def signature_png(self) -> Path:
        """Return the fixed signature image selected for this review session."""
        return self._signature_png

    @property
    def is_active(self) -> bool:
        """Return whether a new authenticated operation may begin."""
        with self._lock:
            return self._state == "active"

    @property
    def metadata(self) -> SessionMetadata:
        """Build safe metadata without exposing invocation paths or hashes."""
        placements = (
            list(self._input_profile.placements)
            if self._input_profile is not None
            else []
        )
        return SessionMetadata(
            page_count=self._pdf.page_count,
            initial_placements=placements,
            default_signature_width=self._default_signature_width,
        )

    def matches_token(self, candidate: str | None) -> bool:
        """Compare an untrusted credential without ordinary string timing leakage."""
        return candidate is not None and secrets.compare_digest(candidate, self._token)

    def save(self, placements: object) -> PlacementProfile:
        """Validate, stamp, and build the final profile for one save attempt."""
        validated = validate_placements(
            placements,
            page_count=self._pdf.page_count,
            require_non_empty=True,
        )
        with self._lock:
            if self._state != "active":
                raise SessionInactiveError("Review session is no longer active.")
            self._state = "saving"

        try:
            stamp_l0(
                self._input_pdf,
                self._signature_png,
                self._output_pdf,
                validated,
                pages=self._pdf.pages,
                signature=self._signature,
                overwrite=self._overwrite,
                finalize=(
                    self._l1_signer.sign if self._l1_signer is not None else None
                ),
            )
            return build_final_profile(
                source_sha256=self._pdf.sha256,
                pages=self._pdf.pages,
                placements=validated,
                input_profile=self._input_profile,
            )
        except Exception:
            with self._lock:
                self._state = "active"
            raise

    def finish_save(self, profile: PlacementProfile) -> None:
        """Consume the session after FastAPI has completed the success response."""
        with self._lock:
            if self._state != "saving":
                raise SessionInactiveError("Review session has no pending save.")
            self._result = profile
            self._state = "saved"
            self._finished.set()

    def close(self) -> None:
        """Invalidate a session when its owning CLI/server lifetime ends."""
        with self._lock:
            if self._state != "saved":
                self._state = "closed"
            self._finished.set()

    def wait_for_result(self, timeout: float | None = None) -> PlacementProfile | None:
        """Wait for save or close; later CLI lifecycle code can consume the result."""
        self._finished.wait(timeout)
        with self._lock:
            return self._result


def prepare_review_session(
    *,
    input_pdf: Path,
    signature_png: Path,
    output_pdf: Path,
    input_profile: PlacementProfile | None = None,
    default_signature_width: float = 0.16,
    overwrite: bool = False,
    l1_signer: L1Signer | None = None,
    pdf: PdfInspection | None = None,
) -> ReviewSession:
    """Inspect fixed invocation resources and create a protected session."""
    pdf = inspect_pdf(input_pdf) if pdf is None else pdf
    signature = inspect_signature_png(signature_png)
    if input_profile is not None:
        validate_profile_match(input_profile, pdf)
    return ReviewSession(
        input_pdf=input_pdf,
        signature_png=signature_png,
        output_pdf=output_pdf,
        pdf=pdf,
        signature=signature,
        input_profile=input_profile,
        default_signature_width=default_signature_width,
        overwrite=overwrite,
        l1_signer=l1_signer,
    )


class _SessionProtectionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, session: ReviewSession) -> None:
        super().__init__(app)
        self._session = session

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if not self._session.is_active:
            return _error_response(401, "Review session is no longer active.")
        if not _is_same_origin(request):
            return _error_response(403, "Cross-origin requests are not allowed.")

        bootstrap_token = request.query_params.get("token")
        if request.method == "GET" and request.url.path == "/" and bootstrap_token:
            if not self._session.matches_token(bootstrap_token):
                return _error_response(401, "Invalid review session.")
            response = RedirectResponse("/", status_code=303)
            response.set_cookie(
                SESSION_COOKIE,
                self._session.token,
                httponly=True,
                samesite="strict",
                secure=False,
            )
            return _harden(response)

        if not self._session.matches_token(_request_token(request)):
            return _error_response(401, "Invalid review session.")
        return _harden(await call_next(request))


def create_review_app(
    session: ReviewSession,
    *,
    frontend_directory: Path | None = None,
) -> FastAPI:
    """Create the narrowly scoped ASGI application for one review session."""
    app = FastAPI(
        title="PDF Signoff local review",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.review_session = session
    app.add_middleware(_SessionProtectionMiddleware, session=session)

    frontend_index: Path | None = None
    if frontend_directory is not None:
        frontend_index = frontend_directory / "index.html"
        assets_directory = frontend_directory / "assets"
        if not frontend_index.is_file() or not assets_directory.is_dir():
            raise ValueError("frontend directory must contain index.html and assets/")
        app.mount(
            "/assets",
            StaticFiles(directory=assets_directory, check_dir=True),
            name="frontend-assets",
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(
        _request: Request,
        _error: RequestValidationError,
    ) -> JSONResponse:
        return _error_response(422, "Invalid request.")

    @app.get("/", include_in_schema=False)
    async def frontend() -> Response:
        if frontend_index is None:
            raise HTTPException(status_code=404, detail="Frontend is not installed.")
        return FileResponse(frontend_index, media_type="text/html")

    @app.get("/api/document", include_in_schema=False)
    async def document() -> FileResponse:
        return FileResponse(session.input_pdf, media_type="application/pdf")

    @app.get("/api/signature", include_in_schema=False)
    async def signature() -> FileResponse:
        return FileResponse(session.signature_png, media_type="image/png")

    @app.get(
        "/api/session",
        response_model=SessionMetadata,
        response_model_by_alias=True,
        include_in_schema=False,
    )
    async def metadata() -> SessionMetadata:
        return session.metadata

    @app.post(
        "/api/save",
        response_model=SaveResponse,
        include_in_schema=False,
    )
    def save(
        request: SaveRequest,
        background_tasks: BackgroundTasks,
    ) -> SaveResponse:
        try:
            profile = session.save(request.placements)
        except SessionInactiveError as exc:
            raise HTTPException(
                status_code=409, detail="Save is already complete."
            ) from exc
        except (ValueError, StampingError) as exc:
            raise HTTPException(status_code=422, detail="Invalid placements.") from exc
        except OutputError as exc:
            raise HTTPException(
                status_code=409, detail="Output cannot be written."
            ) from exc
        except L1SigningError as exc:
            raise HTTPException(
                status_code=500, detail="Cryptographic signing failed."
            ) from exc
        background_tasks.add_task(session.finish_save, profile)
        return SaveResponse()

    return app


class ReviewServer:
    """Threaded Uvicorn handle with an observable pre-bound ephemeral port."""

    def __init__(
        self,
        app: FastAPI,
        *,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        startup_timeout: float = 5.0,
        log_level: str | int = logging.INFO,
    ) -> None:
        address = ip_address(host)
        if not address.is_loopback:
            raise ValueError("review server host must be a loopback IP address")
        if not 0 <= port <= 65535:
            raise ValueError("review server port must be between 0 and 65535")
        if startup_timeout <= 0:
            raise ValueError("startup timeout must be greater than zero")
        self.app = app
        self.host = host
        self.requested_port = port
        self.startup_timeout = startup_timeout
        self.log_level = log_level
        self.port: int | None = None
        self._socket: socket.socket | None = None
        self._server: uvicorn.Server | None = None
        self._thread: Thread | None = None

    @property
    def url(self) -> str:
        """Return the secret bootstrap URL only to the owning CLI integration."""
        if self.port is None:
            raise RuntimeError("review server has not started")
        host = f"[{self.host}]" if ":" in self.host else self.host
        token = quote(self.app.state.review_session.token, safe="")
        return f"http://{host}:{self.port}/?token={token}"

    def start(self) -> ReviewServer:
        """Bind and start Uvicorn, preserving port 0's selected port."""
        if self._thread is not None:
            raise RuntimeError("review server has already started")
        family = socket.AF_INET6 if ":" in self.host else socket.AF_INET
        bound_socket = socket.socket(family, socket.SOCK_STREAM)
        try:
            bound_socket.bind((self.host, self.requested_port))
            bound_socket.listen(128)
            self.port = int(bound_socket.getsockname()[1])
            config = uvicorn.Config(
                self.app,
                host=self.host,
                port=self.port,
                access_log=False,
                log_config=_UVICORN_LOG_CONFIG,
                log_level=self.log_level,
            )
            self._socket = bound_socket
            self._server = uvicorn.Server(config)
            self._thread = Thread(
                target=self._server.run,
                kwargs={"sockets": [bound_socket]},
                name="pdf-signoff-review-server",
                daemon=True,
            )
            self._thread.start()
            deadline = monotonic() + self.startup_timeout
            while not self._server.started:
                if not self._thread.is_alive():
                    raise RuntimeError("review server failed to start")
                if monotonic() >= deadline:
                    raise RuntimeError("review server startup timed out")
                sleep(0.01)
        except Exception:
            bound_socket.close()
            self.stop()
            raise
        return self

    def stop(self) -> None:
        """Stop Uvicorn and invalidate the session owned by this server."""
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=self.startup_timeout)
            if self._thread.is_alive():
                logging.getLogger(__name__).error("Review server did not stop cleanly.")
        if self._socket is not None:
            self._socket.close()
        session: ReviewSession = self.app.state.review_session
        session.close()

    def __enter__(self) -> ReviewServer:
        return self.start()

    def __exit__(self, *_exc_info: object) -> None:
        self.stop()


def _request_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if authorization is not None:
        scheme, separator, credential = authorization.partition(" ")
        if separator and scheme.lower() == "bearer":
            return credential
    return request.cookies.get(SESSION_COOKIE)


def _is_same_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    if origin is None:
        return request.headers.get("sec-fetch-site") != "cross-site"
    parsed = urlsplit(origin)
    return parsed.scheme in {"http", "https"} and parsed.netloc == request.headers.get(
        "host"
    )


def _error_response(status_code: int, detail: str) -> JSONResponse:
    response = JSONResponse({"detail": detail}, status_code=status_code)
    _harden(response)
    return response


def _harden(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
