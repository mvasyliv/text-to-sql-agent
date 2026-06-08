#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

ENV_FILE="${TEXT_TO_SQL_ENV_FILE:-$ROOT/.env.dev}"
if [[ -f "$ENV_FILE" ]]; then
	set -a
	# shellcheck disable=SC1090
	source "$ENV_FILE"
	set +a
fi

: "${PG_HOST:?Error: PG_HOST is not set.}"
: "${PG_PORT:?Error: PG_PORT is not set.}"
: "${PG_USER:?Error: PG_USER is not set.}"
: "${PG_PASSWORD:?Error: PG_PASSWORD is not set.}"
: "${PG_DATABASE:?Error: PG_DATABASE is not set.}"

if command -v pg_isready >/dev/null 2>&1; then
	if ! PGPASSWORD="$PG_PASSWORD" pg_isready \
		-h "$PG_HOST" \
		-p "$PG_PORT" \
		-d "$PG_DATABASE" \
		-U "$PG_USER" >/dev/null 2>&1; then
		echo "Warning: PostgreSQL preflight failed; continuing to start MCP server." >&2
	fi
else
	echo "Warning: pg_isready not found; skipping PostgreSQL preflight." >&2
fi

SERVER_CMD="${MCP_POSTGRESQL_SERVER_CMD:-${POSTGRESQL_MCP_SERVER_CMD:-postgresql-mcp-server}}"
if ! command -v "$SERVER_CMD" >/dev/null 2>&1; then
	echo "Error: PostgreSQL MCP server command not found: $SERVER_CMD" >&2
	exit 1
fi

# Compatibility mapping for postgresql-mcp-server implementations that require env keys.
PG_DEFAULT_SCHEMA="${PG_DEFAULT_SCHEMA:-${POSTGRES_DEFAULT_SCHEMA:-public}}"
export POSTGRES_HOST="${POSTGRES_HOST:-$PG_HOST}"
export POSTGRES_PORT="${POSTGRES_PORT:-$PG_PORT}"
export POSTGRES_USER="${POSTGRES_USER:-$PG_USER}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$PG_PASSWORD}"
export POSTGRES_DEFAULT_DATABASE="${POSTGRES_DEFAULT_DATABASE:-$PG_DATABASE}"
export POSTGRES_DEFAULT_SCHEMA="${POSTGRES_DEFAULT_SCHEMA:-$PG_DEFAULT_SCHEMA}"
export POSTGRES_ALLOWED_DATABASES="${POSTGRES_ALLOWED_DATABASES:-$PG_DATABASE}"
export POSTGRES_DATABASE_SCHEMAS="${POSTGRES_DATABASE_SCHEMAS:-$PG_DATABASE:$PG_DEFAULT_SCHEMA}"

# Convert terminal interrupts into TERM for cleaner AnyIO/FastMCP shutdown.
_server_pid=""
_shutdown() {
	if [[ -n "${_server_pid}" ]] && kill -0 "${_server_pid}" >/dev/null 2>&1; then
		kill -TERM "${_server_pid}" >/dev/null 2>&1 || true
	fi
}
trap _shutdown INT TERM

"$SERVER_CMD" \
	--transport "${MCP_POSTGRESQL_TRANSPORT:-stdio}" \
	--host "$PG_HOST" \
	--port "$PG_PORT" \
	--user "$PG_USER" \
	--password "$PG_PASSWORD" \
	--database "$PG_DATABASE" \
	--ssl-mode "${PG_SSL_MODE:-disable}" \
	"$@" &
_server_pid=$!

set +e
wait "${_server_pid}"
_exit_code=$?
set -e

trap - INT TERM
if [[ "${_exit_code}" -eq 130 || "${_exit_code}" -eq 143 ]]; then
	exit 0
fi
exit "${_exit_code}"
