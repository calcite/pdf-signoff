"""Integration tests for invisible L1 integrity signing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

import pymupdf
import pytest
from click.testing import CliRunner
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization.pkcs12 import (
    serialize_key_and_certificates,
)
from fastapi.testclient import TestClient
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko.sign.validation.status import SignatureCoverageLevel
from pyhanko_certvalidator import ValidationContext

import pdf_signoff.crypto as crypto_module
from pdf_signoff import cli
from pdf_signoff.crypto import L1Signer, L1SigningError, load_l1_signer
from pdf_signoff.inspection import inspect_pdf
from pdf_signoff.profile import load_profile
from pdf_signoff.server import create_review_app, prepare_review_session

PASSWORD_ENV = "PDF_SIGNOFF_TEST_PKCS12_PASSWORD"
PASSWORD = "test-password-that-must-stay-secret"
REASON = "Test-only internal approval"


@dataclass(frozen=True)
class Credential:
    path: Path
    config: dict[str, object]


@pytest.fixture(scope="module")
def credential(tmp_path_factory: pytest.TempPathFactory) -> Credential:
    directory = tmp_path_factory.mktemp("l1-credential")
    path = directory / "generated-self-signed.p12"
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "L1 test")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    path.write_bytes(
        serialize_key_and_certificates(
            b"pdf-signoff-test",
            key,
            certificate,
            None,
            serialization.BestAvailableEncryption(PASSWORD.encode()),
        )
    )
    return Credential(
        path=path,
        config={
            "pkcs12_path": str(path),
            "password_env": PASSWORD_ENV,
            "reason": REASON,
        },
    )


@pytest.fixture
def signing_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    input_pdf = tmp_path / "input.pdf"
    signature_png = tmp_path / "signature.png"
    profile = tmp_path / "profile.json"
    with pymupdf.open() as document:
        page = document.new_page(width=400, height=600)
        page.draw_rect(page.rect, color=(0, 1, 0), fill=(0, 1, 0))
        page.insert_text((40, 40), "Approval form")
        document.save(input_pdf)
    pixels = bytes((255, 0, 0, 255)) * (40 * 20)
    signature_png.write_bytes(
        pymupdf.Pixmap(pymupdf.csRGB, 40, 20, pixels, True).tobytes("png")
    )
    profile.write_text(
        json.dumps(
            {
                "version": 1,
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
    return input_pdf, signature_png, profile


def _write_config(path: Path, credential_path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "l1": {
                    "pkcs12_path": str(credential_path),
                    "password_env": PASSWORD_ENV,
                    "reason": REASON,
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def _invoke_auto(
    signing_files: tuple[Path, Path, Path],
    output: Path,
    *extra: str,
    env: dict[str, str] | None = None,
):
    input_pdf, signature_png, profile = signing_files
    return CliRunner().invoke(
        cli.main,
        [
            str(input_pdf),
            "--signature",
            str(signature_png),
            "--coords",
            str(profile),
            "--output",
            str(output),
            "--auto",
            *extra,
        ],
        env=env,
    )


def _validate_signature(path: Path):
    with path.open("rb") as stream:
        reader = PdfFileReader(stream)
        assert len(reader.embedded_regular_signatures) == 1
        assert reader.embedded_timestamp_signatures == []
        embedded = reader.embedded_regular_signatures[0]
        status = validate_pdf_signature(
            embedded,
            signer_validation_context=ValidationContext(
                trust_roots=[], allow_fetching=False
            ),
        )
        reason = str(embedded.sig_object["/Reason"])
        rectangle = list(embedded.sig_field["/Rect"])
        byte_range = [int(value) for value in embedded.sig_object["/ByteRange"]]
    return status, reason, rectangle, byte_range


def _render(path: Path) -> bytes:
    with pymupdf.open(path) as document:
        assert document[0].get_images()
        return document[0].get_pixmap(alpha=False).samples


def test_auto_l1_signs_complete_l0_revision_invisibly_and_detects_tampering(
    signing_files: tuple[Path, Path, Path],
    credential: Credential,
    tmp_path: Path,
) -> None:
    config = _write_config(tmp_path / "config.yaml", credential.path)
    l0_output = tmp_path / "l0.pdf"
    l1_output = tmp_path / "l1.pdf"

    l0_result = _invoke_auto(signing_files, l0_output)
    l1_result = _invoke_auto(
        signing_files,
        l1_output,
        "--level",
        "l1",
        "--config",
        str(config),
        env={PASSWORD_ENV: PASSWORD},
    )

    assert l0_result.exit_code == 0
    assert l1_result.exit_code == 0
    assert json.loads(l1_result.stdout) == json.loads(l0_result.stdout)
    status, reason, rectangle, byte_range = _validate_signature(l1_output)
    assert status.intact
    assert status.valid
    assert not status.trusted
    assert not status.bottom_line
    assert status.coverage == SignatureCoverageLevel.ENTIRE_FILE
    assert reason == REASON
    assert rectangle == [0, 0, 0, 0]
    assert _render(l1_output) == _render(l0_output)

    tampered = tmp_path / "tampered.pdf"
    signed_bytes = bytearray(l1_output.read_bytes())
    first_signed_section_end = byte_range[1]
    producer_offset = signed_bytes.index(b"MuPDF", 0, first_signed_section_end)
    signed_bytes[producer_offset] = ord("m")
    tampered.write_bytes(signed_bytes)
    tampered_status, _reason, _rectangle, _byte_range = _validate_signature(tampered)
    assert not tampered_status.intact
    assert not tampered_status.bottom_line


def test_review_l1_uses_the_same_transactional_integrity_stage(
    signing_files: tuple[Path, Path, Path],
    credential: Credential,
    tmp_path: Path,
) -> None:
    input_pdf, signature_png, _profile = signing_files
    output = tmp_path / "review-l1.pdf"
    signer = load_l1_signer(
        credential.config,
        environ={PASSWORD_ENV: PASSWORD},
    )
    session = prepare_review_session(
        input_pdf=input_pdf,
        signature_png=signature_png,
        output_pdf=output,
        l1_signer=signer,
    )
    client = TestClient(create_review_app(session))

    response = client.post(
        "/api/save",
        json={
            "placements": [
                {"page": 1, "x": 0.25, "y": 0.25, "width": 0.5, "height": 1 / 6}
            ]
        },
        headers={"Authorization": f"Bearer {session.token}"},
    )

    assert response.status_code == 200
    assert session.wait_for_result(timeout=0) is not None
    status, reason, rectangle, _byte_range = _validate_signature(output)
    assert status.intact and status.valid and not status.trusted
    assert reason == REASON
    assert rectangle == [0, 0, 0, 0]
    assert _render(output)


@pytest.mark.parametrize("mode", ["auto", "review"])
@pytest.mark.parametrize("level", ["l0", "l1"])
def test_signed_input_requires_expert_override_in_every_supported_mode(
    signing_files: tuple[Path, Path, Path],
    credential: Credential,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    level: str,
) -> None:
    input_pdf, signature_png, profile_path = signing_files
    output = tmp_path / f"{mode}-{level}.pdf"
    signer = load_l1_signer(credential.config, environ={PASSWORD_ENV: PASSWORD})
    signer.sign(input_pdf)
    assert inspect_pdf(input_pdf).has_cryptographic_signatures

    review_calls = 0

    def run_review_without_browser(
        invocation: cli.Invocation,
        *,
        pdf=None,
        l1_signer=None,
    ):
        nonlocal review_calls
        review_calls += 1
        profile = load_profile(profile_path, auto=False)
        session = prepare_review_session(
            input_pdf=invocation.input_pdf,
            signature_png=invocation.signature,
            output_pdf=invocation.output,
            input_profile=profile,
            default_signature_width=invocation.config["default_signature_width"],
            overwrite=invocation.overwrite,
            l1_signer=l1_signer,
            pdf=pdf,
        )
        result = session.save(profile.placements)
        session.finish_save(result)
        return result

    if mode == "review":
        monkeypatch.setattr(cli, "_run_review_l0", run_review_without_browser)

    config = _write_config(tmp_path / "config.yaml", credential.path)
    args = [
        str(input_pdf),
        "--signature",
        str(signature_png),
        "--coords",
        str(profile_path),
        "--output",
        str(output),
        f"--{mode}",
        "--level",
        level,
    ]
    if level == "l1":
        args.extend(("--config", str(config)))

    runner = CliRunner()
    refused = runner.invoke(cli.main, args, env={PASSWORD_ENV: PASSWORD})

    assert refused.exit_code == 1
    assert refused.stdout == ""
    assert "existing cryptographic signature" in refused.stderr
    assert "may invalidate prior signatures" in refused.stderr
    assert "--allow-signed-input" in refused.stderr
    assert not output.exists()
    assert not list(tmp_path.glob(f".{output.name}.*.tmp"))
    assert review_calls == 0

    allowed = runner.invoke(
        cli.main,
        [*args, "--allow-signed-input"],
        env={PASSWORD_ENV: PASSWORD},
    )

    assert allowed.exit_code == 0
    assert json.loads(allowed.stdout)["version"] == 1
    assert allowed.stderr.startswith("WARNING: ")
    assert "may invalidate prior signatures" in allowed.stderr
    assert "no claim is made about the validity" in allowed.stderr
    assert "remains valid" not in allowed.stderr
    assert allowed.stderr.endswith(f"Saved signed PDF: {output}\n")
    assert output.is_file()
    assert review_calls == (1 if mode == "review" else 0)


def test_malformed_filled_signature_dictionary_is_still_detected(
    signing_files: tuple[Path, Path, Path],
    credential: Credential,
) -> None:
    input_pdf, _signature_png, _profile = signing_files
    signer = load_l1_signer(credential.config, environ={PASSWORD_ENV: PASSWORD})
    signer.sign(input_pdf)
    signed_bytes = input_pdf.read_bytes()
    assert b"/ByteRange" in signed_bytes
    input_pdf.write_bytes(signed_bytes.replace(b"/ByteRange", b"/ByteRangX", 1))

    assert inspect_pdf(input_pdf).has_cryptographic_signatures


def test_password_environment_takes_precedence_over_secure_tty_prompt(
    credential: Credential,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        crypto_module.getpass,
        "getpass",
        lambda _prompt: pytest.fail("password prompt should not run"),
    )

    signer = load_l1_signer(
        credential.config,
        environ={PASSWORD_ENV: PASSWORD},
        input_stream=StringIO(),
    )

    assert isinstance(signer, L1Signer)
    assert PASSWORD not in repr(signer)


def test_missing_password_uses_secure_prompt_only_for_a_tty(
    credential: Credential,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class TtyInput(StringIO):
        def isatty(self) -> bool:
            return True

    prompts: list[str] = []

    def prompt(message: str) -> str:
        prompts.append(message)
        return PASSWORD

    monkeypatch.setattr(crypto_module.getpass, "getpass", prompt)
    signer = load_l1_signer(
        credential.config,
        environ={},
        input_stream=TtyInput(),
    )

    assert isinstance(signer, L1Signer)
    assert prompts == ["PKCS#12 password: "]
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


def test_missing_password_without_tty_is_a_sanitized_failure(
    credential: Credential,
) -> None:
    with pytest.raises(L1SigningError, match="password is unavailable") as raised:
        load_l1_signer(
            credential.config,
            environ={},
            input_stream=StringIO(),
        )

    assert PASSWORD_ENV not in str(raised.value)
    assert str(credential.path) not in str(raised.value)


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ({}, "configuration is incomplete"),
        (
            {"pkcs12_path": "", "password_env": "PASSWORD", "reason": "reason"},
            "credential is not configured",
        ),
        (
            {
                "pkcs12_path": "key.pem",
                "password_env": "PASSWORD",
                "reason": "reason",
            },
            "must be a PKCS#12",
        ),
        (
            {"pkcs12_path": "key.p12", "password_env": "", "reason": "reason"},
            "environment variable is not configured",
        ),
        (
            {"pkcs12_path": "key.p12", "password_env": "PASSWORD", "reason": 1},
            "reason is invalid",
        ),
    ],
)
def test_invalid_signer_configuration_is_rejected_without_sensitive_details(
    config: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(L1SigningError, match=message):
        load_l1_signer(config, environ={"PASSWORD": PASSWORD})


def test_unreadable_and_invalid_credentials_have_fixed_secret_safe_errors(
    credential: Credential,
    tmp_path: Path,
) -> None:
    missing = {**credential.config, "pkcs12_path": str(tmp_path / "private.p12")}
    with pytest.raises(L1SigningError, match="could not be read") as unreadable:
        load_l1_signer(missing, environ={PASSWORD_ENV: PASSWORD})
    with pytest.raises(L1SigningError, match="could not be loaded") as invalid:
        load_l1_signer(credential.config, environ={PASSWORD_ENV: "wrong-secret"})

    messages = f"{unreadable.value} {invalid.value}"
    assert str(credential.path) not in messages
    assert PASSWORD not in messages
    assert "wrong-secret" not in messages


def test_cli_credential_failures_emit_no_profile_and_commit_no_output(
    signing_files: tuple[Path, Path, Path],
    credential: Credential,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    output = tmp_path / "protected.pdf"
    output.write_bytes(b"existing output")
    invalid_bundle = tmp_path / "sensitive-private-bundle.pfx"
    invalid_bundle.write_bytes(b"not a credential")
    config = _write_config(tmp_path / "invalid.yaml", invalid_bundle)

    result = _invoke_auto(
        signing_files,
        output,
        "--level",
        "l1",
        "--config",
        str(config),
        "--general--log-level",
        "DEBUG",
        "--overwrite",
        env={PASSWORD_ENV: PASSWORD},
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "could not be loaded" in result.stderr
    assert PASSWORD not in result.stderr
    assert str(invalid_bundle) not in result.stderr
    assert str(credential.path) not in result.stderr
    assert PASSWORD not in caplog.text
    assert str(invalid_bundle) not in caplog.text
    assert output.read_bytes() == b"existing output"
    assert not list(tmp_path.glob(".protected.pdf.*.tmp"))


def test_missing_cli_credential_fails_before_output_or_profile(
    signing_files: tuple[Path, Path, Path],
    tmp_path: Path,
) -> None:
    output = tmp_path / "missing.pdf"

    result = _invoke_auto(
        signing_files,
        output,
        "--level",
        "l1",
        "--general--log-level",
        "DEBUG",
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "credential is not configured" in result.stderr
    assert not output.exists()
    assert not list(tmp_path.glob(".missing.pdf.*.tmp"))


def test_post_stamp_signing_failure_rolls_back_cli_output_and_is_sanitized(
    signing_files: tuple[Path, Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "rollback.pdf"
    private_detail = "private key operation leaked"

    class FailingSigner:
        def sign(self, _path: Path) -> None:
            try:
                raise RuntimeError(private_detail)
            except RuntimeError as exc:
                raise L1SigningError("Cryptographic PDF signing failed.") from exc

    monkeypatch.setattr(cli, "load_l1_signer", lambda _config: FailingSigner())
    result = _invoke_auto(
        signing_files,
        output,
        "--level",
        "l1",
        "--general--log-level",
        "DEBUG",
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr.endswith("Error: Cryptographic PDF signing failed.\n")
    assert private_detail not in result.stderr
    assert not output.exists()
    assert not list(tmp_path.glob(".rollback.pdf.*.tmp"))


def test_l1_signer_translates_pyhanko_failures_without_file_or_key_details(
    credential: Credential,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    signer = load_l1_signer(credential.config, environ={PASSWORD_ENV: PASSWORD})
    invalid_pdf = tmp_path / "sensitive-document-name.pdf"
    invalid_pdf.write_bytes(b"not a PDF")

    with pytest.raises(L1SigningError) as raised:
        signer.sign(invalid_pdf)

    assert str(raised.value) == "Cryptographic PDF signing failed."
    assert str(invalid_pdf) not in str(raised.value)
    assert str(invalid_pdf) not in caplog.text
    assert PASSWORD not in caplog.text
