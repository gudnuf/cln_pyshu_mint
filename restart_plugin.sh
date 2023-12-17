#! /usr/bin/env nix-shell
#! nix-shell -i bash -p bash

set -eu

. ./.env

if [ ! -f "$PLUGIN_PATH" ]; then
  echo "Error: Path to plugin not found. Check the .testing.env file"
  exit 1
fi

if [ $# -eq 0 ]; then
  NODE_NUM=2
else
  NODE_NUM="$1"
fi

LN_DIR="$PATH_TO_LIGHTNING/l$NODE_NUM"

if [ ! -d "$LN_DIR" ]; then
  echo "Error: Lightning directory not found. Make sure your node is started"
  exit 1
fi

LN_CLI="$LIGHTNING_BIN_DIR/lightning-cli --lightning-dir=$LN_DIR"

if $LN_CLI plugin list | grep -q "$PLUGIN_PATH"; then
     $LN_CLI plugin stop "$PLUGIN_PATH" >> /dev/null
fi

$LN_CLI plugin start "$PLUGIN_PATH"