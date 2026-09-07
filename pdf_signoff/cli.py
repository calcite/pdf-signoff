"""Click entry point and Onacol configuration bootstrap."""

import webbrowser
from collections.abc import Mapping
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
    }
)
@click.argument(
    "input_pdf",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--signature",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Signature PNG path.",
)
@click.option(
    "--coords",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Optional placement-profile JSON path.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Explicit output PDF path.",
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
    help="Allow replacement of an existing output file.",
)
@click.option(
    "--allow-signed-input",
    is_flag=True,
    help="Expert override to modify a PDF with cryptographic signatures.",
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
    help="Write a schema-free YAML configuration template and exit.",
)
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
    """Validate a PDF signing invocation and run visual or integrity signing.

    Configuration precedence, lowest to highest: bundled defaults, an explicit
    or discovered user YAML, PDF_SIGNOFF__SECTION__KEY environment variables,
    then nested CLI options such as --general--log-level DEBUG.
    """
    try:
        config_manager = load_config(config, ctx.args)
    except CliConfigArgumentError as exc:
        raise click.UsageError(str(exc)) from exc
    except (OnacolException, OSError) as exc:
        raise click.ClickException(f"Configuration validation failed: {exc}") from exc

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
    click.echo(f"Saved signed PDF: {invocation.output}", err=True)
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
    click.echo(
        "WARNING: Input PDF contains an existing cryptographic signature. Continuing "
        "because --allow-signed-input was provided. Stamping or rewriting may "
        "invalidate prior signatures; no claim is made about the validity of any "
        "previous signature.",
        err=True,
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
                    click.echo(
                        "Review session opened in the browser; waiting for Save.",
                        err=True,
                    )
                else:
                    click.echo(
                        "The browser could not be opened; "
                        "review session is still waiting.",
                        err=True,
                    )
            else:
                click.echo(
                    "Review session started; browser opening is disabled.", err=True
                )
            final_profile = session.wait_for_result()
    except KeyboardInterrupt:
        click.echo("Review interrupted; no profile was emitted.", err=True)
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
