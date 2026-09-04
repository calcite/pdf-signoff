"""Exercise release workflows using only an installed wheel environment."""

from __future__ import annotations

import http.cookiejar
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit

import pymupdf
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization.pkcs12 import (
    serialize_key_and_certificates,
)
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext

cli = Path(sys.argv[1]).resolve()
directory = Path(sys.argv[2]).resolve()
directory.mkdir(parents=True)
input_pdf = directory / "input.pdf"
signature = directory / "signature.png"
profile = directory / "profile.json"
capture = directory / "browser-url.txt"
auto_output = directory / "auto.pdf"
review_output = directory / "review.pdf"
l1_output = directory / "l1.pdf"
override_output = directory / "signed-input-override.pdf"

with pymupdf.open() as document:
    page = document.new_page(width=600, height=800)
    page.insert_text((50, 60), "Installed wheel approval form")
    document.save(input_pdf)

pixels = bytes((23, 75, 180, 255)) * (120 * 30)
signature.write_bytes(
    pymupdf.Pixmap(pymupdf.csRGB, 120, 30, pixels, True).tobytes("png")
)
placement = {
    "page": 1,
    "x": 0.2,
    "y": 0.25,
    "width": 0.24,
    "height": 0.045,
}
profile.write_text(
    json.dumps(
        {
            "version": 1,
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
                "required_text": [{"page": 1, "text": "Installed wheel approval form"}],
            },
            "placements": [placement],
        }
    ),
    encoding="utf-8",
)

environment = {
    **os.environ,
    "HOME": str(directory / "home"),
    "PATH": str(cli.parent),
    "XDG_CONFIG_HOME": str(directory / "xdg"),
}
assert shutil.which("node", path=environment["PATH"]) is None

automatic = subprocess.run(
    [
        cli,
        input_pdf,
        "--signature",
        signature,
        "--coords",
        profile,
        "--output",
        auto_output,
        "--auto",
    ],
    cwd=directory,
    env=environment,
    text=True,
    capture_output=True,
    check=True,
)
assert json.loads(automatic.stdout)["placements"] == [placement]
assert automatic.stderr == f"Saved signed PDF: {auto_output}\n"

original_auto = auto_output.read_bytes()
refused_overwrite = subprocess.run(
    [
        cli,
        input_pdf,
        "--signature",
        signature,
        "--coords",
        profile,
        "--output",
        auto_output,
        "--auto",
    ],
    cwd=directory,
    env=environment,
    text=True,
    capture_output=True,
)
assert refused_overwrite.returncode == 1
assert refused_overwrite.stdout == ""
assert "Output already exists" in refused_overwrite.stderr
assert auto_output.read_bytes() == original_auto

approved_overwrite = subprocess.run(
    [
        cli,
        input_pdf,
        "--signature",
        signature,
        "--coords",
        profile,
        "--output",
        auto_output,
        "--auto",
        "--overwrite",
    ],
    cwd=directory,
    env=environment,
    text=True,
    capture_output=True,
    check=True,
)
assert json.loads(approved_overwrite.stdout)["placements"] == [placement]
assert approved_overwrite.stderr == f"Saved signed PDF: {auto_output}\n"

capture_script = Path(__file__).with_name("browser_capture.py").resolve()
environment["PDF_SIGNOFF_BROWSER_CAPTURE"] = str(capture)
environment["BROWSER"] = f'"{sys.executable}" "{capture_script}" %s'
review = subprocess.Popen(
    [
        cli,
        input_pdf,
        "--signature",
        signature,
        "--coords",
        profile,
        "--output",
        review_output,
    ],
    cwd=directory,
    env=environment,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
deadline = time.monotonic() + 10
while not capture.is_file():
    if review.poll() is not None:
        stdout, stderr = review.communicate()
        raise RuntimeError(
            f"review exited before browser launch: {stdout!r} {stderr!r}"
        )
    if time.monotonic() >= deadline:
        review.kill()
        raise RuntimeError("review browser launch timed out")
    time.sleep(0.02)

review_url = capture.read_text(encoding="utf-8")
parsed_review_url = urlsplit(review_url)
assert parsed_review_url.scheme == "http"
assert parsed_review_url.hostname == "127.0.0.1"
review_origin = f"{parsed_review_url.scheme}://{parsed_review_url.netloc}"

try:
    urllib.request.urlopen(f"{review_origin}/api/session", timeout=5)
except HTTPError as error:
    assert error.code == 401
else:
    raise AssertionError("review API accepted a request without session credentials")

opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
)
with opener.open(review_url, timeout=5) as response:
    assert response.status == 200

