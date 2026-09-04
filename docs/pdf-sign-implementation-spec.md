# PDF Sign Utility — Implementation Specification

## 1. Purpose

Implement a small local CLI utility for placing a visual signature PNG onto PDF documents, with an optional lightweight integrity signature.

The primary use case is agent-assisted internal document approval:

1. An agent invokes the CLI with a PDF and signature PNG.
2. The utility either:
   - signs automatically from a previously stored placement profile, or
   - opens a minimal local web UI for human review/placement.
3. The signed PDF is saved to a deterministic output path without a save dialog.
4. The final placement profile is emitted as JSON on `stdout`, so an agent can capture and reuse it.

Project-local terminology:

- **L0** — visual signature only. The PNG is embedded in the PDF. No cryptographic integrity guarantee.
- **L1** — L0 visual signature plus an invisible cryptographic PDF signature over the resulting PDF revision. The certificate may be self-signed; identity assurance is explicitly out of scope.

These labels are internal to this project and are not PDF/PAdES standard profile names.

---

## 2. Technology stack

### Backend

- Python 3.13
- FastAPI
- Uvicorn, embedded/in-process
- PyMuPDF for PDF inspection, text extraction, page geometry and L0 image placement
- pyHanko for L1 PDF signing and inspection of existing digital signatures
- Pydantic v2 models via FastAPI
- Standard-library `argparse` for the CLI
- Standard-library `tomllib` for configuration

### Frontend

- Vue 3
- Vite
- `pdfjs-dist` / PDF.js for PDF rendering
- Plain DOM/CSS overlays for signature placement
- No heavy canvas/UI framework unless later requirements justify it

### Compatibility baseline

At the time of this specification, current PyMuPDF and pyHanko releases support Python 3.13. The implementation should pin tested versions in the project lockfile rather than relying on unconstrained latest releases.

---

## 3. Design principles

1. **The CLI is the product API.** The browser UI is only a local review/placement frontend.
2. **Interactive and automatic signing use the same placement model and backend stamping code.**
3. **`stdout` is machine-readable only.** Successful signing prints exactly one placement-profile JSON object to `stdout`. All logs, warnings and human-readable status go to `stderr`.
4. **Automatic signing is always explicit.** Merely supplying coordinates must never imply unattended signing.
5. **Input PDFs are never modified in place.** Output is always a separate file.
6. **The web server is local-only.** Bind to loopback and never expose arbitrary filesystem access to the browser.
7. **Placement coordinates are independent of browser zoom/resolution.** Store normalized page-relative coordinates.
8. **L0 and L1 share the same visual-placement pipeline.** L1 is implemented as a second integrity-signing stage over the L0 result.
9. **Failure is conservative.** Invalid profiles, template mismatches, signed input, encrypted input, output conflicts, or malformed PDFs should fail rather than guess.

---

## 4. User-visible CLI contract

Primary command:

```bash
pdf-sign INPUT.pdf --signature SIGNATURE.png [OPTIONS]
```

### Required arguments

```text
INPUT.pdf
--signature PATH
```

### Main options

```text
--coords PATH              Optional placement-profile JSON.
--output PATH              Explicit output PDF path.
--review                   Force interactive review mode. This is the default.
--auto                     Sign without opening the UI. Requires --coords.
--level l0|l1              Signing level. Default from config, otherwise l0.
--overwrite                Allow replacing an existing output file.
--allow-signed-input       Explicitly allow modifying a PDF that already contains
                           cryptographic signatures. Emit a strong warning.
--config PATH              Explicit config TOML path.
```

`--review` and `--auto` are mutually exclusive. If neither is supplied, mode is `--review`.

### Examples

Human placement from scratch:

```bash
pdf-sign report.pdf --signature signature.png
```

Human review with a suggested placement:

```bash
pdf-sign report.pdf \
  --signature signature.png \
  --coords trip-report.json \
  --review
```

