"""Launcher for the Chainlit web UI.

This script starts the existing chat app defined in
`src/text_to_sql_agent/ui/chainlit_app.py` so users can ask questions
through a browser.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
SRC_PATH = APP_ROOT / "src"
APP_PATH = Path(__file__).resolve().parent / "src" / "text_to_sql_agent" / "ui" / "chainlit_app.py"


def _is_enabled(value: str | None, default: bool = True) -> bool:
	if value is None:
		return default
	return value.strip().lower() in {"1", "true", "yes", "on"}


def _build_chainlit_base_command() -> list[str]:
	"""Resolve a runnable Chainlit command for the current machine.

	Resolution order:
	1) current interpreter module (`python -m chainlit`)
	2) shell executable (`chainlit`)
	3) project-managed executable (`uv run chainlit`)
	"""
	if importlib.util.find_spec("chainlit") is not None:
		return [sys.executable, "-m", "chainlit"]

	chainlit_bin = shutil.which("chainlit")
	if chainlit_bin:
		return [chainlit_bin]

	uv_bin = shutil.which("uv")
	if uv_bin:
		return [uv_bin, "run", "chainlit"]

	raise RuntimeError(
		"Chainlit is unavailable. Install dependencies with 'uv sync' or install "
		"chainlit in the active Python environment."
	)


def build_chainlit_command() -> list[str]:
	"""Build CLI command for running the Chainlit UI."""
	host = os.getenv("CHAINLIT_HOST", "127.0.0.1")
	port = os.getenv("CHAINLIT_PORT", "8000")
	headless = _is_enabled(os.getenv("CHAINLIT_HEADLESS"), default=True)
	base_command = _build_chainlit_base_command()

	command = [
		*base_command,
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


def _build_runtime_env() -> dict[str, str]:
	"""Build subprocess environment with project import paths."""
	env = os.environ.copy()
	pythonpath_parts = [str(SRC_PATH), str(APP_ROOT)]
	existing_pythonpath = env.get("PYTHONPATH")
	if existing_pythonpath:
		pythonpath_parts.append(existing_pythonpath)
	env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
	return env


def main() -> None:
	"""Start the Chainlit web page for interactive Q&A."""
	if not APP_PATH.exists():
		raise FileNotFoundError(f"Chainlit app file not found: {APP_PATH}")

	command = build_chainlit_command()
	host = os.getenv("CHAINLIT_HOST", "127.0.0.1")
	port = os.getenv("CHAINLIT_PORT", "8000")
	print("Starting Chainlit web UI...")
	print(" ".join(command))
	print(f"Open your browser at http://{host}:{port}.")

	try:
		subprocess.run(command, check=True, cwd=str(APP_ROOT), env=_build_runtime_env())
	except RuntimeError as exc:
		print(f"Failed to prepare Chainlit command: {exc}")
		raise
	except subprocess.CalledProcessError as exc:
		print("Chainlit process exited with an error.")
		print(f"Command: {' '.join(exc.cmd)}")
		raise
	except KeyboardInterrupt:
		print("Chainlit server stopped.")


if __name__ == "__main__":
	main()
