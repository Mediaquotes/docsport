#!/usr/bin/env python3
"""
DocsPort Backend - FastAPI Application
Main application for the DocsPort backend with code analysis and execution features.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# FastAPI imports
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

# DocsPort imports
sys.path.append(str(Path(__file__).parent.parent))
from backend.analysis import PythonCodeAnalyzer
from backend.execution import SecureCodeExecutor
from backend.i18n import detect_locale, t
from backend.visual_analyzer import VisualCodeAnalyzer
from config import DatabaseManager, DocsPortInitializer


# Pydantic Models
class CommentRequest(BaseModel):
    file_path: str
    line_number: Optional[int] = None
    class_name: Optional[str] = None
    function_name: Optional[str] = None
    method_name: Optional[str] = None
    comment_text: str
    comment_type: str = "general"

class CodeExecutionRequest(BaseModel):
    code: str
    execution_type: str = "python"
    timeout: int = Field(default=30, ge=1, le=60)

class AnalysisRequest(BaseModel):
    file_path: str
    force_refresh: bool = False

class DocsPortApp:
    """DocsPort main application."""

    def __init__(self, port: int = None):
        self.initializer = DocsPortInitializer()
        self.config = self.initializer.initialize(preferred_port=port)
        self.db_manager = DatabaseManager()
        self.app = self.create_app()

    def _locale(self, request: Request) -> str:
        """Detect locale from request Accept-Language header."""
        return detect_locale(request.headers.get("accept-language"))

    def _safe_path(self, file_path: str) -> Path:
        """Resolve a file path and ensure it stays within the project directory.

        Raises HTTPException 403 if the path escapes the project root.
        """
        project_root = Path.cwd().resolve()
        resolved = (project_root / file_path).resolve()
        if not str(resolved).startswith(str(project_root)):
            raise HTTPException(status_code=403, detail="Access denied: path outside project directory")
        return resolved

    def create_app(self) -> FastAPI:
        """Create the FastAPI application."""
        app = FastAPI(
            title="DocsPort API",
            description="Intelligent Documentation & Analysis System",
            version="2.0.0",
            docs_url="/api/docs",
            redoc_url="/api/redoc"
        )

        # CORS Middleware — restrict to localhost only
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Static Files
        frontend_path = Path(__file__).parent.parent / "frontend"
        if frontend_path.exists():
            app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")
            # Serve locale files
            locales_path = frontend_path / "locales"
            if locales_path.exists():
                app.mount("/locales", StaticFiles(directory=str(locales_path)), name="locales")

        # Templates
        templates = Jinja2Templates(directory=str(frontend_path / "templates"))

        # Routes
        self.setup_routes(app, templates)

        return app

    def setup_routes(self, app: FastAPI, templates: Jinja2Templates):
        """Set up all API routes."""

        @app.get("/")
        async def root(request: Request):
            """Main page."""
            return templates.TemplateResponse("index.html", {
                "request": request,
                "config": self.config
            })

        @app.get("/api/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "service": "DocsPort",
                "version": "2.0.0",
                "port": self.config.port,
                "timestamp": datetime.now().isoformat()
            }

        @app.get("/api/config")
        async def get_config():
            """Return current configuration."""
            return self.initializer.get_status()

        # Comments API
        @app.post("/api/comments")
        async def create_comment(comment: CommentRequest, request: Request):
            """Create a new comment."""
            locale = self._locale(request)
            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO comments (file_path, line_number, class_name, function_name,
                                            method_name, comment_text, comment_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        comment.file_path,
                        comment.line_number,
                        comment.class_name,
                        comment.function_name,
                        comment.method_name,
                        comment.comment_text,
                        comment.comment_type
                    ))
                    comment_id = cursor.lastrowid
                    conn.commit()

                return {"id": comment_id, "message": t("comment_created", locale)}

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/comments/{file_path:path}")
        async def get_comments(file_path: str):
            """Return comments for a file."""
            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id, file_path, line_number, class_name, function_name,
                               method_name, comment_text, comment_type, created_at, updated_at
                        FROM comments
                        WHERE file_path = ?
                        ORDER BY line_number, created_at
                    """, (file_path,))

                    comments = []
                    for row in cursor.fetchall():
                        comments.append({
                            "id": row[0],
                            "file_path": row[1],
                            "line_number": row[2],
                            "class_name": row[3],
                            "function_name": row[4],
                            "method_name": row[5],
                            "comment_text": row[6],
                            "comment_type": row[7],
                            "created_at": row[8],
                            "updated_at": row[9]
                        })

                return {"comments": comments}

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.delete("/api/comments/{comment_id}")
        async def delete_comment(comment_id: int, request: Request):
            """Delete a comment."""
            locale = self._locale(request)
            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
                    conn.commit()

                return {"message": t("comment_deleted", locale)}

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Code Analysis API
        @app.post("/api/analyze")
        async def analyze_file(request_body: AnalysisRequest):
            """Analyze a Python file."""
            try:
                safe = self._safe_path(request_body.file_path)
                analyzer = PythonCodeAnalyzer(self.db_manager)
                analysis = analyzer.analyze_file(str(safe), request_body.force_refresh)
                return analysis

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/analyze/project")
        async def analyze_project():
            """Analyze all Python files in the project."""
            try:
                analyzer = PythonCodeAnalyzer(self.db_manager)
                analysis = analyzer.analyze_project()
                return analysis

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/visualization/flowchart")
        async def get_flowchart():
            """Generate a flowchart of the code structure."""
            try:
                current_dir = Path.cwd()
                py_files = list(current_dir.rglob("*.py"))

                if not py_files:
                    return {"error": t("no_python_files")}

                target_file = None
                for f in py_files:
                    if f.name == "main.py":
                        target_file = f
                        break
                if not target_file:
                    target_file = py_files[0]

                visual_analyzer = VisualCodeAnalyzer(self.db_manager)
                flowchart = visual_analyzer.analyze_for_visualization(str(target_file))
                return flowchart

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/api/visualization/analyze")
        async def analyze_for_visualization(request_body: AnalysisRequest):
            """Analyze a file for visual representation."""
            try:
                safe = self._safe_path(request_body.file_path)
                visual_analyzer = VisualCodeAnalyzer(self.db_manager)
                analysis = visual_analyzer.analyze_for_visualization(str(safe))
                return analysis

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/metrics/{file_path:path}")
        async def get_code_metrics(file_path: str):
            """Return advanced code metrics."""
            try:
                safe = self._safe_path(file_path)
                visual_analyzer = VisualCodeAnalyzer(self.db_manager)
                metrics = visual_analyzer.get_code_metrics(str(safe))
                return metrics

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Code Execution API
        @app.post("/api/execute")
        async def execute_code(request_body: CodeExecutionRequest):
            """Execute code."""
            try:
                executor = SecureCodeExecutor(self.db_manager)
                result = await executor.execute_code(
                    request_body.code,
                    request_body.execution_type,
                    request_body.timeout
                )
                return result

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/execution/history")
        async def get_execution_history():
            """Return execution history."""
            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id, code_content, execution_type, output, error_output,
                               execution_time, created_at
                        FROM execution_history
                        ORDER BY created_at DESC
                        LIMIT 50
                    """)

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

                return {"history": history}

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # File Management API
        @app.get("/api/files")
        async def list_files():
            """List all Python files."""
            try:
                files = []
                current_dir = Path.cwd()

                for py_file in current_dir.rglob("*.py"):
                    if not any(part.startswith('.') for part in py_file.parts):
                        files.append({
                            "path": str(py_file.relative_to(current_dir)),
                            "name": py_file.name,
                            "size": py_file.stat().st_size,
                            "modified": datetime.fromtimestamp(py_file.stat().st_mtime).isoformat()
                        })

                return {"files": sorted(files, key=lambda x: x["path"])}

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/files/{file_path:path}")
        async def get_file_content(file_path: str, request: Request):
            """Return the content of a file."""
            locale = self._locale(request)
            try:
                file_path_obj = self._safe_path(file_path)

                if not file_path_obj.exists():
                    raise HTTPException(status_code=404, detail=t("file_not_found", locale))

                with open(file_path_obj, 'r', encoding='utf-8') as f:
                    content = f.read()

                return {
                    "content": content,
                    "path": file_path,
                    "size": len(content),
                    "lines": len(content.splitlines())
                }

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/api/files/{file_path:path}")
        async def save_file_content(file_path: str, request: Request, content: str = Form(...)):
            """Save file content."""
            locale = self._locale(request)
            try:
                file_path_obj = self._safe_path(file_path)

                # Create backup
                if file_path_obj.exists():
                    backup_path = file_path_obj.with_suffix(f".backup_{int(datetime.now().timestamp())}.py")
                    file_path_obj.rename(backup_path)

                # Save new file
                with open(file_path_obj, 'w', encoding='utf-8') as f:
                    f.write(content)

                return {"message": t("file_saved", locale)}

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    def run(self):
        """Start the DocsPort server."""
        import uvicorn

        print(f"DocsPort starting on http://{self.config.host}:{self.config.port}")

        uvicorn.run(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info"
        )


def main():
    """Main entry point."""
    app = DocsPortApp()
    app.run()

if __name__ == "__main__":
    main()
