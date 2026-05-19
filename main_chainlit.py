"""Launcher for the Chainlit web UI.

This script starts the existing chat app defined in
`src/text_to_sql_agent/ui/chainlit_app.py` so users can ask questions
through a browser.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


APP_PATH = Path(__file__).resolve().parent / "src" / "text_to_sql_agent" / "ui" / "chainlit_app.py"


def _is_enabled(value: str | None, default: bool = True) -> bool:
	if value is None:
		return default
	return value.strip().lower() in {"1", "true", "yes", "on"}


def build_chainlit_command() -> list[str]:
	"""Build CLI command for running the Chainlit UI."""
	host = os.getenv("CHAINLIT_HOST", "127.0.0.1")
	port = os.getenv("CHAINLIT_PORT", "8000")
	headless = _is_enabled(os.getenv("CHAINLIT_HEADLESS"), default=True)

	command = [
		sys.executable,
		"-m",
		"chainlit",
		"run",
		str(APP_PATH),
		"--host",
		host,
		"--port",
		port,
	]
	if headless:
		command.append("--headless")

	return command


def main() -> None:
	"""Start the Chainlit web page for interactive Q&A."""
	if not APP_PATH.exists():
		raise FileNotFoundError(f"Chainlit app file not found: {APP_PATH}")

	command = build_chainlit_command()
	print("Starting Chainlit web UI...")
	print(" ".join(command))
	print("Open your browser at http://127.0.0.1:8000 (or configured host/port).")

	try:
		subprocess.run(command, check=True)
	except KeyboardInterrupt:
		print("Chainlit server stopped.")


if __name__ == "__main__":
	main()
