"""Launcher for the Gradio web UI."""

from __future__ import annotations

import os
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
SRC_PATH = APP_ROOT / "src"


def _prepare_runtime_environment() -> None:
    if str(SRC_PATH) not in sys.path:
        sys.path.insert(0, str(SRC_PATH))

    from text_to_sql_agent.config import load_runtime_environment

    result = load_runtime_environment(project_root=APP_ROOT)
    for warning in result.warnings:
        print(f"Config warning: {warning}")


def main() -> None:
    _prepare_runtime_environment()

    from text_to_sql_agent.ui.gradio_app import create_app

    host = os.getenv("GRADIO_HOST", "127.0.0.1")
    port = int(os.getenv("GRADIO_PORT", "7860"))
    app = create_app()

    print("Starting Gradio web UI...")
    print(f"Open your browser at http://{host}:{port}.")

    app.queue()
    app.launch(
        server_name=host,
        server_port=port,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
