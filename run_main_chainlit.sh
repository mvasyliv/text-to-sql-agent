#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

MAIN="${ROOT}/main_chainlit.py"
VENV_PYTHON="${ROOT}/venvtext2sql/bin/python"

if [[ ! -f "$MAIN" ]]; then
	echo "Error: main_chainlit.py not found at $MAIN" >&2
	exit 1
fi

find_free_port() {
	local python_bin="$1"
	"$python_bin" - "$@" <<'PY'
import socket

for port in range(8000, 8011):
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
				sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				try:
						sock.bind(("127.0.0.1", port))
				except OSError:
						continue
		print(port)
		raise SystemExit(0)

raise SystemExit(1)
PY
}

if [[ ! -x "$VENV_PYTHON" ]]; then
	echo "Error: venvtext2sql interpreter not found at $VENV_PYTHON" >&2
	echo "Run 'uv sync' to create/update the canonical environment." >&2
	exit 1
fi
PYTHON_BIN="$VENV_PYTHON"

if [[ -z "${CHAINLIT_PORT:-}" ]]; then
	if FREE_PORT="$(find_free_port "$PYTHON_BIN")"; then
		export CHAINLIT_PORT="$FREE_PORT"
		echo "Using CHAINLIT_PORT=$CHAINLIT_PORT"
	fi
fi

exec "$VENV_PYTHON" "$MAIN" "$@"
