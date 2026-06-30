#!/usr/bin/env python3
"""每日推送入口"""

from dotenv import load_dotenv

load_dotenv()

import sys

from src.pipeline import run_daily

if __name__ == "__main__":
    sys.exit(0 if run_daily() else 1)
