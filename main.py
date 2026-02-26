#!/usr/bin/env python3
"""
DocsPort Main Entry Point
Starts the DocsPort system with automatic port allocation and configuration.
"""

import sys
import os
import argparse
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from config import DocsPortInitializer
from backend.app import DocsPortApp


def main():
    """Main entry point for DocsPort."""
    parser = argparse.ArgumentParser(description="DocsPort - Intelligent Documentation & Analysis System")
    parser.add_argument("-p", "--port", type=int, default=None,
                        help="Port to run on (default: auto-detect free port)")
    args = parser.parse_args()

    # Priority: CLI arg > env var > auto-discovery
    port = args.port or int(os.environ.get("DOCSPORT_PORT", 0)) or None

    print("=" * 60)
    print("DOCSPORT - INTELLIGENT DOCUMENTATION & ANALYSIS SYSTEM")
    print("=" * 60)

    try:
        app = DocsPortApp(port=port)

        print(f"\nDocsPort running on: http://{app.config.host}:{app.config.port}")
        print(f"API Documentation: http://{app.config.host}:{app.config.port}/api/docs")
        print("\nPress Ctrl+C to stop...")

        app.run()

    except KeyboardInterrupt:
        print("\nDocsPort shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting DocsPort: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
