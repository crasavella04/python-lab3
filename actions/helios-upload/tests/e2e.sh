#!/usr/bin/env bash
# End-to-end test of upload.sh against a throwaway sshd on 127.0.0.1:2222.
# Runs on a GitHub-hosted Ubuntu runner or in a Debian/Ubuntu container:
#   docker run --rm -v "$PWD:/action" -w /action ubuntu:24.04 bash tests/e2e.sh
set -euo pipefail

HERE=$(cd "$(dirname "$0")/.." && pwd)
export ACTION_PATH=$HERE

# shellcheck source=tests/sshd.sh
source "$HERE/tests/sshd.sh"
trap 'kill "$(cat "$D/sshd.pid")" 2>/dev/null || true; rm -rf "$D"' EXIT

# --- helpers -----------------------------------------------------------------------------------
pass=0
ok()   { echo "PASS  $*"; pass=$((pass + 1)); }
bad()  { echo "FAIL  $*"; exit 1; }
run() {   # run upload.sh with the common inputs plus overrides given as VAR=value arguments
  env INPUT_HOST=127.0.0.1 INPUT_PORT=2222 INPUT_USERNAME="$(id -un)" INPUT_KEY="$(cat "$D/client_key")" \
      INPUT_KNOWN_HOSTS="$KNOWN" GITHUB_OUTPUT="$D/out" "$@" bash "$HERE/upload.sh"
}
out() { grep "^$1=" "$D/out" | tail -n 1 | cut -d= -f2-; }

SRC=$(mktemp -d)
mkdir -p "$SRC/sub"; echo one > "$SRC/a.txt"; echo two > "$SRC/sub/b.txt"
for METHOD in rsync tar; do
  DEST="e2e-$METHOD/site"; rm -rf "$HOME/e2e-$METHOD"; : > "$D/out"
  run INPUT_SOURCE="$SRC" INPUT_DESTINATION="$DEST" INPUT_METHOD=$METHOD >/dev/null
  [[ -f "$HOME/$DEST/a.txt" && -f "$HOME/$DEST/sub/b.txt" ]] && ok "$METHOD: files uploaded" || bad "$METHOD: files missing"
  [[ $(out method) == "$METHOD" && $(out files) == 2 ]] && ok "$METHOD: outputs method=$(out method) files=$(out files)" || bad "$METHOD: outputs"
  [[ $(stat -c %a "$HOME/$DEST/a.txt") == 644 ]] && ok "$METHOD: make-readable → 644" || bad "$METHOD: permissions"

  rm "$SRC/a.txt"; echo three > "$SRC/c.txt"
  run INPUT_SOURCE="$SRC" INPUT_DESTINATION="$DEST" INPUT_METHOD=$METHOD >/dev/null
  [[ -f "$HOME/$DEST/a.txt" && -f "$HOME/$DEST/c.txt" ]] && ok "$METHOD: delete=false keeps stale files" || bad "$METHOD: delete=false"
  run INPUT_SOURCE="$SRC" INPUT_DESTINATION="$DEST" INPUT_METHOD=$METHOD INPUT_DELETE=true >/dev/null
  [[ ! -e "$HOME/$DEST/a.txt" && -f "$HOME/$DEST/c.txt" ]] && ok "$METHOD: delete=true removes stale files" || bad "$METHOD: delete=true"
  [[ -z "$(ls -d "$HOME/$DEST".* 2>/dev/null)" ]] && ok "$METHOD: no temporary directories left" || bad "$METHOD: leftovers"
  echo one > "$SRC/a.txt"; rm "$SRC/c.txt"
done

: > "$D/out"
run INPUT_SOURCE="$SRC" INPUT_DESTINATION="public_html/e2e" >/dev/null
[[ $(out url) == "" ]] && ok "auto: no url for a non-Helios host" || bad "url"
[[ $(out method) == rsync ]] && ok "auto: picks rsync when both sides have it" || bad "auto method"

for dest in "../etc" "/tmp/x" "a/../../b" "x;rm -rf ~" "" "."; do
  if run INPUT_SOURCE="$SRC" INPUT_DESTINATION="$dest" >/dev/null 2>&1; then bad "accepted destination '$dest'"; fi
done
ok "rejects unsafe destinations (.., absolute, ;, empty, .)"
if run INPUT_SOURCE="$SRC" INPUT_DESTINATION=public_html INPUT_DELETE=true >/dev/null 2>&1; then bad "delete on public_html"; fi
ok "refuses delete=true on the whole public_html"
if run INPUT_SOURCE="$SRC" INPUT_DESTINATION=x INPUT_KNOWN_HOSTS="[127.0.0.1]:2222 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl" >/dev/null 2>&1; then
  bad "accepted a wrong host key"
fi
ok "rejects a host with a wrong host key"
if env INPUT_HOST=example.org INPUT_PORT=22 INPUT_USERNAME=u INPUT_KEY=k INPUT_SOURCE="$SRC" INPUT_DESTINATION=x \
     bash "$HERE/upload.sh" >/dev/null 2>&1; then bad "non-Helios host without known-hosts"; fi
ok "requires known-hosts for hosts other than Helios"

echo "All $pass checks passed"
