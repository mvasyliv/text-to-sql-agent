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

SQLITE_PATH="${SQLITE_PATH:-}"
if [[ -z "$SQLITE_PATH" ]]; then
	echo "Error: SQLITE_PATH is not set." >&2
	exit 1
fi
if [[ ! -f "$SQLITE_PATH" ]]; then
	echo "Error: SQLite database not found at $SQLITE_PATH" >&2
	exit 1
fi

SERVER_CMD="${MCP_SQLITE_SERVER_CMD:-${SQLITE_MCP_SERVER_CMD:-sqlite-mcp-server}}"
if ! command -v "$SERVER_CMD" >/dev/null 2>&1; then
	echo "Error: SQLite MCP server command not found: $SERVER_CMD" >&2
	exit 1
fi

exec "$SERVER_CMD" \
	--transport "${MCP_SQLITE_TRANSPORT:-stdio}" \
	--db "$SQLITE_PATH" \
	"$@"