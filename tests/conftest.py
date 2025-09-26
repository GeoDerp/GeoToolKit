"""Test configuration and shared fixtures for GeoToolKit tests.

This module sets up the test environment by adding the project root
to sys.path so that the src module can be imported in tests.
"""

import os
import sys

# Add the project root to sys.path so 'src' can be imported in tests
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