Automatic signing:

```bash
pdf-sign report.pdf \
  --signature signature.png \
  --coords trip-report.json \
  --auto
```

Explicit output and L1 integrity signing:

```bash
pdf-sign report.pdf \
  --signature signature.png \
  --coords trip-report.json \
  --auto \
  --level l1 \
  --output /tmp/report-approved.pdf
```

Capture the final placement profile:

```bash
pdf-sign report.pdf --signature signature.png > placement.json
```

No server messages or logging may appear in `placement.json`.

---

## 5. Process exit and stdout/stderr behavior

### Successful signing

- Save the output PDF successfully.
- Emit exactly one JSON object representing the **final placement state** to `stdout`.
- Print optional human-readable status, including output path, to `stderr`.
- Exit code `0`.

### Failed signing

- Do not emit partial placement JSON to `stdout`.
- Print error information to `stderr`.
- Use a non-zero exit code.
- Do not leave a partial output PDF.

### Interactive cancellation

No visible Cancel button is required in the MVP.

If the user closes the browser without saving, the CLI continues waiting until interrupted. `Ctrl+C` should terminate cleanly, remove temporary files and exit with the normal interrupted-process status.

---

## 6. Output path resolution

Precedence:

1. `--output PATH`
2. configured `output_suffix`
3. default suffix `_signed`

Example:

```text
input:   /work/trip.pdf
suffix:  _signed
output:  /work/trip_signed.pdf
```

For `report.v2.pdf`, the default output is `report.v2_signed.pdf`.

Rules:

- Input and output paths must resolve to different files.
- In-place signing is not supported, even with `--overwrite`.
- If output already exists and `--overwrite` is absent: fail before modifying anything.
- If `--overwrite` is present: write a temporary file in the destination directory and atomically replace the target only after successful completion.
- Never modify the input PDF.

---

## 7. Configuration

Use TOML.

Lookup precedence:

1. `--config PATH`
2. `$XDG_CONFIG_HOME/pdf-sign/config.toml`
3. `~/.config/pdf-sign/config.toml`
4. built-in defaults

Example:

```toml
output_suffix = "_signed"
default_level = "l0"
default_signature_width = 0.16
open_browser = true
host = "127.0.0.1"
port = 0

[l1]
pkcs12_path = "~/.config/pdf-sign/signing.p12"
password_env = "PDF_SIGN_PKCS12_PASSWORD"
reason = "Internal document approval"
```

Notes:

- `port = 0` means choose an available ephemeral local port.
- `default_signature_width` is a normalized fraction of displayed page width used for newly placed signatures.
- Environment expansion and `~` expansion are required for paths.

---

## 8. Placement profile JSON

### 8.1 Coordinate system

All placement rectangles use the same canonical coordinate system:

- coordinates are relative to the **displayed page**
- page CropBox is respected
- page rotation is already applied conceptually
- origin is top-left
- X increases right
- Y increases down
- all coordinates are normalized to `0..1`
- page numbers are 1-based

Example:

```text
(0,0)                              (1,0)
  +----------------------------------+
  |                                  |
  |                     +--------+   |
  |                     | SIGN   |   |
  |                     +--------+   |
  |                                  |
  +----------------------------------+
(0,1)                              (1,1)
```

### 8.2 Version 1 schema

```json
{
  "version": 1,
  "created_from": {
    "sha256": "<informational source PDF hash>"
  },
  "match": {
    "page_count": 2,
    "pages": [
      {
        "page": 1,
        "width_pt": 595.276,
        "height_pt": 841.890,
        "rotation": 0
      },
      {
        "page": 2,
        "width_pt": 595.276,
        "height_pt": 841.890,
        "rotation": 0
      }
    ],
    "required_text": [
      {
        "page": 1,
        "text": "BUSINESS TRIP REPORT"
      },
      {
        "page": 1,
        "text": "Employee signature:"
      }
    ]
  },
  "placements": [
    {
      "page": 1,
      "x": 0.724,
      "y": 0.108,
      "width": 0.137,
      "height": 0.043
    }
  ]
}
```

