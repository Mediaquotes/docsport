#!/usr/bin/env python3
"""
DocsPort Visualization Module
Generates flowcharts and visualizations of code structure using Mermaid.js.
"""

import os
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import hashlib


class MermaidFlowchartGenerator:
    """Generates Mermaid.js flowcharts for code structure."""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def generate_project_flowchart(self) -> Dict[str, Any]:
        """Generate a flowchart for the entire project."""
        analysis_data = self._load_analysis_data()

        if not analysis_data:
            return {
                "error": "No analysis data found. Please run a project analysis first."
            }

        mermaid_code = self._generate_mermaid_diagram(analysis_data)

        return {
            "mermaid_code": mermaid_code,
            "diagram_type": "flowchart",
            "elements_count": len(analysis_data),
            "generated_at": datetime.now().isoformat()
        }

    def generate_file_flowchart(self, file_path: str) -> Dict[str, Any]:
        """Generate a flowchart for a single file."""
        analysis_data = self._load_file_analysis_data(file_path)

        if not analysis_data:
            return {
                "error": f"No analysis data found for {file_path}."
            }

        mermaid_code = self._generate_file_mermaid_diagram(file_path, analysis_data)

        return {
            "mermaid_code": mermaid_code,
            "diagram_type": "flowchart",
            "file_path": file_path,
            "elements_count": len(analysis_data),
            "generated_at": datetime.now().isoformat()
        }

    def generate_class_diagram(self) -> Dict[str, Any]:
        """Generate a class diagram."""
        classes = self._load_classes_data()

        if not classes:
            return {
                "error": "No classes found."
            }

        mermaid_code = self._generate_class_diagram(classes)

        return {
            "mermaid_code": mermaid_code,
            "diagram_type": "classDiagram",
            "classes_count": len(classes),
            "generated_at": datetime.now().isoformat()
        }

    def _load_analysis_data(self) -> List[Dict[str, Any]]:
        """Load all analysis data from the database."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT file_path, analysis_type, name, line_start, line_end,
                           content, dependencies
                    FROM code_analysis
                    ORDER BY file_path, line_start
                """)

                elements = []
                for row in cursor.fetchall():
                    elements.append({
                        "file_path": row[0],
                        "type": row[1],
                        "name": row[2],
                        "line_start": row[3],
                        "line_end": row[4],
                        "content": row[5],
                        "dependencies": json.loads(row[6]) if row[6] else []
                    })

                return elements

        except Exception as e:
            print(f"Error loading analysis data: {e}")
            return []

    def _load_file_analysis_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Load analysis data for a specific file."""
        try:
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
                        "type": row[0],
                        "name": row[1],
                        "line_start": row[2],
                        "line_end": row[3],
                        "content": row[4],
                        "dependencies": json.loads(row[5]) if row[5] else []
                    })

                return elements

        except Exception as e:
            print(f"Error loading file analysis data: {e}")
            return []

    def _load_classes_data(self) -> List[Dict[str, Any]]:
        """Load all classes from the database."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT file_path, name, content, dependencies
                    FROM code_analysis
                    WHERE analysis_type = 'class'
                    ORDER BY file_path, name
                """)

                classes = []
                for row in cursor.fetchall():
                    classes.append({
                        "file_path": row[0],
                        "name": row[1],
                        "content": row[2],
                        "dependencies": json.loads(row[3]) if row[3] else []
                    })

                return classes

        except Exception as e:
            print(f"Error loading class data: {e}")
            return []

    def _generate_mermaid_diagram(self, elements: List[Dict[str, Any]]) -> str:
        """Generate Mermaid diagram code for project overview."""
        lines = ["flowchart TD"]

        # Group elements by files
        files = {}
        for element in elements:
            file_path = element["file_path"]
            if file_path not in files:
                files[file_path] = []
            files[file_path].append(element)

        # Generate nodes for each file
        for file_path, file_elements in files.items():
            file_id = self._sanitize_id(file_path)
            file_name = Path(file_path).name

            # File node
            lines.append(f'    {file_id}["{file_name}"]')

            # Class nodes
            classes = [e for e in file_elements if e["type"] == "class"]
            for cls in classes:
                class_id = self._sanitize_id(f"{file_path}_{cls['name']}")
                lines.append(f'    {class_id}["{cls["name"]}"]')
                lines.append(f'    {file_id} --> {class_id}')

                # Methods of the class
                methods = [e for e in file_elements if e["type"] == "method" and cls["name"] in e.get("parent", "")]
                for method in methods:
                    method_id = self._sanitize_id(f"{file_path}_{cls['name']}_{method['name']}")
                    lines.append(f'    {method_id}["{method["name"]}()"]')
                    lines.append(f'    {class_id} --> {method_id}')

            # Standalone functions
            functions = [e for e in file_elements if e["type"] == "function"]
            for func in functions:
                func_id = self._sanitize_id(f"{file_path}_{func['name']}")
                lines.append(f'    {func_id}["{func["name"]}()"]')
                lines.append(f'    {file_id} --> {func_id}')

        # Styling
        lines.extend([
            "",
            "    classDef fileNode fill:#e1f5fe,stroke:#01579b,stroke-width:2px",
            "    classDef classNode fill:#f3e5f5,stroke:#4a148c,stroke-width:2px",
            "    classDef functionNode fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px",
            "    classDef methodNode fill:#fff3e0,stroke:#e65100,stroke-width:2px"
        ])

        # Apply styling
        for file_path in files.keys():
            file_id = self._sanitize_id(file_path)
            lines.append(f"    class {file_id} fileNode")

            file_elements = files[file_path]
            for element in file_elements:
                element_id = self._sanitize_id(f"{file_path}_{element['name']}")
                if element["type"] == "class":
                    lines.append(f"    class {element_id} classNode")
                elif element["type"] == "function":
                    lines.append(f"    class {element_id} functionNode")
                elif element["type"] == "method":
                    lines.append(f"    class {element_id} methodNode")

        return "\n".join(lines)

    def _generate_file_mermaid_diagram(self, file_path: str, elements: List[Dict[str, Any]]) -> str:
        """Generate Mermaid diagram for a single file."""
        lines = ["flowchart TD"]

        file_name = Path(file_path).name
        file_id = self._sanitize_id(file_path)

        lines.append(f'    {file_id}["{file_name}"]')

        # Classes
        classes = [e for e in elements if e["type"] == "class"]
        for cls in classes:
            class_id = self._sanitize_id(cls["name"])
            lines.append(f'    {class_id}["{cls["name"]}"]')
            lines.append(f'    {file_id} --> {class_id}')

            # Methods
            methods = [e for e in elements if e["type"] == "method" and "parent" in e]
            for method in methods:
                method_id = self._sanitize_id(f"{cls['name']}_{method['name']}")
                lines.append(f'    {method_id}["{method["name"]}()"]')
                lines.append(f'    {class_id} --> {method_id}')

        # Standalone functions
        functions = [e for e in elements if e["type"] == "function"]
        for func in functions:
            func_id = self._sanitize_id(func["name"])
            lines.append(f'    {func_id}["{func["name"]}()"]')
            lines.append(f'    {file_id} --> {func_id}')

        # Styling
        lines.extend([
            "",
            "    classDef fileNode fill:#e1f5fe,stroke:#01579b,stroke-width:2px",
            "    classDef classNode fill:#f3e5f5,stroke:#4a148c,stroke-width:2px",
            "    classDef functionNode fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px",
            "    classDef methodNode fill:#fff3e0,stroke:#e65100,stroke-width:2px",
            "",
            f"    class {file_id} fileNode"
        ])

        for cls in classes:
            class_id = self._sanitize_id(cls["name"])
            lines.append(f"    class {class_id} classNode")

        for func in functions:
            func_id = self._sanitize_id(func["name"])
            lines.append(f"    class {func_id} functionNode")

        return "\n".join(lines)

    def _generate_class_diagram(self, classes: List[Dict[str, Any]]) -> str:
        """Generate a UML class diagram."""
        lines = ["classDiagram"]

        for cls in classes:
            class_name = cls["name"]
            lines.append(f"    class {class_name} {{")

            content = cls["content"]
            methods = self._extract_methods_from_class(content)

            for method in methods:
                lines.append(f"        +{method}()")

            lines.append("    }")

            # Inheritance
            if cls["dependencies"]:
                for dep in cls["dependencies"]:
                    if dep and dep != "object":
                        lines.append(f"    {dep} <|-- {class_name}")

        return "\n".join(lines)

    def _extract_methods_from_class(self, class_content: str) -> List[str]:
        """Extract method names from class content."""
        methods = []
        lines = class_content.split('\n')

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('def ') and '(' in stripped:
                method_name = stripped[4:].split('(')[0]
                if method_name and not method_name.startswith('_'):
                    methods.append(method_name)

        return methods

    def _sanitize_id(self, text: str) -> str:
        """Sanitize text for Mermaid IDs."""
        sanitized = text.replace('/', '_').replace('\\', '_').replace('.', '_')
        sanitized = sanitized.replace('-', '_').replace(' ', '_')

        if sanitized and sanitized[0].isdigit():
            sanitized = 'id_' + sanitized

        return sanitized or 'unknown'


class CodeDependencyAnalyzer:
    """Analyzes code dependencies for improved visualization."""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def analyze_dependencies(self) -> Dict[str, Any]:
        """Analyze dependencies between code elements."""
        elements = self._load_all_elements()
        dependency_graph = self._build_dependency_graph(elements)
        cycles = self._find_cycles(dependency_graph)
        metrics = self._calculate_metrics(dependency_graph)

        return {
            "dependency_graph": dependency_graph,
            "cycles": cycles,
            "metrics": metrics,
            "analyzed_at": datetime.now().isoformat()
        }

    def _load_all_elements(self) -> List[Dict[str, Any]]:
        """Load all code elements from the database."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT file_path, analysis_type, name, dependencies
                    FROM code_analysis
                """)

                elements = []
                for row in cursor.fetchall():
                    elements.append({
                        "file_path": row[0],
                        "type": row[1],
                        "name": row[2],
                        "dependencies": json.loads(row[3]) if row[3] else []
                    })

                return elements

        except Exception as e:
            print(f"Error loading elements: {e}")
            return []

    def _build_dependency_graph(self, elements: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Build a dependency graph."""
        graph = {}

        for element in elements:
            element_id = f"{element['file_path']}::{element['name']}"
            graph[element_id] = []

            for dep in element["dependencies"]:
                if dep:
                    dep_element = self._find_element_by_name(elements, dep)
                    if dep_element:
                        dep_id = f"{dep_element['file_path']}::{dep_element['name']}"
                        graph[element_id].append(dep_id)

        return graph

    def _find_element_by_name(self, elements: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
        """Find an element by name."""
        for element in elements:
            if element["name"] == name:
                return element
        return None

    def _find_cycles(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """Find circular dependencies using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node, path):
            if node in rec_stack:
                cycle_start = path.index(node)
                cycle = path[cycle_start:]
                cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                dfs(neighbor, path + [neighbor])

            rec_stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node, [node])

        return cycles

    def _calculate_metrics(self, graph: Dict[str, List[str]]) -> Dict[str, Any]:
        """Calculate metrics for the dependency graph."""
        total_elements = len(graph)
        total_dependencies = sum(len(deps) for deps in graph.values())

        # Calculate in-degree and out-degree
        in_degree = {}
        out_degree = {}

        for node in graph:
            out_degree[node] = len(graph[node])
            in_degree[node] = 0

        for node, deps in graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        max_in_degree = max(in_degree.values()) if in_degree else 0
        max_out_degree = max(out_degree.values()) if out_degree else 0

        high_in_degree = [node for node, degree in in_degree.items() if degree == max_in_degree]
        high_out_degree = [node for node, degree in out_degree.items() if degree == max_out_degree]

        return {
            "total_elements": total_elements,
            "total_dependencies": total_dependencies,
            "max_in_degree": max_in_degree,
            "max_out_degree": max_out_degree,
            "high_in_degree_nodes": high_in_degree,
            "high_out_degree_nodes": high_out_degree,
            "average_dependencies": total_dependencies / total_elements if total_elements > 0 else 0
        }


def main():
    """Test function."""
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from config import DatabaseManager

    db_manager = DatabaseManager()

    generator = MermaidFlowchartGenerator(db_manager)
    flowchart = generator.generate_project_flowchart()

    print("Flowchart generated:")
    print(json.dumps(flowchart, indent=2, ensure_ascii=False))

    analyzer = CodeDependencyAnalyzer(db_manager)
    dependencies = analyzer.analyze_dependencies()

    print("\nDependency analysis:")
    print(json.dumps(dependencies, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
