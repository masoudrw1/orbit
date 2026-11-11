#!/usr/bin/env bash
# Build the upstream library into this checkout, without sudo or a system install.
set -euo pipefail
orbit_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
orbit_runtime="$orbit_dir/.runtime"
orbit_source="$orbit_runtime/source-1.0.4"
orbit_build="$orbit_runtime/build-1.0.4"
for orbit_tool in curl tar meson ninja pkg-config gcc g-ir-scanner; do
  if ! command -v "$orbit_tool" >/dev/null; then
    echo "Missing $orbit_tool. See the native dependency command in docs/START_HERE_FA.md."
    exit 1
  fi
done
for orbit_pkg in gtk4 wayland-client wayland-protocols gobject-introspection-1.0; do
  pkg-config --exists "$orbit_pkg" || { echo "Missing development library: $orbit_pkg"; exit 1; }
done
mkdir -p "$orbit_runtime"
if [[ ! -d "$orbit_source" ]]; then
  curl --fail --location --output "$orbit_runtime/layer-shell-1.0.4.tar.gz" \
    https://github.com/wmww/gtk4-layer-shell/archive/refs/tags/v1.0.4.tar.gz
  mkdir -p "$orbit_source"
  tar --extract --gzip --file "$orbit_runtime/layer-shell-1.0.4.tar.gz" \
    --directory "$orbit_source" --strip-components=1
fi
if [[ ! -f "$orbit_build/build.ninja" ]]; then
  meson setup "$orbit_build" "$orbit_source" --prefix="$orbit_runtime" --libdir=lib \
    -Dexamples=false -Ddocs=false -Dtests=false -Dvapi=false -Dintrospection=true
fi
meson compile -C "$orbit_build"
meson install -C "$orbit_build" --no-rebuild
echo 'Layer Shell built locally. Start Orbit with: bash run.sh'
