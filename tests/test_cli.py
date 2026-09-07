"""Tests for the Click command contract."""

import json
from hashlib import sha256
from importlib.metadata import entry_points, version
from pathlib import Path

import pymupdf
import pytest
from click.testing import CliRunner

from pdf_signoff import cli
from pdf_signoff.inspection import inspect_pdf
from pdf_signoff.profile import PlacementProfile
from pdf_signoff.stamping import StampingError


@pytest.fixture
def signing_paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    input_pdf = tmp_path / "input.pdf"
    signature = tmp_path / "signature.png"
    coords = tmp_path / "coords.json"
    with pymupdf.open() as document:
        document.new_page(width=400, height=600)
        document.save(input_pdf)
    signature.touch()
    coords.touch()
    return input_pdf, signature, coords


@pytest.fixture(autouse=True)
def stub_review_execution(monkeypatch: pytest.MonkeyPatch) -> PlacementProfile:
    profile = PlacementProfile.model_validate(
        {
            "version": 1,
            "match": {
                "page_count": 1,
                "pages": [
                    {"page": 1, "width_pt": 400, "height_pt": 600, "rotation": 0}
                ],
            },
            "placements": [
                {"page": 1, "x": 0.25, "y": 0.25, "width": 0.5, "height": 0.25}
            ],
        }
    )
    monkeypatch.setattr(
        cli,
        "_run_review_l0",
        lambda _invocation, *, pdf=None, l1_signer=None: profile,
    )
    return profile


