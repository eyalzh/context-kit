#!/usr/bin/env python3
"""
Simple test runner for the context-kit project.
This can be used to run tests without requiring pytest installation.
"""

import subprocess
import sys
from pathlib import Path


def run_pytest():
    """Run tests with pytest if available."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/e2e/", "-v"],
            cwd=Path(__file__).parent,
        )
        return result.returncode
    except FileNotFoundError:
        print("pytest not found. Install with: pip install pytest pytest-asyncio")
        return 1


def run_single_test():
    """Run tests directly with python unittest if pytest not available."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests/e2e",
                "-p",
                "test_*.py",
                "-v",
            ],
            cwd=Path(__file__).parent,
        )
        return result.returncode
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


if __name__ == "__main__":
    print("Running context-kit e2e tests...")

    # Try pytest first, fall back to unittest
    exit_code = run_pytest()
    if exit_code != 0:
        print("\nPytest failed or not available, trying unittest...")
        exit_code = run_single_test()

    sys.exit(exit_code)
