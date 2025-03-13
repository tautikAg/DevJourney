#!/usr/bin/env python
"""
DevJourney CLI script.

This script provides a command-line interface for the DevJourney application.
"""

import os
import sys

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from devjourney.main import main

if __name__ == "__main__":
    main() 