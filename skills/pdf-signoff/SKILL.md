---
name: pdf-signoff
description: Sign PDFs with a PNG through human review or a reusable placement profile, optionally adding an L1 integrity signature. Use when asked to place a signature image on a PDF with the pdf-signoff CLI and safely interpret its PDF and JSON outputs.
license: MIT
compatibility: Requires the pdf-signoff command on PATH. Review mode requires a trusted local browser session; unattended signing requires a placement profile.
---

# PDF Signoff

Use `pdf-signoff` to place one PNG identity on one or more PDF pages. The command
writes a separate PDF and returns the final reusable placement profile as JSON.

## Source Of Truth

Run this before constructing an invocation:

```bash
pdf-signoff --help
```

Follow the installed help for current options, defaults, configuration, output
semantics, and trust boundaries. Use `pdf-signoff --version` when reporting or
debugging behavior. Do not rely on a remembered option list.

## Decide Before Running

1. Confirm the requested input PDF and signature PNG. Never infer authorization
   to apply a signature image or cryptographic credential.
2. Use review mode when placement is new, uncertain, or requires human approval.
   Use `--auto` only when unattended signing is authorized and a trusted profile
   applies to this document.
3. Choose L0 for visual placement unless L1 integrity is explicitly required.
   Make `--level` explicit when local configuration must not change the outcome.
4. Prefer an explicit `--output` so the result path is known without parsing
   diagnostics.
5. Never add `--overwrite` or `--allow-signed-input` without explicit acceptance
   of the risk described by `--help`.

## Invoke

For review, let the browser open and tell the user that signing completes only
after Save. Browser launch is not success, and closing the tab does not cancel.
Interrupt with Ctrl+C if the user cancels.

For automatic signing, provide the reviewed profile and `--auto`. Keep stderr
visible for diagnostics, but capture stdout separately. Prefer the agent's
process-result API. If only shell redirection is available, write to a new
temporary profile path and move it to the intended path only after validation;
redirection truncates an existing file before the command starts.

Example shape only; consult `--help` before use:

```bash
pdf-signoff input.pdf \
  --signature signature.png \
  --coords reviewed-profile.json \
  --auto \
  --level l0 \
  --output signed.pdf \
  > profile.tmp.json
```

## Validate Success

Accept the operation only when all checks pass:

- The process exits zero.
- Stdout is exactly one JSON object with no non-JSON status text.
- The profile has `version: 1`, document match metadata, and the expected final
  placements.
- The selected output PDF exists at the expected path.
- No stderr warning requires unresolved user judgment.

The JSON is a placement profile, not the signed PDF and not proof of identity or
authorization. Preserve the emitted profile rather than the input profile:
review may change placements, and the tool refreshes document metadata. Treat
`created_from.sha256` as informational; profile reuse is governed by page and
optional required-text matching described by `--help`.

For L1, the PDF includes an invisible integrity signature over the stamped
revision. Do not describe it as trusted identity, timestamped, legal, or
qualified merely because the command succeeded.

## Handle Failure

On nonzero exit, treat the signing attempt as failed. Signing failures should
leave stdout empty and commit no new partial PDF.

- If the output exists, choose a new path or ask before using `--overwrite`.
- If a profile mismatches, do not weaken checks or invent corrected geometry.
  Return to review or request the correct profile.
- If the input is already signed, explain the invalidation risk and ask before
  using `--allow-signed-input`.
- If an input is unsupported, do not repair, decrypt, or convert it unless the
  user separately authorizes that document-changing operation.
- If L1 credentials fail, do not print secrets or place passwords in arguments.
  Use the configured password environment variable and protected PKCS#12 file.

Never accept a run based only on a file's presence: a prior output may already
exist. Require the process result and valid profile as well.

## Security

Keep review on loopback and do not expose, proxy, share, or log its tokenized
URL. Treat the browser, local account, machine, signature PNG, placement profile,
PKCS#12 file, and password source as trusted workflow inputs. The caller remains
responsible for authorization, approvals, storage, distribution, and legal use.
