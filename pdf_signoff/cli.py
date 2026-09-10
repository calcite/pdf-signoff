"""Click entry point and Onacol configuration bootstrap."""

import logging
import webbrowser
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TextIO

import click
from onacol import ConfigManager, OnacolException  # type: ignore[import-untyped]
from pydantic import ValidationError

from pdf_signoff.config import (
    DEFAULT_CONFIG_FILE,
    CliConfigArgumentError,
    load_config,
)
from pdf_signoff.crypto import L1Signer, L1SigningError, load_l1_signer
from pdf_signoff.inspection import (
    InputInspectionError,
    PdfInspection,
    ProfileMismatchError,
    inspect_pdf,
    inspect_signature_png,
    validate_profile_match,
)
from pdf_signoff.output import OutputError, resolve_output_path
from pdf_signoff.profile import (
    PlacementProfile,
    build_final_profile,
    load_profile,
    serialize_profile,
)
from pdf_signoff.server import (
    PACKAGED_FRONTEND,
    ReviewServer,
    create_review_app,
    prepare_review_session,
)
from pdf_signoff.stamping import StampingError, stamp_l0

LOGGER = logging.getLogger(__name__)

HELP_EPILOG = """
\b
MODES
  Review is the default. It opens a protected one-shot loopback session and
  completes only when Save is selected. Closing the browser does not cancel;
  press Ctrl+C to stop without creating an output or emitting a profile.

\b
  --auto never opens the UI and requires --coords with at least one placement.
  --coords alone still uses review mode, where placements are editable.

\b
OUTPUTS AND PROCESS CONTRACT
  The input is never modified. Without --output, the configured suffix is
  inserted before the final extension (report.v2.pdf -> report.v2_signed.pdf).
  Input and output must differ. Existing outputs require explicit --overwrite.

\b
  A PDF is published transactionally only after every requested stage passes.
  After successful signing, stdout contains exactly one compact version-1
  placement-profile JSON object plus a newline. At the default INFO log level,
  stderr reports the PDF path. Higher levels may suppress that message, so
  automation should track --output instead of parsing stderr.

\b
  Failure returns nonzero, leaves stdout empty, and commits no partial output.

\b
PLACEMENT PROFILES
  Pages are 1-based. x, y, width, and height are fractions from 0 to 1 of the
  displayed CropBox after rotation; the origin is top-left. Page count,
  dimensions, rotations, and optional required text must match before reuse.
  created_from.sha256 is informational. Retain the emitted final profile because
  review may edit placements and the tool refreshes metadata.

\b
SIGNING LEVELS
  l0 places the PNG only; it provides no tamper evidence. l1 adds an invisible
  signature over the L0 revision and requires a configured PKCS#12 .p12/.pfx.
  Its password comes from the configured environment variable or a secure prompt.
  L1 provides revision integrity, not trust, identity, timestamping, or a
  legal/qualified signature claim.

\b
  PDFs containing a cryptographic signature are refused by default. Use
  --allow-signed-input only after accepting that processing may invalidate prior
  signatures; the override does not validate them.

\b
CONFIGURATION
  Precedence, lowest to highest: bundled defaults; --config FILE, otherwise
  $XDG_CONFIG_HOME/pdf-signoff/config.yaml then
  ~/.config/pdf-signoff/config.yaml; PDF_SIGNOFF__SECTION__KEY environment
  variables; nested options below.

\b
  --general--log-level LEVEL     INFO; DEBUG|INFO|WARNING|ERROR|CRITICAL
  --output-suffix TEXT           _signed; non-empty
  --default-level LEVEL          l0; l0|l1
  --default-signature-width N    0.16; > 0 and <= 1
  --open-browser BOOLEAN         true
  --host LOOPBACK_IP             127.0.0.1; non-loopback addresses are refused
  --port INTEGER                 0 (ephemeral); 0 through 65535
  --l1--pkcs12-path PATH         empty by default
  --l1--password-env NAME        PDF_SIGN_PKCS12_PASSWORD
  --l1--reason TEXT              Internal document approval

\b
  Nested options require a value, including booleans as true or false. Generate
  complete schema-free YAML with --get-config-template FILE; use - for stdout.

\b
EXAMPLES
  Review and capture the final profile:
    pdf-signoff report.pdf --signature signature.png > placement.json

\b
  Reuse it unattended with an explicit destination:
    pdf-signoff report.pdf --signature signature.png --coords placement.json \\
      --auto --level l0 --output report-approved.pdf > final-profile.json

\b
The caller is responsible for authorization, choosing the inputs and level, and
accepting the resulting PDF. Encrypted, malformed, repaired, and zero-page PDFs,
and non-PNG signature assets, are rejected.
"""


