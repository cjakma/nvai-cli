#!/usr/bin/env bash
set -euo pipefail

# User-local uninstaller for nvai-cli.
# Defaults remove the installed app and wrapper, but keep user config/API keys.
# Set NVAI_REMOVE_CONFIG=1 to also remove ~/.config/nvai and ~/.local/share/nvai.

log() { printf '[nvai uninstall] %s\n' "$*"; }

NVAI_INSTALL_DIR="${NVAI_INSTALL_DIR:-$HOME/.local/share/nvai-cli}"
NVAI_BIN_DIR="${NVAI_BIN_DIR:-$HOME/.local/bin}"
NVAI_WRAPPER="$NVAI_BIN_DIR/nvai"

if [ -e "$NVAI_WRAPPER" ]; then
  rm -f "$NVAI_WRAPPER"
  log "removed wrapper: $NVAI_WRAPPER"
else
  log "wrapper not found: $NVAI_WRAPPER"
fi

if [ -d "$NVAI_INSTALL_DIR" ]; then
  rm -rf "$NVAI_INSTALL_DIR"
  log "removed install dir: $NVAI_INSTALL_DIR"
else
  log "install dir not found: $NVAI_INSTALL_DIR"
fi

if [ "${NVAI_REMOVE_CONFIG:-0}" = "1" ]; then
  rm -rf "$HOME/.config/nvai" "$HOME/.local/share/nvai"
  log "removed user config and data: ~/.config/nvai ~/.local/share/nvai"
else
  log "kept user config/API keys. To remove them: NVAI_REMOVE_CONFIG=1 bash scripts/uninstall-user.sh"
fi

log "done"
