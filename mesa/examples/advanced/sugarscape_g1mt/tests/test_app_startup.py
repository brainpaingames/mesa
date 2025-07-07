import sys
import subprocess
import time
import os
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

@pytest.mark.app
def test_streamlit_dashboard_startup():
    """
    Tests if the main Streamlit dashboard can be launched without crashing.
    """
    # The new entry point for the Streamlit application
    app_path = "sugarscape_g1mt/dashboard.py"
    
    command = [
        sys.executable, "-m", "streamlit", "run", app_path,
        "--", "--server.headless", "true"
    ]
    
    # Setting PYTHONPATH ensures that the `sugarscape_g1mt` module can be found
    # when the test is run from the project root.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT.parent)

    process = subprocess.Popen(command, env=env, cwd=PROJECT_ROOT.parent)
    try:
        # Give the app a moment to start up and potentially fail
        time.sleep(15)
        assert process.poll() is None, "Streamlit dashboard process terminated unexpectedly."
    finally:
        process.terminate()
        process.wait() # Ensure the process is fully cleaned up