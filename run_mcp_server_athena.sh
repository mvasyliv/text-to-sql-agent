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

: "${ATHENA_AWS_REGION:?Error: ATHENA_AWS_REGION is not set.}"
: "${ATHENA_S3_OUTPUT_LOCATION:?Error: ATHENA_S3_OUTPUT_LOCATION is not set.}"
: "${ATHENA_WORKGROUP:?Error: ATHENA_WORKGROUP is not set.}"
: "${ATHENA_CATALOG:?Error: ATHENA_CATALOG is not set.}"
: "${ATHENA_SCHEMA:?Error: ATHENA_SCHEMA is not set.}"

if command -v aws >/dev/null 2>&1; then
	if ! aws athena list-data-catalogs --region "$ATHENA_AWS_REGION" --max-results 5 >/dev/null 2>&1; then
		echo "Warning: Athena catalog preflight failed; continuing to start MCP server." >&2
	fi
	if ! aws s3 ls "$ATHENA_S3_OUTPUT_LOCATION" >/dev/null 2>&1; then
		echo "Warning: Athena S3 preflight failed; continuing to start MCP server." >&2
	fi
else
	echo "Warning: aws CLI not found; skipping Athena preflight checks." >&2
fi

SERVER_CMD="${MCP_ATHENA_SERVER_CMD:-${ATHENA_MCP_SERVER_CMD:-athena-mcp-server}}"
if ! command -v "$SERVER_CMD" >/dev/null 2>&1; then
	echo "Error: Athena MCP server command not found: $SERVER_CMD" >&2
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
	--transport "${MCP_ATHENA_TRANSPORT:-stdio}" \
	--region "$ATHENA_AWS_REGION" \
	--s3-output-location "$ATHENA_S3_OUTPUT_LOCATION" \
	--workgroup "$ATHENA_WORKGROUP" \
	--catalog "$ATHENA_CATALOG" \
	--schema "$ATHENA_SCHEMA" \
	--timeout-ms "${MCP_ATHENA_TIMEOUT_MS:-120000}" \
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
