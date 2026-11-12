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
# We try two paths in order:
#   1. Headless kiwix-serve binary — scriptable, ideal.
#   2. Kiwix.app GUI (Homebrew cask) — fallback; `oracle serve` opens it with your ZIMs.
#
# The kiwix.org CDN is sometimes very slow. If the binary download times out, the
# cask still installs the GUI app and the oracle degrades gracefully.
install_kiwix_binary() {
  case "$OS-$ARCH" in
    Darwin-arm64)  platform="macos-arm64" ;;
    Darwin-x86_64) platform="macos-x86_64" ;;
    Linux-aarch64) platform="linux-aarch64" ;;
    Linux-x86_64)  platform="linux-x86_64" ;;
    *)
      echo "    (no prebuilt kiwix-tools for $OS/$ARCH)"
      return 1
      ;;
  esac

  latest_url="$(curl -sL --max-time 30 https://download.kiwix.org/release/kiwix-tools/ \
    | grep -oE "kiwix-tools_${platform}-[0-9][^\"]*\.tar\.gz" \
    | sort -V | tail -1)"
  if [[ -z "$latest_url" ]]; then
    echo "    (could not list kiwix-tools releases)"
    return 1
  fi
  full_url="https://download.kiwix.org/release/kiwix-tools/$latest_url"
  echo "      → $full_url"

  tmpdir="$(mktemp -d)"
  if ! curl -L --fail --retry 5 --retry-delay 5 --retry-all-errors --max-time 600 \
            --continue-at - -o "$tmpdir/kt.tar.gz" "$full_url"; then
    rm -rf "$tmpdir"
    return 1
  fi
  tar -xzf "$tmpdir/kt.tar.gz" -C "$tmpdir" || { rm -rf "$tmpdir"; return 1; }

  src_bin="$(find "$tmpdir" -maxdepth 3 -type f -name kiwix-serve | head -1)"
  if [[ -z "$src_bin" ]]; then
    rm -rf "$tmpdir"
    return 1
  fi
  install -m 0755 "$src_bin" "$BIN_DIR/kiwix-serve"
  rm -rf "$tmpdir"
  return 0
}

if [[ -x "$BIN_DIR/kiwix-serve" ]]; then
  echo "  [ok] kiwix-serve already installed at $BIN_DIR/kiwix-serve"
elif command -v kiwix-serve >/dev/null 2>&1; then
  echo "  [ok] kiwix-serve on PATH ($(command -v kiwix-serve))"
else
  echo "  [+] fetching kiwix-tools prebuilt binary (may be slow — kiwix.org CDN)"
  if install_kiwix_binary; then
    echo "  [ok] installed kiwix-serve → $BIN_DIR/kiwix-serve"
  else
    echo "  [!] headless kiwix-serve unavailable — falling back to Kiwix.app GUI"
    if [[ "$OS" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
      if [[ ! -d /Applications/Kiwix.app ]]; then
        brew install --cask kiwix || echo "  [!] cask install failed; manual install needed"
      else
        echo "  [ok] Kiwix.app already installed"
      fi
    else
      echo "  [!] install kiwix-serve manually: https://github.com/kiwix/kiwix-tools"
    fi
  fi
fi

echo "==> Deps OK"