cross_origin = urllib.request.Request(
    f"{review_origin}/api/session",
    headers={"Origin": "https://unrelated.example"},
)
try:
    opener.open(cross_origin, timeout=5)
except HTTPError as error:
    assert error.code == 403
else:
    raise AssertionError("review API accepted an unrelated browser origin")

try:
    opener.open(f"{review_origin}/api/files?path=/etc/passwd", timeout=5)
except HTTPError as error:
    assert error.code == 404
else:
    raise AssertionError("review API exposed an unexpected generic file route")

request = urllib.request.Request(
    f"{review_origin}/api/save",
    data=json.dumps({"placements": [placement]}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with opener.open(request, timeout=10) as response:
    assert json.load(response) == {"ok": True}

stdout, stderr = review.communicate(timeout=10)
assert review.returncode == 0
assert json.loads(stdout)["placements"] == [placement]
assert "Review session opened in the browser" in stderr
assert stderr.endswith(f"Saved signed PDF: {review_output}\n")
assert parsed_review_url.query.split("token=", 1)[1] not in stderr
for output in (auto_output, review_output):
    with pymupdf.open(output) as document:
        assert len(document[0].get_images()) == 1

password = "isolated-wheel-test-password"
password_env = "PDF_SIGNOFF_WHEEL_SMOKE_PKCS12_PASSWORD"
credential = directory / "integrity.p12"
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "Wheel smoke signer")])
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
credential.write_bytes(
    serialize_key_and_certificates(
        b"pdf-signoff-wheel-smoke",
        key,
        certificate,
        None,
        serialization.BestAvailableEncryption(password.encode()),
    )
)
config = directory / "config.yaml"
config.write_text(
    json.dumps(
        {
            "l1": {
                "pkcs12_path": str(credential),
                "password_env": password_env,
                "reason": "Isolated wheel integrity smoke",
            }
        }
    ),
    encoding="utf-8",
)
environment[password_env] = password

l1 = subprocess.run(
    [
        cli,
        input_pdf,
        "--signature",
        signature,
        "--coords",
        profile,
        "--output",
        l1_output,
        "--auto",
        "--level",
        "l1",
        "--config",
        config,
    ],
    cwd=directory,
    env=environment,
    text=True,
    capture_output=True,
    check=True,
)
assert json.loads(l1.stdout)["placements"] == [placement]
assert l1.stderr == f"Saved signed PDF: {l1_output}\n"
with l1_output.open("rb") as stream:
    reader = PdfFileReader(stream)
    assert len(reader.embedded_regular_signatures) == 1
    embedded = reader.embedded_regular_signatures[0]
    logging.disable(logging.CRITICAL)
    try:
        status = validate_pdf_signature(
            embedded,
            signer_validation_context=ValidationContext(
                trust_roots=[], allow_fetching=False
            ),
        )
    finally:
        logging.disable(logging.NOTSET)
assert status.intact
assert status.valid
assert not status.trusted

signed_input_refusal = subprocess.run(
    [
        cli,
        l1_output,
        "--signature",
        signature,
        "--coords",
        profile,
        "--output",
        override_output,
        "--auto",
    ],
    cwd=directory,
    env=environment,
    text=True,
    capture_output=True,
)
assert signed_input_refusal.returncode == 1
assert signed_input_refusal.stdout == ""
assert "may invalidate prior signatures" in signed_input_refusal.stderr
assert not override_output.exists()

signed_input_override = subprocess.run(
    [
        cli,
        l1_output,
        "--signature",
        signature,
        "--coords",
        profile,
        "--output",
        override_output,
        "--auto",
        "--allow-signed-input",
    ],
    cwd=directory,
    env=environment,
    text=True,
    capture_output=True,
    check=True,
)
assert json.loads(signed_input_override.stdout)["placements"] == [placement]
assert "WARNING: Input PDF contains an existing cryptographic signature" in (
    signed_input_override.stderr
)
assert signed_input_override.stderr.endswith(f"Saved signed PDF: {override_output}\n")

print(
    "isolated wheel auto/review/L1/security/signature-guard smokes passed "
    "without Node on PATH"
)
