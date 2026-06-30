#!/usr/bin/env python3
"""周报推送入口"""

from dotenv import load_dotenv

load_dotenv()

import sys

from src.pipeline import run_weekly

if __name__ == "__main__":
    sys.exit(0 if run_weekly() else 1)
