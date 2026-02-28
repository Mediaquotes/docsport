#!/usr/bin/env python3
"""
DocsPort Code Analysis Module
Analyzes Python code and extracts classes, functions, and methods using AST.
"""

import ast
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class CodeElement:
    """Represents a code element (class, function, method)."""

    def __init__(self, name: str, element_type: str, line_start: int, line_end: int,
                 content: str, parent: Optional[str] = None):
        self.name = name
        self.element_type = element_type  # 'class', 'function', 'method'
        self.line_start = line_start
        self.line_end = line_end
        self.content = content
        self.parent = parent
        self.dependencies = []
        self.calls = []
        self.imports = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.element_type,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "content": self.content,
            "parent": self.parent,
            "dependencies": self.dependencies,
            "calls": self.calls,
            "imports": self.imports
        }


class PythonCodeAnalyzer:
    """Analyzes Python code using AST."""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def analyze_file(self, file_path: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Analyze a Python file."""
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check if analysis is current and not stale
        if not force_refresh and self._is_analysis_current(file_path):
            return self._get_cached_analysis(file_path)

        try:
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse with AST
            tree = ast.parse(content)

            # Analyze the structure
            analyzer = ASTAnalyzer(content)
            analyzer.visit(tree)
            elements = analyzer.elements

            # Save analysis to database
            self._save_analysis(file_path, elements)

            return {
                "file_path": file_path,
                "elements": [elem.to_dict() for elem in elements],
                "stats": self._calculate_stats(elements),
                "analyzed_at": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "file_path": file_path,
                "error": str(e),
                "analyzed_at": datetime.now().isoformat()
            }

    def analyze_project(self, project_path: str = ".") -> Dict[str, Any]:
        """Analyze all Python files in the project."""
        project_path_obj = Path(project_path)

        results = {
            "project_path": str(project_path_obj.absolute()),
            "files": [],
            "total_stats": {
                "total_files": 0,
                "total_classes": 0,
                "total_functions": 0,
                "total_methods": 0,
                "total_lines": 0
            },
            "analyzed_at": datetime.now().isoformat()
        }

        # Find all Python files
        python_files = []
        for py_file in project_path_obj.rglob("*.py"):
            # Skip hidden directories and virtual environments
            if not any(part.startswith('.') or part in ['venv', '__pycache__']
                      for part in py_file.parts):
                python_files.append(py_file)

        results["total_stats"]["total_files"] = len(python_files)

        # Analyze each file
        for py_file in python_files:
            try:
                file_analysis = self.analyze_file(str(py_file))
                results["files"].append(file_analysis)

                # Update total statistics
                if "stats" in file_analysis:
                    stats = file_analysis["stats"]
                    results["total_stats"]["total_classes"] += stats.get("classes", 0)
                    results["total_stats"]["total_functions"] += stats.get("functions", 0)
                    results["total_stats"]["total_methods"] += stats.get("methods", 0)
                    results["total_stats"]["total_lines"] += stats.get("lines", 0)

            except Exception as e:
                results["files"].append({
                    "file_path": str(py_file),
                    "error": str(e),
                    "analyzed_at": datetime.now().isoformat()
                })

        return results

    def _is_analysis_current(self, file_path: str) -> bool:
        """Check if the analysis is up to date."""
        try:
            file_mtime = Path(file_path).stat().st_mtime

            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT created_at FROM code_analysis
                    WHERE file_path = ?
                    ORDER BY created_at DESC LIMIT 1
                """, (file_path,))

                result = cursor.fetchone()
                if result:
                    analysis_time = datetime.fromisoformat(result[0]).timestamp()
                    return analysis_time > file_mtime

        except Exception:
            pass

        return False

    def _get_cached_analysis(self, file_path: str) -> Dict[str, Any]:
        """Load cached analysis from database."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT analysis_type, name, line_start, line_end, content, dependencies
                FROM code_analysis
                WHERE file_path = ?
                ORDER BY line_start
            """, (file_path,))

            elements = []
            for row in cursor.fetchall():
                elements.append({
                    "name": row[1],
                    "type": row[0],
                    "line_start": row[2],
                    "line_end": row[3],
                    "content": row[4],
                    "dependencies": json.loads(row[5]) if row[5] else []
                })

        return {
            "file_path": file_path,
            "elements": elements,
            "stats": self._calculate_stats_from_elements(elements),
            "analyzed_at": datetime.now().isoformat(),
            "cached": True
        }

    def _save_analysis(self, file_path: str, elements: List[CodeElement]):
        """Save the analysis to the database."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Delete old analysis
            cursor.execute("DELETE FROM code_analysis WHERE file_path = ?", (file_path,))

            # Save new analysis
            for element in elements:
                cursor.execute("""
                    INSERT INTO code_analysis (file_path, analysis_type, name, line_start,
                                             line_end, content, dependencies)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_path,
                    element.element_type,
                    element.name,
                    element.line_start,
                    element.line_end,
                    element.content,
                    json.dumps(element.dependencies)
                ))

            conn.commit()

    def _calculate_stats(self, elements: List[CodeElement]) -> Dict[str, int]:
        """Calculate statistics from CodeElement objects."""
        stats = {
            "classes": 0,
            "functions": 0,
            "methods": 0,
            "lines": 0
        }

        for element in elements:
            if element.element_type == "class":
                stats["classes"] += 1
            elif element.element_type == "function":
                stats["functions"] += 1
            elif element.element_type == "method":
                stats["methods"] += 1

            stats["lines"] += element.line_end - element.line_start + 1

        return stats

    def _calculate_stats_from_elements(self, elements: List[Dict]) -> Dict[str, int]:
        """Calculate statistics from element dictionaries."""
        stats = {
            "classes": 0,
            "functions": 0,
            "methods": 0,
            "lines": 0
        }

        for element in elements:
            if element["type"] == "class":
                stats["classes"] += 1
            elif element["type"] == "function":
                stats["functions"] += 1
            elif element["type"] == "method":
                stats["methods"] += 1

            stats["lines"] += element["line_end"] - element["line_start"] + 1

        return stats


