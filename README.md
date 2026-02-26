# DocsPort

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**Intelligent Python code documentation and analysis tool** with a built-in editor, AST-based analysis, Mermaid.js visualizations, secure code execution, and multilingual UI.

![DocsPort Screenshot](https://via.placeholder.com/800x400?text=DocsPort+Screenshot)

## Features

- **Code Editor** - Monaco-powered editor with syntax highlighting, autocomplete, and keyboard shortcuts (Ctrl+S, F5)
- **AST Code Analysis** - Automatic extraction of classes, functions, methods, dependencies, and call graphs
- **Visualization** - Mermaid.js flowcharts and interactive D3.js node-link diagrams
- **Secure Execution** - Run Python code in an isolated sandbox with timeout protection
- **Comment System** - Annotate code with comments tied to files, lines, and elements (persisted in SQLite)
- **Code Metrics** - Cyclomatic complexity, maintainability index, comment ratio, and more
- **Multilingual UI** - English (default), German, and Spanish — easily extensible
- **Auto Port Discovery** - Automatically finds a free port (8000-9000) on startup

## Installation

**Prerequisites:** Python 3.9 or higher. No installer needed — just clone or download.

```bash
# Option A: Clone with git
git clone https://github.com/mediaquotes/docsport.git

# Option B: Download ZIP from GitHub and extract it
```

```bash
cd docsport
pip install -r requirements.txt
```

On Windows you can also double-click `start_docsport.bat`.

## Usage

```bash
# Start with automatic port discovery
python main.py

# Start on a specific port
python main.py --port 9090
```

You can also set the port via environment variable:

```bash
export DOCSPORT_PORT=9090   # Linux/macOS
set DOCSPORT_PORT=9090      # Windows
python main.py
```

**Port priority:** `--port` flag > `DOCSPORT_PORT` env var > auto-discovery (scans 8500–9500).

DocsPort prints the URL when it starts:

```
DocsPort running on: http://127.0.0.1:8500
```

Open that URL in your browser. You'll see a web UI where you can:

1. **Browse & edit** Python files from the current working directory
2. **Analyze** code structure (classes, functions, dependencies)
3. **Visualize** call graphs and flowcharts
4. **Execute** Python code in a sandboxed environment
5. **Annotate** code with comments

To analyze a different project, run `python /path/to/docsport/main.py` from that project's directory.

## Project Structure

```
docsport/
├── main.py                  # Entry point
├── config.py                # Configuration & port management
├── __init__.py              # Package metadata
├── requirements.txt         # Python dependencies
├── start_docsport.bat       # Windows launcher
├── backend/
│   ├── app.py               # FastAPI application & routes
│   ├── analysis.py          # AST-based code analysis
│   ├── execution.py         # Secure code execution
│   ├── visualization.py     # Mermaid.js flowchart generation
│   ├── visual_analyzer.py   # D3.js visualization data
│   ├── i18n.py              # Backend i18n helper
│   └── locales/             # Backend translation files
│       ├── en.json
│       ├── de.json
│       └── es.json
├── frontend/
│   ├── locales/             # Frontend translation files
│   │   ├── en.json
│   │   ├── de.json
│   │   └── es.json
│   ├── static/
│   │   ├── css/main.css     # Stylesheet
│   │   └── js/
│   │       ├── main.js      # Main application logic
│   │       └── i18n.js      # Frontend i18n helper
│   └── templates/
│       └── index.html       # Single-page HTML template
└── data/                    # Auto-created: SQLite DB & config
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/files` | List Python files |
| GET | `/api/files/{path}` | Read file content |
| POST | `/api/files/{path}` | Save file content |
| POST | `/api/analyze` | Analyze a file |
| GET | `/api/analyze/project` | Analyze entire project |
| GET | `/api/visualization/flowchart` | Generate flowchart |
| POST | `/api/visualization/analyze` | Visual analysis data |
| GET | `/api/metrics/{path}` | Code metrics |
| POST | `/api/execute` | Execute code |
| GET | `/api/execution/history` | Execution history |
| POST | `/api/comments` | Create comment |
| GET | `/api/comments/{path}` | Get comments for file |
| DELETE | `/api/comments/{id}` | Delete comment |

Full interactive docs available at `/api/docs` (Swagger UI).

## Language Support

DocsPort ships with three languages. Switch via the dropdown in the header.

| Code | Language |
|------|----------|
| `en` | English (default) |
| `de` | German |
| `es` | Spanish |

To add a new language, see [CONTRIBUTING.md](CONTRIBUTING.md#adding-translations).

## Tech Stack

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **Frontend**: Vanilla JavaScript + [Monaco Editor](https://microsoft.github.io/monaco-editor/)
- **Visualization**: [Mermaid.js](https://mermaid.js.org/) + [D3.js](https://d3js.org/)
- **Database**: SQLite (zero config)
- **Analysis**: Python `ast` module

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE) - Copyright (c) 2025 MediaQuotes
