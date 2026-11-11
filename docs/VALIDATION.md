# Initial development validation — 2026-11-11

Environment: Pop!_OS 24.04 LTS, COSMIC, Wayland, Python 3.12.3, GTK 4.14.

Executed checks:

- 13 standard-library unit tests passed: command aliases and ambiguity, no implicit
  partial voice execution, wake activation/expiry/cancel, configuration validation,
  and failed-save preservation of existing configuration.
- Real GTK window smoke test: populated 76 desktop apps, expanded/collapsed,
  rendered a widget image, and exited without opening a microphone.
- Real COSMIC/Wayland Layer Shell smoke test passed with `island=True`.
- A GUI integration exercise selected apps, saved an isolated temporary routine,
  dispatched its voice event, and sent ordered launch requests to a **mock**
  launch adapter. It did not launch unrelated desktop apps.
- Vosk native package installed successfully in `.venv`.
- The official small English model downloaded successfully into `.models`.
- Locally synthesized English audio produced transcripts `hey orbit` and
  `programming`. Real Vosk decoding and Orbit's wake gate produced the expected
  wake and command events. The voice worker also passed with this PCM source and
  a mock recorder; no real microphone was used for that check.
- `run.sh --doctor` reported all checked dependencies present.
- Shell helpers passed `bash -n`; Python modules passed compile checks.

## Native runtime provenance

System development headers were not installed or modified. For local UI QA,
the official Debian packages `libgtk4-layer-shell0` and
`gir1.2-gtk4layershell-1.0`, version `1.0.4-2` for amd64, were downloaded from
`https://deb.debian.org/debian/pool/main/g/gtk4-layer-shell/` and extracted.
Their library and typelib were placed in the ignored project-local `.runtime`;
copyright records and download digests were retained there. No Debian repository
was added to APT and no system package installation was performed.

This demonstrates the adapter on the current machine. It is not a supported
cross-distribution deployment strategy. The source-build helper is the documented
development route for a fresh checkout, but it has not been run here because its
native development prerequisites are absent.

## Still required

Real microphone/accents/noise and false-wake testing; CPU/RAM and latency
measurements; multiple monitors/scaling/fullscreen/focus QA; actual app startup
verification; clean-machine installation; service actions; and GNOME desktop QA.
GitHub Actions has not run until the repository is published and the workflow
executes there. Do not describe the alpha as a completed or generally compatible v1.