class ASTAnalyzer(ast.NodeVisitor):
    """AST Node Visitor for code analysis."""

    def __init__(self, source_code: str):
        self.source_code = source_code.splitlines()
        self.elements = []
        self.current_class = None
        self.imports = []
        self.calls = []

    def visit_Import(self, node):
        """Visit import statements."""
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Visit from-import statements."""
        module = node.module or ""
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}")
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Visit class definitions."""
        end_lineno = getattr(node, 'end_lineno', None)
        if end_lineno is None:
            end_lineno = node.lineno + 20  # Fallback

        content = self._extract_content(node.lineno, end_lineno)

        element = CodeElement(
            name=node.name,
            element_type="class",
            line_start=node.lineno,
            line_end=end_lineno,
            content=content
        )

        # Analyze inheritance
        element.dependencies = [self._get_base_name(base) for base in node.bases]

        self.elements.append(element)

        # Set class context for methods
        old_class = self.current_class
        self.current_class = node.name

        self.generic_visit(node)

        self.current_class = old_class

    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        end_lineno = getattr(node, 'end_lineno', None)
        if end_lineno is None:
            end_lineno = node.lineno + 10  # Fallback

        content = self._extract_content(node.lineno, end_lineno)

        element_type = "method" if self.current_class else "function"

        element = CodeElement(
            name=node.name,
            element_type=element_type,
            line_start=node.lineno,
            line_end=end_lineno,
            content=content,
            parent=self.current_class
        )

        # Analyze function calls
        call_analyzer = CallAnalyzer()
        call_analyzer.visit(node)
        element.calls = call_analyzer.calls

        self.elements.append(element)

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        """Visit async function definitions."""
        self.visit_FunctionDef(node)

    def _extract_content(self, start_line: int, end_line: int) -> str:
        """Extract code content between lines."""
        if start_line <= len(self.source_code) and end_line <= len(self.source_code):
            return "\n".join(self.source_code[start_line-1:end_line])
        return ""

    def _get_base_name(self, base_node) -> str:
        """Extract base class name."""
        if isinstance(base_node, ast.Name):
            return base_node.id
        elif isinstance(base_node, ast.Attribute):
            return ast.unparse(base_node)
        return str(base_node)


class CallAnalyzer(ast.NodeVisitor):
    """Analyzes function calls within code."""

    def __init__(self):
        self.calls = []

    def visit_Call(self, node):
        """Visit function call nodes."""
        if isinstance(node.func, ast.Name):
            self.calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.append(ast.unparse(node.func))

        self.generic_visit(node)


def main():
    """Test function."""
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from config import DatabaseManager

    db_manager = DatabaseManager()
    analyzer = PythonCodeAnalyzer(db_manager)

    result = analyzer.analyze_file(__file__)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
