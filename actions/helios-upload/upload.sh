#!/usr/bin/env bash
# Upload a directory to Helios ITMO (or any SSH host) — the implementation of action.yml.
# All inputs arrive as INPUT_* environment variables. Requires bash, ssh, tar; rsync is optional.
set -euo pipefail

fail() { echo "::error title=helios-upload::$*"; exit 1; }
# bash 3.2 (macOS) compatible: no ${var,,}, no date +%N
is_true() { case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in true|yes|1) return 0 ;; *) return 1 ;; esac; }
now_ms() {
  if [[ -n "${EPOCHREALTIME:-}" ]]; then local t=${EPOCHREALTIME/[.,]/}; echo $(( 10#$t / 1000 ))
  else echo $(( $(date +%s) * 1000 )); fi
}

HOST=${INPUT_HOST:-helios.cs.ifmo.ru}
PORT=${INPUT_PORT:-2222}
USER_NAME=${INPUT_USERNAME:-}
SOURCE=${INPUT_SOURCE:-.}
DEST=${INPUT_DESTINATION:-}
METHOD=${INPUT_METHOD:-auto}

# ---- validation ---------------------------------------------------------------------------
[[ -n "$USER_NAME" ]] || fail "input 'username' is required"
[[ "$USER_NAME" =~ ^[A-Za-z0-9._-]+$ ]] || fail "username contains unsupported characters"
[[ "$HOST" =~ ^[A-Za-z0-9.:-]+$ ]] || fail "host contains unsupported characters"
[[ "$PORT" =~ ^[0-9]+$ ]] || fail "port must be a number"
[[ -n "${INPUT_KEY:-}" ]] || fail "input 'key' is empty — pass the private key from a secret"
[[ -d "$SOURCE" ]] || fail "source directory '$SOURCE' does not exist"

# Destination is relative to the home directory; it ends up inside single quotes in remote
# commands, so only a conservative character set is accepted.
DEST=${DEST#./}
DEST=${DEST%/}
[[ -n "$DEST" ]] || fail "input 'destination' is required"
[[ "$DEST" =~ ^[A-Za-z0-9._/+-]+$ ]] || fail "destination contains unsupported characters: $DEST"
[[ "$DEST" != /* ]] || fail "destination must be relative to the home directory"
[[ "/$DEST/" != */../* && "/$DEST/" != */./* ]] || fail "destination must not contain '.' or '..' segments"
if is_true "${INPUT_DELETE:-false}"; then
  case "$DEST" in
    public_html) fail "delete: true for the whole public_html would remove every other site — use a subdirectory" ;;
  esac
fi
case "$METHOD" in auto|rsync|tar) ;; *) fail "method must be auto, rsync or tar" ;; esac

# ---- SSH setup: temporary key and strict host key checking -----------------------------------
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
umask 077
printf '%s\n' "$INPUT_KEY" > "$WORK/key"
if [[ -n "${INPUT_KNOWN_HOSTS:-}" ]]; then
  printf '%s\n' "$INPUT_KNOWN_HOSTS" > "$WORK/known_hosts"
elif [[ "$HOST" == helios.cs.ifmo.ru && "$PORT" == 2222 ]]; then
  cp "$ACTION_PATH/helios_known_hosts" "$WORK/known_hosts"
else
  fail "known-hosts is required for $HOST:$PORT (bundled keys cover only helios.cs.ifmo.ru:2222)"
fi
umask 022

SSH_OPTS=(-p "$PORT" -i "$WORK/key" -o IdentitiesOnly=yes -o BatchMode=yes
          -o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$WORK/known_hosts"
          -o ServerAliveInterval=15 -o ServerAliveCountMax=4 -o ConnectTimeout=30)
TARGET="$USER_NAME@$HOST"
# Remote commands are built on purpose on the client side from validated values
# shellcheck disable=SC2029
remote() { ssh "${SSH_OPTS[@]}" "$TARGET" "$@"; }

remote true || fail "SSH connection to $TARGET:$PORT failed (key, username or host key mismatch)"

# ---- method ---------------------------------------------------------------------------------
if [[ "$METHOD" == auto ]]; then
  if command -v rsync >/dev/null && remote 'command -v rsync' >/dev/null 2>&1; then
    METHOD=rsync
  else
    METHOD=tar
  fi
fi
[[ "$METHOD" != rsync ]] || command -v rsync >/dev/null || fail "method: rsync, but rsync is not installed on the runner"

FILES=$(find "$SOURCE" -type f | wc -l | tr -d ' ')
BYTES=$(find "$SOURCE" -type f -exec cat {} + 2>/dev/null | wc -c | tr -d ' ')
echo "Uploading $FILES files ($BYTES bytes) from '$SOURCE' to $TARGET:$DEST via $METHOD$(is_true "${INPUT_DELETE:-false}" && echo ' with --delete')"

start=$(now_ms)
remote "mkdir -p '$DEST'"
if [[ "$METHOD" == rsync ]]; then
  args=(-rlt --compress --stats)
  is_true "${INPUT_DELETE:-false}" && args+=(--delete)
  # ssh options with spaces are safe here: -e is split by rsync on whitespace and none of them
  # contain spaces except the temporary path, which mktemp creates without spaces on runners
  rsync "${args[@]}" -e "ssh ${SSH_OPTS[*]}" "$SOURCE/" "$TARGET:$DEST/"
else
  if is_true "${INPUT_DELETE:-false}"; then
    # Unpack next to the destination, then swap: the old content disappears only after the new
    # one is complete, and an interrupted upload leaves the destination untouched
    tar -C "$SOURCE" -czf - . | remote "set -e; new='$DEST.upload.'\$\$; rm -rf \"\$new\"; mkdir -p \"\$new\";
      tar -xzf - -C \"\$new\"; rm -rf '$DEST.old'; mv '$DEST' '$DEST.old'; mv \"\$new\" '$DEST'; rm -rf '$DEST.old'"
  else
    tar -C "$SOURCE" -czf - . | remote "tar -xzf - -C '$DEST'"
  fi
fi
if is_true "${INPUT_MAKE_READABLE:-true}"; then
  remote "chmod -R a+rX '$DEST'"
fi
end=$(now_ms)
DURATION=$(( end - start ))

URL=""
if [[ "$HOST" == helios.cs.ifmo.ru && "$DEST" == public_html/* ]]; then
  URL="https://se.ifmo.ru/~$USER_NAME/${DEST#public_html/}/"
fi

{
  echo "method=$METHOD"
  echo "files=$FILES"
  echo "bytes=$BYTES"
  echo "duration-ms=$DURATION"
  echo "url=$URL"
} >> "${GITHUB_OUTPUT:-/dev/null}"
echo "::notice title=helios-upload::$FILES files → $TARGET:$DEST via $METHOD in ${DURATION} ms${URL:+ — $URL}"
