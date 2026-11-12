#!/usr/bin/env bash
# Make a self-signed certificate for the tracker's HTTPS.
# Usage: scripts/make-cert.sh [directory] [host name or IP ...]
# Default directory: ./certs. Writes tracker.crt and tracker.key there.
set -euo pipefail

dir="${1:-certs}"
[ $# -gt 0 ] && shift
names=("${@:-localhost}")
san="DNS:localhost,IP:127.0.0.1"
for n in "${names[@]}"; do
  if [[ "$n" =~ ^[0-9.]+$ || "$n" == *:* ]]; then san+=",IP:$n"; else san+=",DNS:$n"; fi
done

mkdir -p "$dir"
umask 077
openssl req -x509 -newkey rsa:2048 -nodes -days 825 \
  -subj "/CN=${names[0]}" -addext "subjectAltName=$san" \
  -keyout "$dir/tracker.key" -out "$dir/tracker.crt" 2>/dev/null
# The certificate is public; the private key is not. umask 077 already keeps
# the key private, and the explicit 600 makes that independent of the caller's
# umask. Copy both (and chown) if another user, such as the add-on's container
# user, has to read them.
chmod 644 "$dir/tracker.crt"
chmod 600 "$dir/tracker.key"
echo "Wrote $dir/tracker.crt and $dir/tracker.key (valid for: $san)"
