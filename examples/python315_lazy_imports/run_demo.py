"""Run every step of the lazy-imports demo, with and without global lazy mode.

    python run_demo.py

Global lazy mode (PYTHON_LAZY_IMPORTS=all) needs Python 3.15+. On older
versions only the normal runs are shown.
"""

import os
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).parent

STEPS = [
    ("step1_global_lazy_startup.py", []),
    ("step1_global_lazy_startup.py", ["--report"]),
    ("step2_lazy_modules_startup.py", []),
    ("step3_registration_problem.py", []),
    ("step4_fix_importlib.py", []),
    ("step5_fix_filter.py", []),
    ("step6_fix_setup_function.py", []),
]

MODES = [("normal imports", {})]
if hasattr(sys, "set_lazy_imports"):
    MODES.append(("PYTHON_LAZY_IMPORTS=all", {"PYTHON_LAZY_IMPORTS": "all"}))


def run(script: str, args: list[str], extra_env: dict[str, str]) -> str:
    result = subprocess.run(  # noqa: S603
        [sys.executable, script, *args],
        cwd=HERE,
        env={**os.environ, **extra_env},
        capture_output=True,
        text=True,
        check=False,
    )
    return (result.stdout + result.stderr).rstrip()


def main() -> None:
    print(f"Python {sys.version.split()[0]}")
    if len(MODES) == 1:
        print("(Python 3.15+ is needed to show global lazy mode)")

    for script, args in STEPS:
        title = " ".join([script, *args])
        print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")
        for mode_name, extra_env in MODES:
            print(f"\n--- {mode_name} ---")
            print(run(script, args, extra_env))


if __name__ == "__main__":
    main()