### 8.3 Required vs optional fields

Required:

```text
version
match.page_count
match.pages
placements
```

Optional:

```text
created_from.sha256
match.required_text
```

Profiles produced after an interactive save must automatically include:

- `version`
- `created_from.sha256`
- page count
- displayed page dimensions
- page rotations
- final placements

`required_text` cannot be inferred reliably and therefore may be absent on a newly created profile. If it existed in an input profile, preserve it in the output profile.

An agent or user may enrich a stored profile later with `required_text` conditions.

### 8.4 Placement validation

For each placement:

```text
1 <= page <= page_count
0 <= x < 1
0 <= y < 1
0 < width <= 1
0 < height <= 1
x + width <= 1
y + height <= 1
```

Reject profiles with zero placements in `--auto` mode.

The UI may temporarily contain zero placements after the user removes suggestions, but Save must remain disabled until at least one signature is present.

---

## 9. Profile/document matching

Before applying input placements, validate the profile against the current document.

### Mandatory checks

- page count equals `match.page_count`
- each listed page has the expected displayed size within a small numeric tolerance, e.g. 1 PDF point
- page rotation matches

### Optional text checks

If `match.required_text` exists:

- extract text using PyMuPDF
- normalize whitespace before substring matching
- for an item with `page`, require the text on that page
- all required-text conditions must pass

Failure must stop both `--auto` and interactive preloading unless an explicit future override is added. Do not silently use coordinates against a non-matching PDF.

`created_from.sha256` is informational and must **not** be treated as a required exact match. Reusable forms are expected to contain changing field values.

---

## 10. Interactive web UI

### 10.1 Purpose

The browser is a local review and placement surface only. It must not implement PDF persistence itself.

### 10.2 Visible controls

The MVP toolbar contains only:

```text
[ Place signature ]                                  [ Save ]
```

No Save As dialog, filename input, coordinate-save button, settings panel or crypto controls are required.

### 10.3 PDF rendering

- Render pages using PDF.js.
- Each page is a relatively positioned DOM container.
- PDF.js renders the PDF page into a canvas.
- Signature images are absolutely positioned DOM overlays above that canvas.
- Placements are stored in normalized coordinates, not pixels.

Conceptually:

```html
<div class="pdf-page">
  <canvas class="pdf-canvas"></canvas>
  <div class="signature-overlay">...</div>
</div>
```

### 10.4 Signature placement

`Place signature` enters placement mode.

The next left-click on a PDF page creates a signature centered near the click point, with:

- width = configured `default_signature_width`
- height derived from the PNG aspect ratio in physical/displayed page coordinates
- aspect ratio locked
- placement clamped to page bounds

The mode then returns to normal. Repeated placements require repeated presses of `Place signature`.

### 10.5 Editing existing placements

Every signature overlay, regardless of whether loaded from a profile or manually added, behaves identically:

- drag body → move
- drag resize handle/corner → resize with aspect ratio locked
- right-click → custom context menu with one command:

```text
Remove signature
```

Also support the keyboard `Delete` key for the currently selected signature as a convenience, without adding visible UI.

Do not maintain separate frontend types for "suggested" and "manual" signatures.

### 10.6 Preloaded coordinates

If `--coords` is supplied in review mode:

1. validate the profile against the input PDF
2. launch UI
3. initialize the same placement state with profile placements
4. user may move, resize, remove or add placements
5. Save uses the resulting final state

This is the core human-review workflow.

### 10.7 Save

Save is enabled only when at least one valid placement exists.

On Save:

1. frontend POSTs final placement state to backend
2. backend validates again
3. backend writes output PDF
4. backend returns success
5. frontend displays a minimal `Saved` confirmation
6. backend emits final profile JSON on CLI `stdout`
7. local server shuts down after the HTTP response has completed
8. CLI exits 0

