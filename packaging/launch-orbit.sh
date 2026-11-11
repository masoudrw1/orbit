#!/bin/sh
set -eu
orbit_script=$(readlink -f -- "$0")
orbit_dir=$(CDPATH= cd -- "$(dirname -- "$orbit_script")/.." && pwd)
export ORBIT_LAUNCHER="$orbit_script"
export ORBIT_MODEL_DIR="$orbit_dir/models/vosk-model-small-en-us-0.15"
export PYTHONPATH="$orbit_dir/app:$orbit_dir/python"
export LD_LIBRARY_PATH="$orbit_dir/native/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export GI_TYPELIB_PATH="$orbit_dir/native/lib/girepository-1.0${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}"
exec /usr/bin/python3 -P -m orbit "$@"
