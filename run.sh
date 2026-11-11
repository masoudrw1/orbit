#!/usr/bin/env bash
set -euo pipefail
orbit_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$orbit_dir"
export LD_LIBRARY_PATH="$orbit_dir/.runtime/lib:$orbit_dir/.runtime/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
export GI_TYPELIB_PATH="$orbit_dir/.runtime/lib/girepository-1.0:$orbit_dir/.runtime/lib/x86_64-linux-gnu/girepository-1.0:${GI_TYPELIB_PATH:-}"
orbit_python=/usr/bin/python3
if [[ -x "$orbit_dir/.venv/bin/python" ]]; then
  orbit_python="$orbit_dir/.venv/bin/python"
fi
exec "$orbit_python" -m orbit "$@"
