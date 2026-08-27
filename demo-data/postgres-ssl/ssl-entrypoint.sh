#!/usr/bin/env bash
# Wrapper entrypoint for the postgres:16 demo image that enables TLS.
#
# Postgres refuses to start with ssl=on unless the private key file is owned by
# the postgres user (or root) and is not group/world readable. Bind-mounted host
# files keep their host UID/permissions, so we copy them into a postgres-owned
# location with correct ownership/mode before handing off to the real entrypoint.
set -euo pipefail

SRC_DIR=/certs
DST_DIR=/var/lib/postgresql/ssl

mkdir -p "$DST_DIR"
install -o postgres -g postgres -m 0644 "$SRC_DIR/server.crt" "$DST_DIR/server.crt"
install -o postgres -g postgres -m 0600 "$SRC_DIR/server.key" "$DST_DIR/server.key"

exec docker-entrypoint.sh "$@"