Do not make the browser initiate a file download.

---

## 11. Web server/API

The frontend must not send or receive arbitrary filesystem paths.

All file paths are fixed in backend session state from CLI startup.

Suggested endpoints:

```text
GET  /api/document
GET  /api/signature
GET  /api/session
POST /api/save
GET  /                 frontend index
```

### `GET /api/session`

Returns only safe UI metadata, e.g.:

```json
{
  "pageCount": 2,
  "initialPlacements": [...],
  "defaultSignatureWidth": 0.16
}
```

### `POST /api/save`

Input:

```json
{
  "placements": [...]
}
```

No output path, signature path or input path may be accepted from browser input.

Response:

```json
{
  "ok": true
}
```

The final placement-profile JSON goes to CLI stdout, not the browser response.

---

## 12. Local-server security

Even though this is a desktop-local utility, implement basic localhost hardening.

Required:

- bind only to `127.0.0.1` by default
- no permissive CORS
- generate a random high-entropy session token at startup
- include token in the opened browser URL and require it on API calls, or establish a same-session secure cookie from that token
- reject API calls without the active session token
- expose no directory listing
- expose no generic file-read or file-write API
- backend only serves the exact PDF and PNG selected by the CLI
- server lifetime is one signing session

This prevents unrelated browser pages from trivially issuing localhost signing requests.

---

## 13. Coordinate conversion backend

Coordinate conversion must exist in one well-tested module/function. Do not duplicate transformation logic across stamping code.

Suggested interface:

```python
placement_to_pdf_rect(page, placement) -> pymupdf.Rect
```

Input placement coordinates are defined against the **displayed CropBox after rotation**.

The conversion must correctly handle:

- CropBox vs MediaBox
- page rotations 0/90/180/270
- portrait/landscape
- non-A4 dimensions
- non-zero page box origins

The frontend and backend must agree on the same displayed-page definition.

---

## 14. L0 implementation

### 14.1 Semantics

L0 means:

```text
original PDF
+ embedded visual PNG at each final placement
= output PDF
```

No cryptographic signature or Adobe Fill & Sign proprietary metadata is required.

Do not attempt to reproduce `/ADBE_FillSign` data.

### 14.2 Backend flow

Conceptually:

```python
doc = pymupdf.open(input_path)

for placement in placements:
    page = doc[placement.page - 1]
    rect = placement_to_pdf_rect(page, placement)
    page.insert_image(rect, filename=signature_path, overlay=True)

doc.save(temp_output)
```

Exact save arguments should be chosen based on tests for fidelity and reasonable file size.

### 14.3 Signature PNG

- PNG is the only supported signature format in MVP.
- Alpha transparency must be preserved.
- Validate that the file decodes as PNG before UI launch or automatic signing.
- UI always locks image aspect ratio.
- Backend validates that the physical PDF rectangle aspect ratio is reasonably consistent with the image aspect ratio; reject clearly malformed hand-edited profiles instead of silently distorting the signature.

---

## 15. L1 implementation

### 15.1 Semantics

L1 is implemented as:

```text
input PDF
   ↓
L0 visual stamping
   ↓
complete visually approved PDF
   ↓
pyHanko invisible digital signature
   ↓
L1 output PDF
```

The cryptographic signature therefore protects:

- original document content
- visual signature image(s)
- their positions/scales
- all other bytes covered by the signed PDF revision

The L1 signature is not intended to establish a legally verified human identity.

### 15.2 PDF signature appearance

The cryptographic signature should be invisible in the document layout. The visible PNG remains an ordinary L0 image.

Do not initially attempt to combine the PNG with the cryptographic signature-field appearance.

### 15.3 Certificate/key input

Initial implementation should support a PKCS#12 (`.p12`/`.pfx`) signer bundle.

