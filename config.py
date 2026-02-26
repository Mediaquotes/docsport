#!/usr/bin/env python3
"""
DocsPort Configuration Management
Handles configuration, port management, and persistence.
"""

import os
import json
import socket
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class DocsPortConfig:
    """DocsPort configuration."""
    port: int
    host: str = "127.0.0.1"
    debug: bool = False
    data_dir: str = "data"
    frontend_dir: str = "frontend"
    backend_dir: str = "backend"
    instance_id: str = ""
    created_at: str = ""
    last_used: str = ""


class PortManager:
    """Dynamic port management."""

    def __init__(self, config_file: str = ".docsport.json"):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

    def is_port_free(self, port: int, host: str = "127.0.0.1") -> bool:
        """Check if a port is free."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0
        except:
            return False

    def find_free_port(self, start_port: int = 8500, end_port: int = 9500) -> int:
        """Find a free port in the given range."""
        for port in range(start_port, end_port + 1):
            if self.is_port_free(port):
                return port
        raise RuntimeError(f"No free port found between {start_port} and {end_port}")

    def detect_existing_docsport(self) -> Optional[DocsPortConfig]:
        """Detect an existing DocsPort instance."""
        if not self.config_file.exists():
            return None

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            config = DocsPortConfig(**config_data)

            # Check if the instance is still active
            if not self.is_port_free(config.port, config.host):
                if self.is_docsport_instance(config.port, config.host):
                    print(f"Existing DocsPort instance detected on port {config.port}")
                    return config
                else:
                    print(f"Port {config.port} is occupied by another service, finding new port...")
                    return None

        except Exception as e:
            print(f"Error reading configuration: {e}")

        return None

    def is_docsport_instance(self, port: int, host: str = "127.0.0.1") -> bool:
        """Check if a DocsPort instance is running on the port."""
        try:
            import urllib.request
            import urllib.error
            import json

            url = f"http://{host}:{port}/api/health"
            with urllib.request.urlopen(url, timeout=2) as response:
                data = json.loads(response.read().decode())
                return data.get("service") == "DocsPort"
        except:
            return False

    def create_new_config(self) -> DocsPortConfig:
        """Create a new DocsPort configuration."""
        free_port = self.find_free_port()

        config = DocsPortConfig(
            port=free_port,
            instance_id=f"docsport_{free_port}_{int(datetime.now().timestamp())}",
            created_at=datetime.now().isoformat(),
            last_used=datetime.now().isoformat()
        )

        self.save_config(config)
        return config

    def save_config(self, config: DocsPortConfig):
        """Save the configuration."""
        config.last_used = datetime.now().isoformat()

        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(config), f, indent=2, ensure_ascii=False)

    def get_or_create_config(self, preferred_port: int = None) -> DocsPortConfig:
        """Return existing configuration or create a new one.

        Args:
            preferred_port: If set, use this port instead of auto-discovery.
        """
        if preferred_port:
            if not self.is_port_free(preferred_port):
                raise RuntimeError(f"Port {preferred_port} is already in use")
            print(f"Using requested port {preferred_port}")
            config = DocsPortConfig(
                port=preferred_port,
                instance_id=f"docsport_{preferred_port}_{int(datetime.now().timestamp())}",
                created_at=datetime.now().isoformat(),
                last_used=datetime.now().isoformat()
            )
            self.save_config(config)
            return config

        existing_config = self.detect_existing_docsport()

        if existing_config:
            print(f"Existing DocsPort instance detected on port {existing_config.port}")
            return existing_config
        else:
            print("Creating new DocsPort instance...")
            return self.create_new_config()


class DatabaseManager:
    """SQLite Database Manager for DocsPort."""

    def __init__(self, db_path: str = "data/docsport.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def init_database(self):
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Comments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    line_number INTEGER,
                    class_name TEXT,
                    function_name TEXT,
                    method_name TEXT,
                    comment_text TEXT NOT NULL,
                    comment_type TEXT DEFAULT 'general',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Code analysis table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS code_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    line_start INTEGER,
                    line_end INTEGER,
                    content TEXT,
                    dependencies TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Execution history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS execution_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code_content TEXT NOT NULL,
                    execution_type TEXT NOT NULL,
                    output TEXT,
                    error_output TEXT,
                    execution_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    def get_connection(self):
        """Return a database connection."""
        return sqlite3.connect(self.db_path)


class DocsPortInitializer:
    """Main class for DocsPort initialization."""

    def __init__(self):
        self.port_manager = PortManager()
        self.db_manager = DatabaseManager()
        self.config = None

    def initialize(self, preferred_port: int = None) -> DocsPortConfig:
        """Initialize the DocsPort system."""
        print("DocsPort system initializing...")

        # Load or create configuration
        self.config = self.port_manager.get_or_create_config(preferred_port)

        # Initialize database
        self.db_manager.init_database()

        # Create directory structure
        self.create_directory_structure()

        print(f"DocsPort successfully initialized on port {self.config.port}")
        return self.config

    def create_directory_structure(self):
        """Create required runtime directories."""
        for directory in ["data", "logs"]:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def get_status(self) -> Dict[str, Any]:
        """Return current status."""
        if not self.config:
            return {"status": "not_initialized"}

        return {
            "status": "initialized",
            "port": self.config.port,
            "host": self.config.host,
            "instance_id": self.config.instance_id,
            "created_at": self.config.created_at,
            "last_used": self.config.last_used,
            "database_path": str(self.db_manager.db_path),
            "config_file": str(self.port_manager.config_file)
        }


def main():
    """Main function for DocsPort initialization."""
    initializer = DocsPortInitializer()
    config = initializer.initialize()

    print("\n" + "="*50)
    print("DOCSPORT SYSTEM READY")
    print("="*50)
    print(f"Port: {config.port}")
    print(f"Host: {config.host}")
    print(f"Instance ID: {config.instance_id}")
    print(f"URL: http://{config.host}:{config.port}")
    print("="*50)

    return config

if __name__ == "__main__":
    main()
