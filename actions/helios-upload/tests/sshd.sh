#!/usr/bin/env bash
# Throwaway sshd on 127.0.0.1:2222 for tests, running as the current user (no root needed).
#   source tests/sshd.sh                     # sets D (temp dir), KNOWN (known_hosts line), KEY_FILE
#   bash tests/sshd.sh --github-env          # CI: also exports TEST_KNOWN_HOSTS and TEST_KEY to GITHUB_ENV
set -euo pipefail

if ! command -v sshd >/dev/null && [[ ! -x /usr/sbin/sshd ]]; then
  as_root() { if [[ $(id -u) == 0 ]]; then "$@"; else sudo -E "$@"; fi; }
  export DEBIAN_FRONTEND=noninteractive
  as_root apt-get update -qq && as_root apt-get install -y -qq openssh-server openssh-client rsync >/dev/null
fi

D=$(mktemp -d)
ssh-keygen -q -t ed25519 -N '' -f "$D/host_key"
ssh-keygen -q -t ed25519 -N '' -f "$D/client_key"
mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
cat "$D/client_key.pub" >> "$HOME/.ssh/authorized_keys" && chmod 600 "$HOME/.ssh/authorized_keys"
cat > "$D/sshd_config" <<EOF
Port 2222
ListenAddress 127.0.0.1
HostKey $D/host_key
PidFile $D/sshd.pid
AuthorizedKeysFile $HOME/.ssh/authorized_keys
PasswordAuthentication no
KbdInteractiveAuthentication no
UsePAM no
StrictModes no
EOF
mkdir -p /run/sshd 2>/dev/null || sudo mkdir -p /run/sshd 2>/dev/null || true
/usr/sbin/sshd -f "$D/sshd_config" -E "$D/sshd.log"
sleep 1
KNOWN="[127.0.0.1]:2222 $(cut -d' ' -f1,2 "$D/host_key.pub")"
KEY_FILE="$D/client_key"

if [[ "${1:-}" == --github-env ]]; then
  {
    echo "TEST_KNOWN_HOSTS=$KNOWN"
    echo "TEST_KEY<<KEY_EOF"
    cat "$KEY_FILE"
    echo "KEY_EOF"
  } >> "$GITHUB_ENV"
fi
