#!/bin/sh
set -eu
sketch_dir=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
build_dir=$(mktemp -d /tmp/bottle-radar-tests.XXXXXX)
trap 'rm -rf "$build_dir"' EXIT
cxx=${CXX:-clang++}
preview_dir=${1:-$sketch_dir/preview}
mkdir -p "$preview_dir"
"$cxx" -std=c++17 -O1 -g -fsanitize=address,undefined "$sketch_dir/tests/bottle_navigation_test.cpp" -o "$build_dir/navigation"
"$build_dir/navigation"
"$cxx" -std=c++17 -O1 -g -fsanitize=address,undefined -DARDUINO=10819 \
  -I"$sketch_dir/tests/host" -I"$sketch_dir/../libraries/Adafruit_GFX_Library" \
  "$sketch_dir/tests/bottle_ui_preview.cpp" "$sketch_dir/../libraries/Adafruit_GFX_Library/Adafruit_GFX.cpp" -o "$build_dir/preview"
"$build_dir/preview" "$preview_dir"
