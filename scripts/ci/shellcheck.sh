#!/usr/bin/env bash
# Lints scripts/ci/ at one pinned ShellCheck version everywhere. A runner's packaged
# build and a developer's differ in which findings they report, so an unpinned run makes
# the local equivalent of CI a different check. Usage: shellcheck.sh [repo-root]
#
# Uses an installed shellcheck when it is the pinned version; otherwise downloads that
# release once into a cache directory and verifies its checksum before running it.
set -euo pipefail
root="${1:-.}"
version=0.11.0
case "$(uname -s).$(uname -m)" in
  Linux.x86_64)  platform=linux.x86_64;   sha=8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198 ;;
  Linux.aarch64) platform=linux.aarch64;  sha=12b331c1d2db6b9eb13cfca64306b1b157a86eb69db83023e261eaa7e7c14588 ;;
  Darwin.x86_64) platform=darwin.x86_64;  sha=3c89db4edcab7cf1c27bff178882e0f6f27f7afdf54e859fa041fca10febe4c6 ;;
  Darwin.arm64)  platform=darwin.aarch64; sha=56affdd8de5527894dca6dc3d7e0a99a873b0f004d7aabc30ae407d3f48b0a79 ;;
  *) echo "no pinned shellcheck build for $(uname -s) $(uname -m)"; exit 1 ;;
esac

bin=""
if command -v shellcheck > /dev/null \
   && shellcheck --version | grep -qx "version: $version"; then
  bin="$(command -v shellcheck)"
else
  cache="${XDG_CACHE_HOME:-$HOME/.cache}/delivery-kit/shellcheck-v$version"
  bin="$cache/shellcheck"
  if [ ! -x "$bin" ]; then
    mkdir -p "$cache"
    archive="$cache/shellcheck.tar.xz"
    curl -fsSL -o "$archive" \
      "https://github.com/koalaman/shellcheck/releases/download/v$version/shellcheck-v$version.$platform.tar.xz"
    if ! echo "$sha  $archive" | shasum -a 256 -c - > /dev/null; then
      rm -f "$archive"; echo "shellcheck v$version download failed its checksum"; exit 1
    fi
    tar -xJf "$archive" -C "$cache" --strip-components=1 "shellcheck-v$version/shellcheck"
    rm -f "$archive"
  fi
fi

shopt -s nullglob
scripts=("$root"/scripts/ci/*.sh)
[ "${#scripts[@]}" -gt 0 ] || { echo "no scripts/ci/*.sh under $root"; exit 1; }
"$bin" "${scripts[@]}"
echo "ok: shellcheck v$version on ${#scripts[@]} scripts"
