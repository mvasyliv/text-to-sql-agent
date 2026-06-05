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
	PGPASSWORD="$PG_PASSWORD" pg_isready \
		-h "$PG_HOST" \
		-p "$PG_PORT" \
		-d "$PG_DATABASE" \
		-U "$PG_USER"
else
	echo "Warning: pg_isready not found; skipping PostgreSQL preflight." >&2
fi

SERVER_CMD="${MCP_POSTGRESQL_SERVER_CMD:-${POSTGRESQL_MCP_SERVER_CMD:-postgresql-mcp-server}}"
if ! command -v "$SERVER_CMD" >/dev/null 2>&1; then
	echo "Error: PostgreSQL MCP server command not found: $SERVER_CMD" >&2
	exit 1
fi

exec "$SERVER_CMD" \
	--transport "${MCP_POSTGRESQL_TRANSPORT:-stdio}" \
	--host "$PG_HOST" \
	--port "$PG_PORT" \
	--user "$PG_USER" \
	--password "$PG_PASSWORD" \
	--database "$PG_DATABASE" \
	--ssl-mode "${PG_SSL_MODE:-disable}" \
	"$@"