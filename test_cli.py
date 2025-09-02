#!/usr/bin/env python3
"""Test script for running CLI commands from current directory."""

import sys

sys.path.insert(0, "src")

from cc_orchestrator.cli.main import main

if __name__ == "__main__":
    main()
