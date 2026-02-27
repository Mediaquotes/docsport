"""Tests for AST-based code analysis."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.analysis import PythonCodeAnalyzer


def test_analyze_file_finds_classes(db_manager, sample_python_file):
    analyzer = PythonCodeAnalyzer(db_manager)
    result = analyzer.analyze_file(sample_python_file)

    elements = result.get("elements", [])
    class_names = [e["name"] for e in elements if e["type"] == "class"]
    assert "Calculator" in class_names


def test_analyze_file_finds_functions(db_manager, sample_python_file):
    analyzer = PythonCodeAnalyzer(db_manager)
    result = analyzer.analyze_file(sample_python_file)

    elements = result.get("elements", [])
    func_names = [e["name"] for e in elements if e["type"] == "function"]
    assert "greet" in func_names
    assert "main" in func_names


def test_analyze_file_finds_methods(db_manager, sample_python_file):
    analyzer = PythonCodeAnalyzer(db_manager)
    result = analyzer.analyze_file(sample_python_file)

    elements = result.get("elements", [])
    method_names = [e["name"] for e in elements if e["type"] == "method"]
    assert "add" in method_names
    assert "subtract" in method_names


def test_analyze_file_returns_stats(db_manager, sample_python_file):
    analyzer = PythonCodeAnalyzer(db_manager)
    result = analyzer.analyze_file(sample_python_file)

    stats = result.get("stats", {})
    assert stats.get("classes", 0) >= 1
    assert stats.get("functions", 0) >= 2
    assert stats.get("methods", 0) >= 2


def test_analyze_file_nonexistent(db_manager):
    analyzer = PythonCodeAnalyzer(db_manager)
    result = analyzer.analyze_file("/nonexistent/file.py")

    assert "error" in result or result.get("elements", []) == []


def test_analyze_file_empty(db_manager, tmp_path):
    empty_file = tmp_path / "empty.py"
    empty_file.write_text("")

    analyzer = PythonCodeAnalyzer(db_manager)
    result = analyzer.analyze_file(str(empty_file))

    elements = result.get("elements", [])
    assert len(elements) == 0


def test_analyze_file_syntax_error(db_manager, tmp_path):
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("def broken(:\n    pass")

    analyzer = PythonCodeAnalyzer(db_manager)
    result = analyzer.analyze_file(str(bad_file))

    # Should handle gracefully, not crash
    assert "error" in result or isinstance(result, dict)
