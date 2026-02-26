#!/usr/bin/env python3
"""
DocsPort Code Execution Module
Secure Python code execution with isolation and monitoring.
"""

import os
import sys
import subprocess
import tempfile
import uuid
import json
import time
import signal
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import sqlite3


class CodeExecutionResult:
    """Result of a code execution."""

    def __init__(self):
        self.output = ""
        self.error_output = ""
        self.return_code = 0
        self.execution_time = 0.0
        self.timeout_occurred = False
        self.memory_usage = 0
        self.execution_id = str(uuid.uuid4())
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "output": self.output,
            "error_output": self.error_output,
            "return_code": self.return_code,
            "execution_time": self.execution_time,
            "timeout_occurred": self.timeout_occurred,
            "memory_usage": self.memory_usage,
            "timestamp": self.timestamp,
            "success": self.return_code == 0 and not self.timeout_occurred
        }


class SecureCodeExecutor:
    """Secure code executor with isolation."""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.temp_dir = Path(tempfile.gettempdir()) / "docsport_execution"
        self.temp_dir.mkdir(exist_ok=True)

    async def execute_code(self, code: str, execution_type: str = "python",
                          timeout: int = 30) -> Dict[str, Any]:
        """Execute code securely."""
        result = CodeExecutionResult()

        try:
            # Validate code
            if not self._validate_code(code):
                result.error_output = "Code contains forbidden operations"
                result.return_code = 1
                return result.to_dict()

            # Execute code
            if execution_type == "python":
                result = await self._execute_python_code(code, timeout)
            else:
                result.error_output = f"Unsupported execution type: {execution_type}"
                result.return_code = 1

            # Save execution to database
            self._save_execution_history(code, execution_type, result)

            return result.to_dict()

        except Exception as e:
            result.error_output = str(e)
            result.return_code = 1
            return result.to_dict()

    def _validate_code(self, code: str) -> bool:
        """Validate code for security."""
        dangerous_operations = [
            "import os",
            "import sys",
            "import subprocess",
            "import shutil",
            "import socket",
            "import urllib",
            "import requests",
            "from os import",
            "from sys import",
            "from subprocess import",
            "from shutil import",
            "from socket import",
            "from urllib import",
            "from requests import",
            "exec(",
            "eval(",
            "compile(",
            "__import__(",
            "open(",
            "file(",
            "input(",
            "raw_input(",
            "exit(",
            "quit(",
            "globals(",
            "locals(",
            "vars(",
            "dir(",
            "getattr(",
            "setattr(",
            "delattr(",
            "hasattr(",
            "reload(",
            "importlib",
            "pickle",
            "cPickle",
            "marshal",
            "tempfile",
            "pathlib",
            "glob",
            "fnmatch"
        ]

        code_lower = code.lower()

        for operation in dangerous_operations:
            if operation in code_lower:
                return False

        return True

    async def _execute_python_code(self, code: str, timeout: int) -> CodeExecutionResult:
        """Execute Python code in an isolated subprocess."""
        result = CodeExecutionResult()

        # Create temporary file
        temp_file = self.temp_dir / f"execution_{result.execution_id}.py"

        try:
            # Write code to temporary file
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)

            # Execute code
            start_time = time.time()

            process = subprocess.Popen(
                [sys.executable, str(temp_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.temp_dir
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
                result.output = stdout
                result.error_output = stderr
                result.return_code = process.returncode

            except subprocess.TimeoutExpired:
                process.kill()
                result.timeout_occurred = True
                result.error_output = f"Execution timed out after {timeout} seconds"
                result.return_code = -1

            result.execution_time = time.time() - start_time

        finally:
            # Delete temporary file
            if temp_file.exists():
                temp_file.unlink()

        return result

    def _save_execution_history(self, code: str, execution_type: str, result: CodeExecutionResult):
        """Save execution history to database."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO execution_history (code_content, execution_type, output,
                                                 error_output, execution_time)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    code,
                    execution_type,
                    result.output,
                    result.error_output,
                    result.execution_time
                ))
                conn.commit()

        except Exception as e:
            print(f"Error saving execution history: {e}")

    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return execution history."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, code_content, execution_type, output, error_output,
                           execution_time, created_at
                    FROM execution_history
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))

                history = []
                for row in cursor.fetchall():
                    history.append({
                        "id": row[0],
                        "code_content": row[1],
                        "execution_type": row[2],
                        "output": row[3],
                        "error_output": row[4],
                        "execution_time": row[5],
                        "created_at": row[6]
                    })

                return history

        except Exception as e:
            print(f"Error loading execution history: {e}")
            return []


class InteractiveCodeExecutor:
    """Interactive code executor for REPL-like functionality."""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.sessions = {}

    def create_session(self) -> str:
        """Create a new execution session."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "globals": {},
            "locals": {},
            "created_at": datetime.now(),
            "last_used": datetime.now()
        }
        return session_id

    def execute_in_session(self, session_id: str, code: str) -> Dict[str, Any]:
        """Execute code in a session."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]
        session["last_used"] = datetime.now()

        result = CodeExecutionResult()

        try:
            import io
            import contextlib

            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            start_time = time.time()

            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):
                exec(code, session["globals"], session["locals"])

            result.output = stdout_capture.getvalue()
            result.error_output = stderr_capture.getvalue()
            result.execution_time = time.time() - start_time

        except Exception as e:
            result.error_output = str(e)
            result.return_code = 1

        return result.to_dict()

    def get_session_variables(self, session_id: str) -> Dict[str, Any]:
        """Return session variables."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]

        variables = {}
        for name, value in session["locals"].items():
            if not name.startswith("_"):
                try:
                    variables[name] = str(value)
                except:
                    variables[name] = f"<{type(value).__name__}>"

        return {"variables": variables}

    def clear_session(self, session_id: str) -> Dict[str, Any]:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return {"message": "Session deleted"}
        else:
            return {"error": "Session not found"}


class CodeSnippetManager:
    """Manages code snippets and templates."""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.init_snippets_table()

    def init_snippets_table(self):
        """Initialize the snippets table."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS code_snippets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    code TEXT NOT NULL,
                    language TEXT DEFAULT 'python',
                    category TEXT DEFAULT 'general',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save_snippet(self, name: str, code: str, description: str = "",
                    language: str = "python", category: str = "general") -> Dict[str, Any]:
        """Save a code snippet."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO code_snippets (name, description, code, language, category)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, description, code, language, category))

                snippet_id = cursor.lastrowid
                conn.commit()

                return {
                    "id": snippet_id,
                    "message": "Snippet saved successfully"
                }

        except Exception as e:
            return {"error": str(e)}

    def get_snippets(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return code snippets."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                if category:
                    cursor.execute("""
                        SELECT id, name, description, code, language, category, created_at
                        FROM code_snippets
                        WHERE category = ?
                        ORDER BY name
                    """, (category,))
                else:
                    cursor.execute("""
                        SELECT id, name, description, code, language, category, created_at
                        FROM code_snippets
                        ORDER BY category, name
                    """)

                snippets = []
                for row in cursor.fetchall():
                    snippets.append({
                        "id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "code": row[3],
                        "language": row[4],
                        "category": row[5],
                        "created_at": row[6]
                    })

                return snippets

        except Exception as e:
            return []


def main():
    """Test function."""
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from config import DatabaseManager

    db_manager = DatabaseManager()
    executor = SecureCodeExecutor(db_manager)

    test_code = """
print("Hello, DocsPort!")
x = 5
y = 10
print(f"x + y = {x + y}")
"""

    import asyncio
    result = asyncio.run(executor.execute_code(test_code))

    print("Execution result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
