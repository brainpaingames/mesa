import sys
import subprocess
import time
import os
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

@pytest.mark.app
def test_solara_app_startup():
    """
    Tests if the Solara app can be launched without crashing immediately.
    """
    command = [
        "solara", "run", "sugarscape_g1mt.app",
        "--", "--mesa-dev"
    ]
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT.parent)
    
    process = subprocess.Popen(command, env=env, cwd=PROJECT_ROOT.parent)
    try:
        time.sleep(15)
        assert process.poll() is None, "Solara app process terminated unexpectedly."
    finally:
        process.terminate()
        process.wait() # Ensure the process is fully cleaned up

@pytest.mark.app
def test_streamlit_app_startup():
    """
    Tests if the Streamlit app can be launched without crashing immediately.
    """
    command = [
        sys.executable, "-m", "streamlit", "run", "sugarscape_g1mt/analysis_app.py",
        "--", "--server.headless", "true"
    ]
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT.parent)

    process = subprocess.Popen(command, env=env, cwd=PROJECT_ROOT.parent)
    try:
        time.sleep(15)
        assert process.poll() is None, "Streamlit app process terminated unexpectedly."
    finally:
        process.terminate()
        process.wait() # Ensure the process is fully cleaned up