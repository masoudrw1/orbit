# Installer and hidden activation validation — 2026-11-12

Target: Pop!_OS 24.04, COSMIC/Wayland, amd64, Python 3.12.3, GTK 4.14.
The user previously reported that the original prototype worked with their own
voice. They have now installed alpha 2 and tried a spoken IntelliJ command, reporting
that a different phrase was recognized. The exact utterance and returned transcript
have not yet been captured.

Checks performed for this phase:

- 25 core/activation/packaging unit tests passed. They include login-entry rollback
  on failed settings writes and rejection of altered cached assets.
- Real GTK/Wayland lifecycle checks used a fake microphone adapter on a private
  D-Bus session without desktop service activation. They covered activation hiding,
  wake-event reveal, same-instance reopening, error recovery, and deactivation.
- Background resume used saved activation and remained hidden until a wake event.
- A deactivated background start exited without a window or microphone listener.
- The real speech model and Vosk bundled in the extracted installer recognized
  synthetic English `hey orbit` followed by `programming` through Orbit's voice
  worker, with a PCM-source substitute for the microphone.
- The payload was run with `/usr/bin/python3`, from outside the source checkout.
  Missing Ubuntu Python dependency packages were downloaded and extracted into an
  isolated QA user-site directory. The developer `.venv` was not used by the payload.
- The extracted installer passed its COSMIC island smoke test and doctor report.
- `apt-get -s install <installer>` resolved dependencies: Orbit plus six additional
  Python packages, no removals. This was a simulation, not a system installation.
- The desktop entry passed `desktop-file-validate`.
- Python compile checks and shell syntax checks passed.
- Two offline builds from the final source/assets produced byte-identical `.deb`
  files. The final payload contained 86 entries with root ownership, no developer
  venv or home-directory paths, and bundled-component license text.
- The user reported successful installation, and `dpkg-query` confirmed
  `orbit-launcher 0.1.0~alpha2-1` with status `install ok installed` on the original
  development machine. This is not a clean-machine installation test.
- Read-only desktop discovery confirmed that the registered phrase `open idea`
  uniquely maps to the installed `IntelliJ IDEA` desktop application. Spoken
  recognition of that alias has not yet been reported by the user.

Package inputs are pinned in `packaging/assets.json`; component licenses and
source/provenance are documented in `packaging/THIRD_PARTY.md`. The package
includes a build receipt and a separate SHA-256 file is generated beside it.

## Acceptance still requiring the user/device

Complete real microphone command coverage, including the reported IntelliJ
misrecognition; verify a real logout/login; and test installation and uninstall
on a fresh machine. A private-session background launch is not a real reboot test.
Broad accent/noise/false-wake, latency/resource, multi-monitor and GNOME QA remain.
Changes in this phase have not been committed, pushed, or published as a release
by the assistant. Installer construction does not imply installation or activation.
