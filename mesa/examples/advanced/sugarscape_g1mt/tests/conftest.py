import sys
from pathlib import Path

# This is a special pytest configuration file.
# The code in this file is automatically executed by pytest before it runs any tests.

# --- WHY THIS FILE IS NEEDED ---
#
# When running pytest from the project's parent directory (e.g., `.../advanced`),
# pytest needs to know where to find the main application package ('sugarscape_g1mt').
# By default, when executing a test file like `tests/test_e2e_runs.py`, Python's
# import search path might not include the parent directory (`advanced/`), leading
# to `ModuleNotFoundError` when the test tries to do `from sugarscape_g1mt import ...`.
#
# This `conftest.py` file solves this problem robustly.
# 1. It is automatically found and run by pytest.
# 2. It calculates the path to the project's root directory (`.../advanced/`).
# 3. It adds this root directory to Python's system path (`sys.path`).
#
# As a result, any test file can now reliably import the `sugarscape_g1mt` package
# without needing its own `sys.path` manipulation. This centralizes the
# configuration and keeps the individual test files cleaner.

# Add the project's root directory (`.../advanced/`) to the Python path.
# Path(__file__) is this file: `.../advanced/sugarscape_g1mt/tests/conftest.py`
# .parent is `.../tests/`
# .parent.parent is `.../sugarscape_g1mt/`
# .parent.parent.parent is `.../advanced/`
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))