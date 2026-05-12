# Test Package Layout

The `tests/text_to_sql_agent/` tree mirrors `src/text_to_sql_agent/`.

Rule:
- Place tests for module `src/text_to_sql_agent/<package>/...` under `tests/text_to_sql_agent/<package>/...`.

Examples:
- `src/text_to_sql_agent/prompts/prompt_manifest.py` -> `tests/text_to_sql_agent/prompts/test_prompt_manifest.py`
- `src/text_to_sql_agent/services/sql_service.py` -> `tests/text_to_sql_agent/services/test_sql_service.py`

Notes:
- Keep shared fixtures in `tests/conftest.py` or package-local `conftest.py` files.
- Empty package directories can contain `.gitkeep` to preserve the structure in git.
- For packages without real tests yet, keep a scaffold file named `test_<package>_scaffold.py` as a temporary placeholder.
