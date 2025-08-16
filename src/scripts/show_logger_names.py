#!/usr/bin/env python3
"""
Script to display available logger names for environment configuration.
"""

import sys
import os

# Add the specific directory to Python path to avoid importing the full logging package
logging_core_path = os.path.join(
    os.path.dirname(__file__), "..", "logging", "core"
)
sys.path.insert(0, logging_core_path)

# Import LoggerNames directly from the file
from logger_names import LoggerNames


def main():
    print("📋 Available Logger Names for SP_ONCALL_MODULE_LEVELS:")
    print()

    # Get all logger names and sort them
    names = LoggerNames.get_all_loggers()
    names.sort()

    print("Environment variable format examples:")
    print('export SP_ONCALL_MODULE_LEVELS="logger_name=debug"')
    print('export SP_ONCALL_MODULE_LEVELS="logger1=debug,logger2=info"')
    print()

    print("Available logger names:")
    for name in names:
        print(f"  {name}")

    print()


if __name__ == "__main__":
    main()
