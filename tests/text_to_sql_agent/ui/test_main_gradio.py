"""Focused tests for the Gradio launcher entrypoint."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MAIN_GRADIO_PATH = REPO_ROOT / "main_gradio.py"


def _load_main_gradio_module():
    spec = importlib.util.spec_from_file_location("test_main_gradio_module", MAIN_GRADIO_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prepare_runtime_environment_adds_src_path_and_prints_warnings(monkeypatch, capsys) -> None:
    module = _load_main_gradio_module()

    class FakeEnvResult:
        warnings = ["warning-a", "warning-b"]

    src_path = str(module.SRC_PATH)
    sys.path = [path for path in sys.path if path != src_path]

    import text_to_sql_agent.config as config_module

    monkeypatch.setattr(
        config_module,
        "load_runtime_environment",
        lambda project_root: FakeEnvResult(),
    )

    module._prepare_runtime_environment()

    captured = capsys.readouterr()
    assert sys.path[0] == src_path
    assert "Config warning: warning-a" in captured.out
    assert "Config warning: warning-b" in captured.out


def test_main_launches_gradio_app_with_env_host_and_port(monkeypatch) -> None:
    module = _load_main_gradio_module()
    launch_calls: list[dict[str, object]] = []
    queue_calls: list[str] = []

    class FakeApp:
        def queue(self) -> None:
            queue_calls.append("queue")

        def launch(self, **kwargs: object) -> None:
            launch_calls.append(kwargs)

    monkeypatch.setattr(module, "_prepare_runtime_environment", lambda: None)

    import text_to_sql_agent.ui.gradio_app as gradio_app_module

    monkeypatch.setattr(gradio_app_module, "create_app", lambda: FakeApp())
    monkeypatch.setenv("GRADIO_HOST", "0.0.0.0")
    monkeypatch.setenv("GRADIO_PORT", "8899")

    module.main()

    assert queue_calls == ["queue"]
    assert launch_calls == [
        {
            "server_name": "0.0.0.0",
            "server_port": 8899,
            "share": False,
            "show_error": True,
        }
    ]