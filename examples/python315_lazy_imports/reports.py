"""A slow module, standing in for a heavy optional dependency."""

import time

from injectq import singleton


print("  [reports] loading heavy module (1 second)...")
time.sleep(1)


@singleton
class ReportService:
    def build(self) -> str:
        return "monthly report built"
