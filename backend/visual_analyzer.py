#!/usr/bin/env python3
"""
DocsPort Visual Code Analyzer
Advanced visualization and analysis of code structure with dropdown functionality.
"""

import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from backend.analysis import PythonCodeAnalyzer, CodeElement


@dataclass
class CodeNode:
    """Represents a node in the code structure visualization."""
    id: str
    name: str
    type: str  # 'class', 'function', 'method', 'import'
    line: int
    parent: Optional[str] = None
    children: List[str] = None
    dependencies: List[str] = None
    complexity: int = 0
    description: str = ""

    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.dependencies is None:
            self.dependencies = []


class VisualCodeAnalyzer:
    """Advanced code analysis for visual representation."""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.analyzer = PythonCodeAnalyzer(db_manager)

    def analyze_for_visualization(self, file_path: str) -> Dict[str, Any]:
        """Analyze code for visual representation."""
        base_analysis = self.analyzer.analyze_file(file_path)

        if "error" in base_analysis:
            return base_analysis

        nodes = []
        links = []
        structure_tree = self._build_structure_tree(base_analysis["elements"])

        # Create nodes for D3.js visualization
        for element in base_analysis["elements"]:
            node = CodeNode(
                id=f"{element['type']}_{element['name']}_{element['line_start']}",
                name=element["name"],
                type=element["type"],
                line=element["line_start"],
                parent=element.get("parent"),
                complexity=self._calculate_complexity(element["content"])
            )
            nodes.append(node)

        # Create links based on dependencies
        for element in base_analysis["elements"]:
            element_id = f"{element['type']}_{element['name']}_{element['line_start']}"

            # Parent-child relationships
            if element.get("parent"):
                parent_elements = [e for e in base_analysis["elements"]
                                 if e["name"] == element["parent"] and e["type"] == "class"]
                if parent_elements:
                    parent_id = f"class_{parent_elements[0]['name']}_{parent_elements[0]['line_start']}"
                    links.append({
                        "source": parent_id,
                        "target": element_id,
                        "type": "contains"
                    })

            # Dependency links
            for dep in element.get("dependencies", []):
                dep_elements = [e for e in base_analysis["elements"] if e["name"] == dep]
                if dep_elements:
                    dep_id = f"{dep_elements[0]['type']}_{dep_elements[0]['name']}_{dep_elements[0]['line_start']}"
                    links.append({
                        "source": element_id,
                        "target": dep_id,
                        "type": "depends_on"
                    })

        # Generate Mermaid flowchart
        mermaid_code = self._generate_mermaid_flowchart(base_analysis["elements"])

        return {
            "file_path": file_path,
            "nodes": [node.__dict__ for node in nodes],
            "links": links,
            "structure_tree": structure_tree,
            "mermaid": mermaid_code,
            "dropdown_data": self._create_dropdown_data(base_analysis["elements"]),
            "stats": base_analysis["stats"],
            "analyzed_at": base_analysis["analyzed_at"]
        }

    def _build_structure_tree(self, elements: List[Dict]) -> Dict[str, Any]:
        """Build hierarchical structure for dropdown tree."""
        tree = {
            "name": "Code Structure",
            "type": "root",
            "children": []
        }

        classes = [e for e in elements if e["type"] == "class"]
        functions = [e for e in elements if e["type"] == "function"]

        # Add classes
        for cls in classes:
            class_node = {
                "name": cls["name"],
                "type": "class",
                "line": cls["line_start"],
                "children": []
            }

            # Add methods to the class
            methods = [e for e in elements if e["type"] == "method" and e.get("parent") == cls["name"]]
            for method in methods:
                method_node = {
                    "name": method["name"],
                    "type": "method",
                    "line": method["line_start"],
                    "children": []
                }
                class_node["children"].append(method_node)

            tree["children"].append(class_node)

        # Add standalone functions
        for func in functions:
            func_node = {
                "name": func["name"],
                "type": "function",
                "line": func["line_start"],
                "children": []
            }
            tree["children"].append(func_node)

        return tree

    def _create_dropdown_data(self, elements: List[Dict]) -> Dict[str, List[Dict]]:
        """Create data for dropdown menus."""
        dropdown_data = {
            "classes": [],
            "functions": [],
            "methods": [],
            "imports": []
        }

        for element in elements:
            item = {
                "name": element["name"],
                "line": element["line_start"],
                "complexity": self._calculate_complexity(element["content"]),
                "description": self._extract_docstring(element["content"])
            }

            if element["type"] == "class":
                dropdown_data["classes"].append(item)
            elif element["type"] == "function":
                dropdown_data["functions"].append(item)
            elif element["type"] == "method":
                dropdown_data["methods"].append(item)

        return dropdown_data

    def _calculate_complexity(self, code: str) -> int:
        """Calculate cyclomatic complexity."""
        try:
            tree = ast.parse(code)
            complexity = 1  # Base complexity

            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                    complexity += 1
                elif isinstance(node, ast.ExceptHandler):
                    complexity += 1
                elif isinstance(node, (ast.With, ast.AsyncWith)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1

            return complexity
        except:
            return 1

    def _extract_docstring(self, code: str) -> str:
        """Extract docstring from code."""
        try:
            tree = ast.parse(code)
            if (tree.body and
                isinstance(tree.body[0], ast.Expr) and
                isinstance(tree.body[0].value, ast.Str)):
                return tree.body[0].value.s.strip()
        except:
            pass
        return ""

    def _generate_mermaid_flowchart(self, elements: List[Dict]) -> str:
        """Generate Mermaid flowchart from code elements."""
        mermaid_lines = ["flowchart TD"]

        # Classes as rectangles
        for element in elements:
            if element["type"] == "class":
                mermaid_lines.append(f"    {element['name']}[{element['name']}]")

        # Functions as circles
        for element in elements:
            if element["type"] == "function":
                mermaid_lines.append(f"    {element['name']}(({element['name']}))")

        # Methods as rhombuses
        for element in elements:
            if element["type"] == "method":
                parent = element.get("parent", "unknown")
                mermaid_lines.append(f"    {parent}_{element['name']}{{{element['name']}}}")
                mermaid_lines.append(f"    {parent} --> {parent}_{element['name']}")

        # Dependencies as connections
        for element in elements:
            for dep in element.get("dependencies", []):
                if dep != element["name"]:
                    mermaid_lines.append(f"    {element['name']} --> {dep}")

        return "\n".join(mermaid_lines)

    def get_code_metrics(self, file_path: str) -> Dict[str, Any]:
        """Calculate advanced code metrics."""
        analysis = self.analyzer.analyze_file(file_path)

        if "error" in analysis:
            return {"error": analysis["error"]}

        metrics = {
            "cyclomatic_complexity": 0,
            "maintainability_index": 0,
            "lines_of_code": 0,
            "comment_ratio": 0,
            "class_coupling": 0,
            "inheritance_depth": 0,
            "method_count_per_class": {},
            "complexity_distribution": {"low": 0, "medium": 0, "high": 0}
        }

        total_complexity = 0

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            metrics["lines_of_code"] = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
            comment_lines = len([l for l in lines if l.strip().startswith('#')])
            metrics["comment_ratio"] = comment_lines / len(lines) if lines else 0

            for element in analysis["elements"]:
                complexity = self._calculate_complexity(element["content"])
                total_complexity += complexity

                # Complexity distribution
                if complexity <= 5:
                    metrics["complexity_distribution"]["low"] += 1
                elif complexity <= 10:
                    metrics["complexity_distribution"]["medium"] += 1
                else:
                    metrics["complexity_distribution"]["high"] += 1

                # Methods per class
                if element["type"] == "method" and element.get("parent"):
                    parent = element["parent"]
                    if parent not in metrics["method_count_per_class"]:
                        metrics["method_count_per_class"][parent] = 0
                    metrics["method_count_per_class"][parent] += 1

            metrics["cyclomatic_complexity"] = total_complexity

            # Simplified Maintainability Index
            if metrics["lines_of_code"] > 0:
                metrics["maintainability_index"] = max(0,
                    171 - 5.2 * (total_complexity / len(analysis["elements"]) if analysis["elements"] else 1)
                    - 0.23 * metrics["lines_of_code"]
                    + 16.2 * metrics["comment_ratio"]
                )

        except Exception as e:
            metrics["error"] = str(e)

        return metrics


def main():
    """Test function."""
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from config import DatabaseManager

    db_manager = DatabaseManager()
    visual_analyzer = VisualCodeAnalyzer(db_manager)

    result = visual_analyzer.analyze_for_visualization(__file__)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
