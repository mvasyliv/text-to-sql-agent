"""Launcher for the Streamlit web UI."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
SRC_PATH = APP_ROOT / "src"
APP_PATH = APP_ROOT / "src" / "text_to_sql_agent" / "ui" / "streamlit_app.py"


def _build_streamlit_base_command() -> list[str]:
    """Resolve a runnable Streamlit command for the current machine."""
    if importlib.util.find_spec("streamlit") is not None:
        return [sys.executable, "-m", "streamlit"]

    streamlit_bin = shutil.which("streamlit")
    if streamlit_bin:
        return [streamlit_bin]

    uv_bin = shutil.which("uv")
    if uv_bin:
        return [uv_bin, "run", "streamlit"]

    raise RuntimeError(
        "Streamlit is unavailable. Install dependencies with 'uv sync' or install "
        "streamlit in the active Python environment."
    )


def build_streamlit_command() -> list[str]:
    host = os.getenv("STREAMLIT_HOST", "127.0.0.1")
    port = os.getenv("STREAMLIT_PORT", "8501")
    base_command = _build_streamlit_base_command()
    return [
        *base_command,
        "run",
        str(APP_PATH),
        "--server.address",
        host,
        "--server.port",
        port,
    ]


def _build_runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    pythonpath_parts = [str(SRC_PATH), str(APP_ROOT)]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    return env


def _prepare_runtime_environment() -> None:
    if str(SRC_PATH) not in sys.path:
        sys.path.insert(0, str(SRC_PATH))

    from text_to_sql_agent.config import load_runtime_environment

    result = load_runtime_environment(project_root=APP_ROOT)
    for warning in result.warnings:
        print(f"Config warning: {warning}")


def main() -> None:
    if not APP_PATH.exists():
        raise FileNotFoundError(f"Streamlit app file not found: {APP_PATH}")

    _prepare_runtime_environment()

    command = build_streamlit_command()
    host = os.getenv("STREAMLIT_HOST", "127.0.0.1")
    port = os.getenv("STREAMLIT_PORT", "8501")
    print("Starting Streamlit web UI...")
    print(" ".join(command))
    print(f"Open your browser at http://{host}:{port}.")

    try:
        subprocess.run(command, check=True, cwd=str(APP_ROOT), env=_build_runtime_env())
    except RuntimeError as exc:
        print(f"Failed to prepare Streamlit command: {exc}")
        raise
    except subprocess.CalledProcessError as exc:
        print("Streamlit process exited with an error.")
        print(f"Command: {' '.join(exc.cmd)}")
        raise
    except KeyboardInterrupt:
        print("Streamlit server stopped.")


if __name__ == "__main__":
    main()

