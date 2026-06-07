"""
Main entry point of the IIT framework.

Usage:
    uv run exec.py              → single analysis (main.py)
    uv run exec.py --batch      → batch processing from Excel (main_batch.py)

Application settings live in src/models/base/application.py.
"""

import sys

from src.models.base.application import application


def main():
    application.enable_profiling()
    application.set_sample_network_page("A")

    if "--batch" in sys.argv:
        from main_batch import run
    else:
        from main import run

    run()


if __name__ == "__main__":
    main()
