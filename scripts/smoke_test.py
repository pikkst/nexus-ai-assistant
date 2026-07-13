"""Packaging smoke test for a clean installed environment."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    try:
        subprocess.run(
            [sys.executable, "-c", "import src; import src.main; from src.main import main as _; print('OK')"],
            capture_output=True,
            text=True,
            check=True,
        )
        print("Smoke test passed: installed package imports and entry point are valid.")
        return 0
    except Exception as exc:
        print(f"Smoke test failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