Configuration:

```toml
[l1]
pkcs12_path = "~/.config/pdf-sign/signing.p12"
password_env = "PDF_SIGN_PKCS12_PASSWORD"
reason = "Internal document approval"
```

Password rules:

1. read the configured environment variable
2. if absent and running interactively on a TTY, a secure password prompt may be used
3. never accept or print the password in logs
4. never put the password directly in command-line arguments by default, to avoid shell history/process-list leakage

The certificate may be self-signed.

### 15.4 Credential bootstrap

A helper for generating a self-signed PKCS#12 bundle is desirable but not required for the first L0 milestone.

If implemented, generate a normal broadly compatible RSA/SHA-256 certificate and clearly document that it provides key continuity/integrity, not external identity assurance.

### 15.5 Timestamping/revocation

Out of scope for MVP:

- TSA timestamping
- OCSP/CRL embedding
- PAdES LT/LTA
- qualified signatures
- certificate-chain trust management

---

## 16. Existing digital signatures on input

Before modifying an input PDF, inspect it for existing cryptographic PDF signatures.

Default behavior:

```text
existing digital signature found -> refuse
```

Error should explain that rewriting/stamping the PDF can invalidate prior signatures.

If `--allow-signed-input` is supplied:

- emit a strong warning to `stderr`
- proceed
- make no claim that previous signatures remain valid

This flag is an expert override, not normal workflow.

---

## 17. Unsupported/problematic inputs

MVP should reject with clear errors:

- encrypted/password-protected PDFs
- malformed/unreadable PDFs
- non-PNG signature asset
- zero-page PDFs
- invalid/out-of-range placement data
- output path equal to input path
- existing output without `--overwrite`
- `--auto` without `--coords`
- profile/document mismatch
- L1 requested without available signer credentials

Do not add password-unlock workflows in MVP.

---

## 18. Suggested internal Python model

```python
class Placement(BaseModel):
    page: int
    x: float
    y: float
    width: float
    height: float


class PageMatch(BaseModel):
    page: int
    width_pt: float
    height_pt: float
    rotation: int


class RequiredText(BaseModel):
    page: int | None = None
    text: str


class MatchSpec(BaseModel):
    page_count: int
    pages: list[PageMatch]
    required_text: list[RequiredText] = []


class CreatedFrom(BaseModel):
    sha256: str | None = None


class PlacementProfile(BaseModel):
    version: Literal[1]
    created_from: CreatedFrom | None = None
    match: MatchSpec
    placements: list[Placement]
```

Use the same Pydantic models for CLI profile loading and `/api/save` validation where practical.

---

## 19. Suggested repository structure

```text
pdf-sign/
├── pyproject.toml
├── README.md
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.vue
│       ├── api.ts
│       ├── models.ts
│       └── components/
│           ├── PdfDocument.vue
│           ├── PdfPage.vue
│           ├── SignatureOverlay.vue
│           └── SignatureContextMenu.vue
├── src/
│   └── pdf_sign/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── models.py
│       ├── profile.py
│       ├── geometry.py
│       ├── pdf_inspect.py
│       ├── pdf_stamp.py
│       ├── pdf_crypto.py
│       ├── output.py
│       ├── server.py
│       └── web_dist/
└── tests/
    ├── fixtures/
    ├── test_cli.py
    ├── test_config.py
    ├── test_profile.py
    ├── test_geometry.py
    ├── test_pdf_stamp.py
    ├── test_pdf_crypto.py
    ├── test_output.py
    └── e2e/
```

The Vite production build should be copied/packaged into `src/pdf_sign/web_dist/` so an installed CLI does not require a Node runtime.

Node/Vite are development/build dependencies only.

---

## 20. Backend execution flow

### 20.1 Common startup

