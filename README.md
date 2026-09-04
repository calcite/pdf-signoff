# PDF Signoff

PDF Signoff is a local, agent-friendly command-line utility for placing one
signature PNG on one or more PDF pages. It can either open a minimal browser UI
for human review or apply a previously saved placement profile unattended. An
optional L1 stage adds an invisible PDF digital signature for tamper evidence.

The CLI is the product API. Every successful signing invocation writes a
separate PDF and emits exactly one reusable placement-profile JSON object on
stdout. Status, warnings, and errors are written to stderr.

PDF Signoff is pre-alpha software. Review its output before relying on it.

## Installation

PDF Signoff requires Python 3.13 or newer.

```console
python3.13 -m pip install pdf-signoff
pdf-signoff --help
```

The wheel includes the production Vue/PDF.js review UI. Node.js is not required
to run either review or automatic signing from an installed package.

To install the checked-out project with its locked development dependencies:

```console
uv sync --frozen --group dev
uv run pdf-signoff --help
```

## Review Mode

Review is the default mode. This starts a protected one-shot web server on a
loopback address, opens the review page in the default browser, and waits until
Save is selected:

```console
pdf-signoff report.pdf --signature signature.png > report-placement.json
```

The UI starts empty when `--coords` is omitted. Select **Place signature**, then
select a PDF page to add one signature. A placement can be moved, resized with
its aspect ratio locked, removed from its right-click menu, or removed with the
Delete key while selected. The only normal visible toolbar controls are
**Place signature** and **Save**. Save writes the configured output directly;
it does not open a filename dialog or download a file through the browser.

Supply an existing profile to preload editable suggestions:

```console
pdf-signoff report.pdf \
  --signature signature.png \
  --coords report-placement.json \
  --review \
  > reviewed-placement.json
```

The emitted profile contains the final edited placements, not merely the
preloaded suggestions. Closing the browser without saving does not cancel the
operation; the CLI continues waiting. Press Ctrl+C to stop it without emitting
a profile or creating an output.

## Automatic Mode

Automatic signing is always explicit and requires a non-empty placement
profile:

```console
pdf-signoff report.pdf \
  --signature signature.png \
  --coords reviewed-placement.json \
  --auto \
  > final-placement.json
```

Supplying `--coords` alone never enables unattended signing. `--review` and
`--auto` are mutually exclusive.

Before using a profile, PDF Signoff requires its page count, listed displayed
CropBox dimensions (within 1 PDF point), rotations, and optional required-text
conditions to match the current PDF. The source SHA-256 in `created_from` is
informational so a profile can be reused for changing instances of the same
form.

## Output And Capture

Unless `--output` is supplied, the output suffix is inserted before the final
extension:

```text
report.pdf       -> report_signed.pdf
report.v2.pdf    -> report.v2_signed.pdf
```

An explicit destination takes precedence over the configured suffix:

```console
pdf-signoff report.pdf \
  --signature signature.png \
  --coords reviewed-placement.json \
  --auto \
  --output /tmp/report-approved.pdf \
  > /tmp/report-approved-placement.json
```

The input PDF is never modified in place, and input and output may not resolve
to the same file. Existing destinations are refused unless `--overwrite` is
explicit:

```console
pdf-signoff report.pdf \
  --signature signature.png \
  --coords reviewed-placement.json \
  --auto \
  --output report-approved.pdf \
  --overwrite \
  > report-approved-placement.json
```

Output is built in a temporary file in the destination directory and published
only after every requested stage succeeds. With `--overwrite`, replacement is
atomic. Without it, PDF Signoff also prevents a destination created by another
process while signing from being replaced.

On success, stdout is one compact JSON document followed by a newline, stderr
reports the output path, and the exit status is zero. On failure, stdout is
empty, the exit status is non-zero, and no partial output is committed. Keep
stdout redirected when an agent needs to capture the final profile while still
allowing diagnostics to reach the terminal:

```console
pdf-signoff report.pdf --signature signature.png > placement.json
```

## Placement Profiles

Version 1 profiles use normalized coordinates against the displayed page
CropBox after rotation. The origin is at the top left, x increases right, y
increases down, values are in the range 0 through 1, and page numbers are
1-based.

