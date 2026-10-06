"""
conftest.py — makes the rules_engine package importable from the tests/ directory.
"""
import sys
import os

# Ensure the exercise root (containing the rules_engine package) is on sys.path
sys.path.insert(0, os.path.dirname(__file__))