@dataclass(frozen=True)
class Invocation:
    """Validated command inputs handed to the later signing workflow."""

    input_pdf: Path
    signature: Path
    coords: Path | None
    output: Path
    mode: Literal["review", "auto"]
    level: Literal["l0", "l1"]
    overwrite: bool
    allow_signed_input: bool
    config: Mapping[str, Any]


class ReviewError(Exception):
    """The interactive review lifecycle could not complete."""


@contextmanager
def _configured_logging(log_level: str) -> Iterator[None]:
    """Temporarily route package logging to the invocation's stderr."""
    package_logger = logging.getLogger("pdf_signoff")
    previous_handlers = package_logger.handlers[:]
    previous_level = package_logger.level
    previous_propagate = package_logger.propagate
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    package_logger.handlers.clear()
    package_logger.addHandler(handler)
    package_logger.setLevel(log_level)
    package_logger.propagate = False
    try:
        yield
    finally:
        package_logger.removeHandler(handler)
        package_logger.handlers.extend(previous_handlers)
        package_logger.setLevel(previous_level)
        package_logger.propagate = previous_propagate


def _write_config_template(
    ctx: click.Context,
    _param: click.Parameter,
    output_file: TextIO | None,
) -> None:
    if output_file is None or ctx.resilient_parsing:
        return
    ConfigManager(DEFAULT_CONFIG_FILE).generate_config_example(output_file)
    ctx.exit()


@click.command(
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
    },
    epilog=HELP_EPILOG,
)
@click.argument(
    "input_pdf",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--signature",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="PNG to place; one signature image per invocation.",
)
@click.option(
    "--coords",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Version-1 profile to edit in review or apply in auto mode.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Explicit output PDF; otherwise use the configured suffix.",
)
@click.option(
    "--review",
    is_flag=True,
    help="Use interactive review mode (the default).",
)
@click.option(
    "--auto",
    "automatic",
    is_flag=True,
    help="Sign without opening the UI; requires --coords.",
)
@click.option(
    "--level",
    type=click.Choice(("l0", "l1"), case_sensitive=True),
    default=None,
    help="Signing level; defaults to the configured default_level.",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Explicitly allow atomic replacement of an existing output.",
)
@click.option(
    "--allow-signed-input",
    is_flag=True,
    help="Accept possible invalidation of prior PDF signatures.",
)
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Explicit user YAML; otherwise XDG and home paths are searched.",
)
@click.option(
    "--get-config-template",
    type=click.File("w"),
    callback=_write_config_template,
    expose_value=False,
    is_eager=True,
    help="Write schema-free YAML and exit; use - for stdout.",
)
@click.version_option(package_name="pdf-signoff")
@click.pass_context
def main(
    ctx: click.Context,
    input_pdf: Path,
    signature: Path,
    coords: Path | None,
    output: Path | None,
    review: bool,
    automatic: bool,
    level: Literal["l0", "l1"] | None,
    overwrite: bool,
    allow_signed_input: bool,
    config: Path | None,
) -> Invocation:
    """Validate a PDF signing invocation and run visual or integrity signing."""
    try:
        config_manager = load_config(config, ctx.args)
    except CliConfigArgumentError as exc:
        raise click.UsageError(str(exc)) from exc
    except (OnacolException, OSError) as exc:
        raise click.ClickException(f"Configuration validation failed: {exc}") from exc

    with _configured_logging(config_manager.config["general"]["log_level"]):
        if review and automatic:
            raise click.UsageError("--review and --auto are mutually exclusive.")
        if automatic and coords is None:
            raise click.UsageError("--auto requires --coords.")

        try:
            resolved_output = resolve_output_path(
                input_pdf,
                explicit_output=output,
                output_suffix=config_manager.config["output_suffix"],
                overwrite=overwrite,
            )
        except OutputError as exc:
            raise click.ClickException(str(exc)) from exc

        invocation = Invocation(
            input_pdf=input_pdf,
            signature=signature,
            coords=coords,
            output=resolved_output,
            mode="auto" if automatic else "review",
            level=level or config_manager.config["default_level"],
            overwrite=overwrite,
            allow_signed_input=allow_signed_input,
            config=config_manager.config,
        )
        LOGGER.debug(
            "Signing request configured for %s mode at level %s.",
            invocation.mode,
            invocation.level.upper(),
        )
        try:
            pdf = inspect_pdf(invocation.input_pdf)
            _enforce_signed_input_policy(invocation, pdf)
            l1_signer = (
                load_l1_signer(invocation.config["l1"])
                if invocation.level == "l1"
                else None
            )
            final_profile = (
                _run_automatic_l0(invocation, pdf=pdf, l1_signer=l1_signer)
                if invocation.mode == "auto"
                else _run_review_l0(invocation, pdf=pdf, l1_signer=l1_signer)
            )
        except (
            InputInspectionError,
            L1SigningError,
            ProfileMismatchError,
            ReviewError,
            StampingError,
            OutputError,
            OSError,
            RuntimeError,
            UnicodeError,
            ValueError,
            ValidationError,
        ) as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(serialize_profile(final_profile))
        LOGGER.info("Saved signed PDF: %s", invocation.output)
        return invocation


