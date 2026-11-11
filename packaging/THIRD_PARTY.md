# Bundled components in the personal alpha package

Orbit source is MIT. The installer also includes the following components, each
retaining its own license. System Python/GTK/audio dependencies are installed and
updated by APT rather than copied from a developer virtual environment.

- Vosk API 0.3.45, including `libvosk.so`: Apache-2.0; official PyPI Linux amd64
  wheel. Its distribution metadata is retained under `/opt/orbit/python`; the full
  Apache-2.0 text is included under `/usr/share/doc/orbit-launcher/third-party/licenses`.
- Vosk small English model `vosk-model-small-en-us-0.15`: Apache-2.0 as listed at
  https://alphacephei.com/vosk/models. The original README is retained with the model.
- GTK4 Layer Shell 1.0.4, Debian packaging revision 1.0.4-2: MIT library from
  https://github.com/wmww/gtk4-layer-shell; official Debian amd64 package payloads
  are included privately under `/opt/orbit/native`. Original copyright files are
  retained under `/usr/share/doc/orbit-launcher/third-party`. Source is available at
  https://deb.debian.org/debian/pool/main/g/gtk4-layer-shell/gtk4-layer-shell_1.0.4.orig.tar.gz.

The bundled native runtime is specific to the alpha's Pop!_OS/Ubuntu 24.04 amd64
target. It does not install Debian repositories or replace system GTK libraries.
This is not a Debian archive submission or a claim of universal Linux compatibility.
Before publishing general releases, maintain native runtime update and source-build
policies alongside the application itself.

`assets.json` pins downloaded files. Vosk's wheel digest is published by PyPI.
Native package and model digests were recorded from the official HTTPS downloads;
these are reproducibility checks, not a claim of upstream signatures on the model.
Every built package includes a source-tree and bundled-component receipt.
