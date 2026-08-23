""" 
    runs every check in this folder

    run it with: python3 tests/run_all.py
"""
import os
import subprocess
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SUITES = ["golden_cli.py", "test_loaders.py", "test_config.py", "test_traverse.py", "test_web.py"]

if __name__ == '__main__':
    failed = []
    for suite in SUITES:
        print(f"\n=== {suite} ===")
        finished = subprocess.run([sys.executable, os.path.join(TESTS_DIR, suite)])
        if finished.returncode:
            failed.append(suite)

    print("\n" + "=" * 40)
    if failed:
        raise SystemExit(f"FAILED: {', '.join(failed)}")
    print(f"all {len(SUITES)} suites passed")
