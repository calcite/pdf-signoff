# History

## 0.2.1 (2026-10-25)

* Unblock the frontend release audit by updating Vite to `7.3.7`, Vitest to
  `4.1.12`, happy-dom to `21.0.4`, and locked source-map-js to `1.2.2`.
  The updated test runner removes the vulnerable tinypool dependency.

## 0.2.0 (2026-10-25)

* Support host-local Docker review sessions with configurable IPv4/IPv6 bind
  addresses and a separate browser-facing `public_url` for published ports.
* Add an opt-in private, atomic `session_info_file` for applications to obtain
  the ready review link, with cleanup after save or graceful cancellation.

## 0.1.2 (2026-09-10)

* Expanded `pdf-signoff --help` into a self-contained operating reference and
  added a portable Agent Skills workflow for conservative PDF signing.

## 0.1.1 (2026-09-08)

* Initial release.