```text
parse CLI
  ↓
load config
  ↓
validate input PDF + PNG
  ↓
resolve output path
  ↓
check output collision
  ↓
check encrypted PDF
  ↓
check existing digital signatures
  ↓
load/validate optional placement profile
  ↓
validate profile against current PDF
```

### 20.2 Review mode

```text
common startup
  ↓
create signing session
  ↓
start loopback FastAPI/Uvicorn server
  ↓
open browser
  ↓
PDF.js displays document
  ↓
preload placements if supplied
  ↓
human adds/moves/resizes/removes
  ↓
Save
  ↓
validate final placements
  ↓
L0 stamp
  ↓
optional L1 crypto-sign
  ↓
atomic output commit
  ↓
construct final PlacementProfile
  ↓
emit JSON to stdout
  ↓
return success to browser
  ↓
shutdown server
  ↓
exit 0
```

### 20.3 Auto mode

```text
common startup
  ↓
require --coords
  ↓
L0 stamp profile placements
  ↓
optional L1 crypto-sign
  ↓
atomic output commit
  ↓
emit final profile JSON to stdout
  ↓
exit 0
```

The profile emitted by auto mode should be the same normalized structure as the input profile, refreshed with current source metadata where appropriate.

---

## 21. Logging

Use Python `logging` directed to `stderr`.

Suggested normal messages:

```text
Opening browser at http://127.0.0.1:54321/...
Saved signed PDF: /work/report_signed.pdf
```

Warnings and errors also use `stderr`.

Never log:

- private key bytes
- PKCS#12 password
- session token at normal verbosity if avoidable

The stdout contract must be protected by tests.

---

## 22. Tests

### 22.1 Unit tests

#### Configuration

- default suffix
- config precedence
- XDG path handling
- `~` expansion
- CLI overrides

#### Output paths

- `foo.pdf -> foo_signed.pdf`
- multi-dot filenames
- explicit output
- existing output rejection
- overwrite behavior
- input/output equality rejection

#### Profile validation

- valid profile
- page out of range
- negative coords
- rectangle outside page
- unknown profile version
- zero placements

#### Document matching

- matching page count/size/rotation
- page count mismatch
- size mismatch
- rotation mismatch
- required text success/failure
- whitespace normalization

#### Geometry

Create synthetic PDFs covering:

- rotation 0
- rotation 90
- rotation 180
- rotation 270
- portrait
- landscape
- non-zero CropBox origin
- CropBox smaller than MediaBox
- non-A4 pages

Assert round-trip/expected rectangle placement.

### 22.2 L0 integration tests

For a synthetic PDF:

1. apply one known placement
2. reopen output with PyMuPDF
3. render page
4. confirm signature appears in expected region
5. test transparent PNG
6. test multiple signatures and multiple pages
7. verify input file hash is unchanged

Avoid pixel-perfect anti-aliasing assertions; use tolerant region/image checks.

### 22.3 L1 integration tests

Using test-only generated credentials:

1. create L0-stamped PDF
2. L1 sign it with pyHanko
3. validate signature cryptographically
4. confirm self-signed trust status does not prevent integrity validation
5. alter the signed PDF and verify validation no longer reports an intact signed revision
6. confirm visual PNG remains present

### 22.4 Existing-signature tests

- digitally signed input is refused by default
- override flag permits processing with warning

### 22.5 CLI contract tests

Critical tests:

- successful `--auto` stdout parses as exactly one JSON document
- normal logging appears only on stderr
- failure emits no JSON stdout
- exit codes are correct

### 22.6 Frontend tests

Use Vitest for pure placement math/state where useful.

Add at least one Playwright end-to-end test covering:

1. open review UI
2. verify preloaded placement
3. drag placement
4. resize placement
5. right-click and remove
6. add a replacement signature
7. Save
8. assert output exists
9. assert CLI emits the final, edited placement state

---

## 23. Implementation milestones

### Milestone 1 — Headless L0 core

Deliver:

