# JetBrains Venv Checklist

Use this checklist when opening the project in JetBrains IDEs (PyCharm, IntelliJ with Python plugin) to ensure `venvtext2sql` is active.

1. Set the project Python interpreter to `venvtext2sql/bin/python` (Project Settings -> Python Interpreter).
2. In terminal settings, use a shell path that activates the environment, for example: `bash -lc 'source venvtext2sql/bin/activate && exec bash'`.
3. Verify activation in the IDE terminal:
   - `echo $VIRTUAL_ENV` should end with `/venvtext2sql`.
   - `python -c "import sys; print(sys.executable)"` should point to `venvtext2sql/bin/python`.

