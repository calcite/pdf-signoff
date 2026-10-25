# 0001: Host-local review sessions through container port publishing

Date: 2026-10-25

Status: Accepted

## Context

The browser and calling application run on the same host, while pdf-signoff may
run inside Docker. A container-loopback listener cannot receive ordinary Docker
published-port traffic. The listening IP/port can also differ from the address
the browser uses, so deriving HTTP Host validation and review links solely from
the listening socket prevents this deployment.

An application must be able to obtain the ready session's credential-bearing
link without launching a browser inside the container. CLI stdout remains the
final placement profile, and routine logs must not contain session credentials.

## Decision

- Keep `127.0.0.1` and an ephemeral port as listener defaults, but allow any literal
  IPv4/IPv6 bind address, including wildcards. Deployment controls the network
  boundary: publish container ports to host loopback for this host-local use.
- Add optional `public_url`, a root HTTP(S) origin with no credentials, path,
  query or fragment. It determines both the generated review link and the exact
  allowed HTTP Host header, independently of the listener. Without it, use the
  bound address/selected port, substituting loopback for a wildcard address.
- Keep token authentication, same-origin checks, CSP and one-shot lifetime.
  Do not trust arbitrary Hosts or infer the public origin from request headers.
- Python callers use `ReviewServer.url`. CLI callers may set `session_info_file`:
  once the server is ready, atomically create a private POSIX-mode-0600 JSON file
  containing `{"version":1,"url":"<token-bearing review URL>"}`. Existing files
  are refused. Remove the file when the review lifecycle ends. The caller reads
  it from a shared directory and presents the URL to the host browser.

## Consequences

The calling application explicitly supplies the published origin when it differs
from the listening address/port. Fixed container ports can be published to a
different fixed host-loopback port. No new unauthenticated discovery endpoint or
credential-bearing log output is needed, and stdout retains its existing contract.

A shared session-info directory must already exist and be writable by the
container process and readable by the calling application's user. Each concurrent
session needs its own path and published port. Atomic publication prevents
partial JSON; the caller must also watch process exit. Termination by SIGTERM or
SIGKILL can leave a stale file that the caller must remove before reusing its path.
Graceful cancellation uses SIGINT. Remote and multi-user service operation are
outside this deployment contract.

## Alternatives considered

- Host networking avoids normal Docker publishing but is platform-dependent and
  does not address the independent link-handoff interface.
- Allowing arbitrary Hosts discards existing validation unnecessarily.
- Printing the secret URL to stdout breaks profile consumers; logging it to stderr
  unnecessarily mixes credentials with routine diagnostics.
