#!/usr/bin/env python3
"""
DocsPort Main Entry Point
Starts the DocsPort system with automatic port allocation and configuration.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from config import DocsPortInitializer
from backend.app import DocsPortApp


def main():
    """Main entry point for DocsPort."""

    print("=" * 60)
    print("DOCSPORT - INTELLIGENT DOCUMENTATION & ANALYSIS SYSTEM")
    print("=" * 60)
    print("Features:")
    print("- Automatic port allocation")
    print("- Code editor with syntax highlighting")
    print("- Code analysis and visualization")
    print("- Secure code execution")
    print("- Comment system")
    print("- Mermaid.js flowcharts")
    print("=" * 60)

    try:
        # Initialize DocsPort
        app = DocsPortApp()

        print(f"\nDocsPort running on: http://{app.config.host}:{app.config.port}")
        print(f"API Documentation: http://{app.config.host}:{app.config.port}/api/docs")
        print(f"Instance ID: {app.config.instance_id}")
        print("\nPress Ctrl+C to stop...")

        # Start the server
        app.run()

    except KeyboardInterrupt:
        print("\nDocsPort shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting DocsPort: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
