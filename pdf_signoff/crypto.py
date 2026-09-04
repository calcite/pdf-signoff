"""Secret-safe cryptographic PDF signing boundary."""

from __future__ import annotations

import getpass
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign.fields import SigFieldSpec, enumerate_sig_fields
from pyhanko.sign.signers import PdfSignatureMetadata, PdfSigner, SimpleSigner

SIGNATURE_FIELD_NAME = "PdfSignoffIntegrity"


class L1SigningError(Exception):
    """L1 credentials could not be loaded or the PDF could not be signed."""


@dataclass(frozen=True, repr=False)
class L1Signer:
    """Loaded private signer and non-secret signature metadata."""

    signer: SimpleSigner
    reason: str

    def sign(self, pdf_path: Path) -> None:
        """Add an invisible approval signature to the complete current revision."""
        try:
            with pdf_path.open("r+b") as stream:
                writer = IncrementalPdfFileWriter(stream)
                existing_names = {
                    str(field_name)
                    for field_name, _value, _reference in enumerate_sig_fields(writer)
                }
                field_name = SIGNATURE_FIELD_NAME
                suffix = 2
                while field_name in existing_names:
                    field_name = f"{SIGNATURE_FIELD_NAME}{suffix}"
                    suffix += 1
                PdfSigner(
                    PdfSignatureMetadata(
                        field_name=field_name,
                        reason=self.reason,
                    ),
                    signer=self.signer,
                    new_field_spec=SigFieldSpec(
                        sig_field_name=field_name,
                        box=None,
                    ),
                ).sign_pdf(writer, in_place=True)
        except Exception as exc:
            raise L1SigningError("Cryptographic PDF signing failed.") from exc


def load_l1_signer(
    config: Mapping[str, object],
    *,
    environ: Mapping[str, str] | None = None,
    input_stream: TextIO | None = None,
) -> L1Signer:
    """Load configured PKCS#12 credentials without exposing sensitive details."""
    try:
        configured_path = config["pkcs12_path"]
        password_env = config["password_env"]
        reason = config["reason"]
    except KeyError as exc:
        raise L1SigningError("L1 signer configuration is incomplete.") from exc

    if not isinstance(configured_path, str) or not configured_path:
        raise L1SigningError("L1 PKCS#12 credential is not configured.")
    if Path(configured_path).suffix.lower() not in {".p12", ".pfx"}:
        raise L1SigningError("L1 credential must be a PKCS#12 .p12 or .pfx file.")
    if not isinstance(password_env, str) or not password_env:
        raise L1SigningError("L1 password environment variable is not configured.")
    if not isinstance(reason, str):
        raise L1SigningError("L1 signature reason is invalid.")

    environment = os.environ if environ is None else environ
    if password_env in environment:
        password = environment[password_env]
    elif (sys.stdin if input_stream is None else input_stream).isatty():
        password = getpass.getpass("PKCS#12 password: ")
    else:
        raise L1SigningError(
            "L1 credential password is unavailable; set the configured "
            "environment variable or run interactively."
        )

    try:
        pkcs12_data = Path(configured_path).read_bytes()
    except OSError as exc:
        raise L1SigningError("L1 PKCS#12 credential could not be read.") from exc

    try:
        signer = SimpleSigner.load_pkcs12_data(
            pkcs12_data,
            other_certs=[],
            passphrase=password.encode("utf-8"),
        )
    except Exception as exc:
        raise L1SigningError(
            "L1 PKCS#12 credential could not be loaded; verify the credential "
            "and password."
        ) from exc
    return L1Signer(signer=signer, reason=reason)