@pytest.fixture
def automatic_signing_paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    input_pdf = tmp_path / "input.pdf"
    signature = tmp_path / "signature.png"
    coords = tmp_path / "coords.json"
    with pymupdf.open() as document:
        page = document.new_page(width=400, height=600)
        page.insert_text((50, 50), "Approval form")
        document.save(input_pdf)
    pixels = bytes((255, 0, 0, 255)) * (40 * 20)
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, 40, 20, pixels, True)
    signature.write_bytes(pixmap.tobytes("png"))
    coords.write_text(
        json.dumps(
            {
                "version": 1,
                "created_from": {"sha256": "stale"},
                "match": {
                    "page_count": 1,
                    "pages": [
                        {
                            "page": 1,
                            "width_pt": 400,
                            "height_pt": 600,
                            "rotation": 0,
                        }
                    ],
                    "required_text": [{"page": 1, "text": "Approval form"}],
                },
                "placements": [
                    {
                        "page": 1,
                        "x": 0.25,
                        "y": 0.25,
                        "width": 0.5,
                        "height": 1 / 6,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return input_pdf, signature, coords


def invoke_validated(
    runner: CliRunner,
    signing_paths: tuple[Path, Path, Path],
    *extra_args: str,
    standalone_mode: bool = False,
):
    input_pdf, signature, _coords = signing_paths
    return runner.invoke(
        cli.main,
        [str(input_pdf), "--signature", str(signature), *extra_args],
        standalone_mode=standalone_mode,
    )


def test_console_script_is_named_pdf_signoff() -> None:
    scripts = entry_points(group="console_scripts", name="pdf-signoff")

    assert len(scripts) == 1
    assert next(iter(scripts)).value == "pdf_signoff.cli:main"


def test_version_uses_installed_package_metadata_without_signing_arguments() -> None:
    result = CliRunner().invoke(cli.main, ["--version"], prog_name="pdf-signoff")

    assert result.exit_code == 0
    assert result.stdout == f"pdf-signoff, version {version('pdf-signoff')}\n"


def test_command_accepts_full_contract_and_returns_handoff(
    signing_paths: tuple[Path, Path, Path],
    stub_review_execution: PlacementProfile,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_pdf, signature, coords = signing_paths
    output = input_pdf.with_name("output.pdf")
    signer = object()
    monkeypatch.setattr(cli, "load_l1_signer", lambda _config: signer)
    monkeypatch.setattr(
        cli,
        "_run_automatic_l0",
        lambda _invocation, *, pdf=None, l1_signer=None: stub_review_execution,
    )

    result = invoke_validated(
        CliRunner(),
        signing_paths,
        "--coords",
        str(coords),
        "--output",
        str(output),
        "--auto",
        "--level",
        "l1",
        "--overwrite",
        "--allow-signed-input",
    )

    assert result.exit_code == 0
    assert result.stdout == cli.serialize_profile(stub_review_execution) + "\n"
    assert result.stderr == f"Saved signed PDF: {output}\n"
    assert result.return_value == cli.Invocation(
        input_pdf=input_pdf,
        signature=signature,
        coords=coords,
        output=output,
        mode="auto",
        level="l1",
        overwrite=True,
        allow_signed_input=True,
        config=result.return_value.config,
    )


def test_review_is_default_and_level_comes_from_config(
    signing_paths: tuple[Path, Path, Path],
    stub_review_execution: PlacementProfile,
) -> None:
    result = invoke_validated(CliRunner(), signing_paths)

    assert result.exit_code == 0
    assert result.return_value.mode == "review"
    assert result.return_value.level == "l0"
    assert result.return_value.output == signing_paths[0].with_name("input_signed.pdf")
    assert result.stdout == cli.serialize_profile(stub_review_execution) + "\n"
    assert result.stderr == f"Saved signed PDF: {result.return_value.output}\n"


def test_configured_output_suffix_is_resolved_by_cli(
    signing_paths: tuple[Path, Path, Path],
) -> None:
    result = invoke_validated(
        CliRunner(), signing_paths, "--output-suffix", "_approved"
    )

    assert result.exit_code == 0
    assert result.return_value.output == signing_paths[0].with_name(
        "input_approved.pdf"
    )


def test_cli_rejects_existing_resolved_output(
    signing_paths: tuple[Path, Path, Path],
) -> None:
    output = signing_paths[0].with_name("input_signed.pdf")
    output.write_bytes(b"existing")

    result = invoke_validated(CliRunner(), signing_paths, standalone_mode=True)

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Output already exists" in result.stderr


@pytest.mark.parametrize(
    ("extra_args", "message"),
    [
        (("--review", "--auto"), "--review and --auto are mutually exclusive"),
        (("--auto",), "--auto requires --coords"),
    ],
)
def test_command_rejects_invalid_modes(
    signing_paths: tuple[Path, Path, Path],
    extra_args: tuple[str, ...],
    message: str,
) -> None:
    result = invoke_validated(
        CliRunner(), signing_paths, *extra_args, standalone_mode=True
    )

    assert result.exit_code == 2
    assert result.stdout == ""
    assert message in result.stderr


def test_explicit_review_accepts_optional_coords(
    signing_paths: tuple[Path, Path, Path],
) -> None:
    coords = signing_paths[2]

    result = invoke_validated(
        CliRunner(), signing_paths, "--review", "--coords", str(coords)
    )

    assert result.exit_code == 0
    assert result.return_value.mode == "review"
    assert result.return_value.coords == coords


def test_required_paths_are_enforced(tmp_path: Path) -> None:
    input_pdf = tmp_path / "input.pdf"
    input_pdf.touch()
    runner = CliRunner()

    missing_signature = runner.invoke(cli.main, [str(input_pdf)])
    missing_input = runner.invoke(cli.main, ["--signature", str(input_pdf)])

    assert missing_signature.exit_code == 2
    assert missing_signature.stdout == ""
    assert "Missing option '--signature'" in missing_signature.stderr
    assert missing_input.exit_code == 2
    assert missing_input.stdout == ""
    assert "Missing argument 'INPUT_PDF'" in missing_input.stderr


def test_configured_log_level_changes_stderr_without_changing_stdout(
    signing_paths: tuple[Path, Path, Path],
    stub_review_execution: PlacementProfile,
) -> None:
    assert cli.main.context_settings["ignore_unknown_options"] is True
    assert cli.main.context_settings["allow_extra_args"] is True

    debug = invoke_validated(
        CliRunner(), signing_paths, "--general--log-level", "DEBUG"
    )
    warning = invoke_validated(
        CliRunner(), signing_paths, "--general--log-level", "WARNING"
    )

    expected_stdout = cli.serialize_profile(stub_review_execution) + "\n"
    assert debug.exit_code == warning.exit_code == 0
    assert debug.stdout == warning.stdout == expected_stdout
    assert debug.stderr == (
        "Signing request configured for review mode at level L0.\n"
        f"Saved signed PDF: {debug.return_value.output}\n"
    )
    assert warning.stderr == ""


@pytest.mark.parametrize("option", ["--no-such-flag", "--autoo"])
def test_command_rejects_unrecognized_options(
    signing_paths: tuple[Path, Path, Path],
    option: str,
) -> None:
    result = invoke_validated(CliRunner(), signing_paths, option, standalone_mode=True)

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "Usage:" in result.stderr
    assert f"Unrecognized option: {option}" in result.stderr


def test_unknown_options_are_rejected_before_output_or_pdf_processing(
    signing_paths: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(*_args, **_kwargs):
        pytest.fail("output resolution or PDF inspection ran")

    monkeypatch.setattr(cli, "resolve_output_path", fail_if_called)
    monkeypatch.setattr(cli, "inspect_pdf", fail_if_called)

    result = invoke_validated(
        CliRunner(), signing_paths, "--autoo", standalone_mode=True
    )

    assert result.exit_code == 2
    assert "Unrecognized option: --autoo" in result.stderr


@pytest.mark.parametrize(
    "args",
    [
        ("--level", "INVALID"),
        ("--default-level", "INVALID"),
        ("--port", "-1"),
    ],
)
def test_command_rejects_invalid_level_or_configuration(
    signing_paths: tuple[Path, Path, Path],
    args: tuple[str, str],
) -> None:
    result = invoke_validated(CliRunner(), signing_paths, *args, standalone_mode=True)

    assert result.exit_code != 0
    assert result.stdout == ""
    assert "invalid" in result.stderr.lower()


def test_command_help_documents_contract_and_configuration() -> None:
    result = CliRunner().invoke(cli.main, ["--help"])

    assert result.exit_code == 0
    assert "run visual or integrity signing" in result.output
    for option in (
        "--signature",
        "--coords",
        "--output",
        "--review",
        "--auto",
        "--level",
        "--overwrite",
        "--allow-signed-input",
        "--config",
        "--get-config-template",
    ):
        assert option in result.output
    assert "PDF_SIGNOFF__SECTION__KEY" in result.output
    assert "--general--log-level DEBUG" in result.output


def test_bundled_config_exists() -> None:
    assert Path(cli.DEFAULT_CONFIG_FILE).is_file()


def test_config_template_generation_needs_no_signing_arguments() -> None:
    result = CliRunner().invoke(cli.main, ["--get-config-template", "-"])

    assert result.exit_code == 0
    assert "default_level: l0" in result.output
    assert "port: 0" in result.output
    assert "pkcs12_path: ''" in result.output
    assert "password_env: PDF_SIGN_PKCS12_PASSWORD" in result.output
    assert "reason: Internal document approval" in result.output
    assert "oc_schema" not in result.output


def test_automatic_l0_emits_one_refreshed_profile_after_transactional_save(
    automatic_signing_paths: tuple[Path, Path, Path],
) -> None:
    input_pdf, signature, coords = automatic_signing_paths
    input_hash = sha256(input_pdf.read_bytes()).hexdigest()

    result = CliRunner().invoke(
        cli.main,
        [
            str(input_pdf),
            "--signature",
            str(signature),
            "--coords",
            str(coords),
            "--auto",
        ],
    )

    assert result.exit_code == 0
    decoder = json.JSONDecoder()
    profile_data, end = decoder.raw_decode(result.stdout)
    assert result.stdout[end:] == "\n"
    final_profile = PlacementProfile.model_validate(profile_data)
    output_pdf = input_pdf.with_name("input_signed.pdf")
    inspected = inspect_pdf(input_pdf)
    assert final_profile.created_from is not None
    assert final_profile.created_from.sha256 == input_hash
    assert final_profile.match.pages == list(inspected.pages)
    assert final_profile.match.required_text is not None
    assert final_profile.match.required_text[0].text == "Approval form"
    assert final_profile.placements[0].width == 0.5
    assert result.stderr == f"Saved signed PDF: {output_pdf}\n"
    assert output_pdf.is_file()
    assert sha256(input_pdf.read_bytes()).hexdigest() == input_hash
    with pymupdf.open(output_pdf) as document:
        assert document[0].get_images()


@pytest.mark.parametrize("failure", ["mismatch", "aspect"])
def test_automatic_l0_failure_has_empty_stdout_and_no_artifacts(
    automatic_signing_paths: tuple[Path, Path, Path],
    failure: str,
) -> None:
    input_pdf, signature, coords = automatic_signing_paths
    profile_data = json.loads(coords.read_text(encoding="utf-8"))
    if failure == "mismatch":
        profile_data["match"]["pages"][0]["rotation"] = 180
    else:
        profile_data["placements"][0]["height"] = 0.3
    coords.write_text(json.dumps(profile_data), encoding="utf-8")
    input_hash = sha256(input_pdf.read_bytes()).hexdigest()

    result = CliRunner().invoke(
        cli.main,
        [
            str(input_pdf),
            "--signature",
            str(signature),
            "--coords",
            str(coords),
            "--auto",
        ],
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr.startswith("Error: ")
    assert sha256(input_pdf.read_bytes()).hexdigest() == input_hash
    assert not input_pdf.with_name("input_signed.pdf").exists()
    assert not list(input_pdf.parent.glob(".input_signed.pdf.*.tmp"))


def test_automatic_l0_rejects_placement_on_page_without_match_metadata(
    automatic_signing_paths: tuple[Path, Path, Path],
) -> None:
    input_pdf, signature, coords = automatic_signing_paths
    with pymupdf.open(input_pdf) as document:
        document.new_page(width=600, height=400)
        document.saveIncr()
    profile_data = json.loads(coords.read_text(encoding="utf-8"))
    profile_data["match"]["page_count"] = 2
    profile_data["placements"][0]["page"] = 2
    coords.write_text(json.dumps(profile_data), encoding="utf-8")
    input_hash = sha256(input_pdf.read_bytes()).hexdigest()

    result = CliRunner().invoke(
        cli.main,
        [
            str(input_pdf),
            "--signature",
            str(signature),
            "--coords",
            str(coords),
            "--auto",
        ],
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "match.pages is missing metadata for page(s): 2" in result.stderr
    assert sha256(input_pdf.read_bytes()).hexdigest() == input_hash
    assert not input_pdf.with_name("input_signed.pdf").exists()
    assert not list(input_pdf.parent.glob(".input_signed.pdf.*.tmp"))


def test_automatic_l0_reusable_seam_requires_profile_path(
    signing_paths: tuple[Path, Path, Path],
) -> None:
    input_pdf, signature, _coords = signing_paths
    invocation = cli.Invocation(
        input_pdf=input_pdf,
        signature=signature,
        coords=None,
        output=input_pdf.with_name("output.pdf"),
        mode="auto",
        level="l0",
        overwrite=False,
        allow_signed_input=False,
        config={},
    )

    with pytest.raises(StampingError, match="requires a placement profile"):
        cli._run_automatic_l0(invocation)


def test_invalid_profile_becomes_a_clean_cli_failure(
    automatic_signing_paths: tuple[Path, Path, Path],
) -> None:
    input_pdf, signature, coords = automatic_signing_paths
    coords.write_text("{}", encoding="utf-8")
    result = CliRunner().invoke(
        cli.main,
        [
            str(input_pdf),
            "--signature",
            str(signature),
            "--coords",
            str(coords),
            "--auto",
        ],
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr.startswith("Error: ")
