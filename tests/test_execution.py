"""Tests for code execution sandbox and blacklist."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.execution import SecureCodeExecutor


def run_async(coro):
    """Helper to run async code in tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


def test_safe_code_executes(db_manager):
    executor = SecureCodeExecutor(db_manager)
    result = run_async(executor.execute_code('print("hello")'))

    assert result["success"] is True
    assert "hello" in result["output"]


def test_math_code_executes(db_manager):
    executor = SecureCodeExecutor(db_manager)
    result = run_async(executor.execute_code('print(2 + 3)'))

    assert result["success"] is True
    assert "5" in result["output"]


def test_import_os_blocked(db_manager):
    executor = SecureCodeExecutor(db_manager)
    result = run_async(executor.execute_code('import os'))

    assert result["success"] is False
    assert "forbidden" in result["error_output"].lower()


def test_import_subprocess_blocked(db_manager):
    executor = SecureCodeExecutor(db_manager)
    result = run_async(executor.execute_code('import subprocess'))

    assert result["success"] is False


def test_exec_blocked(db_manager):
    executor = SecureCodeExecutor(db_manager)
    result = run_async(executor.execute_code('exec("print(1)")'))

    assert result["success"] is False


def test_eval_blocked(db_manager):
    executor = SecureCodeExecutor(db_manager)
    result = run_async(executor.execute_code('eval("1+1")'))

    assert result["success"] is False


def test_open_blocked(db_manager):
    executor = SecureCodeExecutor(db_manager)
    result = run_async(executor.execute_code('open("/etc/passwd")'))

    assert result["success"] is False


def test_dunder_builtins_blocked(db_manager):
    executor = SecureCodeExecutor(db_manager)
    result = run_async(executor.execute_code('print(__builtins__)'))

    assert result["success"] is False


def test_dunder_subclasses_blocked(db_manager):
    executor = SecureCodeExecutor(db_manager)
    result = run_async(executor.execute_code('().__class__.__subclasses__()'))

    assert result["success"] is False


def test_import_with_extra_spaces_blocked(db_manager):
    executor = SecureCodeExecutor(db_manager)
    result = run_async(executor.execute_code('import  os'))

    assert result["success"] is False


def test_from_import_blocked(db_manager):
    executor = SecureCodeExecutor(db_manager)
    result = run_async(executor.execute_code('from os import system'))

    assert result["success"] is False


def test_breakpoint_blocked(db_manager):
    executor = SecureCodeExecutor(db_manager)
    result = run_async(executor.execute_code('breakpoint()'))

    assert result["success"] is False


def test_timeout_enforced(db_manager):
    executor = SecureCodeExecutor(db_manager)
    # Use a very short timeout
    result = run_async(executor.execute_code(
        'import time\ntime.sleep(10)',
        timeout=2
    ))

    # Should fail because time is not in blacklist but the timeout should trigger
    # Actually 'import time' is allowed, so this tests the timeout mechanism
    assert result["timeout_occurred"] is True or result["success"] is False
