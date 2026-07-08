#!/usr/bin/env bash
set -euo pipefail

# User-local installer for nvai-cli.
# Intended usage after publishing to GitHub:
#   curl -fsSL https://raw.githubusercontent.com/cjakma/nvai-cli/main/scripts/install-user.sh | bash
#
# Optional environment variables:
#   NVAI_REPO_URL     Git repository URL to clone. Required unless NVAI_SOURCE_DIR is set.
#   NVAI_REF          Git ref/branch/tag to install. Default: main
#   NVAI_SOURCE_DIR   Local source tree to install from, useful for tests/development.
#   NVAI_INSTALL_DIR  Install location. Default: ~/.local/share/nvai-cli
#   NVAI_BIN_DIR      Wrapper location. Default: ~/.local/bin

log() { printf '[nvai install] %s\n' "$*"; }
fail() { printf '[nvai install] ERROR: %s\n' "$*" >&2; exit 1; }

NVAI_REF="${NVAI_REF:-main}"
NVAI_INSTALL_DIR="${NVAI_INSTALL_DIR:-$HOME/.local/share/nvai-cli}"
NVAI_BIN_DIR="${NVAI_BIN_DIR:-$HOME/.local/bin}"
NVAI_APP_DIR="$NVAI_INSTALL_DIR/app"
NVAI_VENV_DIR="$NVAI_INSTALL_DIR/.venv"
NVAI_WRAPPER="$NVAI_BIN_DIR/nvai"

if [ -n "${NVAI_SOURCE_DIR:-}" ]; then
  [ -d "$NVAI_SOURCE_DIR" ] || fail "NVAI_SOURCE_DIR does not exist: $NVAI_SOURCE_DIR"
elif [ -z "${NVAI_REPO_URL:-}" ]; then
  fail "NVAI_REPO_URL is required when installing from curl. Example: NVAI_REPO_URL=https://github.com/cjakma/nvai-cli.git bash install-user.sh"
fi

command -v python3 >/dev/null 2>&1 || fail "python3 is required"

mkdir -p "$NVAI_INSTALL_DIR" "$NVAI_BIN_DIR"

TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

log "install dir: $NVAI_INSTALL_DIR"
log "bin dir: $NVAI_BIN_DIR"

if [ -n "${NVAI_SOURCE_DIR:-}" ]; then
  log "copying local source: $NVAI_SOURCE_DIR"
  mkdir -p "$TMP_DIR/src"
  tar \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='*.egg-info' \
    -C "$NVAI_SOURCE_DIR" -cf - . | tar -C "$TMP_DIR/src" -xf -
else
  command -v git >/dev/null 2>&1 || fail "git is required to clone NVAI_REPO_URL"
  log "cloning $NVAI_REPO_URL ref=$NVAI_REF"
  git clone --depth 1 --branch "$NVAI_REF" "$NVAI_REPO_URL" "$TMP_DIR/src" >/dev/null 2>&1 || \
    fail "failed to clone $NVAI_REPO_URL ref=$NVAI_REF"
fi

[ -f "$TMP_DIR/src/pyproject.toml" ] || fail "source tree does not look like nvai-cli: missing pyproject.toml"

rm -rf "$NVAI_APP_DIR"
mkdir -p "$NVAI_APP_DIR"
tar -C "$TMP_DIR/src" -cf - . | tar -C "$NVAI_APP_DIR" -xf -

if command -v uv >/dev/null 2>&1; then
  log "creating virtualenv with uv"
  uv venv "$NVAI_VENV_DIR" --python 3.11 --clear >/dev/null
  log "installing nvai-cli with uv"
  uv pip install --python "$NVAI_VENV_DIR/bin/python" "$NVAI_APP_DIR" >/dev/null
else
  log "creating virtualenv with python3 -m venv"
  rm -rf "$NVAI_VENV_DIR"
  python3 -m venv "$NVAI_VENV_DIR"
  log "installing nvai-cli with pip"
  "$NVAI_VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
  "$NVAI_VENV_DIR/bin/python" -m pip install "$NVAI_APP_DIR" >/dev/null
fi

cat > "$NVAI_WRAPPER" <<EOF
#!/usr/bin/env bash
set -euo pipefail
NVAI_PYTHON="$NVAI_VENV_DIR/bin/python"
if [ ! -x "\$NVAI_PYTHON" ]; then
  echo "nvai: installed Python not found: \$NVAI_PYTHON" >&2
  echo "nvai: reinstall with the nvai install script" >&2
  exit 127
fi
exec "\$NVAI_PYTHON" -m nvai.cli "\$@"
EOF
chmod +x "$NVAI_WRAPPER"

case ":$PATH:" in
  *":$NVAI_BIN_DIR:"*) log "PATH already contains $NVAI_BIN_DIR" ;;
  *)
    log "$NVAI_BIN_DIR is not in current PATH"
    if [ "$NVAI_BIN_DIR" = "$HOME/.local/bin" ]; then
      if ! grep -F 'export PATH="$HOME/.local/bin:$PATH"' "$HOME/.bashrc" >/dev/null 2>&1; then
        printf '\n# nvai-cli user-local bin\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$HOME/.bashrc"
        log "added ~/.local/bin to ~/.bashrc; open a new shell or run: source ~/.bashrc"
      fi
    else
      log "add this to your shell profile: export PATH=\"$NVAI_BIN_DIR:\$PATH\""
    fi
    ;;
esac

log "installed wrapper: $NVAI_WRAPPER"
"$NVAI_WRAPPER" --help >/dev/null
log "ok: run 'nvai' to start, or 'nvai doctor' to inspect the installation"
