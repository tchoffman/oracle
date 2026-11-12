#!/usr/bin/env bash
# Install system dependencies for the oracle. Idempotent — safe to re-run.
#
# - ollama: installed via Homebrew (has Metal/GPU acceleration on Apple Silicon)
# - kiwix-serve: Homebrew doesn't ship it; we grab the official prebuilt binary
#   from https://download.kiwix.org/release/kiwix-tools/ and drop it in build/bin/.
set -euo pipefail

cd "$(dirname "$0")/.."

OS="$(uname -s)"       # Darwin / Linux
ARCH="$(uname -m)"     # arm64 / x86_64
BIN_DIR="build/bin"
mkdir -p "$BIN_DIR"

echo "==> Checking system dependencies ($OS/$ARCH)"

# ---- ollama ----
if command -v ollama >/dev/null 2>&1; then
  echo "  [ok] ollama already installed ($(ollama --version 2>&1 | head -1))"
else
  if command -v brew >/dev/null 2>&1; then
    echo "  [+] installing ollama via brew"
    brew install ollama
  else
    echo "Error: ollama missing and Homebrew not found." >&2
    echo "Install from https://ollama.com/download" >&2
    exit 1
  fi
fi

# Start the Ollama server if it's not already running.
if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "==> Starting Ollama server in background"
  (nohup ollama serve >/dev/null 2>&1 &) || true
  for _ in {1..10}; do
    curl -sf http://localhost:11434/api/tags >/dev/null 2>&1 && break
    sleep 1
  done
fi

# ---- kiwix-serve ----
if [[ -x "$BIN_DIR/kiwix-serve" ]]; then
  echo "  [ok] kiwix-serve already installed at $BIN_DIR/kiwix-serve"
elif command -v kiwix-serve >/dev/null 2>&1; then
  echo "  [ok] kiwix-serve on PATH ($(command -v kiwix-serve))"
else
  echo "  [+] fetching kiwix-tools prebuilt binary"

  case "$OS-$ARCH" in
    Darwin-arm64)  platform="macos-arm64" ;;
    Darwin-x86_64) platform="macos-x86_64" ;;
    Linux-aarch64) platform="linux-aarch64" ;;
    Linux-x86_64)  platform="linux-x86_64" ;;
    *)
      echo "Error: no prebuilt kiwix-tools for $OS/$ARCH. Build from source: https://github.com/kiwix/kiwix-tools" >&2
      exit 1
      ;;
  esac

  # Find the latest release tarball for this platform.
  latest_url="$(curl -sL https://download.kiwix.org/release/kiwix-tools/ \
    | grep -oE "kiwix-tools_${platform}-[0-9][^\"]*\.tar\.gz" \
    | sort -V | tail -1)"
  if [[ -z "$latest_url" ]]; then
    echo "Error: could not find kiwix-tools release for $platform" >&2
    exit 1
  fi
  full_url="https://download.kiwix.org/release/kiwix-tools/$latest_url"
  echo "      → $full_url"

  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT
  # kiwix.org can be flaky — retry aggressively and allow resume.
  curl -L --fail --retry 10 --retry-delay 5 --retry-all-errors \
       --continue-at - -o "$tmpdir/kt.tar.gz" "$full_url"
  tar -xzf "$tmpdir/kt.tar.gz" -C "$tmpdir"

  # The archive contains a directory like kiwix-tools_macos-arm64-3.8.2/ with binaries.
  src_bin="$(find "$tmpdir" -maxdepth 3 -type f -name kiwix-serve -perm +111 2>/dev/null | head -1)"
  if [[ -z "$src_bin" ]]; then
    src_bin="$(find "$tmpdir" -maxdepth 3 -type f -name kiwix-serve | head -1)"
  fi
  if [[ -z "$src_bin" ]]; then
    echo "Error: kiwix-serve not found inside archive" >&2
    exit 1
  fi
  install -m 0755 "$src_bin" "$BIN_DIR/kiwix-serve"
  echo "  [ok] installed kiwix-serve → $BIN_DIR/kiwix-serve"
fi

echo "==> Deps OK"