```json
{
  "version": 1,
  "created_from": {
    "sha256": "<informational SHA-256 of the source PDF>"
  },
  "match": {
    "page_count": 1,
    "pages": [
      {
        "page": 1,
        "width_pt": 600.0,
        "height_pt": 800.0,
        "rotation": 0
      }
    ],
    "required_text": [
      {
        "page": 1,
        "text": "Employee signature:"
      }
    ]
  },
  "placements": [
    {
      "page": 1,
      "x": 0.62,
      "y": 0.72,
      "width": 0.24,
      "height": 0.045
    }
  ]
}
```

`created_from` and `match.required_text` are optional. PDF Signoff preserves
input required-text conditions in the final profile but cannot infer them for a
new profile. Each placement must have positive width and height and remain
fully within its referenced page. Its physical PDF rectangle must also match
the PNG aspect ratio within the backend tolerance; malformed hand-edited
profiles are rejected rather than distorted.

## Configuration

PDF Signoff uses Onacol with schema-backed YAML configuration. Generate a
schema-free template without supplying signing arguments:

```console
pdf-signoff --get-config-template config.yaml
```

The generated values are:

```yaml
general:
  log_level: INFO

output_suffix: _signed
default_level: l0
default_signature_width: 0.16
open_browser: true
host: 127.0.0.1
port: 0
l1:
  pkcs12_path: ''
  password_env: PDF_SIGN_PKCS12_PASSWORD
  reason: Internal document approval
```

Configuration precedence from lowest to highest is:

1. Bundled defaults.
2. One user YAML file: explicit `--config PATH`, otherwise
   `$XDG_CONFIG_HOME/pdf-signoff/config.yaml`, otherwise
   `~/.config/pdf-signoff/config.yaml`.
3. Environment variables such as `PDF_SIGNOFF__DEFAULT_LEVEL` and
   `PDF_SIGNOFF__L1__PKCS12_PATH`.
4. Nested Onacol CLI options such as `--output-suffix _approved` or
   `--general--log-level DEBUG`.

For example:

```console
PDF_SIGNOFF__DEFAULT_LEVEL=l0 \
  pdf-signoff report.pdf \
  --signature signature.png \
  --coords reviewed-placement.json \
  --auto \
  --output-suffix _approved \
  > approved-placement.json
```

An explicit config file replaces, rather than layers on top of, a discovered
user file. Environment variables and `~` in `l1.pkcs12_path` are expanded after
configuration is merged and validated. Port `0` asks the operating system for
an available ephemeral port. The review host must parse as a loopback IP
address; remote binding is rejected.

## L0 And L1

`--level l0` embeds the supplied PNG at every final placement. Transparency is
preserved. L0 does not add a cryptographic signature and makes no claim that
the PDF has not subsequently changed. It does not create Adobe Fill & Sign
proprietary metadata.

`--level l1` first produces the same complete visual result, then adds an
invisible pyHanko approval signature over that revision before the output is
committed. L1 can detect changes to the covered revision, including changes to
the visible image or its placement. It does not prove who controlled the key,
who reviewed the document, or whether a certificate should be trusted.

L1 requires a PKCS#12 `.p12` or `.pfx` signer bundle. Configure its path, the
name of the password environment variable, and the non-secret reason:

```yaml
l1:
  pkcs12_path: ~/.config/pdf-signoff/signing.p12
  password_env: PDF_SIGN_PKCS12_PASSWORD
  reason: Internal document approval
```

Then set the password without putting it in command arguments and request L1:

```console
export PDF_SIGN_PKCS12_PASSWORD='read-secret-from-your-secret-store'
pdf-signoff report.pdf \
  --signature signature.png \
  --coords reviewed-placement.json \
  --auto \
  --level l1 \
  > integrity-placement.json
```

If the configured password variable is absent, an interactive TTY may use a
secure password prompt. Non-interactive runs fail instead. Protect the PKCS#12
file and password as private signing credentials. PDF Signoff does not print
passwords, private-key material, or sensitive signer details. Missing, invalid,
or unreadable credentials fail without committing an output or emitting a
profile.

A self-signed certificate can provide integrity and key continuity while still
being untrusted. PDF Signoff does not perform public-CA identity validation,
certificate trust management, timestamping, revocation embedding, or long-term
validation. L1 is not a legal, qualified, or externally verified human
signature claim.

## Previously Signed Inputs

PDF Signoff refuses an input containing an existing filled PDF cryptographic
signature field before opening review or creating output. Rewriting or stamping
such a PDF may invalidate its previous signatures.

`--allow-signed-input` is an expert override:

```console
pdf-signoff previously-signed.pdf \
  --signature signature.png \
  --coords reviewed-placement.json \
  --auto \
  --allow-signed-input \
  > final-placement.json
```

