#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$SCRIPT_DIR/../references"
REPO_URL="git@github.com:Textualize/textual.git"
BRANCH="main"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo "Fetching Textual docs..."

git clone \
  --depth 1 \
  --branch "$BRANCH" \
  --no-checkout \
  --filter=blob:none \
  "$REPO_URL" \
  "$TMP_DIR"

git -C "$TMP_DIR" sparse-checkout set docs
git -C "$TMP_DIR" checkout

echo "Syncing docs into $TARGET_DIR..."

rm -rf "$TARGET_DIR"
mv "$TMP_DIR/docs" "$TARGET_DIR"

echo "Done. Textual docs are available at $TARGET_DIR"