- CLI parsing
- config
- placement-profile schema
- PDF/profile validation
- normalized-to-PDF geometry
- deterministic output naming
- L0 stamping
- `--auto`
- stdout/stderr contract
- unit/integration tests

Acceptance example:

```bash
pdf-sign input.pdf \
  --signature sig.png \
  --coords profile.json \
  --auto
```

produces `input_signed.pdf` and prints a valid placement profile to stdout.

### Milestone 2 — Review UI

Deliver:

- FastAPI local session
- packaged Vue/PDF.js frontend
- place/move/resize/remove interactions
- preloaded profile support
- Save workflow
- browser/server lifecycle
- Playwright E2E

Acceptance example:

```bash
pdf-sign input.pdf --signature sig.png --coords profile.json
```

opens a browser with suggested signatures, allows editing/removal, saves without a file dialog and emits the final profile on stdout.

### Milestone 3 — L1 integrity signing

Deliver:

- PKCS#12 credential loading
- invisible pyHanko digital signature after L0 stamping
- signature verification tests
- credentials/password handling

Acceptance:

```bash
pdf-sign input.pdf \
  --signature sig.png \
  --coords profile.json \
  --auto \
  --level l1
```

produces a PDF whose cryptographic signature validates as intact, although its self-signed certificate may be untrusted.

### Milestone 4 — Hardening

Deliver:

- existing-signature detection and override behavior
- localhost session token
- atomic output writes
- malformed/encrypted input handling
- packaging/install documentation
- final README examples

---

## 24. Definition of done

The project is complete for the initial target when all of the following are true:

1. `pdf-sign` runs on Python 3.13.
2. A PNG can be placed visually onto arbitrary normal PDF pages.
3. Placement coordinates are reusable independent of browser zoom/resolution.
4. Rotation and CropBox cases are tested.
5. Without `--coords`, review UI starts with no signatures.
6. With `--coords` in review mode, suggestions are preloaded and editable.
7. Right-click removal works for every signature.
8. `Delete` removal works for the selected signature.
9. The UI contains only Place signature and Save as normal visible controls.
10. Save never opens a filename dialog.
11. Output path follows CLI/config/default precedence.
12. Existing output is not overwritten without explicit `--overwrite`.
13. Input is never modified in place.
14. `--auto` requires explicit use and a placement profile.
15. Every successful save emits final placement JSON to stdout.
16. stdout contains no logs or status text.
17. Human corrections in review mode are reflected in emitted JSON.
18. L0 output contains visual image placement only, with no claim of cryptographic protection.
19. L1 output contains the same visual placement plus a valid PDF digital signature.
20. Existing digitally signed input is refused by default.
21. Browser server is loopback-only and session-protected.
22. Automated tests cover CLI, geometry, stamping, UI workflow and L1 validation.

---

## 25. Explicit non-goals for the MVP

Do not expand scope into:

- legal/qualified electronic signatures
- public CA identity validation
- timestamp authorities
- long-term PAdES validation
- Adobe Fill & Sign proprietary metadata compatibility
- handwriting capture
- image editing
- OCR-based automatic signature-position discovery
- automatic document/template classification
- multi-user server deployment
- remote web service
- cloud storage integration
- PDF form filling beyond signature placement
- password-protected PDF support
- multiple different signature PNG identities in one invocation
- audit database/workflow engine

The utility should remain a small local signing primitive that an external agent/workflow can orchestrate.

---

## 26. Important architectural boundary

The utility is deliberately **not responsible for deciding whether a document should be signed**.

The agent/workflow layer decides:

- which PDF to sign
- which signature PNG to use
- which stored placement profile applies
- whether human review is required
- whether `--auto` is appropriate

The utility is responsible only for:

- validating the supplied document/profile
- obtaining or reviewing placements
- producing the signed PDF
- optionally sealing the resulting revision cryptographically
- returning the final placement profile in a machine-readable form

This boundary should remain explicit during implementation.
