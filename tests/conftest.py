"""Shared test fixtures for DocsPort."""

import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_python_code():
    """Simple Python code for testing analysis."""
    return '''
class Calculator:
    """A simple calculator."""

    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b


def greet(name):
    """Return a greeting."""
    return f"Hello, {name}!"


def main():
    calc = Calculator()
    print(calc.add(1, 2))
    print(greet("World"))
'''


@pytest.fixture
def sample_python_file(tmp_path, sample_python_code):
    """Write sample code to a temp file and return its path."""
    file = tmp_path / "sample.py"
    file.write_text(sample_python_code)
    return str(file)


@pytest.fixture
def db_manager(tmp_path):
    """Create a temporary database manager."""
    from config import DatabaseManager
    db_path = str(tmp_path / "test.db")
    return DatabaseManager(db_path=db_path)
