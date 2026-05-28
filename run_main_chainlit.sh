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

resolve_python() {
	if [[ -x "$VENV_PYTHON" ]]; then
		echo "$VENV_PYTHON"
		return
	fi
	if command -v python3 >/dev/null 2>&1; then
		command -v python3
		return
	fi
	if command -v python >/dev/null 2>&1; then
		command -v python
		return
	fi
	echo ""
}

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

PYTHON_BIN="$(resolve_python)"
if [[ -z "$PYTHON_BIN" ]]; then
	echo "Error: Python interpreter not found." >&2
	exit 1
fi

if [[ -z "${CHAINLIT_PORT:-}" ]]; then
	if FREE_PORT="$(find_free_port "$PYTHON_BIN")"; then
		export CHAINLIT_PORT="$FREE_PORT"
		echo "Using CHAINLIT_PORT=$CHAINLIT_PORT"
	fi
fi

if [[ -x "$VENV_PYTHON" ]]; then
	exec "$VENV_PYTHON" "$MAIN" "$@"
fi

if command -v uv >/dev/null 2>&1; then
	exec uv run python "$MAIN" "$@"
fi

exec python3 "$MAIN" "$@"