The override emits a strong warning only to stderr. It permits processing but
does not validate previous signatures or claim that any previous signature
remains valid.

## Local Review Security

Review mode is a local desktop session, not a network service:

- The server accepts only loopback IP addresses and defaults to `127.0.0.1` on
  an operating-system-selected port.
- One random 256-bit credential protects one signing session. The bootstrap URL
  transfers it to an HttpOnly, SameSite=Strict cookie and redirects to remove it
  from the address; bearer authentication is also supported by the backend.
- API requests without the active credential and unrelated browser origins are
  rejected. No permissive CORS policy is enabled.
- The server exposes only the invocation-selected PDF and PNG, path-free session
  metadata, fixed frontend assets, and a placement-only save operation. It has
  no generic file API or directory listing.
- Access logging is disabled to avoid routinely logging token-bearing URLs, and
  the session is invalidated after its one successful save or server shutdown.

The server uses plain HTTP on loopback, so its session cookie is intentionally
not marked `Secure`. The security boundary assumes the CLI, browser, operating
system account, and local machine are trusted. Other processes running as the
same user, browser extensions, endpoint compromise, or disclosure of the
bootstrap URL are outside that boundary. Do not expose or proxy the review
server, share the tokenized URL, or configure it as a multi-user service.

## Supported And Rejected Inputs

The MVP supports readable, unencrypted, non-empty normal PDFs and one decodable
PNG signature asset per invocation. It supports multiple placements and pages,
displayed CropBoxes, non-zero page-box origins, arbitrary normal page sizes,
and rotations of 0, 90, 180, and 270 degrees.

It rejects these inputs or invocations conservatively:

- Encrypted or password-protected PDFs.
- Malformed, repaired, unreadable, non-PDF, or zero-page documents.
- Non-PNG or undecodable signature assets.
- Invalid, empty-in-auto-mode, out-of-range, or aspect-inconsistent placements.
- Unsupported profile versions and profile/document page, geometry, rotation,
  or required-text mismatches.
- An output equal to the input, or an existing output without `--overwrite`.
- `--auto` without `--coords`.
- L1 without available valid signer credentials.
- Previously signed PDFs without `--allow-signed-input`.

Required-text matching uses text extractable by PyMuPDF. There is no OCR or PDF
password-unlock workflow.

## Responsibility Boundary

PDF Signoff deliberately does not decide whether a document should be signed.
The calling user, agent, or workflow is responsible for deciding:

- Which PDF should be signed.
- Which signature PNG and signing credential may be used.
- Which stored placement profile applies to the document.
- Whether human review is required or unattended `--auto` is appropriate.
- Whether L0 or L1 meets the workflow's policy and legal requirements.
- Whether the final PDF and emitted profile should be accepted or distributed.

PDF Signoff only validates the supplied inputs and profile, obtains or reviews
placements, creates a separate output, optionally seals that revision for
integrity, and returns the final normalized profile. An external workflow must
provide authorization, identity, approvals, storage, retention, and audit
policy.

## MVP Non-Goals

The MVP does not provide:

- Legal or qualified electronic signatures.
- Public-CA identity validation.
- Timestamp authorities.
- Long-term PAdES validation, including PAdES LT/LTA.
- OCSP/CRL embedding, certificate-chain trust management, or other revocation
  and trust services.
- Adobe Fill & Sign proprietary metadata compatibility.
- Handwriting capture or image editing.
- OCR-based automatic signature-position discovery.
- Automatic document or template classification.
- Multi-user server deployment or a remote web service.
- Cloud storage integration.
- PDF form filling beyond signature placement.
- Password-protected PDF support.
- Multiple different signature PNG identities in one invocation.
- An audit database or workflow engine.

## Development Verification

The release checks use the Python and Node lockfiles:

```console
uv sync --frozen --group dev
uv lock --check
uv run pytest --cov=pdf_signoff tests/
uv run ruff check .
uv run ruff format --check .
uv run mypy pdf_signoff
uv run tox

cd frontend
npm ci
npm audit
npm run typecheck
npm test
npm run build
npm run test:e2e
```

The configured Python coverage threshold is 100%. Playwright requires its
Chromium browser and host dependencies in the development environment. Building
the release artifacts uses `uv build`; running the resulting wheel does not
require Node.js, npm, Vite, Vitest, or Playwright.

## License

PDF Signoff is distributed under the MIT license.