def _enforce_signed_input_policy(
    invocation: Invocation,
    pdf: PdfInspection,
) -> None:
    """Refuse signed inputs unless the caller explicitly accepts invalidation risk."""
    if not pdf.has_cryptographic_signatures:
        return
    if not invocation.allow_signed_input:
        raise InputInspectionError(
            "Input PDF contains an existing cryptographic signature. Stamping or "
            "rewriting the PDF may invalidate prior signatures. Refusing to continue; "
            "use --allow-signed-input only if you accept this risk."
        )
    LOGGER.warning(
        "WARNING: Input PDF contains an existing cryptographic signature. Continuing "
        "because --allow-signed-input was provided. Stamping or rewriting may "
        "invalidate prior signatures; no claim is made about the validity of any "
        "previous signature."
    )


def _run_review_l0(
    invocation: Invocation,
    *,
    pdf: PdfInspection | None = None,
    l1_signer: L1Signer | None = None,
) -> PlacementProfile:
    """Run one protected browser session and wait for its completed response."""
    input_profile = (
        load_profile(invocation.coords, auto=False)
        if invocation.coords is not None
        else None
    )
    session = prepare_review_session(
        input_pdf=invocation.input_pdf,
        signature_png=invocation.signature,
        output_pdf=invocation.output,
        input_profile=input_profile,
        default_signature_width=invocation.config["default_signature_width"],
        overwrite=invocation.overwrite,
        l1_signer=l1_signer,
        pdf=pdf,
    )
    app = create_review_app(session, frontend_directory=PACKAGED_FRONTEND)
    server = ReviewServer(
        app,
        host=invocation.config["host"],
        port=invocation.config["port"],
        log_level=invocation.config["general"]["log_level"],
    )

    try:
        with server:
            if invocation.config["open_browser"]:
                try:
                    opened = webbrowser.open(server.url)
                except webbrowser.Error as exc:
                    raise ReviewError(
                        f"Could not open the review browser: {exc}"
                    ) from exc
                if opened:
                    LOGGER.info(
                        "Review session opened in the browser; waiting for Save."
                    )
                else:
                    LOGGER.info(
                        "The browser could not be opened; "
                        "review session is still waiting."
                    )
            else:
                LOGGER.info("Review session started; browser opening is disabled.")
            final_profile = session.wait_for_result()
    except KeyboardInterrupt:
        LOGGER.info("Review interrupted; no profile was emitted.")
        raise

    if final_profile is None:
        raise ReviewError("Review session ended without saving.")
    return final_profile


def _run_automatic_l0(
    invocation: Invocation,
    *,
    pdf: PdfInspection | None = None,
    l1_signer: L1Signer | None = None,
) -> PlacementProfile:
    """Run conservative startup and the shared transactional L0 pipeline."""
    if invocation.coords is None:  # Guard the reusable seam as well as the CLI.
        raise StampingError("Automatic signing requires a placement profile.")

    pdf = inspect_pdf(invocation.input_pdf) if pdf is None else pdf
    signature = inspect_signature_png(invocation.signature)
    profile = load_profile(invocation.coords, auto=True)
    validate_profile_match(profile, pdf)
    stamp_l0(
        invocation.input_pdf,
        invocation.signature,
        invocation.output,
        profile.placements,
        pages=pdf.pages,
        signature=signature,
        overwrite=invocation.overwrite,
        finalize=l1_signer.sign if l1_signer is not None else None,
    )
    return build_final_profile(
        source_sha256=pdf.sha256,
        pages=pdf.pages,
        placements=profile.placements,
        input_profile=profile,
    )


if __name__ == "__main__":
    main()  # pragma: no cover
