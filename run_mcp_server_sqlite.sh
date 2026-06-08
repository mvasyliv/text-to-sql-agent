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

# Convert terminal interrupts into TERM for cleaner AnyIO/FastMCP shutdown.
_server_pid=""
_shutdown() {
	if [[ -n "${_server_pid}" ]] && kill -0 "${_server_pid}" >/dev/null 2>&1; then
		kill -TERM "${_server_pid}" >/dev/null 2>&1 || true
	fi
}
trap _shutdown INT TERM

"$SERVER_CMD" \
	--transport "${MCP_SQLITE_TRANSPORT:-stdio}" \
	--db "$SQLITE_PATH" \
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
