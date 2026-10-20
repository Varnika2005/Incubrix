#!/usr/bin/env python3
"""
ClipPilot AI — Unified Test Runner
Runs unit, integration, and end-to-end tests without requiring external API keys.

Usage:
  python scripts/run_all_tests.py
  (or simply: pytest)
"""

import sys
import subprocess
from pathlib import Path

def main():
    root_dir = Path(__file__).resolve().parent.parent
    print("=" * 60)
    print("ClipPilot AI — IncuBrix Unified Test Suite")
    print("=" * 60)
    
    # Run pytest across the entire test suite
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short"
    ]
    
    res = subprocess.run(cmd, cwd=str(root_dir))
    if res.returncode == 0:
        print("\n" + "=" * 60)
        print("ALL UNIT, INTEGRATION, AND E2E TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print(f"TEST SUITE FAILED with exit code {res.returncode}")
        print("=" * 60)
    
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
