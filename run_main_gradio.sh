#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

MAIN="${ROOT}/main_gradio.py"
VENV_PYTHON="${ROOT}/venvtext2sql/bin/python"

if [[ ! -f "$MAIN" ]]; then
	echo "Error: main_gradio.py not found at $MAIN" >&2
	exit 1
fi

find_free_port() {
	local python_bin="$1"
	"$python_bin" - <<'PY'
import socket

for port in range(7860, 7871):
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

PYTHON_BIN="$VENV_PYTHON"

if [[ -z "${GRADIO_PORT:-}" ]]; then
	if FREE_PORT="$(find_free_port "$PYTHON_BIN")"; then
		export GRADIO_PORT="$FREE_PORT"
		echo "Using GRADIO_PORT=$GRADIO_PORT"
	fi
fi

exec "$VENV_PYTHON" "$MAIN" "$@"