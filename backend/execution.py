#!/usr/bin/env python3
"""
DocsPort Code Execution Module
Secure Python code execution with isolation and monitoring.
"""

import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


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
        """Validate code for security.

        Uses a blacklist approach on normalized code. This is NOT a full sandbox —
        it prevents common dangerous patterns but cannot guarantee complete isolation.
        Code runs in a subprocess with timeout, which limits blast radius.
        """
        import re

        # Normalize whitespace: collapse runs of spaces/tabs between tokens
        code_normalized = re.sub(r'[ \t]+', ' ', code.lower())

        # Dangerous module imports
        dangerous_modules = [
            "os", "sys", "subprocess", "shutil", "socket", "urllib",
            "requests", "importlib", "pickle", "cpickle", "marshal",
            "tempfile", "pathlib", "glob", "fnmatch", "ctypes",
            "multiprocessing", "signal", "pty", "code", "codeop",
            "webbrowser", "http", "ftplib", "smtplib", "telnetlib",
        ]

        for mod in dangerous_modules:
            if re.search(rf'\bimport\s+{mod}\b', code_normalized):
                return False
            if re.search(rf'\bfrom\s+{mod}\b', code_normalized):
                return False

        # Dangerous builtins and functions
        dangerous_calls = [
            "exec(", "eval(", "compile(", "__import__(", "open(",
            "file(", "input(", "raw_input(", "exit(", "quit(",
            "globals(", "locals(", "vars(", "getattr(", "setattr(",
            "delattr(", "hasattr(", "reload(", "breakpoint(",
        ]

        for call in dangerous_calls:
            if call in code_normalized:
                return False

        # Dangerous dunder attributes (sandbox escape vectors)
        dangerous_attrs = [
            "__builtins__", "__subclasses__", "__bases__", "__class__",
            "__mro__", "__globals__", "__code__", "__import__",
        ]

        for attr in dangerous_attrs:
            if attr in code_normalized:
                return False

        return True

    @staticmethod
    def _apply_rlimits(timeout: int):
        """Return a preexec_fn that caps CPU, memory, file size and process count.

        These are hard, kernel-enforced limits — the real containment layer.
        Returns None on platforms without the resource module (e.g. Windows).
        """
        try:
            import resource
        except ImportError:
            return None

        def _set_limits():
            cpu = max(1, int(timeout) + 1)
            resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
            mem = 256 * 1024 * 1024  # 256 MB address space
            resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
            fsize = 10 * 1024 * 1024  # 10 MB max file write
            resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))
            try:
                resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))  # anti fork-bomb
            except (ValueError, OSError):
                pass

        return _set_limits

    @staticmethod
    def _kill_process_tree(process):
        """Kill the whole process group so orphaned children don't survive a timeout."""
        try:
            if os.name == "posix":
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:
                process.kill()
        except (ProcessLookupError, OSError):
            try:
                process.kill()
            except OSError:
                pass

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

            # Scrub environment so executed code cannot read server secrets/tokens
            safe_env = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1",
                "HOME": str(self.temp_dir),
                "TMPDIR": str(self.temp_dir),
            }

            popen_kwargs = dict(
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.temp_dir,
                env=safe_env,
            )
            # New session/process group so timeout kills the whole tree, not just the parent.
            # rlimits (CPU/memory/file-size/process-count) are a real, OS-enforced boundary —
            # unlike the best-effort source blacklist. Unix only.
            if os.name == "posix":
                popen_kwargs["start_new_session"] = True
                popen_kwargs["preexec_fn"] = self._apply_rlimits(timeout)

            process = subprocess.Popen(
                [sys.executable, "-I", str(temp_file)],
                **popen_kwargs,
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
                result.output = stdout
                result.error_output = stderr
                result.return_code = process.returncode

            except subprocess.TimeoutExpired:
                self._kill_process_tree(process)
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
